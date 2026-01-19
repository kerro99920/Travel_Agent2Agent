#!/usr/bin/env python3
"""
SmartVoyage 格式化工具模块
src/utils/formatters.py

提供数据格式化和类型转换功能
"""

import json
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Union


class DateTimeEncoder(json.JSONEncoder):
    """
    自定义JSON编码器
    
    处理datetime、date、timedelta、Decimal等非标准JSON类型
    """
    
    def default(self, obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        if isinstance(obj, date):
            return obj.strftime('%Y-%m-%d')
        if isinstance(obj, timedelta):
            return str(obj)
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


def encode_special_types(obj: Any) -> Any:
    """
    编码特殊类型为JSON兼容格式
    
    Args:
        obj: 待编码对象
        
    Returns:
        JSON兼容的对象
    """
    if isinstance(obj, datetime):
        return obj.strftime('%Y-%m-%d %H:%M:%S')
    if isinstance(obj, date):
        return obj.strftime('%Y-%m-%d')
    if isinstance(obj, timedelta):
        return str(obj)
    if isinstance(obj, Decimal):
        return float(obj)
    return obj


def format_dict_values(data: Dict) -> Dict:
    """
    格式化字典中的特殊类型值
    
    Args:
        data: 原始字典
        
    Returns:
        格式化后的字典
    """
    result = {}
    for key, value in data.items():
        if isinstance(value, dict):
            result[key] = format_dict_values(value)
        elif isinstance(value, list):
            result[key] = [format_dict_values(item) if isinstance(item, dict) else encode_special_types(item) for item in value]
        else:
            result[key] = encode_special_types(value)
    return result


def to_json(data: Any, ensure_ascii: bool = False, indent: int = None) -> str:
    """
    安全地将数据转换为JSON字符串
    
    Args:
        data: 待转换数据
        ensure_ascii: 是否转义非ASCII字符
        indent: 缩进空格数
        
    Returns:
        JSON字符串
    """
    return json.dumps(data, cls=DateTimeEncoder, ensure_ascii=ensure_ascii, indent=indent)


def format_price(price: Union[float, Decimal, str]) -> str:
    """
    格式化价格显示
    
    Args:
        price: 价格数值
        
    Returns:
        格式化的价格字符串
    """
    if isinstance(price, str):
        price = float(price)
    return f"¥{price:,.2f}"


def format_datetime(dt: Union[datetime, str], fmt: str = '%Y-%m-%d %H:%M') -> str:
    """
    格式化日期时间
    
    Args:
        dt: 日期时间对象或字符串
        fmt: 输出格式
        
    Returns:
        格式化的日期时间字符串
    """
    if isinstance(dt, str):
        # 尝试解析常见格式
        for parse_fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M', '%Y-%m-%d']:
            try:
                dt = datetime.strptime(dt, parse_fmt)
                break
            except ValueError:
                continue
        else:
            return dt
    return dt.strftime(fmt)


def format_duration(minutes: int) -> str:
    """
    格式化时长
    
    Args:
        minutes: 分钟数
        
    Returns:
        格式化的时长字符串
    """
    if minutes < 60:
        return f"{minutes}分钟"
    hours = minutes // 60
    mins = minutes % 60
    if mins == 0:
        return f"{hours}小时"
    return f"{hours}小时{mins}分钟"


class TicketFormatter:
    """票务信息格式化器"""
    
    @staticmethod
    def format_train_tickets(tickets: List[Dict]) -> str:
        """格式化火车票列表"""
        if not tickets:
            return "😔 未找到符合条件的火车票信息"
        
        lines = [f"🚄 找到 {len(tickets)} 条火车票信息：\n"]
        
        for i, t in enumerate(tickets, 1):
            lines.append(f"【{i}】{t.get('train_number', '')} {t.get('seat_type', '')}")
            lines.append(f"    {t.get('departure_city', '')} → {t.get('arrival_city', '')}")
            lines.append(f"    出发: {format_datetime(t.get('departure_time', ''))}")
            lines.append(f"    到达: {format_datetime(t.get('arrival_time', ''))}")
            lines.append(f"    💰 {format_price(t.get('price', 0))} | 余票: {t.get('remaining_seats', 0)}张")
            lines.append(f"    🎫 票务ID: {t.get('id', '')}")
            lines.append("")
        
        lines.append("💡 如需订票，请提供票务ID和联系人信息")
        return '\n'.join(lines)
    
    @staticmethod
    def format_flight_tickets(tickets: List[Dict]) -> str:
        """格式化机票列表"""
        if not tickets:
            return "😔 未找到符合条件的机票信息"
        
        lines = [f"✈️ 找到 {len(tickets)} 条机票信息：\n"]
        
        for i, t in enumerate(tickets, 1):
            lines.append(f"【{i}】{t.get('flight_number', '')} {t.get('cabin_type', '')}")
            lines.append(f"    {t.get('departure_city', '')} → {t.get('arrival_city', '')}")
            lines.append(f"    出发: {format_datetime(t.get('departure_time', ''))}")
            lines.append(f"    到达: {format_datetime(t.get('arrival_time', ''))}")
            lines.append(f"    💰 {format_price(t.get('price', 0))} | 余票: {t.get('remaining_seats', 0)}张")
            lines.append(f"    🎫 票务ID: {t.get('id', '')}")
            lines.append("")
        
        lines.append("💡 如需订票，请提供票务ID和联系人信息")
        return '\n'.join(lines)
    
    @staticmethod
    def format_concert_tickets(tickets: List[Dict]) -> str:
        """格式化演唱会票列表"""
        if not tickets:
            return "😔 未找到符合条件的演唱会票信息"
        
        lines = [f"🎤 找到 {len(tickets)} 条演唱会信息：\n"]
        
        for i, t in enumerate(tickets, 1):
            lines.append(f"【{i}】{t.get('artist', '')} - {t.get('ticket_type', '')}")
            lines.append(f"    📍 {t.get('city', '')} · {t.get('venue', '')}")
            lines.append(f"    🕐 {format_datetime(t.get('start_time', ''))}")
            lines.append(f"    💰 {format_price(t.get('price', 0))} | 余票: {t.get('remaining_seats', 0)}张")
            lines.append(f"    🎫 票务ID: {t.get('id', '')}")
            lines.append("")
        
        lines.append("💡 如需订票，请提供票务ID和联系人信息")
        return '\n'.join(lines)


class WeatherFormatter:
    """天气信息格式化器"""
    
    @staticmethod
    def format_weather(weather_data: List[Dict]) -> str:
        """格式化天气信息"""
        if not weather_data:
            return "😔 未找到天气数据，请确认城市名称是否正确"
        
        lines = []
        
        for w in weather_data:
            city = w.get('city', '')
            date_str = w.get('fx_date', '')
            temp_max = w.get('temp_max', '')
            temp_min = w.get('temp_min', '')
            text_day = w.get('text_day', '')
            text_night = w.get('text_night', '')
            humidity = w.get('humidity', '')
            wind_dir = w.get('wind_dir_day', '')
            wind_scale = w.get('wind_scale_day', '')
            uv_index = w.get('uv_index', 0)
            
            lines.append(f"🌤️ {city} {date_str} 天气预报\n")
            lines.append(f"🌡️ 温度: {temp_min}°C ~ {temp_max}°C")
            lines.append(f"☀️ 白天: {text_day}")
            lines.append(f"🌙 夜间: {text_night}")
            lines.append(f"💧 湿度: {humidity}%")
            lines.append(f"🌬️ 风向: {wind_dir} {wind_scale}级")
            
            # 紫外线提示
            uv = int(uv_index) if uv_index else 0
            if uv >= 8:
                lines.append(f"☀️ 紫外线: {uv} (很强，注意防晒)")
            elif uv >= 5:
                lines.append(f"☀️ 紫外线: {uv} (中等)")
            else:
                lines.append(f"☀️ 紫外线: {uv} (弱)")
            
            lines.append("")
        
        return '\n'.join(lines)


class OrderFormatter:
    """订单信息格式化器"""
    
    @staticmethod
    def format_order_success(order_data: Dict) -> str:
        """格式化订单成功信息"""
        lines = ["✅ 订票成功！\n"]
        lines.append(f"📋 订单号: {order_data.get('order_no', 'N/A')}")
        lines.append(f"🎫 票务类型: {order_data.get('ticket_type', '')}")
        lines.append(f"📦 数量: {order_data.get('quantity', 1)}张")
        lines.append(f"💰 总价: {format_price(order_data.get('total_price', 0))}")
        lines.append(f"👤 联系人: {order_data.get('contact_name', '')}")
        lines.append(f"📱 电话: {order_data.get('contact_phone', '')}")
        lines.append(f"\n⏰ 请在30分钟内完成支付")
        return '\n'.join(lines)
    
    @staticmethod
    def format_order_failed(message: str) -> str:
        """格式化订单失败信息"""
        return f"❌ 订票失败: {message}"
