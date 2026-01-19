#!/usr/bin/env python3
"""
SmartVoyage Streamlit Web应用
src/app.py

提供Web用户界面
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import List, Dict, Tuple

import streamlit as st
from python_a2a import AgentNetwork, TextContent, Message, MessageRole, Task
from langchain_openai import ChatOpenAI
import pytz

from src.config import config, logger
from src.prompts.templates import prompts


# ==================== 页面配置 ====================
st.set_page_config(
    page_title="SmartVoyage 智能旅行助手",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ==================== 自定义样式 ====================
st.markdown("""
<style>
/* 主容器样式 */
.main .block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
}

/* 聊天消息样式 */
.stChatMessage {
    background-color: #f8f9fa !important;
    border-radius: 12px !important;
    padding: 1rem !important;
    margin-bottom: 1rem !important;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1) !important;
}

/* 用户消息 */
.stChatMessage[data-testid="user-message"] {
    background-color: #e3f2fd !important;
}

/* 助手消息 */
.stChatMessage[data-testid="assistant-message"] {
    background-color: #f5f5f5 !important;
}

/* 侧边栏样式 */
.css-1d391kg {
    background-color: #f8f9fa;
}

/* 标题样式 */
h1 {
    color: #1976d2;
}

/* 卡片样式 */
.agent-card {
    background: white;
    border-radius: 8px;
    padding: 1rem;
    margin-bottom: 0.5rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.agent-card h4 {
    color: #1976d2;
    margin-bottom: 0.5rem;
}

.status-online {
    color: #4caf50;
    font-weight: bold;
}

.status-offline {
    color: #f44336;
    font-weight: bold;
}
</style>
""", unsafe_allow_html=True)


# ==================== 初始化会话状态 ====================
def init_session_state():
    """初始化会话状态"""
    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "conversation_history" not in st.session_state:
        st.session_state.conversation_history = ""

    if "agent_network" not in st.session_state:
        # 初始化Agent网络
        network = AgentNetwork(name="SmartVoyage Network")
        network.add("WeatherQueryAssistant", config.agents.weather_url)
        network.add("TicketQueryAssistant", config.agents.ticket_url)
        network.add("TicketOrderAssistant", config.agents.order_url)
        st.session_state.agent_network = network

    if "llm" not in st.session_state:
        st.session_state.llm = ChatOpenAI(
            model=config.llm.model_name,
            api_key=config.llm.api_key,
            base_url=config.llm.base_url,
            temperature=config.llm.temperature
        )


# ==================== 业务逻辑 ====================
def get_current_date() -> str:
    """获取当前日期"""
    tz = pytz.timezone(config.timezone)
    return datetime.now(tz).strftime('%Y-%m-%d')


def recognize_intent(user_input: str) -> Tuple[List[str], Dict, str]:
    """识别用户意图"""
    import re

    chain = prompts.intent_recognition() | st.session_state.llm
    recent_history = '\n'.join(st.session_state.conversation_history.split("\n")[-6:])

    response = chain.invoke({
        "conversation_history": recent_history,
        "query": user_input,
        "current_date": get_current_date()
    }).content.strip()

    logger.info(f"意图识别响应: {response}")

    # 清理markdown
    response = re.sub(r'^```json\s*|\s*```$', '', response).strip()

    try:
        result = json.loads(response)
        return (
            result.get("intents", []),
            result.get("user_queries", {}),
            result.get("follow_up_message", "")
        )
    except json.JSONDecodeError:
        return ["out_of_scope"], {}, "抱歉，我无法理解您的问题。"


async def call_agent(agent_name: str, query: str) -> str:
    """调用Agent"""
    try:
        agent = st.session_state.agent_network.get_agent(agent_name)

        chat_history = '\n'.join(st.session_state.conversation_history.split("\n")[-7:-1])
        full_query = f"{chat_history}\nUser: {query}" if chat_history else query

        message = Message(
            content=TextContent(text=full_query),
            role=MessageRole.USER
        )
        task = Task(id=f"task-{uuid.uuid4()}", message=message.to_dict())

        response = await agent.send_task_async(task)
        logger.info(f"{agent_name} 响应: {response}")

        if response.status.state == 'completed':
            return response.artifacts[0]['parts'][0]['text']
        else:
            msg = response.status.message
            if isinstance(msg, dict):
                return msg.get('content', {}).get('text', '查询失败')
            return str(msg)

    except Exception as e:
        logger.error(f"调用Agent失败: {e}")
        return f"服务暂时不可用: {str(e)}"


def summarize_response(agent_name: str, query: str, raw_response: str) -> str:
    """总结Agent响应"""
    try:
        if agent_name == "WeatherQueryAssistant":
            chain = prompts.weather_summary() | st.session_state.llm
            return chain.invoke({"query": query, "raw_response": raw_response}).content.strip()
        elif agent_name == "TicketQueryAssistant":
            chain = prompts.ticket_summary() | st.session_state.llm
            return chain.invoke({"query": query, "raw_response": raw_response}).content.strip()
        return raw_response
    except:
        return raw_response


async def process_user_input(user_input: str) -> str:
    """处理用户输入"""
    st.session_state.conversation_history += f"\nUser: {user_input}"

    # 意图识别
    intents, user_queries, follow_up = recognize_intent(user_input)

    # 处理超出范围或追问
    if "out_of_scope" in intents or follow_up:
        response = follow_up or "您好，我是智能旅行助手。"
        st.session_state.conversation_history += f"\nAssistant: {response}"
        return response

    # 处理各个意图
    responses = []
    intent_agent_map = {
        "weather": "WeatherQueryAssistant",
        "train": "TicketQueryAssistant",
        "flight": "TicketQueryAssistant",
        "concert": "TicketQueryAssistant",
        "order": "TicketOrderAssistant"
    }

    for intent in intents:
        logger.info(f"处理意图: {intent}")

        if intent == "attraction":
            chain = prompts.attraction_recommendation() | st.session_state.llm
            rec = chain.invoke({"query": user_input}).content.strip()
            responses.append(rec)
        else:
            agent_name = intent_agent_map.get(intent)
            if agent_name:
                query = user_queries.get(intent, user_input)
                raw_response = await call_agent(agent_name, query)

                if agent_name != "TicketOrderAssistant":
                    final_response = summarize_response(agent_name, query, raw_response)
                else:
                    final_response = raw_response

                responses.append(final_response)

    response = "\n\n".join(responses) if responses else "抱歉，暂时无法处理您的请求。"
    st.session_state.conversation_history += f"\nAssistant: {response}"

    return response


# ==================== 侧边栏 ====================
def render_sidebar():
    """渲染侧边栏"""
    with st.sidebar:
        st.image("https://via.placeholder.com/200x60?text=SmartVoyage", width=200)
        st.markdown("---")

        st.subheader("🛠️ Agent 服务状态")

        agents_info = [
            ("WeatherQueryAssistant", "天气查询", config.agents.weather_url, "🌤️"),
            ("TicketQueryAssistant", "票务查询", config.agents.ticket_url, "🎫"),
            ("TicketOrderAssistant", "票务预订", config.agents.order_url, "📋"),
        ]

        for name, desc, url, icon in agents_info:
            try:
                card = st.session_state.agent_network.get_agent_card(name)
                status = "🟢 在线"
            except:
                status = "🔴 离线"

            with st.expander(f"{icon} {desc}", expanded=False):
                st.markdown(f"**名称:** {name}")
                st.markdown(f"**地址:** `{url}`")
                st.markdown(f"**状态:** {status}")

        st.markdown("---")

        st.subheader("💡 使用提示")
        st.markdown("""
        - 🌤️ **天气查询**: 北京明天天气
        - 🚄 **火车票**: 北京到上海的高铁
        - ✈️ **机票**: 上海飞广州的机票
        - 🎤 **演唱会**: 周杰伦演唱会
        - 🎫 **订票**: 订一张火车票，张三，138xxxx
        - 🏞️ **景点**: 北京有什么好玩的
        """)

        st.markdown("---")

        if st.button("🗑️ 清空对话", use_container_width=True):
            st.session_state.messages = []
            st.session_state.conversation_history = ""
            st.rerun()


# ==================== 主界面 ====================
def render_main():
    """渲染主界面"""
    st.title("🤖 SmartVoyage 智能旅行助手")
    st.markdown("欢迎使用智能旅行助手！我可以帮您查询天气、票务，推荐景点，还能在线订票。")

    st.markdown("---")

    # 显示对话历史
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # 用户输入
    if prompt := st.chat_input("请输入您的问题..."):
        # 显示用户消息
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        # 处理并显示助手响应
        with st.chat_message("assistant"):
            with st.spinner("正在思考..."):
                try:
                    response = asyncio.run(process_user_input(prompt))
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                except Exception as e:
                    error_msg = f"处理失败: {str(e)}"
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})


# ==================== 主函数 ====================
def main():
    """主函数"""
    init_session_state()
    render_sidebar()
    render_main()

    # 页脚
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: #666;'>"
        "Powered by SmartVoyage Team | 基于A2A的智能旅行助手系统 v2.0"
        "</div>",
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
