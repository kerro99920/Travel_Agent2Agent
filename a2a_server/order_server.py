#!/usr/bin/env python3
"""
订票代理 A2A 服务器
order_server.py

作用：对用户的订票需求进行分析，先调用票务Agent服务器查询余票信息，
      如果有余票则完成订票，否则让用户修改需求。

项目定位：执行层，接收路由任务，查询余票并完成订票。

核心功能：
1. 解析用户订票意图，提取关键信息
2. 调用票务Agent服务器（ticket_server）查询余票
3. 根据余票信息调用订票MCP服务器完成订票
4. 返回订票结果或引导用户修改需求
"""

import json
import asyncio
import uuid
import httpx
from datetime import datetime
from typing import Optional, Dict, Any, List

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from python_a2a import A2AServer, run_server, AgentCard, AgentSkill, TaskStatus, TaskState
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
import pytz

from SmartVoyage.config import Config
from SmartVoyage.create_logger import logger

conf = Config()

# ==================== 配置区域 ====================
TZ = pytz.timezone('Asia/Shanghai')

# 票务Agent服务器地址（用于查询余票）
TICKET_AGENT_URL = "http://127.0.0.1:5006"

# 订票MCP服务器地址（用于创建订单）
ORDER_MCP_URL = "http://127.0.0.1:8002/mcp"

# 初始化LLM
llm = ChatOpenAI(
    model=conf.model_name,
    base_url=conf.base_url,
    api_key=conf.api_key,
    temperature=0.1
)

# ==================== 意图解析提示词 ====================
INTENT_PROMPT = ChatPromptTemplate.from_template(
    """
你是一个订票意图解析器，需要从用户输入中提取订票相关信息。

【当前日期】{current_date}

【用户输入】{user_input}

【解析规则】
1. 识别订票类型：
   - 火车票/高铁票 → "train"
   - 机票/飞机票 → "flight"  
   - 演唱会票 → "concert"

2. 提取必要信息：
   - 火车票/机票：出发城市、到达城市、日期、座位类型（可选）
   - 演唱会票：城市、艺人、日期、票类型（可选）

3. 提取联系人信息：姓名、电话、身份证号

4. 如果用户提供了票务ID，直接使用

【输出格式】
如果信息足够查询，输出JSON：
{{
    "status": "ready",
    "ticket_type": "train/flight/concert",
    "query_params": {{
        "departure_city": "出发城市（火车/机票）",
        "arrival_city": "到达城市（火车/机票）",
        "city": "城市（演唱会）",
        "artist": "艺人（演唱会）",
        "date": "YYYY-MM-DD",
        "seat_type": "座位类型（可选）",
        "ticket_type": "票类型（演唱会，可选）"
    }},
    "ticket_id": 票务ID（如果用户指定）,
    "quantity": 数量（默认1）,
    "contact": {{
        "name": "联系人姓名",
        "phone": "联系人电话",
        "id_card": "身份证号（可选）"
    }}
}}

如果缺少必要信息，输出：
{{
    "status": "input_required",
    "message": "需要补充的具体信息",
    "missing_fields": ["缺少的字段列表"]
}}

【示例】
用户：订一张明天北京到上海的高铁票，二等座，张三，13800138000
输出：
{{
    "status": "ready",
    "ticket_type": "train",
    "query_params": {{
        "departure_city": "北京",
        "arrival_city": "上海",
        "date": "2025-01-19",
        "seat_type": "二等座"
    }},
    "quantity": 1,
    "contact": {{
        "name": "张三",
        "phone": "13800138000"
    }}
}}

用户：买票务ID 123的火车票，2张
输出：
{{
    "status": "ready",
    "ticket_type": "train",
    "ticket_id": 123,
    "quantity": 2,
    "contact": {{}}
}}

用户：订火车票
输出：
{{
    "status": "input_required",
    "message": "请提供以下信息：出发城市、到达城市、出行日期、联系人姓名和电话",
    "missing_fields": ["departure_city", "arrival_city", "date", "contact_name", "contact_phone"]
}}
"""
)


