#!/usr/bin/env python3
"""
票务查询服务器验证脚本
check_ticket_server.py

验证 ticket_server.py 的各项功能
注意：此文件不使用 pytest，请直接运行 python check_ticket_server.py
"""

import asyncio
import httpx
import json
import uuid
from datetime import datetime, timedelta

# ==================== 配置 ====================
TICKET_SERVER_URL = "http://127.0.0.1:5006"


# ==================== 工具函数 ====================
async def send_a2a_request(message: str) -> dict:
    """
    发送A2A请求到票务服务器

    Args:
        message: 用户消息

    Returns:
        服务器响应
    """
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
            f"{TICKET_SERVER_URL}/a2a",
            json=request_data,
            headers={"Content-Type": "application/json"}
        )
        return response.json()


def print_result(test_name: str, result: dict):
    """打印测试结果"""
    print(f"\n{'=' * 60}")
    print(f"测试: {test_name}")
    print('=' * 60)

    if "result" in result:
        task_result = result["result"]
        state = task_result.get("state", "unknown")
        message = task_result.get("message", {})
        content = message.get("content", "") if isinstance(message, dict) else str(message)

        print(f"状态: {state}")
        print(f"响应:\n{content}")
    elif "error" in result:
        print(f"错误: {result['error']}")
    else:
        print(f"原始响应: {json.dumps(result, ensure_ascii=False, indent=2)}")


# ==================== 验证用例 ====================
async def check_train_ticket_query():
    """验证火车票查询"""
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')

    test_cases = [
        f"查询{tomorrow}北京到上海的高铁票",
        "明天广州到深圳的火车票",
        "北京到杭州的二等座",
        "查询G1001次列车",
    ]

    print("\n" + "=" * 60)
    print("🚄 火车票查询测试")
    print("=" * 60)

    for query in test_cases:
        result = await send_a2a_request(query)
        print_result(query, result)
        await asyncio.sleep(1)


async def check_flight_ticket_query():
    """验证机票查询"""
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')

    test_cases = [
        f"查询{tomorrow}上海到北京的机票",
        "明天深圳飞广州的经济舱",
        "北京到成都的航班",
    ]

    print("\n" + "=" * 60)
    print("✈️ 机票查询测试")
    print("=" * 60)

    for query in test_cases:
        result = await send_a2a_request(query)
        print_result(query, result)
        await asyncio.sleep(1)


async def check_concert_ticket_query():
    """验证演唱会票查询"""
    test_cases = [
        "周杰伦北京演唱会",
        "五月天上海演唱会门票",
        "刀郎广州站VIP票",
    ]

    print("\n" + "=" * 60)
    print("🎤 演唱会票查询测试")
    print("=" * 60)

    for query in test_cases:
        result = await send_a2a_request(query)
        print_result(query, result)
        await asyncio.sleep(1)


async def check_input_required():
    """验证信息不足时的追问"""
    test_cases = [
        "火车票",
        "机票",
        "演唱会",
        "查票",
    ]

    print("\n" + "=" * 60)
    print("❓ 追问测试（信息不足）")
    print("=" * 60)

    for query in test_cases:
        result = await send_a2a_request(query)
        print_result(query, result)
        await asyncio.sleep(1)


async def check_agent_card():
    """验证获取Agent卡片"""
    print("\n" + "=" * 60)
    print("📇 Agent卡片测试")
    print("=" * 60)

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(f"{TICKET_SERVER_URL}/.well-known/agent.json")

        if response.status_code == 200:
            card = response.json()
            print(f"名称: {card.get('name')}")
            print(f"描述: {card.get('description')}")
            print(f"版本: {card.get('version')}")
            print(f"技能:")
            for skill in card.get('skills', []):
                print(f"  - {skill.get('name')}: {skill.get('description')}")
        else:
            print(f"获取失败: HTTP {response.status_code}")


async def check_health():
    """验证健康检查"""
    print("\n" + "=" * 60)
    print("💚 健康检查测试")
    print("=" * 60)

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(f"{TICKET_SERVER_URL}/health")
            print(f"状态码: {response.status_code}")
            print(f"响应: {response.text}")
        except Exception as e:
            print(f"健康检查失败: {e}")


# ==================== 主验证函数 ====================
async def run_all_checks():
    """运行所有验证"""
    print("=" * 60)
    print("🎫 票务查询服务器验证")
    print(f"服务器地址: {TICKET_SERVER_URL}")
    print("=" * 60)

    # 健康检查
    await check_health()

    # Agent卡片
    await check_agent_card()

    # 火车票查询
    await check_train_ticket_query()

    # 机票查询
    await check_flight_ticket_query()

    # 演唱会查询
    await check_concert_ticket_query()

    # 追问验证
    await check_input_required()

    print("\n" + "=" * 60)
    print("✅ 所有验证完成")
    print("=" * 60)


async def run_single_check(query: str):
    """运行单个验证"""
    print(f"查询: {query}")
    result = await send_a2a_request(query)
    print_result("单次查询", result)


# ==================== 入口 ====================
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # 命令行参数作为查询
        query = ' '.join(sys.argv[1:])
        asyncio.run(run_single_check(query))
    else:
        # 运行所有验证
        asyncio.run(run_all_checks())