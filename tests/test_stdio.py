import subprocess
import json


# 4条JSON-RPC消息
test_messages = [
    {"jsonrpc":"2.0","id":0,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{"sampling":{}},"clientInfo":{"name":"mcp","version":"0.1.0"}}},
    {"jsonrpc":"2.0","method":"notifications/initialized"},
    {"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}},
    {"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"get_current_weather","arguments":{"province":"北京","city":"海淀"}}}
]

def main():
    # 启动接收端脚本，通过管道通信
    process = subprocess.Popen(
        ["python", "weather_stdio.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
        encoding='utf-8'
    )

    responses = []
    for idx, msg in enumerate(test_messages, 1):
        print(f"\n{'='*30}\n请求 {idx}:")
        print(json.dumps(msg, indent=2, ensure_ascii=False))
        msg_str = json.dumps(msg) + "\n\n"
        process.stdin.write(msg_str)
        process.stdin.flush()

        if "id" in msg:
            response = process.stdout.readline().strip()
            if response:
                try:
                    resp_obj = json.loads(response)
                    formatted = json.dumps(resp_obj, indent=2, ensure_ascii=False)
                except Exception:
                    formatted = response
                print(f"\n响应 {idx}:")
                print(formatted)
                print(f"{'-'*30}")
                responses.append(response)

    # 关闭管道并等待接收端进程结束
    process.stdin.close()
    process.wait()

    # 打印所有响应
    for i, resp in enumerate(responses, 1):
        print(f"Response {i}:   {resp}")

if __name__ == "__main__":
    main()
