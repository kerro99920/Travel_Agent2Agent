import asyncio
import json
import uuid
from datetime import datetime
import pytz
import re
from python_a2a import AgentNetwork, TextContent, Message, MessageRole, Task
from langchain_openai import ChatOpenAI

from SmartVoyage.config import Config
from SmartVoyage.create_logger import logger
from SmartVoyage.main_prompts import SmartVoyagePrompts

conf = Config()

# 初始化全局变量，用于模拟会话状态   这些变量替换了Streamlit的session_state
messages = []  # 存储对话历史消息列表，每个元素为字典{"role": "user/assistant", "content": "消息内容"}
agent_network = None  # 代理网络实例
llm = None  # 大语言模型实例
agent_urls = {}  # 存储代理的URL信息字典
conversation_history = ""  # 存储整个对话历史字符串，用于意图识别


# 初始化代理网络和相关组件   此部分在脚本启动时执行一次，模拟Streamlit的初始化
def initialize_system():
    """
    初始化系统组件，包括代理网络、路由器、LLM和会话状态
    核心逻辑：构建AgentNetwork，添加代理，创建路由器和LLM
    """
    global agent_network, llm, agent_urls, conversation_history
    # 存储代理URL信息，便于查看
    agent_urls = {
        "WeatherQueryAssistant": "http://localhost:5005",  # 天气代理URL
        "TicketQueryAssistant": "http://localhost:5006",  # 票务代理URL
        "TicketOrderAssistant": "http://localhost:5007" # 票务预定URL
    }
    # 创建代理网络
    network = AgentNetwork(name="旅行助手网络")
    network.add("WeatherQueryAssistant", "http://localhost:5005")
    network.add("TicketQueryAssistant", "http://localhost:5006")
    network.add("TicketOrderAssistant", "http://localhost:5007")
    agent_network = network

    # 加载配置并创建LLM
    llm = ChatOpenAI(
        model=conf.model_name,
        api_key=conf.api_key,
        base_url=conf.base_url,
        temperature=0.1
    )

    # 初始化对话历史为空字符串
    conversation_history = ""


# 意图识别agent
def intent_agent(user_input):
    global conversation_history, llm

    # 创建意图识别链：提示模板 + LLM
    chain = SmartVoyagePrompts.intent_prompt() | llm

    # 调用LLM进行意图识别
    current_date = datetime.now(pytz.timezone('Asia/Shanghai')).strftime('%Y-%m-%d')  # 获取当前日期（Asia/Shanghai时区）
    intent_response = chain.invoke(
        {"conversation_history": '\n'.join(conversation_history.split("\n")[-6:]), "query": user_input,
         "current_date": current_date}).content.strip()
    logger.info(f"意图识别原始响应: {intent_response}")

    # 清理响应：移除可能的Markdown代码块标记
    intent_response = re.sub(r'^```json\s*|\s*```$', '', intent_response).strip()
    logger.info(f"清理后响应: {intent_response}")
    intent_output = json.loads(intent_response)
    # 提取意图、改写问题和追问消息
    intents = intent_output.get("intents", [])
    user_queries = intent_output.get("user_queries", {})
    follow_up_message = intent_output.get("follow_up_message", "")
    logger.info(f"intents: {intents}||user_queries: {user_queries}||follow_up_message: {follow_up_message} ")

    return intents, user_queries, follow_up_message

