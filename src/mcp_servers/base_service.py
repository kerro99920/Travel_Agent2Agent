#!/usr/bin/env python3
"""
MCP服务基类
src/mcp_servers/base_service.py

提供MCP服务的通用功能
"""

import json
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

import mysql.connector
from mysql.connector import Error as MySQLError

from src.config import config, logger


class DateTimeEncoder(json.JSONEncoder):
    """自定义JSON编码器，处理日期时间类型"""

    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        if isinstance(obj, date):
            return obj.strftime('%Y-%m-%d')
        if isinstance(obj, timedelta):
            return str(obj)
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


class DatabaseService:
    """数据库服务基类"""

    def __init__(self):
        """初始化数据库连接"""
        self._conn = None
        self._connect()

    def _connect(self):
        """建立数据库连接"""
        try:
            self._conn = mysql.connector.connect(
                host=config.database.host,
                port=config.database.port,
                user=config.database.user,
                password=config.database.password,
                database=config.database.name,
                charset='utf8mb4',
                autocommit=True
            )
            logger.info("数据库连接成功")
        except MySQLError as e:
            logger.error(f"数据库连接失败: {e}")
            raise

    def _ensure_connection(self):
        """确保数据库连接有效"""
        try:
            if self._conn is None or not self._conn.is_connected():
                self._connect()
        except MySQLError:
            self._connect()

    def execute_query(self, sql: str) -> str:
        """
        执行SQL查询

        Args:
            sql: SQL查询语句

        Returns:
            JSON格式的查询结果
        """
        self._ensure_connection()

        try:
            cursor = self._conn.cursor(dictionary=True)
            cursor.execute(sql)
            results = cursor.fetchall()
            cursor.close()

            # 格式化特殊类型
            for row in results:
                for key, value in row.items():
                    if isinstance(value, (date, datetime, timedelta, Decimal)):
                        row[key] = self._encode_value(value)

            if results:
                return json.dumps(
                    {"status": "success", "data": results},
                    cls=DateTimeEncoder,
                    ensure_ascii=False
                )
            else:
                return json.dumps(
                    {"status": "no_data", "message": "未找到数据"},
                    ensure_ascii=False
                )

        except MySQLError as e:
            logger.error(f"SQL执行错误: {e}")
            return json.dumps(
                {"status": "error", "message": str(e)},
                ensure_ascii=False
            )

    def execute_insert(self, sql: str, params: tuple = None) -> Dict[str, Any]:
        """
        执行INSERT语句

        Args:
            sql: INSERT语句
            params: 参数元组

        Returns:
            执行结果字典
        """
        self._ensure_connection()

        try:
            cursor = self._conn.cursor()
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)

            self._conn.commit()
            last_id = cursor.lastrowid
            cursor.close()

            return {"status": "success", "id": last_id}

        except MySQLError as e:
            logger.error(f"INSERT执行错误: {e}")
            self._conn.rollback()
            return {"status": "error", "message": str(e)}

    def execute_update(self, sql: str, params: tuple = None) -> Dict[str, Any]:
        """
        执行UPDATE语句

        Args:
            sql: UPDATE语句
            params: 参数元组

        Returns:
            执行结果字典
        """
        self._ensure_connection()

        try:
            cursor = self._conn.cursor()
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)

            self._conn.commit()
            affected = cursor.rowcount
            cursor.close()

            return {"status": "success", "affected_rows": affected}

        except MySQLError as e:
            logger.error(f"UPDATE执行错误: {e}")
            self._conn.rollback()
            return {"status": "error", "message": str(e)}

    def _encode_value(self, value: Any) -> Any:
        """编码特殊类型值"""
        if isinstance(value, datetime):
            return value.strftime('%Y-%m-%d %H:%M:%S')
        if isinstance(value, date):
            return value.strftime('%Y-%m-%d')
        if isinstance(value, timedelta):
            return str(value)
        if isinstance(value, Decimal):
            return float(value)
        return value

    def close(self):
        """关闭数据库连接"""
        if self._conn and self._conn.is_connected():
            self._conn.close()
            logger.info("数据库连接已关闭")
