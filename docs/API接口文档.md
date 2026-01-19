# SmartVoyage API 接口文档

> 文档版本：V2.0  
> 更新日期：2026-01-19  
> 协议：A2A (Agent-to-Agent) / MCP (Model Context Protocol)

---

## 目录

1. [概述](#1-概述)
2. [A2A Agent 接口](#2-a2a-agent-接口)
3. [MCP 服务接口](#3-mcp-服务接口)
4. [错误码说明](#4-错误码说明)
5. [示例代码](#5-示例代码)

---

## 1. 概述

### 1.1 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                      客户端层                                │
│              (Web UI / CLI / 第三方应用)                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼ A2A Protocol
┌─────────────────────────────────────────────────────────────┐
│                     Agent 服务层                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │Weather Agent│  │Ticket Agent │  │ Order Agent │         │
│  │   :5005     │  │   :5006     │  │   :5007     │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼ MCP Protocol
┌─────────────────────────────────────────────────────────────┐
│                     MCP 服务层                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ Weather MCP │  │ Ticket MCP  │  │  Order MCP  │         │
│  │   :8000     │  │   :8001     │  │   :8002     │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     数据层 (MySQL)                           │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 服务端口

| 服务 | 端口 | 协议 | 说明 |
|------|------|------|------|
| Weather Agent | 5005 | A2A | 天气查询代理 |
| Ticket Agent | 5006 | A2A | 票务查询代理 |
| Order Agent | 5007 | A2A | 订票代理 |
| Weather MCP | 8000 | MCP | 天气数据服务 |
| Ticket MCP | 8001 | MCP | 票务数据服务 |
| Order MCP | 8002 | MCP | 订单数据服务 |
| Web UI | 8501 | HTTP | Streamlit界面 |

---

## 2. A2A Agent 接口

### 2.1 通用接口格式

#### 获取 Agent 卡片

```http
GET /.well-known/agent.json
```

**响应示例：**
```json
{
  "name": "WeatherQueryAgent",
  "description": "天气查询代理，提供城市天气预报查询服务",
  "url": "http://localhost:5005",
  "version": "2.0.0",
  "capabilities": {
    "streaming": false,
    "pushNotifications": false
  },
  "skills": [
    {
      "name": "query_weather",
      "description": "查询指定城市的天气预报",
      "examples": [
        "北京今天天气怎么样",
        "上海明天会下雨吗"
      ]
    }
  ]
}
```

#### 发送任务

```http
POST /a2a
Content-Type: application/json
```

**请求格式（JSON-RPC 2.0）：**
```json
{
  "jsonrpc": "2.0",
  "method": "tasks/send",
  "params": {
    "message": {
      "role": "user",
      "content": "用户消息内容"
    }
  },
  "id": "unique-request-id"
}
```

**响应格式：**
```json
{
  "jsonrpc": "2.0",
  "result": {
    "state": "completed | input_required | failed",
    "message": {
      "role": "assistant",
      "content": "响应内容"
    }
  },
  "id": "unique-request-id"
}
```

### 2.2 Weather Agent (天气查询)

**端点：** `http://localhost:5005`

#### 查询天气

**请求：**
```json
{
  "jsonrpc": "2.0",
  "method": "tasks/send",
  "params": {
    "message": {
      "role": "user",
      "content": "北京明天天气怎么样"
    }
  },
  "id": "weather-001"
}
```

**成功响应：**
```json
{
  "jsonrpc": "2.0",
  "result": {
    "state": "completed",
    "message": {
      "role": "assistant",
      "content": "🌤️ 天气预报查询结果：\n\n📍 北京 - 2026-01-20\n   ☀️ 晴 / 晴\n   🌡️ 温度: -2°C ~ 8°C\n   💧 湿度: 35%\n   🌬️ 风向: 西北风 3-4级"
    }
  },
  "id": "weather-001"
}
```

**需要补充信息：**
```json
{
  "jsonrpc": "2.0",
  "result": {
    "state": "input_required",
    "message": {
      "role": "assistant",
      "content": "请告诉我您想查询哪个城市的天气？目前支持：北京、上海、广州、深圳"
    }
  },
  "id": "weather-001"
}
```

### 2.3 Ticket Agent (票务查询)

**端点：** `http://localhost:5006`

#### 查询火车票

**请求：**
```json
{
  "jsonrpc": "2.0",
  "method": "tasks/send",
  "params": {
    "message": {
      "role": "user",
      "content": "查询明天北京到上海的高铁票"
    }
  },
  "id": "ticket-001"
}
```

**响应：**
```json
{
  "jsonrpc": "2.0",
  "result": {
    "state": "completed",
    "message": {
      "role": "assistant",
      "content": "🚄 找到 5 条火车票信息：\n\n【1】G101 二等座\n    北京 → 上海\n    出发: 2026-01-20 07:00\n    到达: 2026-01-20 11:30\n    💰 ¥553.5 | 余票: 234张\n    🎫 票务ID: 1\n..."
    }
  },
  "id": "ticket-001"
}
```

#### 查询机票

**请求：**
```json
{
  "jsonrpc": "2.0",
  "method": "tasks/send",
  "params": {
    "message": {
      "role": "user",
      "content": "查询1月25日上海到广州的机票"
    }
  },
  "id": "ticket-002"
}
```

#### 查询演唱会票

**请求：**
```json
{
  "jsonrpc": "2.0",
  "method": "tasks/send",
  "params": {
    "message": {
      "role": "user",
      "content": "周杰伦北京演唱会门票"
    }
  },
  "id": "ticket-003"
}
```

### 2.4 Order Agent (订票)

**端点：** `http://localhost:5007`

#### 预订票务

**请求：**
```json
{
  "jsonrpc": "2.0",
  "method": "tasks/send",
  "params": {
    "message": {
      "role": "user",
      "content": "订一张明天北京到上海的高铁票，二等座，张三，13800138000"
    }
  },
  "id": "order-001"
}
```

**成功响应：**
```json
{
  "jsonrpc": "2.0",
  "result": {
    "state": "completed",
    "message": {
      "role": "assistant",
      "content": "✅ 订票成功！\n\n📋 订单号: ORD20260119143052ABC123\n🎫 数量: 1张\n💰 总价: ¥553.5\n👤 联系人: 张三\n📱 电话: 13800138000\n\n⏰ 请在30分钟内完成支付"
    }
  },
  "id": "order-001"
}
```

#### 通过票务ID订票

**请求：**
```json
{
  "jsonrpc": "2.0",
  "method": "tasks/send",
  "params": {
    "message": {
      "role": "user",
      "content": "订票务ID 1的火车票，2张，李四，13900139000"
    }
  },
  "id": "order-002"
}
```

---

## 3. MCP 服务接口

### 3.1 MCP 协议说明

MCP (Model Context Protocol) 使用 Streamable HTTP 传输，通过工具调用方式访问数据。

### 3.2 Weather MCP (天气数据)

**端点：** `http://localhost:8000/mcp`

#### 工具：query_weather

**参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| sql | string | 是 | SQL查询语句 |

**示例调用：**
```python
result = await session.call_tool("query_weather", {
    "sql": "SELECT city, fx_date, temp_max, temp_min, text_day FROM weather_data WHERE city = '北京' AND fx_date = '2026-01-20'"
})
```

**返回：**
```json
{
  "status": "success",
  "data": [
    {
      "city": "北京",
      "fx_date": "2026-01-20",
      "temp_max": 8,
      "temp_min": -2,
      "text_day": "晴"
    }
  ]
}
```

### 3.3 Ticket MCP (票务数据)

**端点：** `http://localhost:8001/mcp`

#### 工具：query_tickets

通用SQL查询接口。

#### 工具：query_train_tickets

**参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| departure_city | string | 是 | 出发城市 |
| arrival_city | string | 是 | 到达城市 |
| date | string | 是 | 日期 (YYYY-MM-DD) |
| seat_type | string | 否 | 座位类型 |

#### 工具：query_flight_tickets

**参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| departure_city | string | 是 | 出发城市 |
| arrival_city | string | 是 | 到达城市 |
| date | string | 是 | 日期 (YYYY-MM-DD) |
| cabin_type | string | 否 | 舱位类型 |

#### 工具：query_concert_tickets

**参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| city | string | 否 | 城市 |
| artist | string | 否 | 艺人名称 |
| date | string | 否 | 日期 (YYYY-MM-DD) |
| ticket_type | string | 否 | 票类型 |

### 3.4 Order MCP (订单数据)

**端点：** `http://localhost:8002/mcp`

#### 工具：create_order

**参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| ticket_type | string | 是 | 票务类型 (train/flight/concert) |
| ticket_id | int | 是 | 票务ID |
| quantity | int | 是 | 数量 |
| contact_name | string | 是 | 联系人姓名 |
| contact_phone | string | 是 | 联系人电话 |
| contact_id_card | string | 否 | 身份证号 |

**返回：**
```json
{
  "status": "success",
  "data": {
    "order_no": "ORD20260119143052ABC123",
    "ticket_type": "train",
    "ticket_id": 1,
    "quantity": 1,
    "total_price": 553.5,
    "status": "pending"
  }
}
```

#### 工具：query_order

**参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| order_no | string | 是 | 订单号 |

#### 工具：cancel_order

**参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| order_no | string | 是 | 订单号 |

#### 工具：list_orders

**参数：**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| contact_phone | string | 否 | 联系人电话 |
| status | string | 否 | 订单状态 |
| limit | int | 否 | 返回数量限制 |

---

## 4. 错误码说明

### 4.1 任务状态

| 状态 | 说明 |
|------|------|
| completed | 任务完成 |
| input_required | 需要补充信息 |
| failed | 任务失败 |
| working | 处理中 |

### 4.2 错误响应

```json
{
  "status": "error",
  "message": "错误描述"
}
```

### 4.3 常见错误

| 错误信息 | 说明 | 解决方案 |
|----------|------|----------|
| 票务不存在 | 指定的票务ID无效 | 检查票务ID |
| 余票不足 | 剩余票数不够 | 减少购买数量或选择其他班次 |
| 数据库连接失败 | 无法连接MySQL | 检查数据库配置 |
| LLM调用失败 | 无法调用大模型 | 检查API Key |

---

## 5. 示例代码

### 5.1 Python 调用示例

```python
import asyncio
import httpx
import uuid

async def query_weather(city: str, date: str):
    """查询天气"""
    request = {
        "jsonrpc": "2.0",
        "method": "tasks/send",
        "params": {
            "message": {
                "role": "user",
                "content": f"{city}{date}天气怎么样"
            }
        },
        "id": str(uuid.uuid4())
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "http://localhost:5005/a2a",
            json=request
        )
        result = response.json()
        
        if "result" in result:
            return result["result"]["message"]["content"]
        return None

async def book_ticket(
    departure: str,
    arrival: str,
    date: str,
    name: str,
    phone: str
):
    """订票"""
    request = {
        "jsonrpc": "2.0",
        "method": "tasks/send",
        "params": {
            "message": {
                "role": "user",
                "content": f"订一张{date}{departure}到{arrival}的高铁票，{name}，{phone}"
            }
        },
        "id": str(uuid.uuid4())
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            "http://localhost:5007/a2a",
            json=request
        )
        return response.json()

# 使用示例
async def main():
    # 查询天气
    weather = await query_weather("北京", "明天")
    print(weather)
    
    # 订票
    result = await book_ticket(
        "北京", "上海", "明天",
        "张三", "13800138000"
    )
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
```

### 5.2 cURL 调用示例

```bash
# 获取Agent卡片
curl http://localhost:5005/.well-known/agent.json

# 查询天气
curl -X POST http://localhost:5005/a2a \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tasks/send",
    "params": {
      "message": {
        "role": "user",
        "content": "北京明天天气"
      }
    },
    "id": "test-001"
  }'

# 查询火车票
curl -X POST http://localhost:5006/a2a \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tasks/send",
    "params": {
      "message": {
        "role": "user",
        "content": "查询明天北京到上海的高铁"
      }
    },
    "id": "test-002"
  }'

# 订票
curl -X POST http://localhost:5007/a2a \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tasks/send",
    "params": {
      "message": {
        "role": "user",
        "content": "订票务ID 1，张三，13800138000"
      }
    },
    "id": "test-003"
  }'
```

---

## 附录

### A. 数据表结构

详见 `sql/init_database.sql`

### B. 配置说明

详见 `.env.example`

### C. 更新日志

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| 2.0.0 | 2026-01-19 | 重构项目结构，优化接口设计 |
| 1.0.0 | 2026-01-15 | 初始版本 |