# 处理用户输入的核心函数
# 此函数模拟Streamlit的输入处理逻辑，包括意图识别、路由和响应生成
def process_user_input(prompt):
    """
    处理用户输入：识别意图、调用代理、生成响应
    核心逻辑：使用LLM进行意图识别，根据意图路由到相应代理或直接生成内容
    """
    global messages, conversation_history, llm
    # 添加用户消息到历史
    messages.append({"role": "user", "content": prompt})
    conversation_history += f"\nUser: {prompt}"

    print("正在分析您的意图...")
    try:
        # 意图识别过程
        intents, user_queries, follow_up_message = intent_agent(prompt)

        # 根据意图输出生成响应
        if "out_of_scope" in intents:
            # 如果意图超出范围，返回大模型直接回复
            response = follow_up_message
            conversation_history += f"\nAssistant: {response}"
        elif follow_up_message != "":
            # 如果有追问消息，则直接返回
            response = follow_up_message
            conversation_history += f"\nAssistant: {response}"  # 更新历史
        else: # 处理有效意图
            responses = []  # 存储每个意图的响应列表
            routed_agents = []  # 记录路由到的代理列表
            for intent in intents:
                logger.info(f"处理意图：{intent}")
                # 根据意图确定代理名称
                if intent == "weather":
                    agent_name = "WeatherQueryAssistant"
                elif intent in ["flight", "train", "concert"]:
                    agent_name = "TicketQueryAssistant"
                elif intent == "order":
                    agent_name = "TicketOrderAssistant"
                else:
                    agent_name = None

                # 不同意图处理方式
                if intent == "attraction":
                    # 对于景点推荐，直接使用LLM生成
                    chain = SmartVoyagePrompts.attraction_prompt() | llm
                    rec_response = chain.invoke({"query": prompt}).content.strip()
                    responses.append(rec_response)
                elif agent_name:
                    # 对于代理意图，则调用代理
                    # 1）获取问题
                    query_str = user_queries.get(intent, {})
                    logger.info(f"{agent_name} 查询：{query_str}")
                    # 2）获取代理实例
                    agent = agent_network.get_agent(agent_name)
                    # 3）构建历史对话信息+新查询，然后调用代理
                    chat_history = '\n'.join(conversation_history.split("\n")[-7:-1]) + f'\nUser: {query_str}'
                    message = Message(content=TextContent(text=chat_history), role=MessageRole.USER)
                    task = Task(id="task-" + str(uuid.uuid4()), message=message.to_dict())
                    raw_response = asyncio.run(agent.send_task_async(task))
                    logger.info(f"{agent_name} 原始响应: {raw_response}") # 记录原始响应日志
                    # 4）处理结果
                    if raw_response.status.state == 'completed':  # 正常结果
                        agent_result = raw_response.artifacts[0]['parts'][0]['text']
                    else:  # 异常结果
                        agent_result = raw_response.status.message['content']['text']

                    # 根据代理类型总结响应
                    if agent_name == "WeatherQueryAssistant":
                        chain = SmartVoyagePrompts.summarize_weather_prompt() | llm
                        final_response = chain.invoke({"query": query_str, "raw_response": agent_result}).content.strip()
                    elif agent_name == "TicketQueryAssistant":
                        chain = SmartVoyagePrompts.summarize_ticket_prompt() | llm
                        final_response = chain.invoke({"query": query_str, "raw_response": agent_result}).content.strip()
                    else :
                        final_response = agent_result

                    # 5）添加到历史
                    responses.append(final_response)  # 添加到响应列表
                    routed_agents.append(agent_name)  # 记录路由代理
                else:
                    # 不支持的意图
                    responses.append("暂不支持此意图。")

            # 组合所有响应
            response = "\n\n".join(responses)
            if routed_agents:
                logger.info(f"路由到代理：{routed_agents}")
            conversation_history += f"\nAssistant: {response}"  # 更新历史

        # 输出助手响应（模拟Streamlit的显示）
        print(f"\n助手回复：\n{response}\n")  # 打印响应
        # 添加到消息历史
        messages.append({"role": "assistant", "content": response})

    except json.JSONDecodeError as json_err:
        # 处理JSON解析错误
        logger.error(f"意图识别JSON解析失败")
        error_message = f"意图识别JSON解析失败：{str(json_err)}。请重试。"
        print(f"\n助手回复：\n{error_message}\n")  # 打印错误
        messages.append({"role": "assistant", "content": error_message})
    except Exception as e:
        # 处理其他异常
        logger.error(f"处理异常: {str(e)}")
        error_message = f"处理失败：{str(e)}。请重试。"
        print(f"\n助手回复：\n{error_message}\n")  # 打印错误
        messages.append({"role": "assistant", "content": error_message})

# 显示代理卡片信息
# 此函数模拟Streamlit的右侧Agent Card，打印代理详情
def display_agent_cards():
    """
    显示所有代理的卡片信息，包括技能、描述、地址和状态
    核心逻辑：遍历代理网络，获取并打印卡片内容
    """
    print("\n🛠️ Agent Cards:")
    for agent_name in agent_network.agents.keys():
        # 获取代理卡片
        agent_card = agent_network.get_agent_card(agent_name)
        agent_url = agent_urls.get(agent_name, "未知地址")
        print(f"\n--- Agent: {agent_name} ---")
        print(f"技能: {agent_card.skills}")
        print(f"描述: {agent_card.description}")
        print(f"地址: {agent_url}")
        print(f"状态: 在线")  # 固定状态为在线

# 主函数：脚本入口
# 初始化系统并进入交互循环
if __name__ == "__main__":
    # 初始化系统
    initialize_system()
    print("🤖 基于A2A的SmartVoyage旅行智能助手")
    print("欢迎体验智能对话！输入问题，按回车提交；输入'quit'退出；输入'cards'查看代理卡片。")

    # 显示初始代理卡片
    display_agent_cards()

    # 交互循环：模拟Streamlit的连续输入
    while True:
        # 获取用户输入
        prompt = input("\n请输入您的问题: ").strip()
        if prompt.lower() == 'quit':
            print("感谢使用SmartVoyage！再见！")
            break
        elif prompt.lower() == 'cards':  # 查看卡片条件
            display_agent_cards()  # 重新显示卡片
            continue
        elif not prompt:  # 空输入跳过
            continue
        else:
            # 处理输入
            process_user_input(prompt)  # 调用核心处理函数

    # 脚本结束时打印页脚信息
    print("\n---")
    print("Powered by 黑马程序员 | 基于Agent2Agent的旅行助手系统 v2.0")