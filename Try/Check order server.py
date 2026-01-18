#!/usr/bin/env python3
"""
订票服务器验证脚本
check_order_server.py

验证 order_server.py 的各项功能
注意：此文件不使用 pytest，请直接运行 python check_order_server.py
"""

import asyncio
import httpx
import json
import uuid
from datetime import datetime, timedelta

# ==================== 配置 ====================
ORDER_SERVER_URL = "http://127.0.0.1:5007"
TICKET_SERVER_URL = "http://127.0.0.1:5006"


# ==================== 工具函数 ====================
async def send_a2a_request(url: str, message: str) -> dict:
    """
    发送A2A请求

    Args:
        url: 服务器URL
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

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{url}/a2a",
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

        state_emoji = {
            "completed": "✅",
            "failed": "❌",
            "input_required": "❓",
            "working": "⏳"
        }.get(state, "❔")

        print(f"状态: {state_emoji} {state}")
        print(f"响应:\n{content}")
    elif "error" in result:
        print(f"❌ 错误: {result['error']}")
    else:
        print(f"原始响应: {json.dumps(result, ensure_ascii=False, indent=2)}")


# ==================== 验证用例 ====================
async def check_book_train_ticket():
    """验证火车票预订"""
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')

    test_cases = [
        f"订一张{tomorrow}北京到上海的高铁票，二等座，张三，13800138000",
        "买明天广州到深圳的火车票，一等座，李四，13900139000，身份证110101199001011234",
    ]

    print("\n" + "=" * 60)
    print("🚄 火车票预订测试")
    print("=" * 60)

    for query in test_cases:
        result = await send_a2a_request(ORDER_SERVER_URL, query)
        print_result(query[:30] + "...", result)
        await asyncio.sleep(2)


async def check_book_flight_ticket():
    """验证机票预订"""
    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')

    test_cases = [
        f"订{tomorrow}上海到北京的机票，经济舱，王五，13700137000",
        "买明天深圳飞广州的商务舱，赵六，13600136000",
    ]

    print("\n" + "=" * 60)
    print("✈️ 机票预订测试")
    print("=" * 60)

    for query in test_cases:
        result = await send_a2a_request(ORDER_SERVER_URL, query)
        print_result(query[:30] + "...", result)
        await asyncio.sleep(2)


async def check_book_concert_ticket():
    """验证演唱会票预订"""
    test_cases = [
        "订周杰伦北京演唱会的内场票，孙七，13500135000",
        "买五月天上海站VIP票，2张，周八，13400134000",
    ]

    print("\n" + "=" * 60)
    print("🎤 演唱会票预订测试")
    print("=" * 60)

    for query in test_cases:
        result = await send_a2a_request(ORDER_SERVER_URL, query)
        print_result(query[:30] + "...", result)
        await asyncio.sleep(2)


async def check_book_by_ticket_id():
    """验证通过票务ID预订"""
    test_cases = [
        "订票务ID 1的火车票，张三，13800138000",
        "买票务ID 5的机票，2张，李四，13900139000",
        "购买票务ID 10的演唱会票，王五，13700137000",
    ]

    print("\n" + "=" * 60)
    print("🎫 通过票务ID预订测试")
    print("=" * 60)

    for query in test_cases:
        result = await send_a2a_request(ORDER_SERVER_URL, query)
        print_result(query, result)
        await asyncio.sleep(2)


async def check_input_required():
    """验证信息不足时的追问"""
    test_cases = [
        "订火车票",
        "买机票",
        "订票",
        "订一张北京到上海的火车票",  # 缺少联系人
        "订明天的高铁，张三，13800138000",  # 缺少城市
    ]

    print("\n" + "=" * 60)
    print("❓ 追问测试（信息不足）")
    print("=" * 60)

    for query in test_cases:
        result = await send_a2a_request(ORDER_SERVER_URL, query)
        print_result(query, result)
        await asyncio.sleep(1)


async def check_no_ticket_scenario():
    """验证无票情况"""
    test_cases = [
        "订2099年1月1日北京到火星的火车票，张三，13800138000",
        "买不存在航班的机票，李四，13900139000",
    ]

    print("\n" + "=" * 60)
    print("😔 无票情况测试")
    print("=" * 60)

    for query in test_cases:
        result = await send_a2a_request(ORDER_SERVER_URL, query)
        print_result(query[:30] + "...", result)
        await asyncio.sleep(2)


async def check_agent_card():
    """验证获取Agent卡片"""
    print("\n" + "=" * 60)
    print("📇 Agent卡片测试")
    print("=" * 60)

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(f"{ORDER_SERVER_URL}/.well-known/agent.json")

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


async def check_dependencies():
    """验证依赖服务是否可用"""
    print("\n" + "=" * 60)
    print("🔗 依赖服务检查")
    print("=" * 60)

    services = [
        ("订票服务器", ORDER_SERVER_URL),
        ("票务服务器", TICKET_SERVER_URL),
    ]

    async with httpx.AsyncClient(timeout=5.0) as client:
        for name, url in services:
            try:
                response = await client.get(f"{url}/.well-known/agent.json")
                if response.status_code == 200:
                    print(f"✅ {name} ({url}) - 正常")
                else:
                    print(f"⚠️ {name} ({url}) - HTTP {response.status_code}")
            except Exception as e:
                print(f"❌ {name} ({url}) - 无法连接: {e}")


# ==================== 交互式验证 ====================
async def interactive_check():
    """交互式验证"""
    print("\n" + "=" * 60)
    print("🎮 交互式订票测试")
    print("输入 'quit' 或 'exit' 退出")
    print("=" * 60)

    while True:
        try:
            query = input("\n请输入订票需求: ").strip()

            if query.lower() in ['quit', 'exit', 'q']:
                print("退出测试")
                break

            if not query:
                continue

            result = await send_a2a_request(ORDER_SERVER_URL, query)
            print_result("用户输入", result)

        except KeyboardInterrupt:
            print("\n退出测试")
            break
        except Exception as e:
            print(f"错误: {e}")


# ==================== 完整流程验证 ====================
async def check_full_booking_flow():
    """验证完整订票流程"""
    print("\n" + "=" * 60)
    print("🔄 完整订票流程测试")
    print("=" * 60)

    tomorrow = (datetime.now() + timedelta(days=1)).strftime('%m月%d日')

    # 步骤1: 先查询余票
    print("\n📋 步骤1: 查询余票")
    query_result = await send_a2a_request(
        TICKET_SERVER_URL,
        f"查询明天北京到上海的高铁票"
    )
    print_result("查询余票", query_result)

    await asyncio.sleep(2)

    # 步骤2: 下单
    print("\n📋 步骤2: 提交订单")
    book_result = await send_a2a_request(
        ORDER_SERVER_URL,
        f"订一张明天北京到上海的高铁票，二等座，测试用户，13800000000"
    )
    print_result("提交订单", book_result)


# ==================== 主验证函数 ====================
async def run_all_checks():
    """运行所有验证"""
    print("=" * 60)
    print("🎫 订票服务器验证")
    print(f"订票服务器: {ORDER_SERVER_URL}")
    print(f"票务服务器: {TICKET_SERVER_URL}")
    print("=" * 60)

    # 检查依赖服务
    await check_dependencies()

    # Agent卡片
    await check_agent_card()

    # 追问验证
    await check_input_required()

    # 通过票务ID预订
    await check_book_by_ticket_id()

    # 火车票预订
    await check_book_train_ticket()

    # 机票预订
    await check_book_flight_ticket()

    # 演唱会票预订
    await check_book_concert_ticket()

    # 无票情况
    await check_no_ticket_scenario()

    # 完整流程
    await check_full_booking_flow()

    print("\n" + "=" * 60)
    print("✅ 所有验证完成")
    print("=" * 60)


async def run_single_check(query: str):
    """运行单个验证"""
    print(f"订票请求: {query}")
    result = await send_a2a_request(ORDER_SERVER_URL, query)
    print_result("单次订票", result)


# ==================== 入口 ====================
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        arg = sys.argv[1]

        if arg == "-i" or arg == "--interactive":
            # 交互式验证
            asyncio.run(interactive_check())
        elif arg == "-f" or arg == "--flow":
            # 完整流程验证
            asyncio.run(check_full_booking_flow())
        elif arg == "-d" or arg == "--deps":
            # 依赖检查
            asyncio.run(check_dependencies())
        else:
            # 命令行参数作为查询
            query = ' '.join(sys.argv[1:])
            asyncio.run(run_single_check(query))
    else:
        # 运行所有验证
        asyncio.run(run_all_checks())