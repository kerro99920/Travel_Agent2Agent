import requests
import mysql.connector
from datetime import datetime, timedelta
import schedule
import time
import json
import gzip
import pytz

# 配置
API_KEY = "8707d53a847745ee95d02332aa39fe51"
city_codes = {
    "北京": "101010100",
    "上海": "101020100",
    "广州": "101280101",
    "深圳": "101280601"
}
BASE_URL = "https://ne5u9wc3nu.re.qweatherapi.com/v7/weather/30d"
TZ = pytz.timezone('Asia/Shanghai')  # 使用上海时区

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

def fetch_weather_data(city, location):
    headers = {
        "X-QW-Api-Key": API_KEY,
        "Accept-Encoding": "gzip"
    }
    url = f"{BASE_URL}?location={location}"
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        if response.headers.get('Content-Encoding') == 'gzip':
            data = gzip.decompress(response.content).decode('utf-8')
        else:
            data = response.text
        return json.loads(data)
    except requests.RequestException as e:
        print(f"请求 {city} 天气数据失败: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"{city} JSON 解析错误: {e}, 响应内容: {response.text[:500]}...")
        return None
    except gzip.BadGzipFile:
        print(f"{city} 数据未正确解压，尝试直接解析: {response.text[:500]}...")
        return json.loads(response.text) if response.text else None

def get_latest_update_time(cursor, city):
    cursor.execute("SELECT MAX(update_time) FROM weather_data WHERE city = %s", (city,))
    result = cursor.fetchone()
    return result[0] if result[0] else None

def should_update_data(latest_time, force_update=False):
    if force_update:
        return True
    if not latest_time:
        return True
    current_time = datetime.now(TZ)
    latest_time = latest_time.replace(tzinfo=TZ)
    return (current_time - latest_time).total_seconds() / 3600 >= 24

def store_weather_data(conn, cursor, city, data):
    if not data or data.get("code") != "200":
        print(f"{city} 数据无效，跳过存储。")
        return

    daily_data = data.get("daily", [])
    update_time = datetime.fromisoformat(data.get("updateTime").replace("+08:00", "+08:00")).replace(tzinfo=TZ)

    for day in daily_data:
        fx_date = datetime.strptime(day["fxDate"], "%Y-%m-%d").date()
        values = (
            city, fx_date,
            day.get("sunrise"), day.get("sunset"),
            day.get("moonrise"), day.get("moonset"),
            day.get("moonPhase"), day.get("moonPhaseIcon"),
            day.get("tempMax"), day.get("tempMin"),
            day.get("iconDay"), day.get("textDay"),
            day.get("iconNight"), day.get("textNight"),
            day.get("wind360Day"), day.get("windDirDay"), day.get("windScaleDay"), day.get("windSpeedDay"),
            day.get("wind360Night"), day.get("windDirNight"), day.get("windScaleNight"), day.get("windSpeedNight"),
            day.get("precip"), day.get("uvIndex"),
            day.get("humidity"), day.get("pressure"),
            day.get("vis"), day.get("cloud"),
            update_time
        )
        insert_query = """
        INSERT INTO weather_data (
            city, fx_date, sunrise, sunset, moonrise, moonset, moon_phase, moon_phase_icon,
            temp_max, temp_min, icon_day, text_day, icon_night, text_night,
            wind360_day, wind_dir_day, wind_scale_day, wind_speed_day,
            wind360_night, wind_dir_night, wind_scale_night, wind_speed_night,
            precip, uv_index, humidity, pressure, vis, cloud, update_time
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            sunrise = VALUES(sunrise), sunset = VALUES(sunset), moonrise = VALUES(moonrise),
            moonset = VALUES(moonset), moon_phase = VALUES(moon_phase), moon_phase_icon = VALUES(moon_phase_icon),
            temp_max = VALUES(temp_max), temp_min = VALUES(temp_min), icon_day = VALUES(icon_day),
            text_day = VALUES(text_day), icon_night = VALUES(icon_night), text_night = VALUES(text_night),
            wind360_day = VALUES(wind360_day), wind_dir_day = VALUES(wind_dir_day), wind_scale_day = VALUES(wind_scale_day),
            wind_speed_day = VALUES(wind_speed_day), wind360_night = VALUES(wind360_night),
            wind_dir_night = VALUES(wind_dir_night), wind_scale_night = VALUES(wind_scale_night),
            wind_speed_night = VALUES(wind_speed_night), precip = VALUES(precip), uv_index = VALUES(uv_index),
            humidity = VALUES(humidity), pressure = VALUES(pressure), vis = VALUES(vis),
            cloud = VALUES(cloud), update_time = VALUES(update_time)
        """
        try:
            cursor.execute(insert_query, values)
            print(f"{city} {fx_date} 数据写入/更新成功: {day.get('textDay')}, 影响行数: {cursor.rowcount}")
            conn.commit()
            print(f"{city} 事务提交完成。")
        except mysql.connector.Error as e:
            print(f"{city} {fx_date} 数据库错误: {e}")
            conn.rollback()
            print(f"{city} 事务回滚。")

def update_weather(force_update=False):
    conn = connect_db()
    cursor = conn.cursor()

    for city, location in city_codes.items():
        latest_time = get_latest_update_time(cursor, city)
        if should_update_data(latest_time, force_update):
            print(f"开始更新 {city} 天气数据...")
            data = fetch_weather_data(city, location)
            if data:
                store_weather_data(conn, cursor, city, data)
        else:
            print(f"{city} 数据已为最新，无需更新。最新更新时间: {latest_time}")

    cursor.close()
    conn.close()

def setup_scheduler():
    # 北京时间 1:00 对应 PDT 前一天的 16:00（夏令时）
    schedule.every().day.at("16:00").do(update_weather)
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    # 初始检查和更新
    with mysql.connector.connect(**db_config) as conn:
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS weather_data (
            id INT AUTO_INCREMENT PRIMARY KEY,
            city VARCHAR(50) NOT NULL COMMENT '城市名称',
            fx_date DATE NOT NULL COMMENT '预报日期',
            sunrise TIME COMMENT '日出时间',
            sunset TIME COMMENT '日落时间',
            moonrise TIME COMMENT '月升时间',
            moonset TIME COMMENT '月落时间',
            moon_phase VARCHAR(20) COMMENT '月相名称',
            moon_phase_icon VARCHAR(10) COMMENT '月相图标代码',
            temp_max INT COMMENT '最高温度',
            temp_min INT COMMENT '最低温度',
            icon_day VARCHAR(10) COMMENT '白天天气图标代码',
            text_day VARCHAR(20) COMMENT '白天天气描述',
            icon_night VARCHAR(10) COMMENT '夜间天气图标代码',
            text_night VARCHAR(20) COMMENT '夜间天气描述',
            wind360_day INT COMMENT '白天风向360角度',
            wind_dir_day VARCHAR(20) COMMENT '白天风向',
            wind_scale_day VARCHAR(10) COMMENT '白天风力等级',
            wind_speed_day INT COMMENT '白天风速 (km/h)',
            wind360_night INT COMMENT '夜间风向360角度',
            wind_dir_night VARCHAR(20) COMMENT '夜间风向',
            wind_scale_night VARCHAR(10) COMMENT '夜间风力等级',
            wind_speed_night INT COMMENT '夜间风速 (km/h)',
            precip DECIMAL(5,1) COMMENT '降水量 (mm)',
            uv_index INT COMMENT '紫外线指数',
            humidity INT COMMENT '相对湿度 (%)',
            pressure INT COMMENT '大气压强 (hPa)',
            vis INT COMMENT '能见度 (km)',
            cloud INT COMMENT '云量 (%)',
            update_time DATETIME COMMENT '数据更新时间',
            UNIQUE KEY unique_city_date (city, fx_date)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='天气数据表'
        """)
        conn.commit()

    # 立即执行一次更新
    update_weather()

    # 启动定时任务
    setup_scheduler()