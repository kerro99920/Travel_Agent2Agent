#!/usr/bin/env python3
"""
数据验证工具
src/utils/validators.py

提供各种数据验证功能
"""

import re
from datetime import datetime, date
from typing import Optional, Tuple


class Validators:
    """数据验证器"""

    @staticmethod
    def validate_phone(phone: str) -> Tuple[bool, str]:
        """
        验证手机号码

        Args:
            phone: 手机号码

        Returns:
            (是否有效, 错误信息)
        """
        if not phone:
            return False, "手机号不能为空"

        # 中国大陆手机号: 1开头，第二位3-9，共11位
        pattern = r'^1[3-9]\d{9}$'
        if re.match(pattern, phone):
            return True, ""

        return False, "请输入有效的11位手机号码"

    @staticmethod
    def validate_id_card(id_card: str) -> Tuple[bool, str]:
        """
        验证身份证号码

        Args:
            id_card: 身份证号码

        Returns:
            (是否有效, 错误信息)
        """
        if not id_card:
            return True, ""  # 身份证可选

        # 18位身份证
        pattern = r'^\d{17}[\dXx]$'
        if not re.match(pattern, id_card):
            return False, "请输入有效的18位身份证号码"

        # 校验码验证
        weights = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
        check_codes = ['1', '0', 'X', '9', '8', '7', '6', '5', '4', '3', '2']

        try:
            total = sum(int(id_card[i]) * weights[i] for i in range(17))
            expected = check_codes[total % 11]
            if id_card[-1].upper() != expected:
                return False, "身份证号码校验码不正确"
        except:
            return False, "身份证号码格式不正确"

        return True, ""

    @staticmethod
    def validate_date(date_str: str, allow_past: bool = False) -> Tuple[bool, str]:
        """
        验证日期格式

        Args:
            date_str: 日期字符串 (YYYY-MM-DD)
            allow_past: 是否允许过去的日期

        Returns:
            (是否有效, 错误信息)
        """
        if not date_str:
            return False, "日期不能为空"

        try:
            parsed_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return False, "日期格式不正确，请使用 YYYY-MM-DD 格式"

        if not allow_past and parsed_date < date.today():
            return False, "日期不能早于今天"

        return True, ""

    @staticmethod
    def validate_city(city: str, supported_cities: list = None) -> Tuple[bool, str]:
        """
        验证城市名称

        Args:
            city: 城市名称
            supported_cities: 支持的城市列表

        Returns:
            (是否有效, 错误信息)
        """
        if not city:
            return False, "城市不能为空"

        if supported_cities and city not in supported_cities:
            return False, f"暂不支持该城市，目前支持: {', '.join(supported_cities)}"

        return True, ""

    @staticmethod
    def validate_quantity(quantity: int, max_quantity: int = 10) -> Tuple[bool, str]:
        """
        验证购买数量

        Args:
            quantity: 购买数量
            max_quantity: 最大允许数量

        Returns:
            (是否有效, 错误信息)
        """
        if quantity < 1:
            return False, "购买数量至少为1"

        if quantity > max_quantity:
            return False, f"单次购买数量不能超过{max_quantity}张"

        return True, ""

    @staticmethod
    def validate_name(name: str) -> Tuple[bool, str]:
        """
        验证姓名

        Args:
            name: 姓名

        Returns:
            (是否有效, 错误信息)
        """
        if not name:
            return False, "姓名不能为空"

        if len(name) < 2:
            return False, "姓名至少需要2个字符"

        if len(name) > 20:
            return False, "姓名不能超过20个字符"

        # 检查是否包含非法字符
        if re.search(r'[0-9@#$%^&*()+=\[\]{}|\\/<>]', name):
            return False, "姓名包含非法字符"

        return True, ""

    @staticmethod
    def validate_order_no(order_no: str) -> Tuple[bool, str]:
        """
        验证订单号

        Args:
            order_no: 订单号

        Returns:
            (是否有效, 错误信息)
        """
        if not order_no:
            return False, "订单号不能为空"

        # 订单号格式: ORD + 14位时间戳 + 6位随机字符
        pattern = r'^ORD\d{14}[A-Z0-9]{6}$'
        if not re.match(pattern, order_no):
            return False, "订单号格式不正确"

        return True, ""


