#!/usr/bin/env python3
"""
单元测试
tests/test_validators.py

测试数据验证器
"""

import pytest
from src.utils.validators import Validators, BookingValidator


class TestValidators:
    """测试Validators类"""

    def test_validate_phone_valid(self):
        """测试有效手机号"""
        valid, msg = Validators.validate_phone("13800138000")
        assert valid is True
        assert msg == ""

    def test_validate_phone_invalid(self):
        """测试无效手机号"""
        # 空号码
        valid, msg = Validators.validate_phone("")
        assert valid is False

        # 位数不对
        valid, msg = Validators.validate_phone("1380013800")
        assert valid is False

        # 格式不对
        valid, msg = Validators.validate_phone("23800138000")
        assert valid is False

    def test_validate_id_card_valid(self):
        """测试有效身份证"""
        # 空身份证（可选字段）
        valid, msg = Validators.validate_id_card("")
        assert valid is True

    def test_validate_id_card_invalid(self):
        """测试无效身份证"""
        # 位数不对
        valid, msg = Validators.validate_id_card("11010119900101123")
        assert valid is False

    def test_validate_date_valid(self):
        """测试有效日期"""
        from datetime import datetime, timedelta
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        valid, msg = Validators.validate_date(tomorrow)
        assert valid is True

    def test_validate_date_invalid(self):
        """测试无效日期"""
        # 格式不对
        valid, msg = Validators.validate_date("2026/01/20")
        assert valid is False

        # 空日期
        valid, msg = Validators.validate_date("")
        assert valid is False

    def test_validate_date_past(self):
        """测试过去日期"""
        valid, msg = Validators.validate_date("2020-01-01")
        assert valid is False
        assert "不能早于" in msg

    def test_validate_city(self):
        """测试城市验证"""
        # 有效城市
        valid, msg = Validators.validate_city("北京", ["北京", "上海"])
        assert valid is True

        # 不支持的城市
        valid, msg = Validators.validate_city("杭州", ["北京", "上海"])
        assert valid is False

    def test_validate_quantity(self):
        """测试数量验证"""
        # 有效数量
        valid, msg = Validators.validate_quantity(1)
        assert valid is True

        valid, msg = Validators.validate_quantity(5)
        assert valid is True

        # 无效数量
        valid, msg = Validators.validate_quantity(0)
        assert valid is False

        valid, msg = Validators.validate_quantity(100)
        assert valid is False

    def test_validate_name(self):
        """测试姓名验证"""
        # 有效姓名
        valid, msg = Validators.validate_name("张三")
        assert valid is True

        valid, msg = Validators.validate_name("李四五")
        assert valid is True

        # 无效姓名
        valid, msg = Validators.validate_name("")
        assert valid is False

        valid, msg = Validators.validate_name("A")
        assert valid is False


class TestBookingValidator:
    """测试BookingValidator类"""

    def test_validate_train_booking_valid(self):
        """测试有效火车票预订"""
        from datetime import datetime, timedelta
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')

        valid, msg = BookingValidator.validate_train_booking(
            departure_city="北京",
            arrival_city="上海",
            date=tomorrow,
            seat_type="二等座",
            contact_name="张三",
            contact_phone="13800138000"
        )
        assert valid is True

    def test_validate_train_booking_same_city(self):
        """测试出发到达城市相同"""
        from datetime import datetime, timedelta
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')

        valid, msg = BookingValidator.validate_train_booking(
            departure_city="北京",
            arrival_city="北京",
            date=tomorrow,
            seat_type="二等座",
            contact_name="张三",
            contact_phone="13800138000"
        )
        assert valid is False
        assert "不能相同" in msg

    def test_validate_train_booking_invalid_seat(self):
        """测试无效座位类型"""
        from datetime import datetime, timedelta
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')

        valid, msg = BookingValidator.validate_train_booking(
            departure_city="北京",
            arrival_city="上海",
            date=tomorrow,
            seat_type="特等座",
            contact_name="张三",
            contact_phone="13800138000"
        )
        assert valid is False

    def test_validate_flight_booking_valid(self):
        """测试有效机票预订"""
        from datetime import datetime, timedelta
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')

        valid, msg = BookingValidator.validate_flight_booking(
            departure_city="上海",
            arrival_city="广州",
            date=tomorrow,
            cabin_type="经济舱",
            contact_name="李四",
            contact_phone="13900139000"
        )
        assert valid is True

    def test_validate_concert_booking_valid(self):
        """测试有效演唱会票预订"""
        valid, msg = BookingValidator.validate_concert_booking(
            city="北京",
            artist="周杰伦",
            ticket_type="VIP票",
            contact_name="王五",
            contact_phone="13700137000"
        )
        assert valid is True

    def test_validate_concert_booking_missing_artist(self):
        """测试缺少艺人"""
        valid, msg = BookingValidator.validate_concert_booking(
            city="北京",
            artist="",
            ticket_type="VIP票",
            contact_name="王五",
            contact_phone="13700137000"
        )
        assert valid is False
        assert "艺人" in msg


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
