#!/usr/bin/env python3
"""
SmartVoyage 日志配置模块
src/config/logging_config.py

统一的日志管理，支持控制台和文件输出
"""

import os
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from .settings import config


class LoggerFactory:
    """日志工厂类"""
    
    _loggers = {}
    _initialized = False
    
    @classmethod
    def _ensure_log_dir(cls):
        """确保日志目录存在"""
        log_dir = config.log.file_path.parent
        log_dir.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def _create_formatter(cls) -> logging.Formatter:
        """创建日志格式化器"""
        return logging.Formatter(config.log.format)
    
    @classmethod
    def _create_console_handler(cls) -> logging.StreamHandler:
        """创建控制台处理器"""
        handler = logging.StreamHandler()
        handler.setFormatter(cls._create_formatter())
        handler.setLevel(logging.INFO)
        return handler
    
    @classmethod
    def _create_file_handler(cls) -> RotatingFileHandler:
        """创建文件处理器（支持日志轮转）"""
        cls._ensure_log_dir()
        handler = RotatingFileHandler(
            filename=str(config.log.file_path),
            maxBytes=config.log.max_bytes,
            backupCount=config.log.backup_count,
            encoding='utf-8'
        )
        handler.setFormatter(cls._create_formatter())
        handler.setLevel(logging.DEBUG)
        return handler
    
    @classmethod
    def get_logger(cls, name: str = "SmartVoyage") -> logging.Logger:
        """
        获取Logger实例
        
        Args:
            name: 日志名称
            
        Returns:
            Logger实例
        """
        if name in cls._loggers:
            return cls._loggers[name]
        
        logger = logging.getLogger(name)
        logger.setLevel(getattr(logging, config.log.level.upper(), logging.INFO))
        logger.propagate = False
        
        # 避免重复添加处理器
        if not logger.handlers:
            logger.addHandler(cls._create_console_handler())
            logger.addHandler(cls._create_file_handler())
        
        cls._loggers[name] = logger
        return logger


# 默认Logger实例
logger = LoggerFactory.get_logger()


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    获取Logger实例的便捷函数
    
    Args:
        name: 日志名称，默认为SmartVoyage
        
    Returns:
        Logger实例
    """
    return LoggerFactory.get_logger(name or "SmartVoyage")


# 模块级别的日志函数
def debug(msg: str, *args, **kwargs):
    logger.debug(msg, *args, **kwargs)


def info(msg: str, *args, **kwargs):
    logger.info(msg, *args, **kwargs)


def warning(msg: str, *args, **kwargs):
    logger.warning(msg, *args, **kwargs)


def error(msg: str, *args, **kwargs):
    logger.error(msg, *args, **kwargs)


def critical(msg: str, *args, **kwargs):
    logger.critical(msg, *args, **kwargs)


if __name__ == "__main__":
    # 测试日志
    test_logger = get_logger("TestLogger")
    test_logger.debug("Debug message")
    test_logger.info("Info message")
    test_logger.warning("Warning message")
    test_logger.error("Error message")
    print(f"日志文件位置: {config.log.file_path}")
