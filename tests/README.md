# 测试目录说明（tests/README.md）

本目录用于存放本项目的所有自动化测试脚本，包括单元测试、集成测试和端到端测试。

## 目录结构

```
tests/
├── README.md              # 本说明文件
├── test_stdio.py          # 示例：通过子进程方式测试 MCP Stdio 服务的脚本
├── ...                    # 其他测试脚本
```

## 测试类型说明

- **单元测试**：针对单个函数或模块的功能进行验证，通常不依赖外部服务。
- **集成测试**：验证多个模块/服务之间的协作，常常需要启动主服务或 MCP 工具服务。
- **端到端测试**：模拟真实用户操作，测试整个系统的业务流程。

## 运行测试的方法

### 1. 运行单个测试脚本

在项目根目录下，激活虚拟环境后，进入 `tests/` 目录，直接运行：

```bash
python test_stdio.py
```

### 2. 使用 pytest 统一运行

如果你的测试脚本符合 pytest 规范（以 `test_` 开头的文件和函数），可以直接在 `tests/` 目录下运行：

```bash
pytest
```

### 3. 特殊说明：Stdio 子进程集成测试

有些测试（如 `test_stdio.py`）会通过 `subprocess` 启动 MCP 工具服务（如 `app/mcp_server/weather_service.py`），并通过标准输入输出与其交互。

**注意事项：**
- 请确保被测试的目标脚本路径正确。例如：
  ```python
  script_path = os.path.join(base_dir, '../app/mcp_server/weather_service.py')
  script_path = os.path.normpath(script_path)
  ```
- 目标脚本必须存在且能被独立运行，否则会出现 `FileNotFoundError` 或 `BrokenPipeError`。
- 建议在测试前后清理相关子进程，避免僵尸进程。

## 如何添加新的测试

1. 在 `tests/` 目录下新建以 `test_` 开头的 Python 文件。
2. 编写测试函数，函数名以 `test_` 开头。
3. 推荐使用 `pytest` 框架，便于自动发现和运行测试。
4. 如需模拟 HTTP 请求，可使用 `requests` 或 `httpx`，也可用 `TestClient`（FastAPI自带）。
5. 如需集成测试 MCP 服务，参考 `test_stdio.py` 的写法。

## 依赖管理

- 测试所需的依赖请统一写在项目根目录的 `app/requirements.txt` 或单独的 `requirements-test.txt` 中。
- 安装依赖：
  ```bash
  pip install -r app/requirements.txt
  # 或
  pip install -r requirements-test.txt
  ```

## 常见问题

- **FileNotFoundError**：请检查目标脚本路径是否正确。
- **BrokenPipeError**：通常是目标子进程未正常启动或提前退出。
- **端口冲突**：如测试涉及服务监听端口，确保端口未被占用。
- **天气工具调用失败（ConnectionResetError/Connection aborted）**：
  - 现象：调用 `get_current_weather` 工具时，返回内容如：
    `[TextContent(type='text', text="请求天气信息失败: ('Connection aborted.', ConnectionResetError(54, 'Connection reset by peer'))", annotations=None)]`
  - 原因：MCP 服务端在请求外部天气 API（如 sojson）时，目标服务器断开了连接，常见原因包括：
    - 天气 API 服务已失效、被墙、被限流或临时不可用
    - 本地网络无法访问外部服务（如被防火墙/代理拦截）
    - API 地址写错或目标服务器迁移/下线
    - 请求过于频繁被对方限流
  - 排查方法：
    1. 用浏览器或 curl 直接访问 API 地址，看能否正常返回数据
    2. 检查本地网络、代理、VPN、防火墙设置
    3. 如 API 已失效，建议更换为其他可用的天气 API
  - 说明：此类错误不是 MCP 本地代码问题，而是外部依赖的天气 API 不可用或网络不通导致。

---
如有更多测试需求或问题，欢迎补充本说明文件！

## MCP 客户端调用详解

### MCP 协议基础

