#!/usr/bin/env python3
"""
数据初始化脚本
scripts/init_data.py

初始化测试数据
"""

import random
from datetime import datetime, timedelta

import mysql.connector

from src.config import config


def get_connection():
    """获取数据库连接"""
    return mysql.connector.connect(
        host=config.database.host,
        port=config.database.port,
        user=config.database.user,
        password=config.database.password,
        database=config.database.name
    )


def init_weather_data():
    """初始化天气数据"""
    print("📊 初始化天气数据...")

    conn = get_connection()
    cursor = conn.cursor()

    cities = ["北京", "上海", "广州", "深圳"]
    weathers = ["晴", "多云", "阴", "小雨", "中雨", "雷阵雨"]
    base_date = datetime.now().date()

    count = 0
    for city in cities:
        temp_base = {"北京": 5, "上海": 10, "广州": 18, "深圳": 20}[city]

        for i in range(30):
            fx_date = base_date + timedelta(days=i)
            temp_max = temp_base + random.randint(5, 15)
            temp_min = temp_base + random.randint(-5, 5)

            sql = """
            INSERT INTO weather_data (
                city, fx_date, temp_max, temp_min, text_day, text_night,
                humidity, wind_dir_day, wind_scale_day, precip, uv_index
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE temp_max = VALUES(temp_max)
            """

            cursor.execute(sql, (
                city, fx_date, temp_max, temp_min,
                random.choice(weathers), random.choice(weathers),
                random.randint(30, 90),
                random.choice(["东风", "西风", "南风", "北风"]),
                random.choice(["1-2", "3-4", "4-5"]),
                round(random.uniform(0, 10), 1),
                random.randint(1, 10)
            ))
            count += 1

    conn.commit()
    cursor.close()
    conn.close()
    print(f"  ✅ 天气数据: {count} 条")


def init_train_tickets():
    """初始化火车票数据"""
    print("🚄 初始化火车票数据...")

    conn = get_connection()
    cursor = conn.cursor()

    routes = [
        ("北京", "上海", ["G101", "G103", "G105"], 270, 553.50, 933.50),
        ("上海", "杭州", ["G7501", "G7503", "G7505"], 50, 73.00, 117.00),
        ("广州", "深圳", ["G6001", "G6003", "G6005"], 45, 79.50, 127.00),
        ("成都", "重庆", ["G8501", "G8503", "G8505"], 100, 65.00, 104.00),
    ]

    times = ["07:00", "09:00", "11:00", "14:00", "16:00", "18:00"]
    base_date = datetime.now()

    count = 0
    for dep, arr, trains, duration, price2, price1 in routes:
        for train in trains:
            for day_offset in range(7):
                for time_str in random.sample(times, 3):
                    dep_time = (base_date + timedelta(days=day_offset)).replace(
                        hour=int(time_str.split(":")[0]),
                        minute=int(time_str.split(":")[1]),
                        second=0, microsecond=0
                    )
                    arr_time = dep_time + timedelta(minutes=duration)

                    for seat_type, price in [("二等座", price2), ("一等座", price1)]:
                        sql = """
                        INSERT INTO train_tickets (
                            departure_city, arrival_city, departure_time, arrival_time,
                            train_number, seat_type, total_seats, remaining_seats, price
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE remaining_seats = VALUES(remaining_seats)
                        """

                        cursor.execute(sql, (
                            dep, arr, dep_time, arr_time, train, seat_type,
                            random.randint(500, 1000), random.randint(50, 500), price
                        ))
                        count += 1

    conn.commit()
    cursor.close()
    conn.close()
    print(f"  ✅ 火车票数据: {count} 条")


def init_flight_tickets():
    """初始化机票数据"""
    print("✈️ 初始化机票数据...")

    conn = get_connection()
    cursor = conn.cursor()

    routes = [
        ("北京", "上海", ["CA1001", "MU5101", "CZ3101"], 130, 800, 2000, 4000),
        ("上海", "广州", ["CA1501", "MU5501", "CZ3501"], 150, 900, 2200, 4500),
        ("深圳", "北京", ["CA1801", "MU5801", "CZ3801"], 180, 1000, 2500, 5000),
    ]

    times = ["08:00", "10:00", "13:00", "15:00", "18:00", "20:00"]
    base_date = datetime.now()

    count = 0
    for dep, arr, flights, duration, eco_price, biz_price, first_price in routes:
        for flight in flights:
            for day_offset in range(7):
                for time_str in random.sample(times, 2):
                    dep_time = (base_date + timedelta(days=day_offset)).replace(
                        hour=int(time_str.split(":")[0]),
                        minute=int(time_str.split(":")[1]),
                        second=0, microsecond=0
                    )
                    arr_time = dep_time + timedelta(minutes=duration)

                    cabins = [
                        ("经济舱", eco_price, 150, 80),
                        ("商务舱", biz_price, 30, 15),
                        ("头等舱", first_price, 8, 4),
                    ]

                    for cabin, price, total, remain in cabins:
                        sql = """
                        INSERT INTO flight_tickets (
                            departure_city, arrival_city, departure_time, arrival_time,
                            flight_number, cabin_type, total_seats, remaining_seats, price
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE remaining_seats = VALUES(remaining_seats)
                        """

                        cursor.execute(sql, (
                            dep, arr, dep_time, arr_time, flight, cabin,
                            total, random.randint(0, remain), price
                        ))
                        count += 1

    conn.commit()
    cursor.close()
    conn.close()
    print(f"  ✅ 机票数据: {count} 条")


def init_concert_tickets():
    """初始化演唱会票数据"""
    print("🎤 初始化演唱会票数据...")

    conn = get_connection()
    cursor = conn.cursor()

    concerts = [
        ("周杰伦", "北京", "国家体育场", 680, 1280, 1880, 3880),
        ("周杰伦", "上海", "梅赛德斯奔驰中心", 680, 1280, 1880, 3880),
        ("五月天", "广州", "天河体育中心", 480, 880, 1580, 2880),
        ("刀郎", "深圳", "深圳湾体育中心", 380, 680, 1280, 2280),
    ]

    base_date = datetime.now()

    count = 0
    for artist, city, venue, p1, p2, p3, p4 in concerts:
        for day_offset in [7, 14, 21]:
            start_time = (base_date + timedelta(days=day_offset)).replace(
                hour=19, minute=30, second=0, microsecond=0
            )
            end_time = start_time + timedelta(hours=3)

            tickets = [
                ("看台票", p1, 5000, 2000),
                ("内场票", p2, 2000, 500),
                ("VIP票", p3, 500, 100),
                ("SVIP票", p4, 100, 20),
            ]

            for ticket_type, price, total, remain in tickets:
                sql = """
                INSERT INTO concert_tickets (
                    artist, city, venue, start_time, end_time,
                    ticket_type, total_seats, remaining_seats, price
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE remaining_seats = VALUES(remaining_seats)
                """

                cursor.execute(sql, (
                    artist, city, venue, start_time, end_time,
                    ticket_type, total, random.randint(0, remain), price
                ))
                count += 1

    conn.commit()
    cursor.close()
    conn.close()
    print(f"  ✅ 演唱会票数据: {count} 条")


def main():
    """主函数"""
    print("=" * 60)
    print("📦 SmartVoyage 数据初始化")
    print("=" * 60)

    try:
        init_weather_data()
        init_train_tickets()
        init_flight_tickets()
        init_concert_tickets()

        print("\n" + "=" * 60)
        print("✅ 数据初始化完成!")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 初始化失败: {e}")
        raise


if __name__ == "__main__":
    main()
