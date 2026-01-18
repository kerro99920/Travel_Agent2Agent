#!/usr/bin/env python3
"""
航班机票数据生成器 - Aviationstack API版
表名: flight_tickets

使用Aviationstack API可查询到的热门航线（国际+港澳台）
API文档: https://aviationstack.com/documentation
免费版: 100次/月
"""

import mysql.connector
from datetime import datetime, timedelta
import requests
import schedule
import time
import random
import json
import pytz

# ==================== 配置区域 ====================
TZ = pytz.timezone('Asia/Shanghai')

# Aviationstack API配置
AVIATIONSTACK_API_KEY = "d85f22c765916114e2104a90dc374092"  # 替换为您的API Key
AVIATIONSTACK_URL = "http://api.aviationstack.com/v1/flights"

# MySQL 配置
db_config = {
    "host": "localhost",
    "user": "root",
    "password": "123456",
    "database": "travel_rag",
    "charset": "utf8mb4"
}

# ==================== Aviationstack可查询的热门航线 ====================
# 这些是API中数据较全的航线（国际航线为主）
# 格式: (出发机场IATA, 到达机场IATA, 城市名出发, 城市名到达)

QUERYABLE_ROUTES = [
    # ===== 中国出发国际航线（数据较全）=====
    ("PEK", "ICN", "北京", "首尔"),
    ("PEK", "NRT", "北京", "东京"),
    ("PEK", "SIN", "北京", "新加坡"),
    ("PEK", "BKK", "北京", "曼谷"),
    ("PEK", "HKG", "北京", "香港"),
    ("PVG", "ICN", "上海", "首尔"),
    ("PVG", "NRT", "上海", "东京"),
    ("PVG", "SIN", "上海", "新加坡"),
    ("PVG", "BKK", "上海", "曼谷"),
    ("PVG", "HKG", "上海", "香港"),
    ("CAN", "SIN", "广州", "新加坡"),
    ("CAN", "BKK", "广州", "曼谷"),
    ("CAN", "HKG", "广州", "香港"),
    ("SZX", "HKG", "深圳", "香港"),

    # ===== 亚洲区域航线（数据最全）=====
    ("HKG", "SIN", "香港", "新加坡"),
    ("HKG", "BKK", "香港", "曼谷"),
    ("HKG", "NRT", "香港", "东京"),
    ("HKG", "ICN", "香港", "首尔"),
    ("HKG", "TPE", "香港", "台北"),
    ("SIN", "BKK", "新加坡", "曼谷"),
    ("SIN", "KUL", "新加坡", "吉隆坡"),
    ("SIN", "HKG", "新加坡", "香港"),
    ("ICN", "NRT", "首尔", "东京"),
    ("ICN", "BKK", "首尔", "曼谷"),
    ("BKK", "SIN", "曼谷", "新加坡"),
    ("BKK", "HKG", "曼谷", "香港"),
    ("NRT", "SIN", "东京", "新加坡"),
    ("NRT", "BKK", "东京", "曼谷"),

    # ===== 欧美长途航线（数据较全）=====
    ("PEK", "LAX", "北京", "洛杉矶"),
    ("PEK", "JFK", "北京", "纽约"),
    ("PEK", "LHR", "北京", "伦敦"),
    ("PEK", "CDG", "北京", "巴黎"),
    ("PVG", "LAX", "上海", "洛杉矶"),
    ("PVG", "JFK", "上海", "纽约"),
    ("PVG", "LHR", "上海", "伦敦"),
    ("HKG", "LHR", "香港", "伦敦"),
    ("HKG", "LAX", "香港", "洛杉矶"),
    ("SIN", "LHR", "新加坡", "伦敦"),
]


# ==================== 数据库连接 ====================
def connect_db():
    return mysql.connector.connect(**db_config)