MCP (Model Context Protocol) 使用 JSON-RPC 2.0 协议进行客户端与服务器之间的通信。所有通信都是基于 HTTP 或 stdio 的文本格式。

### 客户端连接与初始化

**使用 fastmcp 客户端连接 MCP 服务器：**

```python
from fastmcp import Client
from fastmcp.client.transports import SSETransport

# 连接到 MCP 服务器
async with Client(SSETransport("http://127.0.0.1:9001")) as client:
    # 在这里进行工具调用
    pass
```

**底层 JSON-RPC 初始化流程：**

```json
// 1. 初始化请求
{
  "jsonrpc": "2.0",
  "id": 0,
  "method": "initialize",
  "params": {
    "protocolVersion": "2024-11-05",
    "capabilities": {
      "sampling": {}
    },
    "clientInfo": {
      "name": "mcp",
      "version": "0.1.0"
    }
  }
}

// 2. 初始化通知
{
  "jsonrpc": "2.0",
  "method": "notifications/initialized"
}
```

### 获取工具列表 (list_tools)

**使用 fastmcp 客户端：**

```python
# 获取服务器提供的所有工具
tools = await client.list_tools()
for tool in tools:
    print(f"工具名: {tool.name}")
    print(f"描述: {tool.description}")
    print(f"输入参数: {tool.inputSchema}")
```

**底层 JSON-RPC 请求：**

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/list",
  "params": {}
}
```

**服务器响应示例：**

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "tools": [
      {
        "name": "get_current_weather",
        "description": "获取中国指定省市的当前天气预报",
        "inputSchema": {
          "type": "object",
          "properties": {
            "province": {
              "type": "string",
              "description": "省份名称"
            },
            "city": {
              "type": "string", 
              "description": "城市名称"
            }
          },
          "required": ["province", "city"]
        }
      }
    ]
  }
}
```

### 调用工具 (call_tool)

**使用 fastmcp 客户端：**

```python
# 调用天气查询工具
result = await client.call_tool("get_current_weather", {
    "province": "北京",
    "city": "海淀"
})
print(f"天气信息: {result}")
```

**底层 JSON-RPC 请求：**

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "get_current_weather",
    "arguments": {
      "province": "北京",
      "city": "海淀"
    }
  }
}
```

**服务器响应示例：**

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"status\":200,\"message\":\"success\",\"data\":{\"shidu\":\"45%\",\"pm25\":\"15\",\"pm10\":\"35\",\"quality\":\"优\",\"wendu\":\"18\",\"ganmao\":\"天气较好，适宜外出活动\"}}"
      }
    ]
  }
}
```

### 实际调用流程示例

**在项目中的完整调用流程：**

1. **工具注册阶段** (`app/mcp_api.py`)：
   ```python
   async def fetch_and_store_mcp_tools(db, server_id, server_url, auth_type, auth_value):
       # 连接到 MCP 服务器
       async with Client(SSETransport(server_url)) as client:
           # 获取工具列表
           tools = await client.list_tools()
           
           # 将工具信息存储到数据库
           for tool in tools:
               cursor.execute(
                   "INSERT INTO mcp_tools (id, server_id, name, description, input_schema) VALUES (?, ?, ?, ?, ?)",
                   (uuid.uuid4(), server_id, tool.name, tool.description, json.dumps(tool.inputSchema))
               )
   ```

2. **工具调用阶段** (`app/main.py`)：
   ```python
   async def generate_with_tools():
       # 从数据库获取已注册的工具
       cursor.execute("SELECT t.*, s.url FROM mcp_tools t JOIN mcp_servers s ON t.server_id = s.id")
       tools = [dict(row) for row in cursor.fetchall()]
       
       # LLM 决策后，调用对应工具
       target_tool = next((t for t in tools if t['name'] == tool_name), None)
       if target_tool:
           # 连接到工具服务器并调用
           async with Client(SSETransport(target_tool['url'])) as client:
               tool_result = await client.call_tool(tool_name, parameters)
   ```

