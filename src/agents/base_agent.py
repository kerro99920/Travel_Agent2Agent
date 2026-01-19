#!/usr/bin/env python3
"""
SmartVoyage Agent基类
src/agents/base_agent.py

所有A2A Agent的抽象基类，提供通用功能
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime

from python_a2a import A2AServer, AgentCard, AgentSkill, TaskStatus, TaskState
from langchain_openai import ChatOpenAI
import pytz

from src.config import config, logger


class BaseAgent(A2AServer, ABC):
    """
    Agent抽象基类
    
    提供以下通用功能：
    - LLM客户端初始化
    - 用户输入提取
    - 错误处理
    - 日志记录
    """
    
    def __init__(self, agent_card: AgentCard):
        """
        初始化Agent
        
        Args:
            agent_card: Agent卡片配置
        """
        super().__init__(agent_card=agent_card)
        self.agent_card = agent_card
        self.timezone = pytz.timezone(config.timezone)
        
        # 初始化LLM
        self.llm = ChatOpenAI(
            model=config.llm.model_name,
            base_url=config.llm.base_url,
            api_key=config.llm.api_key,
            temperature=config.llm.temperature,
            max_tokens=config.llm.max_tokens
        )
        
        logger.info(f"{self.agent_card.name} 初始化完成")
    
    @property
    def current_date(self) -> str:
        """获取当前日期字符串"""
        return datetime.now(self.timezone).strftime('%Y-%m-%d')
    
    @property
    def current_datetime(self) -> str:
        """获取当前日期时间字符串"""
        return datetime.now(self.timezone).strftime('%Y-%m-%d %H:%M:%S')
    
    def extract_user_input(self, task) -> str:
        """
        从任务中提取用户输入
        
        Args:
            task: A2A任务对象
            
        Returns:
            用户输入文本
        """
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
    
    def create_response(
        self, 
        state: TaskState, 
        content: str,
        artifacts: Optional[List[Dict]] = None
    ) -> TaskStatus:
        """
        创建标准响应
        
        Args:
            state: 任务状态
            content: 响应内容
            artifacts: 附加数据
            
        Returns:
            TaskStatus对象
        """
        response = TaskStatus(
            state=state,
            message={
                "role": "assistant",
                "content": content
            }
        )
        
        if artifacts:
            response.artifacts = artifacts
            
        return response
    
    def success_response(self, content: str) -> TaskStatus:
        """创建成功响应"""
        return self.create_response(TaskState.COMPLETED, content)
    
    def error_response(self, content: str) -> TaskStatus:
        """创建错误响应"""
        return self.create_response(TaskState.FAILED, content)
    
    def input_required_response(self, content: str) -> TaskStatus:
        """创建需要更多输入的响应"""
        return self.create_response(TaskState.INPUT_REQUIRED, content)
    
    @abstractmethod
    async def handle_task(self, task) -> TaskStatus:
        """
        处理任务的抽象方法，子类必须实现
        
        Args:
            task: A2A任务对象
            
        Returns:
            TaskStatus对象
        """
        pass
    
    @abstractmethod
    def get_welcome_message(self) -> str:
        """获取欢迎消息，子类必须实现"""
        pass


class MCPClientMixin:
    """
    MCP客户端混入类
    
    提供MCP服务调用的通用方法
    """
    
    async def call_mcp_tool(
        self, 
        mcp_url: str, 
        tool_name: str, 
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        调用MCP工具
        
        Args:
            mcp_url: MCP服务URL
            tool_name: 工具名称
            params: 工具参数
            
        Returns:
            调用结果
        """
        from mcp import ClientSession
        from mcp.client.streamable_http import streamablehttp_client
        
        try:
            async with streamablehttp_client(mcp_url) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    logger.debug(f"调用MCP工具: {tool_name}, 参数: {params}")
                    
                    result = await session.call_tool(tool_name, params)
                    
                    if hasattr(result, 'content') and result.content:
                        text = result.content[0].text
                        return {"status": "success", "data": text}
                    else:
                        return {"status": "success", "data": str(result)}
                        
        except Exception as e:
            logger.error(f"MCP调用失败: {e}")
            return {"status": "error", "message": str(e)}
