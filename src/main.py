#!/usr/bin/env python3
"""
SmartVoyage CLI主程序
src/main.py

命令行界面入口，提供交互式对话功能
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import List, Dict, Tuple

from python_a2a import AgentNetwork, TextContent, Message, MessageRole, Task
from langchain_openai import ChatOpenAI
import pytz

from src.config import config, logger
from src.prompts.templates import prompts


class SmartVoyageCLI:
    """SmartVoyage命令行界面"""
    
    def __init__(self):
        """初始化CLI"""
        self.timezone = pytz.timezone(config.timezone)
        self.messages: List[Dict] = []
        self.conversation_history: str = ""
        
        # 初始化Agent网络
        self.agent_network = AgentNetwork(name="SmartVoyage Network")
        self.agent_network.add("WeatherQueryAssistant", config.agents.weather_url)
        self.agent_network.add("TicketQueryAssistant", config.agents.ticket_url)
        self.agent_network.add("TicketOrderAssistant", config.agents.order_url)
        
        # 初始化LLM
        self.llm = ChatOpenAI(
            model=config.llm.model_name,
            api_key=config.llm.api_key,
            base_url=config.llm.base_url,
            temperature=config.llm.temperature
        )
        
        logger.info("SmartVoyage CLI 初始化完成")
    
    @property
    def current_date(self) -> str:
        """获取当前日期"""
        return datetime.now(self.timezone).strftime('%Y-%m-%d')
    
    def recognize_intent(self, user_input: str) -> Tuple[List[str], Dict, str]:
        """
        识别用户意图
        
        Args:
            user_input: 用户输入
            
        Returns:
            (意图列表, 改写后的查询字典, 追问消息)
        """
        chain = prompts.intent_recognition() | self.llm
        
        # 获取最近的对话历史
        recent_history = '\n'.join(self.conversation_history.split("\n")[-6:])
        
        response = chain.invoke({
            "conversation_history": recent_history,
            "query": user_input,
            "current_date": self.current_date
        }).content.strip()
        
        logger.info(f"意图识别原始响应: {response}")
        
        # 清理markdown标记
        import re
        response = re.sub(r'^```json\s*|\s*```$', '', response).strip()
        
        try:
            result = json.loads(response)
            intents = result.get("intents", [])
            user_queries = result.get("user_queries", {})
            follow_up = result.get("follow_up_message", "")
            
            logger.info(f"识别结果 - 意图: {intents}, 追问: {follow_up}")
            return intents, user_queries, follow_up
            
        except json.JSONDecodeError as e:
            logger.error(f"意图识别JSON解析失败: {e}")
            return ["out_of_scope"], {}, "抱歉，我无法理解您的问题，请重新描述。"
    
    def get_agent_for_intent(self, intent: str) -> str:
        """根据意图获取对应的Agent名称"""
        intent_agent_map = {
            "weather": "WeatherQueryAssistant",
            "train": "TicketQueryAssistant",
            "flight": "TicketQueryAssistant",
            "concert": "TicketQueryAssistant",
            "order": "TicketOrderAssistant"
        }
        return intent_agent_map.get(intent)
    
    async def call_agent(self, agent_name: str, query: str) -> str:
        """
        调用Agent
        
        Args:
            agent_name: Agent名称
            query: 查询内容
            
        Returns:
            Agent响应
        """
        try:
            agent = self.agent_network.get_agent(agent_name)
            
            # 构建消息
            chat_history = '\n'.join(self.conversation_history.split("\n")[-7:-1])
            full_query = f"{chat_history}\nUser: {query}" if chat_history else query
            
            message = Message(
                content=TextContent(text=full_query),
                role=MessageRole.USER
            )
            task = Task(id=f"task-{uuid.uuid4()}", message=message.to_dict())
            
            # 异步调用Agent
            response = await agent.send_task_async(task)
            logger.info(f"{agent_name} 响应: {response}")
            
            # 提取结果
            if response.status.state == 'completed':
                return response.artifacts[0]['parts'][0]['text']
            else:
                return response.status.message.get('content', {}).get('text', '查询失败')
                
        except Exception as e:
            logger.error(f"调用Agent失败: {e}")
            return f"服务暂时不可用: {str(e)}"
    
    def summarize_response(self, agent_name: str, query: str, raw_response: str) -> str:
        """
        总结Agent响应
        
        Args:
            agent_name: Agent名称
            query: 原始查询
            raw_response: Agent原始响应
            
        Returns:
            总结后的响应
        """
        try:
            if agent_name == "WeatherQueryAssistant":
                chain = prompts.weather_summary() | self.llm
                return chain.invoke({"query": query, "raw_response": raw_response}).content.strip()
            elif agent_name == "TicketQueryAssistant":
                chain = prompts.ticket_summary() | self.llm
                return chain.invoke({"query": query, "raw_response": raw_response}).content.strip()
            else:
                return raw_response
        except Exception as e:
            logger.error(f"总结响应失败: {e}")
            return raw_response
    
    def generate_attraction_recommendation(self, query: str) -> str:
        """生成景点推荐"""
        chain = prompts.attraction_recommendation() | self.llm
        return chain.invoke({"query": query}).content.strip()
    
    async def process_input(self, user_input: str) -> str:
        """
        处理用户输入
        
        Args:
            user_input: 用户输入
            
        Returns:
            系统响应
        """
        # 更新对话历史
        self.messages.append({"role": "user", "content": user_input})
        self.conversation_history += f"\nUser: {user_input}"
        
        try:
            # 意图识别
            intents, user_queries, follow_up = self.recognize_intent(user_input)
            
            # 处理超出范围或需要追问的情况
            if "out_of_scope" in intents or follow_up:
                response = follow_up or "您好，我是智能旅行助手，可以帮您查询天气、票务或推荐景点。"
                self.conversation_history += f"\nAssistant: {response}"
                self.messages.append({"role": "assistant", "content": response})
                return response
            
            # 处理各个意图
            responses = []
            for intent in intents:
                logger.info(f"处理意图: {intent}")
                
                if intent == "attraction":
                    # 景点推荐直接由LLM生成
                    rec = self.generate_attraction_recommendation(user_input)
                    responses.append(rec)
                else:
                    # 其他意图调用对应Agent
                    agent_name = self.get_agent_for_intent(intent)
                    if agent_name:
                        query = user_queries.get(intent, user_input)
                        raw_response = await self.call_agent(agent_name, query)
                        
                        # 总结响应
                        if agent_name != "TicketOrderAssistant":
                            final_response = self.summarize_response(agent_name, query, raw_response)
                        else:
                            final_response = raw_response
                        
                        responses.append(final_response)
            
            # 合并响应
            response = "\n\n".join(responses) if responses else "抱歉，暂时无法处理您的请求。"
            
            # 更新历史
            self.conversation_history += f"\nAssistant: {response}"
            self.messages.append({"role": "assistant", "content": response})
            
            return response
            
        except Exception as e:
            logger.error(f"处理输入失败: {e}", exc_info=True)
            error_msg = f"处理失败: {str(e)}"
            self.messages.append({"role": "assistant", "content": error_msg})
            return error_msg
    
    def display_agent_cards(self):
        """显示Agent卡片信息"""
        print("\n🛠️ Agent服务状态:")
        print("-" * 40)
        
        agent_info = [
            ("WeatherQueryAssistant", config.agents.weather_url, "天气查询"),
            ("TicketQueryAssistant", config.agents.ticket_url, "票务查询"),
            ("TicketOrderAssistant", config.agents.order_url, "票务预订"),
        ]
        
        for name, url, desc in agent_info:
            try:
                card = self.agent_network.get_agent_card(name)
                status = "✅ 在线"
            except:
                status = "❌ 离线"
            
            print(f"  {name}")
            print(f"    描述: {desc}")
            print(f"    地址: {url}")
            print(f"    状态: {status}")
            print()
    
    def run(self):
        """运行CLI主循环"""
        print("=" * 60)
        print("🤖 SmartVoyage 智能旅行助手")
        print("=" * 60)
        print("欢迎使用！我可以帮您:")
        print("  🌤️ 查询天气    🚄 查询火车票")
        print("  ✈️ 查询机票    🎤 查询演唱会票")
        print("  🎫 在线订票    🏞️ 推荐景点")
        print("-" * 60)
        print("命令: 输入 'quit' 退出, 'cards' 查看服务状态")
        print("=" * 60)
        
        while True:
            try:
                user_input = input("\n📝 请输入您的问题: ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() == 'quit':
                    print("\n感谢使用 SmartVoyage！再见！👋")
                    break
                
                if user_input.lower() == 'cards':
                    self.display_agent_cards()
                    continue
                
                # 处理用户输入
                print("\n⏳ 正在处理您的请求...")
                response = asyncio.run(self.process_input(user_input))
                print(f"\n🤖 助手回复:\n{response}")
                
            except KeyboardInterrupt:
                print("\n\n感谢使用 SmartVoyage！再见！👋")
                break
            except Exception as e:
                logger.error(f"运行错误: {e}")
                print(f"\n❌ 发生错误: {e}")


def main():
    """主函数"""
    cli = SmartVoyageCLI()
    cli.run()


if __name__ == "__main__":
    main()