### stdio 模式调用

对于 `tests/weather_stdio.py` 这样的 stdio 模式服务器，客户端通过标准输入输出进行通信：

```python
# 测试文件中的调用示例
test_messages = [
    {"jsonrpc":"2.0","id":0,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{"sampling":{}},"clientInfo":{"name":"mcp","version":"0.1.0"}}},
    {"jsonrpc":"2.0","method":"notifications/initialized"},
    {"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}},
    {"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"get_current_weather","arguments":{"province":"北京","city":"海淀"}}}
]

# 通过子进程管道发送 JSON-RPC 消息
process = subprocess.Popen(["python", "weather_stdio.py"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
for msg in test_messages:
    msg_str = json.dumps(msg) + "\n"
    process.stdin.write(msg_str)
    process.stdin.flush()
    response = process.stdout.readline()
```

#### 手动测试 MCP Stdio 服务

除了通过脚本自动化测试，您也可以手动测试 MCP stdio 服务，这对于调试和理解 MCP 协议非常有用。

**步骤 1: 启动 MCP 服务**

在终端中启动 stdio 模式的 MCP 服务：

```bash
cd tests/
python3.13 weather_stdio.py
```

您会看到类似以下的输出：
```
[06/26/25 09:02:48] INFO     Starting MCP server 'weatherMcp' with transport 'stdio' server.py:1246
```

**步骤 2: 发送初始化请求**

在服务启动后，您需要先发送初始化请求。复制以下 JSON 并粘贴到终端：

```json
{"jsonrpc":"2.0","id":0,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{"sampling":{},"roots":{"listChanged":true}},"clientInfo":{"name":"mcp","version":"0.1.0"}}}
```

按回车后，您会收到初始化响应：
```json
{"jsonrpc":"2.0","id":0,"result":{"protocolVersion":"2024-11-05","capabilities":{"experimental":{},"prompts":{"listChanged":false},"resources":{"subscribe":false,"listChanged":false},"tools":{"listChanged":true}},"serverInfo":{"name":"weatherMcp","version":"1.9.4"}}}
```

**步骤 3: 发送初始化通知**

```json
{"jsonrpc":"2.0","method":"notifications/initialized"}
```

**步骤 4: 获取工具列表**

```json
{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}
```

您会收到工具列表响应：
```json
{"jsonrpc":"2.0","id":1,"result":{"tools":[{"name":"get_current_weather","description":"获取中国指定省市的当前天气预报。\n:param province: 省份名称\n:param city: 城市名称\n:return: 天气预报的 JSON 字符串（若失败则返回提示信息）","inputSchema":{"properties":{"province":{"title":"Province","type":"string"},"city":{"title":"City","type":"string"}},"required":["province","city"],"type":"object"}}]}}
```

**步骤 5: 调用工具**

```json
{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"get_current_weather","arguments":{"province":"北京","city":"海淀"}}}
```

**重要注意事项：**

1. **初始化顺序**：必须先发送 `initialize` 请求，然后发送 `notifications/initialized`，最后才能调用其他方法。

2. **错误处理**：如果在初始化完成前发送其他请求，会收到错误响应：
   ```json
   {"jsonrpc":"2.0","id":2,"error":{"code":-32602,"message":"Invalid request parameters","data":""}}
   ```

3. **JSON 格式**：确保 JSON 格式正确，每个请求后按回车发送。

4. **服务状态**：服务会一直运行，等待您的输入。要退出服务，可以按 `Ctrl+C`。

**测试其他功能：**

您也可以测试 prompts 功能（如果服务支持）：
```json
{"jsonrpc":"2.0","id":3,"method":"prompts/get","params":{"name":"ask_review","arguments":{"code_snippet":"def hello():\n    print('world')"}}}
```

这种手动测试方式可以帮助您：
- 理解 MCP 协议的通信流程
- 调试 MCP 服务的功能
- 验证 JSON-RPC 消息的格式
- 测试错误处理机制

### MCP Stdio 服务工作原理详解

