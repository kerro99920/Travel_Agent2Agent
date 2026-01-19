#!/usr/bin/env python3
"""
Agent集成测试
tests/test_agents.py

测试Agent服务的功能
"""

import asyncio
import json
import uuid
from datetime import datetime, timedelta

import pytest
import httpx


# 服务地址
WEATHER_AGENT_URL = "http://localhost:5005"
TICKET_AGENT_URL = "http://localhost:5006"
ORDER_AGENT_URL = "http://localhost:5007"


async def send_a2a_request(url: str, message: str) -> dict:
    """发送A2A请求"""
    request_data = {
        "jsonrpc": "2.0",
        "method": "tasks/send",
        "params": {
            "message": {
                "role": "user",
                "content": message
            }
        },
        "id": str(uuid.uuid4())
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{url}/a2a",
            json=request_data,
            headers={"Content-Type": "application/json"}
        )
        return response.json()


def extract_content(result: dict) -> str:
    """从响应中提取内容"""
    if "result" in result:
        task_result = result["result"]
        if isinstance(task_result, dict):
            message = task_result.get("message", {})
            if isinstance(message, dict):
                return message.get("content", "")
    return ""


def extract_state(result: dict) -> str:
    """从响应中提取状态"""
    if "result" in result:
        return result["result"].get("state", "")
    return ""


class TestWeatherAgent:
    """测试天气Agent"""

    @pytest.mark.asyncio
    async def test_query_weather_valid(self):
        """测试有效的天气查询"""
        result = await send_a2a_request(
            WEATHER_AGENT_URL,
            "北京明天天气怎么样"
        )

        state = extract_state(result)
        content = extract_content(result)

        # 应该是completed或input_required（如果没有数据）
        assert state in ["completed", "input_required"]

        if state == "completed":
            assert "北京" in content or "天气" in content

    @pytest.mark.asyncio
    async def test_query_weather_missing_city(self):
        """测试缺少城市的天气查询"""
        result = await send_a2a_request(
            WEATHER_AGENT_URL,
            "明天天气"
        )

        state = extract_state(result)
        assert state == "input_required"

    @pytest.mark.asyncio
    async def test_agent_card(self):
        """测试获取Agent卡片"""
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{WEATHER_AGENT_URL}/.well-known/agent.json")

        assert response.status_code == 200

        card = response.json()
        assert card.get("name") == "WeatherQueryAgent"
        assert "skills" in card


class TestTicketAgent:
    """测试票务Agent"""

    @pytest.mark.asyncio
    async def test_query_train_ticket(self):
        """测试火车票查询"""
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')

        result = await send_a2a_request(
            TICKET_AGENT_URL,
            f"查询{tomorrow}北京到上海的高铁票"
        )

        state = extract_state(result)
        content = extract_content(result)

        assert state in ["completed", "input_required"]

    @pytest.mark.asyncio
    async def test_query_flight_ticket(self):
        """测试机票查询"""
        result = await send_a2a_request(
            TICKET_AGENT_URL,
            "明天上海飞广州的机票"
        )

        state = extract_state(result)
        assert state in ["completed", "input_required"]

    @pytest.mark.asyncio
    async def test_query_concert_ticket(self):
        """测试演唱会票查询"""
        result = await send_a2a_request(
            TICKET_AGENT_URL,
            "周杰伦北京演唱会"
        )

        state = extract_state(result)
        assert state in ["completed", "input_required"]

    @pytest.mark.asyncio
    async def test_query_missing_info(self):
        """测试信息不足的查询"""
        result = await send_a2a_request(
            TICKET_AGENT_URL,
            "火车票"
        )

        state = extract_state(result)
        assert state == "input_required"


class TestOrderAgent:
    """测试订票Agent"""

    @pytest.mark.asyncio
    async def test_order_missing_contact(self):
        """测试缺少联系人的订票"""
        result = await send_a2a_request(
            ORDER_AGENT_URL,
            "订一张明天北京到上海的高铁票"
        )

        state = extract_state(result)
        content = extract_content(result)

        assert state == "input_required"
        assert "联系人" in content or "姓名" in content or "电话" in content

    @pytest.mark.asyncio
    async def test_order_with_contact(self):
        """测试带联系人的订票"""
        result = await send_a2a_request(
            ORDER_AGENT_URL,
            "订一张明天北京到上海的高铁票，二等座，张三，13800138000"
        )

        state = extract_state(result)
        # 可能是completed（订票成功）或input_required（需要选择或无票）
        assert state in ["completed", "input_required", "failed"]

    @pytest.mark.asyncio
    async def test_order_by_ticket_id(self):
        """测试通过票务ID订票"""
        result = await send_a2a_request(
            ORDER_AGENT_URL,
            "订票务ID 1的火车票，张三，13800138000"
        )

        state = extract_state(result)
        # 可能成功或失败（票不存在）
        assert state in ["completed", "failed", "input_required"]


class TestAgentHealth:
    """测试Agent健康状态"""

    @pytest.mark.asyncio
    async def test_weather_agent_health(self):
        """测试天气Agent健康状态"""
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{WEATHER_AGENT_URL}/.well-known/agent.json")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_ticket_agent_health(self):
        """测试票务Agent健康状态"""
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{TICKET_AGENT_URL}/.well-known/agent.json")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_order_agent_health(self):
        """测试订票Agent健康状态"""
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{ORDER_AGENT_URL}/.well-known/agent.json")
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
