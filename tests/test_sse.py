import requests
from sseclient import SSEClient
import json
import time

# 服务器地址
base_url = 'http://127.0.0.1:9001'
sse_url = f'{base_url}/sse'

# 存储会话 ID 和 POST 端点
session_id = None
post_url = None

# 初始化请求
initialize_request = {
    "jsonrpc": "2.0",
    "id": 0,
    "method": "initialize",
    "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {
            "sampling": {},
            "roots": {"listChanged": True}
        },
        "clientInfo": {
            "name": "mcp",
            "version": "0.1.0"
        }
    }
}

# 通知初始化完成
initialized_notification = {
    "jsonrpc": "2.0",
    "method": "notifications/initialized"
}

# 工具列表请求
tools_list_request = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list",
    "params": {}
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

 

while True:
    try:
        # 连接到 SSE
        messages = SSEClient(sse_url)
        print("Connected to SSE")

        for msg in messages:
            if msg.event == 'endpoint':
                # 解析端点和会话 ID
                endpoint = msg.data
                session_id = endpoint.split('=')[-1]
                post_url = f'{base_url}{endpoint}'
                print(f"Received endpoint: {endpoint}")

                # 发送 initialize 请求
                send_post_request(initialize_request)
                
                
 
            elif msg.event == 'message':
                # 解析 SSE 推送的 JSON-RPC 响应
                try:
                    print(f"SSE message: {msg.data}")
                    # 如果返回的是空
                    if msg.data == '':
                        continue
                    
                    data = json.loads(msg.data)
                   

                    # 处理 initialize 响应
                    if data.get('id') == 0:
                        print("Initialization successful, sending initialized notification")
                        send_post_request(initialized_notification)
                       
                        # 发送 tools/list 请求
                        send_post_request(tools_list_request)
                        

                    # 处理 tools/list 响应
                    elif data.get('id') == 1:
                        print("Tools list received, exiting")
                        exit(0)  # 任务完成，退出

                except json.JSONDecodeError as e:
                    print(f"Failed to parse SSE message: {e}")

            else:
                print(f"Unknown event: {msg.event}, data: {msg.data}")

    except Exception as e:
        print(f"SSE connection error: {e}")
        time.sleep(5)  # 等待 5 秒后重连