#### 为什么可以直接用 JSON 交互？

MCP stdio 服务使用**标准输入输出（stdin/stdout）**作为通信通道，这是 Unix/Linux 系统中最基本的进程间通信方式。

**核心原理：**
1. **stdio 模式**：MCP 服务器启动时指定 `transport="stdio"`
2. **文本协议**：所有通信都是纯文本格式的 JSON-RPC 消息
3. **行分隔**：每条消息以换行符 `\n` 分隔
4. **双向通信**：通过 stdin 接收请求，通过 stdout 发送响应

#### 服务启动流程

当您运行 `python3.13 weather_stdio.py` 时：

```python
# weather_stdio.py 中的关键代码
if __name__ == "__main__":
    # 以 stdio 方式启动 MCP 服务
    mcp.run(transport="stdio")
```

**内部执行过程：**
1. **FastMCP 初始化**：创建 MCP 服务器实例
2. **注册工具**：通过 `@mcp.tool()` 装饰器注册 `get_current_weather` 函数
3. **启动 stdio 监听**：开始监听标准输入
4. **等待消息**：服务进入等待状态，等待 JSON-RPC 消息

#### 每条消息的调用原理

##### 1. 初始化请求 (initialize)

**发送的消息：**
```json
{"jsonrpc":"2.0","id":0,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{"sampling":{},"roots":{"listChanged":true}},"clientInfo":{"name":"mcp","version":"0.1.0"}}}
```

**服务端处理流程：**
1. **接收消息**：从 stdin 读取 JSON 字符串
2. **解析 JSON**：将字符串解析为 Python 对象
3. **验证格式**：检查 JSON-RPC 2.0 格式是否正确
4. **提取参数**：获取 `protocolVersion`、`capabilities`、`clientInfo`
5. **建立会话**：创建客户端会话，记录客户端信息
6. **返回响应**：通过 stdout 发送初始化结果

**返回的响应：**
```json
{"jsonrpc":"2.0","id":0,"result":{"protocolVersion":"2024-11-05","capabilities":{"experimental":{},"prompts":{"listChanged":false},"resources":{"subscribe":false,"listChanged":false},"tools":{"listChanged":true}},"serverInfo":{"name":"weatherMcp","version":"1.9.4"}}}
```

**响应内容解析：**
- `protocolVersion`：确认使用的协议版本
- `capabilities`：服务器支持的功能（tools、prompts、resources 等）
- `serverInfo`：服务器信息（名称、版本等）

##### 2. 初始化通知 (notifications/initialized)

**发送的消息：**
```json
{"jsonrpc":"2.0","method":"notifications/initialized"}
```

**服务端处理流程：**
1. **接收通知**：识别这是一个通知消息（没有 id 字段）
2. **确认初始化**：标记客户端已完成初始化
3. **准备就绪**：服务器现在可以接受工具调用等请求
4. **无响应**：通知消息不需要响应

**为什么需要这个通知？**
- 确保客户端和服务器都准备好进行后续通信
- 防止在初始化完成前发送其他请求

##### 3. 获取工具列表 (tools/list)

**发送的消息：**
```json
{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}
```

**服务端处理流程：**
1. **验证状态**：检查是否已完成初始化
2. **查找工具**：扫描所有通过 `@mcp.tool()` 注册的函数
3. **构建工具信息**：提取工具名称、描述、输入参数模式
4. **格式化响应**：将工具信息转换为标准格式
5. **返回列表**：通过 stdout 发送工具列表

**返回的响应：**
```json
{"jsonrpc":"2.0","id":1,"result":{"tools":[{"name":"get_current_weather","description":"获取中国指定省市的当前天气预报。\n:param province: 省份名称\n:param city: 城市名称\n:return: 天气预报的 JSON 字符串（若失败则返回提示信息）","inputSchema":{"properties":{"province":{"title":"Province","type":"string"},"city":{"title":"City","type":"string"}},"required":["province","city"],"type":"object"}}]}}
```