# ==================== 票务Agent客户端 ====================
class TicketAgentClient:
    """票务Agent客户端，用于调用ticket_server查询余票"""

    def __init__(self, agent_url: str):
        self.agent_url = agent_url

    async def query_tickets(self, query_text: str) -> Dict[str, Any]:
        """
        调用票务Agent查询余票

        Args:
            query_text: 自然语言查询文本

        Returns:
            查询结果
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # 构造A2A请求
                request_data = {
                    "jsonrpc": "2.0",
                    "method": "tasks/send",
                    "params": {
                        "message": {
                            "role": "user",
                            "content": query_text
                        }
                    },
                    "id": str(uuid.uuid4())
                }

                response = await client.post(
                    f"{self.agent_url}/a2a",
                    json=request_data,
                    headers={"Content-Type": "application/json"}
                )

                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"票务Agent响应: {result}")

                    # 提取结果
                    if "result" in result:
                        task_result = result["result"]
                        if isinstance(task_result, dict):
                            message = task_result.get("message", {})
                            content = message.get("content", "") if isinstance(message, dict) else str(message)
                            state = task_result.get("state", "")
                            return {
                                "status": "success" if state == "completed" else state,
                                "content": content
                            }

                    return {"status": "error", "message": "无法解析票务Agent响应"}
                else:
                    return {"status": "error", "message": f"HTTP错误: {response.status_code}"}

        except Exception as e:
            logger.error(f"调用票务Agent失败: {e}")
            return {"status": "error", "message": str(e)}


# ==================== 订票MCP客户端 ====================
class OrderMCPClient:
    """订票MCP客户端，用于创建订单"""

    def __init__(self, mcp_url: str):
        self.mcp_url = mcp_url

    async def create_order(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        调用订票MCP创建订单

        Args:
            order_data: 订单数据

        Returns:
            创建结果
        """
        try:
            async with streamablehttp_client(self.mcp_url) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    logger.info(f"创建订单: {order_data}")

                    result = await session.call_tool("create_order", order_data)

                    if hasattr(result, 'content') and result.content:
                        text = result.content[0].text
                        return {"status": "success", "data": text}
                    else:
                        return {"status": "success", "data": str(result)}

        except Exception as e:
            logger.error(f"创建订单失败: {e}")
            return {"status": "error", "message": str(e)}

    async def query_order(self, order_no: str) -> Dict[str, Any]:
        """查询订单状态"""
        try:
            async with streamablehttp_client(self.mcp_url) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool("query_order", {"order_no": order_no})

                    if hasattr(result, 'content') and result.content:
                        return {"status": "success", "data": result.content[0].text}
                    return {"status": "success", "data": str(result)}

        except Exception as e:
            logger.error(f"查询订单失败: {e}")
            return {"status": "error", "message": str(e)}


# ==================== Agent卡片定义 ====================
agent_card = AgentCard(
    name="OrderBookingAgent",
    description="订票代理，支持火车票、机票、演唱会票的在线预订",
    url="http://localhost:5007",
    version="1.0.0",
    capabilities={
        "streaming": False,
        "pushNotifications": False
    },
    skills=[
        AgentSkill(
            name="book_train_ticket",
            description="预订火车票/高铁票",
            examples=[
                "订一张明天北京到上海的高铁，二等座，张三，13800138000",
                "买票务ID 123的火车票",
                "预订G1234次列车"
            ]
        ),
        AgentSkill(
            name="book_flight_ticket",
            description="预订机票/航班",
            examples=[
                "订1月20日上海到广州的机票，经济舱，李四，13900139000",
                "买票务ID 456的机票，2张"
            ]
        ),
        AgentSkill(
            name="book_concert_ticket",
            description="预订演唱会门票",
            examples=[
                "订周杰伦北京演唱会的内场票，王五，13700137000",
                "买票务ID 789的演唱会票"
            ]
        )
    ]
)


