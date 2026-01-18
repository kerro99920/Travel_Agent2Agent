#!/usr/bin/env python3
"""
票务代理 A2A 服务器
ticket_server.py

作用：处理用户自然语言查询，转为 SQL 调用 MCP，提升智能性，支持追问和默认值。
项目定位：执行层，接收路由任务，生成 SQL 调用 MCP，返回 artifacts 给客户端。

核心功能：
1. 初始化 LLM 和 MCP 客户端
2. 生成 SQL，提取代码块，调用 MCP
3. 解析 JSON 结果，返回格式化文本
"""

import json
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any

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

# 票务MCP服务器地址
TICKET_MCP_URL = "http://127.0.0.1:8001/mcp"

# 初始化LLM
llm = ChatOpenAI(
    model=conf.model_name,
    base_url=conf.base_url,
    api_key=conf.api_key,
    temperature=0.1
)

# ==================== 数据表 Schema ====================
TABLE_SCHEMA = """
-- 火车票表
CREATE TABLE train_tickets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    departure_city VARCHAR(50) NOT NULL COMMENT '出发城市',
    arrival_city VARCHAR(50) NOT NULL COMMENT '到达城市',
    departure_time DATETIME NOT NULL COMMENT '出发时间',
    arrival_time DATETIME NOT NULL COMMENT '到达时间',
    train_number VARCHAR(20) NOT NULL COMMENT '车次号',
    seat_type VARCHAR(20) NOT NULL COMMENT '座位类型（二等座/一等座/商务座）',
    total_seats INT NOT NULL COMMENT '总座位数',
    remaining_seats INT NOT NULL COMMENT '剩余座位数',
    price DECIMAL(10,2) NOT NULL COMMENT '票价'
);

-- 机票表
CREATE TABLE flight_tickets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    departure_city VARCHAR(50) NOT NULL COMMENT '出发城市',
    arrival_city VARCHAR(50) NOT NULL COMMENT '到达城市',
    departure_time DATETIME NOT NULL COMMENT '出发时间',
    arrival_time DATETIME NOT NULL COMMENT '到达时间',
    flight_number VARCHAR(20) NOT NULL COMMENT '航班号',
    cabin_type VARCHAR(20) NOT NULL COMMENT '舱位类型（经济舱/商务舱/头等舱）',
    total_seats INT NOT NULL COMMENT '总座位数',
    remaining_seats INT NOT NULL COMMENT '剩余座位数',
    price DECIMAL(10,2) NOT NULL COMMENT '票价'
);

-- 演唱会票表
CREATE TABLE concert_tickets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    artist VARCHAR(100) NOT NULL COMMENT '艺人名称',
    city VARCHAR(50) NOT NULL COMMENT '举办城市',
    venue VARCHAR(100) NOT NULL COMMENT '场馆',
    start_time DATETIME NOT NULL COMMENT '开始时间',
    end_time DATETIME NOT NULL COMMENT '结束时间',
    ticket_type VARCHAR(20) NOT NULL COMMENT '票类型（看台票/内场票/VIP票）',
    total_seats INT NOT NULL COMMENT '总座位数',
    remaining_seats INT NOT NULL COMMENT '剩余座位数',
    price DECIMAL(10,2) NOT NULL COMMENT '票价'
);
"""

# ==================== SQL生成提示词 ====================
SQL_PROMPT = ChatPromptTemplate.from_template(
    """
你是一个专业的票务SQL生成器。根据用户的自然语言查询，生成对应的SQL语句。

【数据表结构】
{table_schema}

【当前日期】
{current_date}

【用户查询】
{user_query}

【生成规则】
1. 识别查询类型：
   - 火车票/高铁票 → train_tickets 表
   - 机票/飞机票 → flight_tickets 表
   - 演唱会票 → concert_tickets 表

2. 必要信息检查：
   - 火车票/机票：需要出发城市、到达城市、日期
   - 演唱会票：需要城市、艺人、日期
   - 如果缺少必要信息，返回追问JSON

3. 默认值处理：
   - 如果未指定座位/舱位类型，不添加该条件（查询所有类型）
   - 如果说"明天"，转换为具体日期
   - 如果说"今天"，使用当前日期

4. 只查询有余票的记录：remaining_seats > 0

【输出格式】
如果信息完整，输出两行：
第一行：{{"type": "train/flight/concert"}}
第二行：SELECT语句（只查询: id, departure_city/artist, arrival_city/city, departure_time/start_time, arrival_time/end_time, train_number/flight_number/venue, seat_type/cabin_type/ticket_type, price, remaining_seats）

如果信息不足，输出：
{{"status": "input_required", "message": "具体需要补充的信息"}}

【示例】
用户：查一下明天北京到上海的高铁票
输出：
{{"type": "train"}}
SELECT id, departure_city, arrival_city, departure_time, arrival_time, train_number, seat_type, price, remaining_seats FROM train_tickets WHERE departure_city = '北京' AND arrival_city = '上海' AND DATE(departure_time) = '2025-01-19' AND remaining_seats > 0 ORDER BY departure_time

用户：机票
输出：
{{"status": "input_required", "message": "请提供出发城市、到达城市和出行日期，例如：查询1月20日北京到广州的机票"}}
"""
)