**工具信息解析：**
- `name`：工具函数名
- `description`：函数的 docstring 文档
- `inputSchema`：JSON Schema 格式的输入参数定义

##### 4. 调用工具 (tools/call)

**发送的消息：**
```json
{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"get_current_weather","arguments":{"province":"北京","city":"海淀"}}}
```

**服务端处理流程：**
1. **验证工具名**：检查 `get_current_weather` 是否存在
2. **验证参数**：根据 `inputSchema` 验证参数格式
3. **参数转换**：将 JSON 参数转换为 Python 参数
4. **执行函数**：调用实际的 `get_current_weather` 函数
5. **处理结果**：将函数返回值转换为 JSON 格式
6. **返回结果**：通过 stdout 发送执行结果

**函数执行细节：**
```python
# 实际执行的函数
@mcp.tool()
def get_current_weather(province: str, city: str) -> str:
    # 1. 查找城市代码
    cityName = province + city
    cityID = cityMap.get(cityName, '101010200')
    
    # 2. 调用天气 API
    url = f'http://t.weather.sojson.com/api/weather/city/{cityID}'
    response = requests.get(url)
    
    # 3. 返回结果
    return response.text if response.status_code == 200 else '暂无天气预报'
```

#### 错误处理机制

**如果在初始化前发送请求：**
```json
{"jsonrpc":"2.0","id":2,"error":{"code":-32602,"message":"Invalid request parameters","data":""}}
```

**错误处理流程：**
1. **状态检查**：发现请求在初始化完成前发送
2. **拒绝请求**：不执行任何操作
3. **返回错误**：发送标准 JSON-RPC 错误响应
4. **错误代码**：`-32602` 表示无效参数

#### 底层通信机制

**消息传输过程：**
```
客户端 (stdin) → MCP 服务 (stdout) → 客户端
```

1. **编码**：Python 对象 → JSON 字符串
2. **传输**：通过标准输入输出流
3. **解码**：JSON 字符串 → Python 对象
4. **处理**：执行相应的业务逻辑
5. **响应**：结果 → JSON 字符串 → 标准输出

**为什么选择 stdio？**
- **简单可靠**：不依赖网络端口
- **进程隔离**：每个服务独立运行
- **易于调试**：可以直接看到原始消息
- **跨平台**：在所有操作系统上都支持
- **管道支持**：可以轻松集成到其他程序中

#### 与 HTTP 模式的区别

| 特性 | Stdio 模式 | HTTP 模式 |
|------|------------|-----------|
| 通信方式 | 标准输入输出 | HTTP 请求/响应 |
| 启动方式 | `mcp.run(transport="stdio")` | `mcp.run(transport="http")` |
| 端口需求 | 无需端口 | 需要指定端口 |
| 调试难度 | 简单（直接看消息） | 复杂（需要 HTTP 工具） |
| 集成方式 | 子进程管道 | HTTP 客户端 |
| 适用场景 | 本地集成、测试 | 网络服务、分布式 |

通过这种 stdio 模式，MCP 服务可以作为一个独立的进程运行，通过简单的文本协议与客户端进行通信，这就是为什么您可以直接用 JSON 消息与它交互的原理。

### SSE 代码测试方案

#### SSE 模式概述

SSE (Server-Sent Events) 模式是 MCP 的另一种传输方式，使用 HTTP 长连接和事件流进行实时通信。与 stdio 模式不同，SSE 模式支持网络通信，更适合分布式环境。

#### SSE 服务器配置

**服务器端代码** (`tests/weather_server.py`)：

```python
from fastmcp import FastMCP
import requests

# 初始化 FastMCP 服务器，指定主机和端口
mcp = FastMCP("weatherMcp", dependencies=["requests"], host="127.0.0.1", port=9001)

@mcp.tool()
def get_current_weather(province: str, city: str) -> str:
    """获取中国指定省市的当前天气预报"""
    # 天气查询逻辑...
    return json_string

if __name__ == "__main__":
    # 以 SSE 方式启动 MCP 服务
    mcp.run(transport="sse")
```