class BookingValidator:
    """订票信息验证器"""

    SUPPORTED_WEATHER_CITIES = ["北京", "上海", "广州", "深圳"]

    SUPPORTED_SEAT_TYPES = {
        "train": ["二等座", "一等座", "商务座"],
        "flight": ["经济舱", "商务舱", "头等舱"],
        "concert": ["看台票", "内场票", "VIP票", "SVIP票"]
    }

    @classmethod
    def validate_train_booking(
        cls,
        departure_city: str,
        arrival_city: str,
        date: str,
        seat_type: Optional[str],
        contact_name: str,
        contact_phone: str
    ) -> Tuple[bool, str]:
        """验证火车票预订信息"""
        # 验证城市
        if not departure_city or not arrival_city:
            return False, "请提供出发城市和到达城市"

        if departure_city == arrival_city:
            return False, "出发城市和到达城市不能相同"

        # 验证日期
        valid, msg = Validators.validate_date(date)
        if not valid:
            return False, msg

        # 验证座位类型
        if seat_type and seat_type not in cls.SUPPORTED_SEAT_TYPES["train"]:
            return False, f"座位类型不支持，可选: {', '.join(cls.SUPPORTED_SEAT_TYPES['train'])}"

        # 验证联系人
        valid, msg = Validators.validate_name(contact_name)
        if not valid:
            return False, msg

        # 验证电话
        valid, msg = Validators.validate_phone(contact_phone)
        if not valid:
            return False, msg

        return True, ""

    @classmethod
    def validate_flight_booking(
        cls,
        departure_city: str,
        arrival_city: str,
        date: str,
        cabin_type: Optional[str],
        contact_name: str,
        contact_phone: str
    ) -> Tuple[bool, str]:
        """验证机票预订信息"""
        # 验证城市
        if not departure_city or not arrival_city:
            return False, "请提供出发城市和到达城市"

        if departure_city == arrival_city:
            return False, "出发城市和到达城市不能相同"

        # 验证日期
        valid, msg = Validators.validate_date(date)
        if not valid:
            return False, msg

        # 验证舱位类型
        if cabin_type and cabin_type not in cls.SUPPORTED_SEAT_TYPES["flight"]:
            return False, f"舱位类型不支持，可选: {', '.join(cls.SUPPORTED_SEAT_TYPES['flight'])}"

        # 验证联系人
        valid, msg = Validators.validate_name(contact_name)
        if not valid:
            return False, msg

        # 验证电话
        valid, msg = Validators.validate_phone(contact_phone)
        if not valid:
            return False, msg

        return True, ""

    @classmethod
    def validate_concert_booking(
        cls,
        city: str,
        artist: str,
        ticket_type: Optional[str],
        contact_name: str,
        contact_phone: str
    ) -> Tuple[bool, str]:
        """验证演唱会票预订信息"""
        # 验证城市
        if not city:
            return False, "请提供演出城市"

        # 验证艺人
        if not artist:
            return False, "请提供艺人名称"

        # 验证票类型
        if ticket_type and ticket_type not in cls.SUPPORTED_SEAT_TYPES["concert"]:
            return False, f"票类型不支持，可选: {', '.join(cls.SUPPORTED_SEAT_TYPES['concert'])}"

        # 验证联系人
        valid, msg = Validators.validate_name(contact_name)
        if not valid:
            return False, msg

        # 验证电话
        valid, msg = Validators.validate_phone(contact_phone)
        if not valid:
            return False, msg

        return True, ""


# 便捷访问
validators = Validators()
booking_validator = BookingValidator()