# ==================== MCP客户端 ====================
class TicketMCPClient:
    """票务MCP客户端，负责与MCP服务器通信"""

    def __init__(self, mcp_url: str):
        self.mcp_url = mcp_url

    async def query(self, sql: str) -> Dict[str, Any]:
        """
        执行SQL查询

        Args:
            sql: SQL查询语句

        Returns:
            查询结果字典
        """
        try:
            async with streamablehttp_client(self.mcp_url) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    logger.info(f"执行SQL: {sql}")

                    result = await session.call_tool("query_tickets", {"sql": sql})

                    # 解析结果
                    if hasattr(result, 'content') and result.content:
                        text = result.content[0].text
                        return {"status": "success", "data": text}
                    else:
                        return {"status": "success", "data": str(result)}

        except Exception as e:
            logger.error(f"MCP查询失败: {e}")
            return {"status": "error", "message": str(e)}


# ==================== Agent卡片定义 ====================
agent_card = AgentCard(
    name="TicketQueryAgent",
    description="票务查询代理，支持火车票、机票、演唱会票的自然语言查询",
    url="http://localhost:5006",
    version="1.0.0",
    capabilities={
        "streaming": False,
        "pushNotifications": False
    },
    skills=[
        AgentSkill(
            name="query_train_ticket",
            description="查询火车票/高铁票信息",
            examples=[
                "查询明天北京到上海的高铁",
                "1月20日广州到深圳的火车票",
                "北京到杭州的二等座"
            ]
        ),
        AgentSkill(
            name="query_flight_ticket",
            description="查询机票/航班信息",
            examples=[
                "查询1月25日上海到北京的机票",
                "明天深圳飞广州的经济舱",
                "北京到成都的航班"
            ]
        ),
        AgentSkill(
            name="query_concert_ticket",
            description="查询演唱会门票信息",
            examples=[
                "周杰伦北京演唱会",
                "1月30日上海的演唱会",
                "五月天广州站门票"
            ]
        )
    ]
)