**关键配置：**
- `host="127.0.0.1"`：服务器监听地址
- `port=9001`：服务器监听端口
- `transport="sse"`：使用 SSE 传输方式

#### SSE 客户端测试

**测试脚本** (`tests/test_sse.py`)：

```python
import requests
from sseclient import SSEClient
import json
import time

# 服务器地址配置
base_url = 'http://127.0.0.1:9001'
sse_url = f'{base_url}/sse'

# 存储会话信息
session_id = None
post_url = None

# JSON-RPC 请求定义
initialize_request = {
    "jsonrpc": "2.0",
    "id": 0,
    "method": "initialize",
    "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {"sampling": {}, "roots": {"listChanged": True}},
        "clientInfo": {"name": "mcp", "version": "0.1.0"}
    }
}

def send_post_request(data):
    """发送 POST 请求并处理 202 响应"""
    try:
        response = requests.post(post_url, json=data)
        if response.status_code == 202:
            print(f"POST {data.get('method')} accepted")
        else:
            print(f"POST failed with status: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"POST error: {e}")

# 主测试循环
while True:
    try:
        # 连接到 SSE 事件流
        messages = SSEClient(sse_url)
        print("Connected to SSE")

        for msg in messages:
            if msg.event == 'endpoint':
                # 解析端点和会话 ID
                endpoint = msg.data
                session_id = endpoint.split('=')[-1]
                post_url = f'{base_url}{endpoint}'
                print(f"Received endpoint: {endpoint}")

                # 发送初始化请求
                send_post_request(initialize_request)
                
            elif msg.event == 'message':
                # 处理 SSE 推送的 JSON-RPC 响应
                try:
                    print(f"SSE message: {msg.data}")
                    if msg.data == '':
                        continue
                    
                    data = json.loads(msg.data)

                    # 处理初始化响应
                    if data.get('id') == 0:
                        print("Initialization successful, sending initialized notification")
                        send_post_request(initialized_notification)
                        send_post_request(tools_list_request)

                    # 处理工具列表响应
                    elif data.get('id') == 1:
                        print("Tools list received, exiting")
                        exit(0)

                except json.JSONDecodeError as e:
                    print(f"Failed to parse SSE message: {e}")

    except Exception as e:
        print(f"SSE connection error: {e}")
        time.sleep(5)  # 等待 5 秒后重连
```

#### SSE 通信流程详解

##### 1. 连接建立

**客户端连接 SSE 端点：**
```python
messages = SSEClient('http://127.0.0.1:9001/sse')
```

**服务器响应：**
- 建立 HTTP 长连接
- 发送 `endpoint` 事件，包含 POST 端点信息

##### 2. 端点获取

**服务器发送的 endpoint 事件：**
```
event: endpoint
data: /post?session=abc123
```

**客户端处理：**
- 解析端点信息
- 构建 POST 请求 URL：`http://127.0.0.1:9001/post?session=abc123`

##### 3. 初始化流程

**客户端发送初始化请求：**
```python
requests.post(post_url, json=initialize_request)
```

**服务器响应：**
- 返回 HTTP 202 状态码（请求已接受）
- 通过 SSE 流发送初始化结果

**SSE 消息格式：**
```
event: message
data: {"jsonrpc":"2.0","id":0,"result":{"protocolVersion":"2024-11-05",...}}
```

##### 4. 工具调用流程

**客户端发送工具列表请求：**
```python
tools_list_request = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list",
    "params": {}
}
send_post_request(tools_list_request)
```

**服务器响应：**
- 通过 SSE 流返回工具列表
- 客户端解析工具信息

#### SSE 与 Stdio 模式对比

| 特性 | SSE 模式 | Stdio 模式 |
|------|----------|------------|
| 通信方式 | HTTP 长连接 + 事件流 | 标准输入输出 |
| 网络支持 | 支持网络通信 | 仅本地进程 |
| 连接管理 | 自动重连机制 | 进程生命周期 |
| 调试难度 | 需要 HTTP 工具 | 直接查看消息 |
| 适用场景 | 分布式环境、网络服务 | 本地集成、测试 |
| 依赖库 | `sseclient-py` | 无额外依赖 |

