#!/usr/bin/env python3
"""
火车票数据生成器
仿照天气数据爬取脚本结构
表名: train_tickets
生成120条随机数据并写入MySQL
"""

import mysql.connector
from datetime import datetime, timedelta
import schedule
import time
import random
import pytz

# 配置
TZ = pytz.timezone('Asia/Shanghai')

# 线路配置 (出发城市, 到达城市, 车次列表, 行程时长分钟, 二等座价格, 一等座价格)
ROUTES = [
    ("上海", "杭州", ["G7325", "G7501", "G7321", "D3101", "G7535"], 50, 73.00, 117.00),
    ("北京", "上海", ["G1001", "G1003", "G101", "G105", "G111"], 270, 553.50, 933.50),
    ("广州", "深圳", ["D2288", "G6001", "C6701", "G6011", "D2302"], 45, 79.50, 127.00),
    ("成都", "重庆", ["C6003", "G8501", "D1801", "C6005", "G8681"], 100, 65.00, 104.00),
    ("上海", "南京", ["G7001", "G7003", "D3001", "G7101", "G7105"], 70, 134.50, 214.50),
    ("北京", "天津", ["C2001", "C2003", "C2005", "C2007", "C2009"], 35, 54.50, 88.00),
    ("深圳", "广州", ["G6002", "D2289", "C6702", "G6012", "D2303"], 45, 79.50, 127.00),
    ("武汉", "长沙", ["G1113", "G403", "G1101", "G505", "G401"], 90, 164.50, 263.00),
]

DEPARTURE_TIMES = [
    "06:30", "07:00", "07:30", "08:00", "08:30", "09:00", "09:15", "09:30",
    "10:00", "10:30", "11:00", "12:00", "13:00", "14:00", "14:30", "15:00",
    "16:00", "17:00", "18:00", "18:30", "19:00", "20:00", "21:00"
]

# MySQL 配置
db_config = {
    "host": "localhost",
    "user": "root",
    "password": "123456",
    "database": "travel_rag",
    "charset": "utf8mb4"
}


def connect_db():
    return mysql.connector.connect(**db_config)


def generate_ticket_data():
    """生成120条车票数据（模拟从API获取数据）"""
    tickets = []
    base_date = datetime(2025, 8, 12)
    dates = [base_date + timedelta(days=i) for i in range(5)]

    for route in ROUTES:
        dep_city, arr_city, train_list, duration, price_2, price_1 = route

        for train_no in train_list:
            selected_times = random.sample(DEPARTURE_TIMES, random.randint(1, 2))

            for dep_time_str in selected_times:
                travel_date = random.choice(dates)
                dep_datetime = datetime.strptime(
                    f"{travel_date.strftime('%Y-%m-%d')} {dep_time_str}:00",
                    "%Y-%m-%d %H:%M:%S"
                )
                arr_datetime = dep_datetime + timedelta(minutes=duration)

                # 二等座
                tickets.append({
                    "departure_city": dep_city,
                    "arrival_city": arr_city,
                    "departure_time": dep_datetime,
                    "arrival_time": arr_datetime,
                    "train_number": train_no,
                    "seat_type": "二等座",
                    "total_seats": random.randint(500, 1200),
                    "remaining_seats": random.randint(50, 600),
                    "price": price_2
                })

                # 一等座
                tickets.append({
                    "departure_city": dep_city,
                    "arrival_city": arr_city,
                    "departure_time": dep_datetime,
                    "arrival_time": arr_datetime,
                    "train_number": train_no,
                    "seat_type": "一等座",
                    "total_seats": random.randint(200, 400),
                    "remaining_seats": random.randint(20, 150),
                    "price": price_1
                })

    # 补充到120条
    while len(tickets) < 120:
        route = random.choice(ROUTES)
        dep_city, arr_city, train_list, duration, price_2, price_1 = route
        train_no = random.choice(train_list)
        dep_time_str = random.choice(DEPARTURE_TIMES)
        travel_date = random.choice(dates)

        dep_datetime = datetime.strptime(
            f"{travel_date.strftime('%Y-%m-%d')} {dep_time_str}:00",
            "%Y-%m-%d %H:%M:%S"
        )
        arr_datetime = dep_datetime + timedelta(minutes=duration)
        seat_type = random.choice(["二等座", "一等座"])
        price = price_2 if seat_type == "二等座" else price_1
        total = random.randint(500, 1200) if seat_type == "二等座" else random.randint(200, 400)
        remain = random.randint(50, 600) if seat_type == "二等座" else random.randint(20, 150)

        tickets.append({
            "departure_city": dep_city,
            "arrival_city": arr_city,
            "departure_time": dep_datetime,
            "arrival_time": arr_datetime,
            "train_number": train_no,
            "seat_type": seat_type,
            "total_seats": total,
            "remaining_seats": remain,
            "price": price
        })

    return tickets[:120]


