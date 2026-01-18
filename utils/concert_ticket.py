#!/usr/bin/env python3
"""
演唱会票务数据生成器 - Ticketmaster API版
表名: concert_tickets

使用Ticketmaster Discovery API获取全球演唱会数据
API文档: https://developer.ticketmaster.com/products-and-docs/apis/discovery-api/v2/
免费版: 5000次/天
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

# Ticketmaster API配置
TICKETMASTER_API_KEY = "bjwCb6Rjy3GZhmVSSNKfqIKGvUK4WNjo"  # 替换为您的 Consumer Key
TICKETMASTER_URL = "https://app.ticketmaster.com/discovery/v2"

# MySQL 配置
db_config = {
    "host": "localhost",
    "user": "root",
    "password": "123456",
    "database": "travel_rag",
    "charset": "utf8mb4"
}

# ==================== 可查询的城市和国家 ====================
# Ticketmaster 在这些地区数据较全
# 格式: (城市名英文, 国家代码, 城市名中文)

QUERYABLE_CITIES = [
    # ===== 美国主要城市 =====
    ("New York", "US", "纽约"),
    ("Los Angeles", "US", "洛杉矶"),
    ("Chicago", "US", "芝加哥"),
    ("Houston", "US", "休斯顿"),
    ("Las Vegas", "US", "拉斯维加斯"),
    ("Miami", "US", "迈阿密"),
    ("San Francisco", "US", "旧金山"),
    ("Seattle", "US", "西雅图"),
    ("Boston", "US", "波士顿"),
    ("Atlanta", "US", "亚特兰大"),

    # ===== 加拿大 =====
    ("Toronto", "CA", "多伦多"),
    ("Vancouver", "CA", "温哥华"),
    ("Montreal", "CA", "蒙特利尔"),

    # ===== 英国 =====
    ("London", "GB", "伦敦"),
    ("Manchester", "GB", "曼彻斯特"),
    ("Birmingham", "GB", "伯明翰"),

    # ===== 欧洲其他 =====
    ("Paris", "FR", "巴黎"),
    ("Berlin", "DE", "柏林"),
    ("Amsterdam", "NL", "阿姆斯特丹"),
    ("Madrid", "ES", "马德里"),

    # ===== 澳洲 =====
    ("Sydney", "AU", "悉尼"),
    ("Melbourne", "AU", "墨尔本"),

    # ===== 亚洲（数据较少）=====
    ("Tokyo", "JP", "东京"),
    ("Singapore", "SG", "新加坡"),
]

# 热门搜索关键词（艺人/类型）
SEARCH_KEYWORDS = [
    "Taylor Swift",
    "Ed Sheeran",
    "Coldplay",
    "Bruno Mars",
    "The Weeknd",
    "Drake",
    "Beyonce",
    "Adele",
    "BTS",
    "Blackpink",
    "Jay Chou",  # 周杰伦
    "Mayday",  # 五月天
    "concert",
    "music festival",
    "rock",
    "pop",
    "hip hop",
    "jazz",
    "classical",
    "k-pop",
]


# ==================== 数据库连接 ====================
def connect_db():
    return mysql.connector.connect(**db_config)


# ==================== Ticketmaster API ====================
def fetch_events_by_city(city, country_code, size=20):
    """
    按城市获取演唱会数据
    """
    if not TICKETMASTER_API_KEY or TICKETMASTER_API_KEY == "您的ConsumerKey":
        print("⚠️ 请先配置 TICKETMASTER_API_KEY!")
        return None

    url = f"{TICKETMASTER_URL}/events.json"

    params = {
        "apikey": TICKETMASTER_API_KEY,
        "city": city,
        "countryCode": country_code,
        "classificationName": "music",  # 只搜索音乐类活动
        "size": size,
        "sort": "date,asc"  # 按日期排序
    }

    try:
        print(f"  请求: {city}, {country_code}")
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        if "_embedded" not in data:
            print(f"  ✗ 无数据")
            return None

        events = data["_embedded"].get("events", [])
        print(f"  ✓ 获取 {len(events)} 条")
        return events

    except requests.exceptions.RequestException as e:
        print(f"  ✗ 请求失败: {e}")
        return None
    except json.JSONDecodeError:
        print("  ✗ 解析失败")
        return None


def fetch_events_by_keyword(keyword, country_code="US", size=20):
    """
    按关键词搜索演唱会数据
    """
    if not TICKETMASTER_API_KEY or TICKETMASTER_API_KEY == "您的ConsumerKey":
        print("⚠️ 请先配置 TICKETMASTER_API_KEY!")
        return None

    url = f"{TICKETMASTER_URL}/events.json"

    params = {
        "apikey": TICKETMASTER_API_KEY,
        "keyword": keyword,
        "countryCode": country_code,
        "classificationName": "music",
        "size": size,
        "sort": "date,asc"
    }

    try:
        print(f"  搜索: {keyword} ({country_code})")
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        if "_embedded" not in data:
            print(f"  ✗ 无数据")
            return None

        events = data["_embedded"].get("events", [])
        print(f"  ✓ 获取 {len(events)} 条")
        return events

    except requests.exceptions.RequestException as e:
        print(f"  ✗ 请求失败: {e}")
        return None
    except json.JSONDecodeError:
        print("  ✗ 解析失败")
        return None


def convert_api_to_db_format(api_events, city_cn):
    """将API数据转换为数据库格式"""
    db_records = []

    for event in api_events:
        try:
            # 获取艺人名称
            artist = "未知艺人"
            if "_embedded" in event and "attractions" in event["_embedded"]:
                attractions = event["_embedded"]["attractions"]
                if attractions:
                    artist = attractions[0].get("name", "未知艺人")
            else:
                # 使用活动名称
                artist = event.get("name", "未知艺人")

            # 获取场馆信息
            venue = "未知场馆"
            venue_city = city_cn
            if "_embedded" in event and "venues" in event["_embedded"]:
                venues = event["_embedded"]["venues"]
                if venues:
                    venue = venues[0].get("name", "未知场馆")
                    # 获取城市（如果有）
                    venue_city_info = venues[0].get("city", {})
                    if venue_city_info:
                        venue_city = venue_city_info.get("name", city_cn)

            # 获取时间
            dates = event.get("dates", {}).get("start", {})
            date_str = dates.get("localDate")
            time_str = dates.get("localTime", "19:00:00")

            if not date_str:
                continue

            # 解析时间
            start_time = parse_datetime(f"{date_str}T{time_str}")
            if not start_time:
                continue

            # 演唱会一般持续2-3小时
            duration_hours = random.choice([2, 2.5, 3])
            end_time = start_time + timedelta(hours=duration_hours)

            # 获取票价范围
            base_price = 500  # 默认基础价格
            if "priceRanges" in event:
                price_ranges = event["priceRanges"]
                if price_ranges:
                    min_price = price_ranges[0].get("min", 50)
                    max_price = price_ranges[0].get("max", 500)
                    base_price = (min_price + max_price) / 2
                    # 转换为人民币（假设1:7汇率）
                    base_price = base_price * 7

            # 生成多种票类型
            ticket_types = [
                ("看台票", base_price * 0.6, random.randint(5000, 10000), random.randint(100, 2000)),
                ("内场票", base_price, random.randint(2000, 5000), random.randint(50, 500)),
                ("VIP票", base_price * 2, random.randint(500, 1000), random.randint(10, 100)),
                ("SVIP票", base_price * 3.5, random.randint(100, 300), random.randint(0, 30)),
            ]

            for ticket_type, price, total, remaining in ticket_types:
                db_records.append({
                    "artist": artist[:100],  # 限制长度
                    "city": venue_city[:50] if venue_city else city_cn,
                    "venue": venue[:100],
                    "start_time": start_time,
                    "end_time": end_time,
                    "ticket_type": ticket_type,
                    "total_seats": total,
                    "remaining_seats": remaining,
                    "price": round(price, 2)
                })

        except Exception as e:
            print(f"  ⚠️ 转换错误: {e}")
            continue

    return db_records


def parse_datetime(time_str):
    """解析时间"""
    if not time_str:
        return None
    try:
        # 处理多种格式
        for fmt in ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d"]:
            try:
                dt = datetime.strptime(time_str.split("+")[0].split("Z")[0], fmt)
                return dt
            except ValueError:
                continue
        return None
    except:
        return None


# ==================== 数据库操作 ====================
def get_latest_created_time(cursor):
    cursor.execute("SELECT MAX(created_at) FROM concert_tickets")
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


def store_concert_data(conn, cursor, concerts):
    if not concerts:
        return 0

    insert_query = """
    INSERT INTO concert_tickets (
        artist, city, venue, start_time, end_time,
        ticket_type, total_seats, remaining_seats, price
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
        venue = VALUES(venue),
        total_seats = VALUES(total_seats),
        remaining_seats = VALUES(remaining_seats),
        price = VALUES(price)
    """

    success = 0
    for c in concerts:
        try:
            cursor.execute(insert_query, (
                c["artist"], c["city"], c["venue"],
                c["start_time"], c["end_time"],
                c["ticket_type"], c["total_seats"],
                c["remaining_seats"], c["price"]
            ))
            success += 1
            print(f"  ✓ {c['artist']} @ {c['city']} - {c['ticket_type']}")
        except mysql.connector.Error as e:
            pass

    conn.commit()
    return success


# ==================== 主函数 ====================
def update_concerts_by_city(force_update=False, max_cities=5):
    """
    按城市获取演唱会数据

    参数:
        max_cities: 查询城市数（控制API调用次数）
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
    print("Ticketmaster API - 演唱会数据获取（按城市）")
    print(f"计划查询 {max_cities} 个城市")
    print("=" * 60)

    all_concerts = []
    cities = QUERYABLE_CITIES[:max_cities]

    for i, (city_en, country_code, city_cn) in enumerate(cities, 1):
        print(f"\n[{i}/{len(cities)}] {city_cn} ({city_en})")

        api_data = fetch_events_by_city(city_en, country_code, size=20)

        if api_data:
            converted = convert_api_to_db_format(api_data, city_cn)
            all_concerts.extend(converted)

        time.sleep(0.5)  # 避免限流

    print(f"\n{'=' * 60}")
    print(f"共获取 {len(all_concerts)} 条记录")

    if all_concerts:
        success = store_concert_data(conn, cursor, all_concerts)
        print(f"\n写入成功: {success} 条")

    cursor.close()
    conn.close()


def update_concerts_by_keyword(force_update=False, max_keywords=5):
    """
    按关键词搜索演唱会数据

    参数:
        max_keywords: 搜索关键词数
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
    print("Ticketmaster API - 演唱会数据获取（按艺人）")
    print(f"计划搜索 {max_keywords} 个关键词")
    print("=" * 60)

    all_concerts = []
    keywords = SEARCH_KEYWORDS[:max_keywords]

    for i, keyword in enumerate(keywords, 1):
        print(f"\n[{i}/{len(keywords)}] 搜索: {keyword}")

        api_data = fetch_events_by_keyword(keyword, country_code="US", size=10)

        if api_data:
            converted = convert_api_to_db_format(api_data, "")
            all_concerts.extend(converted)

        time.sleep(0.5)

    print(f"\n{'=' * 60}")
    print(f"共获取 {len(all_concerts)} 条记录")

    if all_concerts:
        success = store_concert_data(conn, cursor, all_concerts)
        print(f"\n写入成功: {success} 条")

    cursor.close()
    conn.close()


def setup_scheduler():
    schedule.every().day.at("04:00").do(update_concerts_by_city, max_cities=10)
    schedule.every().day.at("04:30").do(update_concerts_by_keyword, max_keywords=10)
    print("\n定时任务:")
    print("  - 每天04:00 按城市更新")
    print("  - 每天04:30 按艺人更新")
    while True:
        schedule.run_pending()
        time.sleep(60)


# ==================== 入口 ====================
if __name__ == "__main__":
    print("=" * 60)
    print("演唱会数据生成器 - Ticketmaster API")
    print("=" * 60)

    if TICKETMASTER_API_KEY == "您的ConsumerKey":
        print("\n⚠️  请配置 TICKETMASTER_API_KEY")
        print("   注册: https://developer.ticketmaster.com")
        print("\n在脚本第18行修改:")
        print('   TICKETMASTER_API_KEY = "您的真实ConsumerKey"')
        exit(1)

    print(f"API Key: {TICKETMASTER_API_KEY[:8]}...")
    print(f"可查城市: {len(QUERYABLE_CITIES)} 个")
    print(f"搜索关键词: {len(SEARCH_KEYWORDS)} 个")
    print("=" * 60)

    # 方式1: 按城市查询（推荐）
    update_concerts_by_city(force_update=True, max_cities=5)

    # 方式2: 按艺人/关键词搜索
    # update_concerts_by_keyword(force_update=True, max_keywords=5)

    # 定时任务（可选）
    # setup_scheduler()