#### 运行 SSE 测试

**步骤 1: 启动 SSE 服务器**
```bash
cd tests/
python3.13 weather_server.py
```

**步骤 2: 运行 SSE 测试客户端**
```bash
python3.13 test_sse.py
```

**预期输出：**
```
Connected to SSE
Received endpoint: /post?session=abc123
POST initialize accepted
SSE message: {"jsonrpc":"2.0","id":0,"result":{...}}
Initialization successful, sending initialized notification
POST notifications/initialized accepted
POST tools/list accepted
SSE message: {"jsonrpc":"2.0","id":1,"result":{"tools":[...]}}
Tools list received, exiting
```

#### SSE 模式的优势

1. **网络通信**：支持跨网络、跨机器的 MCP 服务调用
2. **实时性**：基于事件流的实时通信
3. **可扩展性**：支持多个客户端同时连接
4. **标准化**：使用标准的 HTTP 和 SSE 协议
5. **错误恢复**：内置重连机制，提高可靠性

#### 注意事项

1. **依赖安装**：需要安装 `sseclient-py` 库
   ```bash
   pip install sseclient-py
   ```

2. **端口管理**：确保端口 9001 未被占用

3. **网络配置**：在生产环境中需要配置防火墙和网络策略

4. **错误处理**：客户端包含重连逻辑，处理网络异常

5. **会话管理**：每个连接都有唯一的会话 ID，用于隔离不同的客户端

通过 SSE 模式，MCP 服务可以作为一个网络服务运行，支持远程调用和分布式部署，为构建可扩展的 AI 工具生态系统提供了基础。

# 测试客户端 `test_client.py` 使用说明

本文档详细介绍了 `test_client.py` 脚本的功能、使用方法和注意事项。该脚本是 MCP (Malleable C2 Protocol) 服务端的核心测试工具，覆盖了多种通信方式和功能调用。

## 1. 脚本功能

`test_client.py` 旨在测试本项目中实现的各类 MCP Agent 服务，主要包括：

- **两种通信协议测试**：
  - `PythonStdioTransport`: 通过标准输入/输出（stdio）与子进程中的 MCP Agent 通信，用于测试独立的工具脚本（如 `weather_stdio.py`）。
  - `SSETransport`: 通过服务器发送事件（Server-Sent Events）与网络上的 MCP Agent 服务通信，用于测试通过 HTTP 暴露的 MCP 服务（如主应用或 `es_mcp_server.py`）。

- **多种 MCP 功能调用**：
  - **`call_tool`**: 调用具体的工具函数（如 `get_current_weather`, `perform_elastic_search`）。
  - **`list_tools`**: 列出 Agent 提供的所有工具。
  - **`list_resources`**: 列出 Agent 提供的所有资源。
  - **`read_resource`**: 读取指定的资源内容。
  - **`get_prompt`**: 获取和渲染一个提示（Prompt）。

## 2. 环境准备与依赖

在运行测试前，请确保已完成以下准备工作：

1. **激活虚拟环境**：
   ```bash
   source venv/bin/activate
   ```

2. **安装项目依赖**：
   ```bash
   pip install -r requirements.txt
   ```

3. **启动所需的服务**：
   - **Elasticsearch 服务**: `test_es_sse` 测试依赖 Elasticsearch。请确保你的 Elasticsearch 服务（推荐 8.x 版本）已通过 Docker 或本地方式启动，并监听在 `9200` 端口。
   - **主应用服务 (可选)**: 如果要运行 `test_sse`，需要先启动主应用服务（`main.py`），它默认监听 `9001` 端口。
   - **ES MCP 服务 (可选)**: 如果要运行 `test_es_sse`，需要先启动 `es_mcp_server.py`，它默认监听 `9005` 端口。
     ```bash
     python tests/es_mcp_server.py
     ```

