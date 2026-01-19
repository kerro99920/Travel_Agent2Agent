#!/usr/bin/env python3
"""
SmartVoyage 全局配置模块
src/config/settings.py

统一管理所有配置项，支持环境变量覆盖
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, Optional
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent


@dataclass
class LLMConfig:
    """大语言模型配置"""
    base_url: str = field(default_factory=lambda: os.getenv(
        "LLM_BASE_URL", 
        "https://dashscope.aliyuncs.com/compatible-mode/v1"
    ))
    api_key: str = field(default_factory=lambda: os.getenv("LLM_API_KEY", ""))
    model_name: str = field(default_factory=lambda: os.getenv("LLM_MODEL_NAME", "qwen-plus"))
    temperature: float = field(default_factory=lambda: float(os.getenv("LLM_TEMPERATURE", "0.1")))
    max_tokens: int = field(default_factory=lambda: int(os.getenv("LLM_MAX_TOKENS", "2048")))


@dataclass
class DatabaseConfig:
    """数据库配置"""
    host: str = field(default_factory=lambda: os.getenv("DB_HOST", "localhost"))
    port: int = field(default_factory=lambda: int(os.getenv("DB_PORT", "3306")))
    user: str = field(default_factory=lambda: os.getenv("DB_USER", "root"))
    password: str = field(default_factory=lambda: os.getenv("DB_PASSWORD", "root"))
    database: str = field(default_factory=lambda: os.getenv("DB_NAME", "travel_rag"))
    charset: str = "utf8mb4"
    pool_size: int = field(default_factory=lambda: int(os.getenv("DB_POOL_SIZE", "5")))
    
    @property
    def connection_params(self) -> Dict:
        """返回数据库连接参数"""
        return {
            "host": self.host,
            "port": self.port,
            "user": self.user,
            "password": self.password,
            "database": self.database,
            "charset": self.charset
        }


@dataclass
class AgentConfig:
    """Agent服务配置"""
    weather_host: str = field(default_factory=lambda: os.getenv("WEATHER_AGENT_HOST", "0.0.0.0"))
    weather_port: int = field(default_factory=lambda: int(os.getenv("WEATHER_AGENT_PORT", "5005")))
    
    ticket_host: str = field(default_factory=lambda: os.getenv("TICKET_AGENT_HOST", "0.0.0.0"))
    ticket_port: int = field(default_factory=lambda: int(os.getenv("TICKET_AGENT_PORT", "5006")))
    
    order_host: str = field(default_factory=lambda: os.getenv("ORDER_AGENT_HOST", "0.0.0.0"))
    order_port: int = field(default_factory=lambda: int(os.getenv("ORDER_AGENT_PORT", "5007")))
    
    @property
    def weather_url(self) -> str:
        return f"http://{self.weather_host}:{self.weather_port}"
    
    @property
    def ticket_url(self) -> str:
        return f"http://{self.ticket_host}:{self.ticket_port}"
    
    @property
    def order_url(self) -> str:
        return f"http://{self.order_host}:{self.order_port}"


@dataclass
class MCPConfig:
    """MCP服务配置"""
    weather_host: str = field(default_factory=lambda: os.getenv("WEATHER_MCP_HOST", "127.0.0.1"))
    weather_port: int = field(default_factory=lambda: int(os.getenv("WEATHER_MCP_PORT", "8000")))
    
    ticket_host: str = field(default_factory=lambda: os.getenv("TICKET_MCP_HOST", "127.0.0.1"))
    ticket_port: int = field(default_factory=lambda: int(os.getenv("TICKET_MCP_PORT", "8001")))
    
    order_host: str = field(default_factory=lambda: os.getenv("ORDER_MCP_HOST", "127.0.0.1"))
    order_port: int = field(default_factory=lambda: int(os.getenv("ORDER_MCP_PORT", "8002")))
    
    @property
    def weather_url(self) -> str:
        return f"http://{self.weather_host}:{self.weather_port}/mcp"
    
    @property
    def ticket_url(self) -> str:
        return f"http://{self.ticket_host}:{self.ticket_port}/mcp"
    
    @property
    def order_url(self) -> str:
        return f"http://{self.order_host}:{self.order_port}/mcp"


@dataclass
class ExternalAPIConfig:
    """外部API配置"""
    # 和风天气API
    qweather_api_key: str = field(default_factory=lambda: os.getenv("QWEATHER_API_KEY", ""))
    qweather_base_url: str = "https://ne5u9wc3nu.re.qweatherapi.com/v7"
    
    # Aviationstack航班API
    aviationstack_api_key: str = field(default_factory=lambda: os.getenv("AVIATIONSTACK_API_KEY", ""))
    aviationstack_base_url: str = "http://api.aviationstack.com/v1"
    
    # Ticketmaster演唱会API
    ticketmaster_api_key: str = field(default_factory=lambda: os.getenv("TICKETMASTER_API_KEY", ""))
    ticketmaster_base_url: str = "https://app.ticketmaster.com/discovery/v2"


@dataclass
class LogConfig:
    """日志配置"""
    level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    format: str = "%(name)s - %(asctime)s - %(levelname)s - %(message)s"
    file_path: Path = field(default_factory=lambda: PROJECT_ROOT / "logs" / "app.log")
    max_bytes: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5


@dataclass
class AppConfig:
    """应用主配置"""
    app_name: str = "SmartVoyage"
    version: str = "2.0.0"
    debug: bool = field(default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true")
    timezone: str = "Asia/Shanghai"
    
    # 子配置
    llm: LLMConfig = field(default_factory=LLMConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    agents: AgentConfig = field(default_factory=AgentConfig)
    mcp: MCPConfig = field(default_factory=MCPConfig)
    external_api: ExternalAPIConfig = field(default_factory=ExternalAPIConfig)
    log: LogConfig = field(default_factory=LogConfig)


# 全局配置实例
config = AppConfig()


def get_config() -> AppConfig:
    """获取配置实例"""
    return config


def print_config():
    """打印当前配置（隐藏敏感信息）"""
    print("=" * 60)
    print(f"SmartVoyage Configuration")
    print("=" * 60)
    print(f"App Name: {config.app_name}")
    print(f"Version: {config.version}")
    print(f"Debug Mode: {config.debug}")
    print(f"Timezone: {config.timezone}")
    print("-" * 60)
    print(f"LLM Model: {config.llm.model_name}")
    print(f"LLM Base URL: {config.llm.base_url}")
    print(f"LLM API Key: {'***' + config.llm.api_key[-4:] if config.llm.api_key else 'NOT SET'}")
    print("-" * 60)
    print(f"Database Host: {config.database.host}:{config.database.port}")
    print(f"Database Name: {config.database.database}")
    print("-" * 60)
    print(f"Weather Agent: {config.agents.weather_url}")
    print(f"Ticket Agent: {config.agents.ticket_url}")
    print(f"Order Agent: {config.agents.order_url}")
    print("-" * 60)
    print(f"Weather MCP: {config.mcp.weather_url}")
    print(f"Ticket MCP: {config.mcp.ticket_url}")
    print(f"Order MCP: {config.mcp.order_url}")
    print("=" * 60)


if __name__ == "__main__":
    print_config()