def get_latest_created_time(cursor):
    """获取最新创建时间"""
    cursor.execute("SELECT MAX(created_at) FROM train_tickets")
    result = cursor.fetchone()
    return result[0] if result[0] else None


def should_update_data(latest_time, force_update=False):
    """判断是否需要更新数据"""
    if force_update:
        return True
    if not latest_time:
        return True
    current_time = datetime.now(TZ)
    if latest_time.tzinfo is None:
        latest_time = TZ.localize(latest_time)
    return (current_time - latest_time).total_seconds() / 3600 >= 24


def store_ticket_data(conn, cursor, tickets):
    """存储车票数据到数据库"""
    if not tickets:
        print("没有数据需要存储。")
        return

    insert_query = """
    INSERT INTO train_tickets (
        departure_city, arrival_city, departure_time, arrival_time,
        train_number, seat_type, total_seats, remaining_seats, price
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
        departure_city = VALUES(departure_city),
        arrival_city = VALUES(arrival_city),
        arrival_time = VALUES(arrival_time),
        total_seats = VALUES(total_seats),
        remaining_seats = VALUES(remaining_seats),
        price = VALUES(price)
    """

    for ticket in tickets:
        values = (
            ticket["departure_city"],
            ticket["arrival_city"],
            ticket["departure_time"],
            ticket["arrival_time"],
            ticket["train_number"],
            ticket["seat_type"],
            ticket["total_seats"],
            ticket["remaining_seats"],
            ticket["price"]
        )
        try:
            cursor.execute(insert_query, values)
            print(f"{ticket['departure_city']}->{ticket['arrival_city']} "
                  f"{ticket['departure_time'].strftime('%Y-%m-%d %H:%M')} "
                  f"{ticket['train_number']} {ticket['seat_type']} "
                  f"数据写入/更新成功, 影响行数: {cursor.rowcount}")
            conn.commit()
        except mysql.connector.Error as e:
            print(f"{ticket['train_number']} 数据库错误: {e}")
            conn.rollback()


def update_tickets(force_update=False):
    """更新火车票数据"""
    conn = connect_db()
    cursor = conn.cursor()

    latest_time = get_latest_created_time(cursor)
    if should_update_data(latest_time, force_update):
        print("开始更新火车票数据...")
        tickets = generate_ticket_data()
        print(f"生成了 {len(tickets)} 条车票数据")
        store_ticket_data(conn, cursor, tickets)
        print("火车票数据更新完成。")
    else:
        print(f"数据已为最新，无需更新。最新创建时间: {latest_time}")

    cursor.close()
    conn.close()


def setup_scheduler():
    """设置定时任务 - 每天凌晨1点更新"""
    schedule.every().day.at("01:00").do(update_tickets)
    print("定时任务已启动，每天凌晨1点更新数据...")
    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    print("=" * 60)
    print("火车票数据生成器 - 写入 train_tickets 表")
    print("=" * 60)

    # 立即执行一次更新（强制更新）
    update_tickets(force_update=True)

    # 启动定时任务
    setup_scheduler()