## 3. 如何运行测试

你可以通过修改 `test_client.py` 文件底部的 `main` 函数，选择性地注释或启用想要运行的测试用例。

- **运行所有测试**:
  确保所有依赖的服务（主应用、ES MCP 服务）都已启动，然后直接运行脚本：
  ```bash
  python tests/test_client.py
  ```

- **运行单个测试**:
  在 `main` 函数中注释掉其他测试，只保留想运行的那个，例如只测试 `test_es_sse`：
  ```python
  async def main():
      # await mytest()
      # ... (其他测试)
      await test_es_sse()

  if __name__ == "__main__":
      asyncio.run(main())
  ```
  然后运行脚本。

## 4. 测试用例详解

- `mytest()`: **天气工具测试 (stdio)**
  - **协议**: `PythonStdioTransport`
  - **目标**: 启动 `weather_stdio.py` 作为子进程，并调用 `get_current_weather` 工具。
  - **说明**: 这是最基础的 MCP Agent 测试，不依赖任何网络服务。

- `test_resource()`: **资源读取测试 (stdio)**
  - **协议**: `PythonStdioTransport`
  - **目标**: 从 `weather_stdio.py` 读取名为 `greeting://ljk` 的虚拟资源。
  - **说明**: 演示了 MCP 的资源读取能力。

- `test_resource_prompt()`: **Prompt 获取测试 (stdio)**
  - **协议**: `PythonStdioTransport`
  - **目标**: 从 `weather_stdio.py` 获取 `ask_review` 这个 Prompt。
  - **说明**: 演示了 MCP 的 Prompt 管理和渲染能力。

- `test_list()`: **工具/资源列表测试 (stdio)**
  - **协议**: `PythonStdioTransport`
  - **目标**: 列出 `weather_stdio.py` 提供的所有工具和资源。

- `test_sse()`: **天气工具测试 (SSE)**
  - **协议**: `SSETransport`
  - **目标**: 连接到主应用（`http://127.0.0.1:9001/sse`），并调用其代理的 `get_current_weather` 工具。
  - **前提**: 主应用 (`main.py`) 必须正在运行。

- `test_es_sse()`: **Elasticsearch 搜索测试 (SSE)**
  - **协议**: `SSETransport`
  - **目标**: 连接到 `es_mcp_server.py` 服务（`http://127.0.0.1:9005/sse`），并调用 `perform_elastic_search` 工具。
  - **前提**: Elasticsearch 服务和 `es_mcp_server.py` 都必须正在运行。

## 5. 常见问题 (Troubleshooting)

- **`httpx.HTTPStatusError: Server error '502 Bad Gateway'`**:
  - **原因**: 尝试连接的 SSE 服务未启动。例如，运行 `test_sse` 前没有启动主应用，或运行 `test_es_sse` 前没有启动 `es_mcp_server.py`。
  - **解决**: 启动对应的服务。

- **`fastmcp.exceptions.ToolError: ... Connection refused`**:
  - **原因**: 工具内部尝试连接的后端服务（如数据库、Elasticsearch）未启动。
  - **解决**: 检查并启动依赖的后端服务（如 Elasticsearch）。

- **`fastmcp.exceptions.ToolError: ... BadRequestError(400, 'media_type_header_exception', ...)`**:
  - **原因**: Python 的 `elasticsearch` 客户端库版本与 Elasticsearch 服务端版本不兼容。例如，客户端是 9.x，而服务端是 8.x。
  - **解决**: 统一版本。推荐使用 8.x 版本的 Elasticsearch 服务端和 `elasticsearch` Python 包（如 `pip install elasticsearch==8.11.4`）。

- **`FileNotFoundError`**:
  - **原因**: `PythonStdioTransport` 找不到指定的脚本文件（如 `weather_stdio.py`）。
  - **解决**: 确保在项目根目录下运行 `test_client.py`，或者提供正确的文件路径。 