# ==================== 票务查询服务器 ====================
class TicketQueryServer(A2AServer):
    """票务查询A2A服务器"""

    def __init__(self):
        super().__init__(agent_card=agent_card)
        self.llm = llm
        self.sql_prompt = SQL_PROMPT
        self.mcp_client = TicketMCPClient(TICKET_MCP_URL)
        logger.info("TicketQueryServer 初始化完成")

    def generate_sql(self, user_query: str) -> Dict[str, Any]:
        """
        使用LLM生成SQL

        Args:
            user_query: 用户自然语言查询

        Returns:
            包含type和sql的字典，或追问信息
        """
        try:
            chain = self.sql_prompt | self.llm
            current_date = datetime.now(TZ).strftime('%Y-%m-%d')

            output = chain.invoke({
                "table_schema": TABLE_SCHEMA,
                "current_date": current_date,
                "user_query": user_query
            }).content.strip()

            logger.info(f"LLM原始输出: {output}")

            # 提取代码块（如果有）
            if "```" in output:
                lines = []
                in_code = False
                for line in output.split('\n'):
                    if line.strip().startswith('```'):
                        in_code = not in_code
                        continue
                    if not in_code or line.strip():
                        lines.append(line)
                output = '\n'.join(lines).strip()

            # 解析输出
            lines = output.strip().split('\n')
            first_line = lines[0].strip()

            # 检查是否是追问
            if first_line.startswith('{"status"'):
                return json.loads(first_line)

            # 解析类型和SQL
            if first_line.startswith('{"type"'):
                query_type = json.loads(first_line).get("type")
                sql = ' '.join(line.strip() for line in lines[1:] if line.strip())
                return {"status": "sql", "type": query_type, "sql": sql}

            # 尝试直接作为SQL
            if "SELECT" in output.upper():
                return {"status": "sql", "type": "unknown", "sql": output}

            return {"status": "input_required", "message": "无法理解您的查询，请提供更多信息。"}

        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}")
            return {"status": "input_required", "message": "解析失败，请重新描述您的需求。"}
        except Exception as e:
            logger.error(f"SQL生成失败: {e}")
            return {"status": "input_required", "message": f"处理失败: {str(e)}"}

    def format_results(self, query_type: str, data: str) -> str:
        """
        格式化查询结果为用户友好文本

        Args:
            query_type: 查询类型 (train/flight/concert)
            data: JSON格式的查询结果

        Returns:
            格式化后的文本
        """
        try:
            records = json.loads(data) if isinstance(data, str) else data

            if not records:
                return "😔 未找到符合条件的票务信息，请尝试调整查询条件。"

            if isinstance(records, dict):
                records = [records]

            lines = []

            if query_type == "train":
                lines.append(f"🚄 找到 {len(records)} 条火车票信息：\n")
                for i, t in enumerate(records, 1):
                    lines.append(f"【{i}】{t.get('train_number', '')} {t.get('seat_type', '')}")
                    lines.append(f"    {t.get('departure_city', '')} → {t.get('arrival_city', '')}")
                    lines.append(f"    出发: {t.get('departure_time', '')}")
                    lines.append(f"    到达: {t.get('arrival_time', '')}")
                    lines.append(f"    💰 ¥{t.get('price', '')} | 余票: {t.get('remaining_seats', '')}张")
                    lines.append(f"    🎫 票务ID: {t.get('id', '')}")
                    lines.append("")

            elif query_type == "flight":
                lines.append(f"✈️ 找到 {len(records)} 条机票信息：\n")
                for i, t in enumerate(records, 1):
                    lines.append(f"【{i}】{t.get('flight_number', '')} {t.get('cabin_type', '')}")
                    lines.append(f"    {t.get('departure_city', '')} → {t.get('arrival_city', '')}")
                    lines.append(f"    出发: {t.get('departure_time', '')}")
                    lines.append(f"    到达: {t.get('arrival_time', '')}")
                    lines.append(f"    💰 ¥{t.get('price', '')} | 余票: {t.get('remaining_seats', '')}张")
                    lines.append(f"    🎫 票务ID: {t.get('id', '')}")
                    lines.append("")

            elif query_type == "concert":
                lines.append(f"🎤 找到 {len(records)} 条演唱会信息：\n")
                for i, t in enumerate(records, 1):
                    lines.append(f"【{i}】{t.get('artist', '')} - {t.get('ticket_type', '')}")
                    lines.append(f"    📍 {t.get('city', '')} · {t.get('venue', '')}")
                    lines.append(f"    🕐 {t.get('start_time', '')} ~ {t.get('end_time', '')}")
                    lines.append(f"    💰 ¥{t.get('price', '')} | 余票: {t.get('remaining_seats', '')}张")
                    lines.append(f"    🎫 票务ID: {t.get('id', '')}")
                    lines.append("")
            else:
                return f"查询结果: {data}"

            lines.append("💡 如需订票，请提供票务ID和联系人信息")
            return '\n'.join(lines)

        except json.JSONDecodeError:
            return f"查询结果: {data}"
        except Exception as e:
            logger.error(f"格式化结果失败: {e}")
            return f"查询结果: {data}"

    async def handle_task(self, task) -> TaskStatus:
        """
        处理A2A任务

        Args:
            task: A2A任务对象

        Returns:
            TaskStatus: 任务状态
        """
        try:
            # 1. 提取用户输入
            user_input = self._extract_user_input(task)

            if not user_input:
                return TaskStatus(
                    state=TaskState.INPUT_REQUIRED,
                    message={
                        "role": "assistant",
                        "content": "请输入您的票务查询需求，例如：查询明天北京到上海的高铁票"
                    }
                )

            logger.info(f"收到查询: {user_input}")

            # 2. 生成SQL
            sql_result = self.generate_sql(user_input)
            logger.info(f"SQL生成结果: {sql_result}")

            # 3. 处理追问
            if sql_result.get("status") == "input_required":
                return TaskStatus(
                    state=TaskState.INPUT_REQUIRED,
                    message={
                        "role": "assistant",
                        "content": sql_result.get("message", "请提供更多信息")
                    }
                )

            # 4. 执行查询
            if sql_result.get("status") == "sql":
                query_type = sql_result.get("type", "unknown")
                sql = sql_result.get("sql", "")

                # 调用MCP
                mcp_result = await self.mcp_client.query(sql)

                if mcp_result.get("status") == "error":
                    return TaskStatus(
                        state=TaskState.FAILED,
                        message={
                            "role": "assistant",
                            "content": f"查询失败: {mcp_result.get('message')}"
                        }
                    )

                # 格式化结果
                formatted = self.format_results(query_type, mcp_result.get("data", ""))

                return TaskStatus(
                    state=TaskState.COMPLETED,
                    message={
                        "role": "assistant",
                        "content": formatted
                    }
                )

            return TaskStatus(
                state=TaskState.FAILED,
                message={
                    "role": "assistant",
                    "content": "无法处理您的请求，请重试。"
                }
            )

        except Exception as e:
            logger.error(f"处理任务失败: {e}", exc_info=True)
            return TaskStatus(
                state=TaskState.FAILED,
                message={
                    "role": "assistant",
                    "content": f"处理请求时发生错误: {str(e)}"
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
    """启动票务查询服务器"""
    print("=" * 60)
    print("🎫 票务查询 A2A 服务器")
    print("=" * 60)
    print(f"服务地址: {agent_card.url}")
    print(f"MCP地址:  {TICKET_MCP_URL}")
    print("=" * 60)
    print("\n支持的查询：")
    print("  🚄 火车票: 明天北京到上海的高铁")
    print("  ✈️ 机票:   1月20日上海飞广州经济舱")
    print("  🎤 演唱会: 周杰伦北京演唱会门票")
    print("=" * 60)

    server = TicketQueryServer()

    try:
        run_server(server, host="0.0.0.0", port=5006)
    except KeyboardInterrupt:
        print("\n服务器已停止")
    except Exception as e:
        logger.error(f"服务器启动失败: {e}")
        raise


if __name__ == "__main__":
    main()