# ==================== 订票服务器 ====================
class OrderBookingServer(A2AServer):
    """订票代理A2A服务器"""

    def __init__(self):
        super().__init__(agent_card=agent_card)
        self.llm = llm
        self.intent_prompt = INTENT_PROMPT
        self.ticket_client = TicketAgentClient(TICKET_AGENT_URL)
        self.order_client = OrderMCPClient(ORDER_MCP_URL)
        logger.info("OrderBookingServer 初始化完成")

    def parse_intent(self, user_input: str) -> Dict[str, Any]:
        """
        解析用户订票意图

        Args:
            user_input: 用户输入

        Returns:
            解析后的意图信息
        """
        try:
            chain = self.intent_prompt | self.llm
            current_date = datetime.now(TZ).strftime('%Y-%m-%d')

            output = chain.invoke({
                "current_date": current_date,
                "user_input": user_input
            }).content.strip()

            logger.info(f"意图解析原始输出: {output}")

            # 清理markdown代码块
            if "```json" in output:
                output = output.split("```json")[1].split("```")[0]
            elif "```" in output:
                output = output.split("```")[1].split("```")[0]

            return json.loads(output.strip())

        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}")
            return {
                "status": "input_required",
                "message": "无法理解您的订票需求，请重新描述。"
            }
        except Exception as e:
            logger.error(f"意图解析失败: {e}")
            return {
                "status": "input_required",
                "message": f"处理失败: {str(e)}"
            }

    def build_query_text(self, intent: Dict[str, Any]) -> str:
        """
        根据意图构建票务查询文本

        Args:
            intent: 解析后的意图

        Returns:
            查询文本
        """
        ticket_type = intent.get("ticket_type", "")
        params = intent.get("query_params", {})

        if ticket_type == "train":
            parts = ["查询火车票"]
            if params.get("date"):
                parts.append(params["date"])
            if params.get("departure_city"):
                parts.append(params["departure_city"])
            if params.get("arrival_city"):
                parts.append(f"到{params['arrival_city']}")
            if params.get("seat_type"):
                parts.append(params["seat_type"])
            return ' '.join(parts)

        elif ticket_type == "flight":
            parts = ["查询机票"]
            if params.get("date"):
                parts.append(params["date"])
            if params.get("departure_city"):
                parts.append(params["departure_city"])
            if params.get("arrival_city"):
                parts.append(f"到{params['arrival_city']}")
            if params.get("cabin_type"):
                parts.append(params["cabin_type"])
            return ' '.join(parts)

        elif ticket_type == "concert":
            parts = ["查询演唱会"]
            if params.get("artist"):
                parts.append(params["artist"])
            if params.get("city"):
                parts.append(params["city"])
            if params.get("date"):
                parts.append(params["date"])
            return ' '.join(parts)

        return "查询票务"

    def extract_tickets_from_response(self, content: str) -> List[Dict[str, Any]]:
        """
        从票务Agent响应中提取票务列表

        Args:
            content: 票务Agent返回的内容

        Returns:
            票务列表
        """
        tickets = []

        # 尝试解析JSON
        try:
            data = json.loads(content)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                return [data]
        except json.JSONDecodeError:
            pass

        # 从文本中提取票务ID
        import re
        id_pattern = r'票务ID[：:]\s*(\d+)'
        matches = re.findall(id_pattern, content)

        for ticket_id in matches:
            tickets.append({"id": int(ticket_id)})

        return tickets

    def format_booking_result(self, result: Dict[str, Any]) -> str:
        """格式化订票结果"""
        if result.get("status") == "success":
            data = result.get("data", {})
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except:
                    return f"✅ 订票成功！\n{data}"

            lines = ["✅ 订票成功！\n"]
            lines.append(f"📋 订单号: {data.get('order_no', 'N/A')}")
            lines.append(f"💰 总价: ¥{data.get('total_price', 'N/A')}")
            lines.append(f"🎫 数量: {data.get('quantity', 1)}张")
            lines.append(f"\n⏰ 请在30分钟内完成支付")
            return '\n'.join(lines)
        else:
            return f"❌ 订票失败: {result.get('message', '未知错误')}"

    async def handle_task(self, task) -> TaskStatus:
        """
        处理A2A任务

        流程：
        1. 解析用户订票意图
        2. 调用票务Agent查询余票
        3. 检查是否有余票
        4. 调用订票MCP创建订单
        5. 返回结果
        """
        try:
            # 1. 提取用户输入
            user_input = self._extract_user_input(task)

            if not user_input:
                return TaskStatus(
                    state=TaskState.INPUT_REQUIRED,
                    message={
                        "role": "assistant",
                        "content": "请输入您的订票需求，例如：订一张明天北京到上海的高铁票，二等座，张三，13800138000"
                    }
                )

            logger.info(f"收到订票请求: {user_input}")

            # 2. 解析意图
            intent = self.parse_intent(user_input)
            logger.info(f"解析意图: {intent}")

            # 3. 检查是否需要补充信息
            if intent.get("status") == "input_required":
                return TaskStatus(
                    state=TaskState.INPUT_REQUIRED,
                    message={
                        "role": "assistant",
                        "content": intent.get("message", "请提供更多订票信息")
                    }
                )

            # 4. 检查联系人信息
            contact = intent.get("contact", {})
            if not contact.get("name") or not contact.get("phone"):
                return TaskStatus(
                    state=TaskState.INPUT_REQUIRED,
                    message={
                        "role": "assistant",
                        "content": "请提供联系人姓名和手机号码，例如：张三，13800138000"
                    }
                )

            # 5. 如果有票务ID，直接下单
            ticket_id = intent.get("ticket_id")
            if ticket_id:
                logger.info(f"使用指定票务ID下单: {ticket_id}")

                order_data = {
                    "ticket_type": intent.get("ticket_type", "train"),
                    "ticket_id": ticket_id,
                    "quantity": intent.get("quantity", 1),
                    "contact_name": contact.get("name", ""),
                    "contact_phone": contact.get("phone", ""),
                    "contact_id_card": contact.get("id_card", "")
                }

                order_result = await self.order_client.create_order(order_data)
                formatted = self.format_booking_result(order_result)

                return TaskStatus(
                    state=TaskState.COMPLETED if order_result.get("status") == "success" else TaskState.FAILED,
                    message={"role": "assistant", "content": formatted}
                )

            # 6. 调用票务Agent查询余票
            query_text = self.build_query_text(intent)
            logger.info(f"查询余票: {query_text}")

            ticket_result = await self.ticket_client.query_tickets(query_text)
            logger.info(f"余票查询结果: {ticket_result}")

            if ticket_result.get("status") == "error":
                return TaskStatus(
                    state=TaskState.FAILED,
                    message={
                        "role": "assistant",
                        "content": f"查询余票失败: {ticket_result.get('message')}"
                    }
                )

            # 7. 检查余票
            content = ticket_result.get("content", "")

            if "未找到" in content or "没有" in content:
                return TaskStatus(
                    state=TaskState.INPUT_REQUIRED,
                    message={
                        "role": "assistant",
                        "content": f"😔 {content}\n\n请调整您的出行计划：\n- 尝试其他日期\n- 尝试其他座位类型\n- 尝试其他车次/航班"
                    }
                )

            # 8. 提取票务信息
            tickets = self.extract_tickets_from_response(content)

            if not tickets:
                # 返回查询结果，让用户选择
                return TaskStatus(
                    state=TaskState.INPUT_REQUIRED,
                    message={
                        "role": "assistant",
                        "content": f"查询到以下票务信息：\n\n{content}\n\n请提供您要预订的票务ID，例如：订票务ID 123"
                    }
                )

            # 9. 如果只有一个选择，自动下单；否则让用户选择
            if len(tickets) == 1:
                ticket = tickets[0]
                order_data = {
                    "ticket_type": intent.get("ticket_type", "train"),
                    "ticket_id": ticket.get("id"),
                    "quantity": intent.get("quantity", 1),
                    "contact_name": contact.get("name", ""),
                    "contact_phone": contact.get("phone", ""),
                    "contact_id_card": contact.get("id_card", "")
                }

                order_result = await self.order_client.create_order(order_data)
                formatted = self.format_booking_result(order_result)

                return TaskStatus(
                    state=TaskState.COMPLETED if order_result.get("status") == "success" else TaskState.FAILED,
                    message={"role": "assistant", "content": formatted}
                )
            else:
                # 多个选择，让用户指定
                return TaskStatus(
                    state=TaskState.INPUT_REQUIRED,
                    message={
                        "role": "assistant",
                        "content": f"查询到多个票务选项：\n\n{content}\n\n请指定您要预订的票务ID，例如：订票务ID 123"
                    }
                )

        except Exception as e:
            logger.error(f"处理订票任务失败: {e}", exc_info=True)
            return TaskStatus(
                state=TaskState.FAILED,
                message={
                    "role": "assistant",
                    "content": f"处理订票请求时发生错误: {str(e)}"
                }
            )

    def _extract_user_input(self, task) -> str:
        """从任务中提取用户输入"""
        if hasattr(task, 'message') and task.message:
            if hasattr(task.message, 'content'):
                content = task.message.content
                if isinstance(content, list):
                    for item in content:
                        if hasattr(item, 'text'):
                            return item.text
                        elif isinstance(item, dict) and 'text' in item:
                            return item['text']
                elif isinstance(content, str):
                    return content
            elif isinstance(task.message, str):
                return task.message
        return ""


# ==================== 主函数 ====================
def main():
    """启动订票服务器"""
    print("=" * 60)
    print("🎫 订票代理 A2A 服务器")
    print("=" * 60)
    print(f"服务地址:     {agent_card.url}")
    print(f"票务Agent:    {TICKET_AGENT_URL}")
    print(f"订票MCP:      {ORDER_MCP_URL}")
    print("=" * 60)
    print("\n订票示例：")
    print("  🚄 订一张明天北京到上海的高铁，二等座，张三，13800138000")
    print("  ✈️ 买1月20日上海到广州的机票，经济舱，李四，13900139000")
    print("  🎤 订周杰伦北京演唱会内场票，王五，13700137000")
    print("  🎫 订票务ID 123，2张，赵六，13600136000")
    print("=" * 60)

    server = OrderBookingServer()

    try:
        run_server(server, host="0.0.0.0", port=5007)
    except KeyboardInterrupt:
        print("\n服务器已停止")
    except Exception as e:
        logger.error(f"服务器启动失败: {e}")
        raise


if __name__ == "__main__":
    main()