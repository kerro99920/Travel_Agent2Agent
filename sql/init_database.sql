-- ============================================================
-- SmartVoyage 智能旅行助手系统 - 数据库初始化脚本
-- ============================================================
-- 文档编号: SV-SQL-001
-- 版本: 2.0.0
-- 创建日期: 2026-01-18
-- ============================================================

-- 创建数据库
CREATE DATABASE IF NOT EXISTS travel_rag 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

USE travel_rag;

-- ============================================================
-- 1. 天气数据表
-- ============================================================
DROP TABLE IF EXISTS weather_data;
CREATE TABLE weather_data (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    city VARCHAR(50) NOT NULL COMMENT '城市名称',
    fx_date DATE NOT NULL COMMENT '预报日期',
    sunrise TIME COMMENT '日出时间',
    sunset TIME COMMENT '日落时间',
    moonrise TIME COMMENT '月升时间',
    moonset TIME COMMENT '月落时间',
    moon_phase VARCHAR(20) COMMENT '月相名称',
    moon_phase_icon VARCHAR(10) COMMENT '月相图标代码',
    temp_max INT COMMENT '最高温度(℃)',
    temp_min INT COMMENT '最低温度(℃)',
    icon_day VARCHAR(10) COMMENT '白天天气图标代码',
    text_day VARCHAR(20) COMMENT '白天天气描述',
    icon_night VARCHAR(10) COMMENT '夜间天气图标代码',
    text_night VARCHAR(20) COMMENT '夜间天气描述',
    wind360_day INT COMMENT '白天风向360角度',
    wind_dir_day VARCHAR(20) COMMENT '白天风向',
    wind_scale_day VARCHAR(10) COMMENT '白天风力等级',
    wind_speed_day INT COMMENT '白天风速(km/h)',
    wind360_night INT COMMENT '夜间风向360角度',
    wind_dir_night VARCHAR(20) COMMENT '夜间风向',
    wind_scale_night VARCHAR(10) COMMENT '夜间风力等级',
    wind_speed_night INT COMMENT '夜间风速(km/h)',
    precip DECIMAL(5,1) COMMENT '降水量(mm)',
    uv_index INT COMMENT '紫外线指数',
    humidity INT COMMENT '相对湿度(%)',
    pressure INT COMMENT '大气压强(hPa)',
    vis INT COMMENT '能见度(km)',
    cloud INT COMMENT '云量(%)',
    update_time DATETIME COMMENT '数据更新时间',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    UNIQUE KEY uk_city_date (city, fx_date),
    INDEX idx_city (city),
    INDEX idx_date (fx_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='天气数据表';

-- ============================================================
-- 2. 火车票数据表
-- ============================================================
DROP TABLE IF EXISTS train_tickets;
CREATE TABLE train_tickets (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    departure_city VARCHAR(50) NOT NULL COMMENT '出发城市',
    arrival_city VARCHAR(50) NOT NULL COMMENT '到达城市',
    departure_time DATETIME NOT NULL COMMENT '出发时间',
    arrival_time DATETIME NOT NULL COMMENT '到达时间',
    train_number VARCHAR(20) NOT NULL COMMENT '车次号',
    seat_type VARCHAR(20) NOT NULL COMMENT '座位类型',
    total_seats INT NOT NULL DEFAULT 0 COMMENT '总座位数',
    remaining_seats INT NOT NULL DEFAULT 0 COMMENT '剩余座位数',
    price DECIMAL(10,2) NOT NULL DEFAULT 0.00 COMMENT '票价(元)',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    UNIQUE KEY uk_train (train_number, departure_time, seat_type),
    INDEX idx_route (departure_city, arrival_city),
    INDEX idx_departure_time (departure_time),
    INDEX idx_remaining (remaining_seats)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='火车票数据表';

-- ============================================================
-- 3. 机票数据表
-- ============================================================
DROP TABLE IF EXISTS flight_tickets;
CREATE TABLE flight_tickets (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    departure_city VARCHAR(50) NOT NULL COMMENT '出发城市',
    arrival_city VARCHAR(50) NOT NULL COMMENT '到达城市',
    departure_time DATETIME NOT NULL COMMENT '出发时间',
    arrival_time DATETIME NOT NULL COMMENT '到达时间',
    flight_number VARCHAR(20) NOT NULL COMMENT '航班号',
    cabin_type VARCHAR(20) NOT NULL COMMENT '舱位类型',
    total_seats INT NOT NULL DEFAULT 0 COMMENT '总座位数',
    remaining_seats INT NOT NULL DEFAULT 0 COMMENT '剩余座位数',
    price DECIMAL(10,2) NOT NULL DEFAULT 0.00 COMMENT '票价(元)',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    UNIQUE KEY uk_flight (flight_number, departure_time, cabin_type),
    INDEX idx_route (departure_city, arrival_city),
    INDEX idx_departure_time (departure_time),
    INDEX idx_remaining (remaining_seats)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='机票数据表';

-- ============================================================
-- 4. 演唱会票数据表
-- ============================================================
DROP TABLE IF EXISTS concert_tickets;
CREATE TABLE concert_tickets (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    artist VARCHAR(100) NOT NULL COMMENT '艺人名称',
    city VARCHAR(50) NOT NULL COMMENT '举办城市',
    venue VARCHAR(100) NOT NULL COMMENT '场馆名称',
    start_time DATETIME NOT NULL COMMENT '开始时间',
    end_time DATETIME NOT NULL COMMENT '结束时间',
    ticket_type VARCHAR(20) NOT NULL COMMENT '票类型',
    total_seats INT NOT NULL DEFAULT 0 COMMENT '总座位数',
    remaining_seats INT NOT NULL DEFAULT 0 COMMENT '剩余座位数',
    price DECIMAL(10,2) NOT NULL DEFAULT 0.00 COMMENT '票价(元)',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    UNIQUE KEY uk_concert (artist, city, start_time, ticket_type),
    INDEX idx_artist (artist),
    INDEX idx_city (city),
    INDEX idx_start_time (start_time),
    INDEX idx_remaining (remaining_seats)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='演唱会票数据表';

-- ============================================================
-- 5. 订单数据表
-- ============================================================
DROP TABLE IF EXISTS orders;
CREATE TABLE orders (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    order_no VARCHAR(32) NOT NULL COMMENT '订单号',
    ticket_type ENUM('train', 'flight', 'concert') NOT NULL COMMENT '票务类型',
    ticket_id INT NOT NULL COMMENT '票务ID',
    quantity INT NOT NULL DEFAULT 1 COMMENT '购买数量',
    unit_price DECIMAL(10,2) NOT NULL DEFAULT 0.00 COMMENT '单价(元)',
    total_price DECIMAL(10,2) NOT NULL DEFAULT 0.00 COMMENT '总价(元)',
    contact_name VARCHAR(50) NOT NULL COMMENT '联系人姓名',
    contact_phone VARCHAR(20) NOT NULL COMMENT '联系人电话',
    contact_id_card VARCHAR(20) DEFAULT '' COMMENT '身份证号',
    status ENUM('pending', 'paid', 'cancelled', 'refunded', 'completed') DEFAULT 'pending' COMMENT '订单状态',
    payment_time DATETIME DEFAULT NULL COMMENT '支付时间',
    cancel_time DATETIME DEFAULT NULL COMMENT '取消时间',
    cancel_reason VARCHAR(200) DEFAULT '' COMMENT '取消原因',
    remark TEXT COMMENT '备注信息',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    UNIQUE KEY uk_order_no (order_no),
    INDEX idx_status (status),
    INDEX idx_contact_phone (contact_phone),
    INDEX idx_ticket (ticket_type, ticket_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='订单数据表';

-- ============================================================
-- 6. 系统配置表(可选)
-- ============================================================
DROP TABLE IF EXISTS system_config;
CREATE TABLE system_config (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    config_key VARCHAR(100) NOT NULL COMMENT '配置键',
    config_value TEXT COMMENT '配置值',
    config_desc VARCHAR(200) DEFAULT '' COMMENT '配置描述',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    
    UNIQUE KEY uk_config_key (config_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统配置表';

-- 插入默认配置
INSERT INTO system_config (config_key, config_value, config_desc) VALUES
('system_version', '2.0.0', '系统版本号'),
('order_expire_minutes', '30', '订单过期时间(分钟)'),
('max_tickets_per_order', '5', '单笔订单最大票数');

-- ============================================================
-- 完成提示
-- ============================================================
SELECT '数据库初始化完成!' AS message;
SELECT TABLE_NAME, TABLE_COMMENT FROM information_schema.TABLES WHERE TABLE_SCHEMA = 'travel_rag';