# ==================== Aviationstack API ====================
def fetch_flights_from_api(dep_iata=None, arr_iata=None, limit=100):
    """
    从 Aviationstack API 获取航班数据
    """
    if not AVIATIONSTACK_API_KEY or AVIATIONSTACK_API_KEY == "您的API_KEY":
        print("⚠️ 请先配置 AVIATIONSTACK_API_KEY!")
        return None

    params = {
        "access_key": AVIATIONSTACK_API_KEY,
        "limit": limit
    }

    if dep_iata:
        params["dep_iata"] = dep_iata
    if arr_iata:
        params["arr_iata"] = arr_iata

    try:
        print(f"  请求: {dep_iata} -> {arr_iata}")
        response = requests.get(AVIATIONSTACK_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        if "error" in data:
            error = data["error"]
            print(f"  ✗ 错误: {error.get('message', '未知')}")
            return None

        flights = data.get("data", [])
        print(f"  ✓ 获取 {len(flights)} 条")
        return flights

    except requests.exceptions.RequestException as e:
        print(f"  ✗ 请求失败: {e}")
        return None
    except json.JSONDecodeError:
        print("  ✗ 解析失败")
        return None


def convert_api_to_db_format(api_flights, dep_city, arr_city):
    """将API数据转换为数据库格式"""
    db_records = []

    for flight in api_flights:
        try:
            departure = flight.get("departure", {})
            arrival = flight.get("arrival", {})
            flight_info = flight.get("flight", {})

            dep_time_str = departure.get("scheduled")
            arr_time_str = arrival.get("scheduled")

            if not dep_time_str or not arr_time_str:
                continue

            dep_time = parse_datetime(dep_time_str)
            arr_time = parse_datetime(arr_time_str)

            if not dep_time or not arr_time:
                continue

            flight_number = flight_info.get("iata", "")
            if not flight_number:
                continue

            # 计算票价
            duration = (arr_time - dep_time).seconds // 60
            base_price = calculate_price(duration)

            # 三种舱位
            cabins = [
                ("经济舱", base_price, random.randint(120, 200), random.randint(10, 100)),
                ("商务舱", base_price * 2.5, random.randint(20, 48), random.randint(2, 20)),
                ("头等舱", base_price * 5, random.randint(8, 16), random.randint(0, 8)),
            ]

            for cabin_type, price, total, remaining in cabins:
                db_records.append({
                    "departure_city": dep_city,
                    "arrival_city": arr_city,
                    "departure_time": dep_time,
                    "arrival_time": arr_time,
                    "flight_number": flight_number,
                    "cabin_type": cabin_type,
                    "total_seats": total,
                    "remaining_seats": remaining,
                    "price": round(price, 2)
                })

        except Exception as e:
            continue

    return db_records


def parse_datetime(time_str):
    """解析时间"""
    if not time_str:
        return None
    try:
        time_str = time_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(time_str)
        dt = dt.astimezone(TZ)
        return dt.replace(tzinfo=None)
    except:
        return None


def calculate_price(duration_minutes):
    """根据飞行时长计算票价"""
    if duration_minutes < 120:
        return random.randint(600, 1200)
    elif duration_minutes < 240:
        return random.randint(1000, 2000)
    elif duration_minutes < 480:
        return random.randint(1800, 3500)
    else:
        return random.randint(3000, 8000)


# ==================== 数据库操作 ====================
def get_latest_created_time(cursor):
    cursor.execute("SELECT MAX(created_at) FROM flight_tickets")
    result = cursor.fetchone()
    return result[0] if result[0] else None


def should_update_data(latest_time, force_update=False):
    if force_update:
        return True
    if not latest_time:
        return True
    current_time = datetime.now(TZ)
    if latest_time.tzinfo is None:
        latest_time = TZ.localize(latest_time)
    return (current_time - latest_time).total_seconds() / 3600 >= 24


def store_flight_data(conn, cursor, flights):
    if not flights:
        return 0

    insert_query = """
    INSERT INTO flight_tickets (
        departure_city, arrival_city, departure_time, arrival_time,
        flight_number, cabin_type, total_seats, remaining_seats, price
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
        total_seats = VALUES(total_seats),
        remaining_seats = VALUES(remaining_seats),
        price = VALUES(price)
    """

    success = 0
    for f in flights:
        try:
            cursor.execute(insert_query, (
                f["departure_city"], f["arrival_city"],
                f["departure_time"], f["arrival_time"],
                f["flight_number"], f["cabin_type"],
                f["total_seats"], f["remaining_seats"], f["price"]
            ))
            success += 1
            print(f"  ✓ {f['departure_city']}->{f['arrival_city']} {f['flight_number']} {f['cabin_type']}")
        except mysql.connector.Error as e:
            pass

    conn.commit()
    return success


# ==================== 主函数 ====================
def update_flights(force_update=False, max_routes=10):
    """
    从API获取数据

    参数:
        max_routes: 查询航线数（控制API调用次数，免费版每月100次）
    """
    conn = connect_db()
    cursor = conn.cursor()

    latest_time = get_latest_created_time(cursor)
    if not should_update_data(latest_time, force_update):
        print(f"数据已最新: {latest_time}")
        cursor.close()
        conn.close()
        return

    print("=" * 60)
    print("Aviationstack API - 航班数据获取")
    print(f"计划查询 {max_routes} 条航线")
    print("=" * 60)

    all_flights = []
    routes = QUERYABLE_ROUTES[:max_routes]

    for i, (dep_iata, arr_iata, dep_city, arr_city) in enumerate(routes, 1):
        print(f"\n[{i}/{len(routes)}] {dep_city} -> {arr_city}")

        api_data = fetch_flights_from_api(dep_iata, arr_iata, limit=10)

        if api_data:
            converted = convert_api_to_db_format(api_data, dep_city, arr_city)
            all_flights.extend(converted)

        time.sleep(1)  # 避免限流

    print(f"\n{'=' * 60}")
    print(f"共获取 {len(all_flights)} 条记录")

    if all_flights:
        success = store_flight_data(conn, cursor, all_flights)
        print(f"\n写入成功: {success} 条")

    cursor.close()
    conn.close()


def setup_scheduler():
    schedule.every().day.at("03:00").do(update_flights)
    print("\n定时任务: 每天03:00更新")
    while True:
        schedule.run_pending()
        time.sleep(60)


# ==================== 入口 ====================
if __name__ == "__main__":
    print("=" * 60)
    print("航班数据生成器 - Aviationstack API")
    print("=" * 60)

    if AVIATIONSTACK_API_KEY == "您的API_KEY":
        print("\n⚠️  请配置 AVIATIONSTACK_API_KEY")
        print("   注册: https://aviationstack.com/signup/free")
        print("\n在脚本第18行修改:")
        print('   AVIATIONSTACK_API_KEY = "您的真实Key"')
        exit(1)

    print(f"API Key: {AVIATIONSTACK_API_KEY[:8]}...")
    print(f"可查航线: {len(QUERYABLE_ROUTES)} 条")
    print("=" * 60)

    # 查询前10条航线（每条消耗1次API调用）
    update_flights(force_update=True, max_routes=10)

    # 定时任务（可选）
    # setup_scheduler()