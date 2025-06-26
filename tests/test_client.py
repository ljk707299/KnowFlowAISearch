from fastmcp import Client
from fastmcp.client.transports import (PythonStdioTransport, SSETransport)
import asyncio
import json

# 测试：通过 stdio 方式调用天气工具
async def mytest():
    print("\n" + "="*40)
    print("[1] test_call_tool (get_current_weather)")
    # 使用 PythonStdioTransport 启动 weather_stdio.py 子进程并建立通信
    async with Client(PythonStdioTransport("weather_stdio.py")) as client:
        # 调用工具 get_current_weather
        result = await client.call_tool("get_current_weather", {"province": "北京", "city": "海淀"})
        # 格式化输出结果
        print(json.dumps(result, indent=2, ensure_ascii=False) if isinstance(result, dict) else result)
        return result

# 测试：读取资源 greeting://ljk
async def test_resource():
    print("\n" + "="*40)

    print("[2] test_resource (greeting://ljk)")
    async with Client(PythonStdioTransport("weather_stdio.py")) as client:
        # 读取资源（Resource）是 MCP 协议中的一种标准数据对象，类似于 Web 的 URL 资源
        # 资源通常用于暴露静态/半静态数据，如配置、文档、模型参数、静态文本等
        # 通过唯一 URI 访问，如 greeting://denggao
        # 这里演示的是服务端通过 @mcp.resource("greeting://{name}") 注册的虚拟资源
        # 实际项目中可以用来暴露数据库内容、配置文件、静态文档等
        result = await client.read_resource("greeting://ljk")
        print(result)  # 输出资源对象列表，包含 uri、mimeType、text 等字段
        # 取出资源文本内容
        text = result[0].text if isinstance(result, list) and hasattr(result[0], 'text') else result
        print("Resource text:", text)  # 输出资源的实际内容
        return text

# 测试：调用 prompt（代码审查）
async def test_resource_prompt():
    print("\n" + "="*40)
    print("[3] test_resource_prompt (ask_review)")
    async with Client(PythonStdioTransport("weather_stdio.py")) as client:
        # 调用 prompt ask_review
        result = await client.get_prompt("ask_review", {"code_snippet": " print('hello') "})
        # result 是 GetPromptResult 对象，直接访问 content.text
        if hasattr(result, 'content') and hasattr(result.content, 'text'):
            print("Prompt content:", result.content.text)
        else:
            print(result)
        return result

# 测试：列出所有工具和资源
async def test_list():
    print("\n" + "="*40)
    print("[4] test_list (tools/resources)")
    async with Client(PythonStdioTransport("weather_stdio.py")) as client:
        # 获取所有工具
        tools = await client.list_tools()
        # 获取所有资源
        resources = await client.list_resources()
        print("Tools:", json.dumps([t.name for t in tools], ensure_ascii=False))
        print("Resources:", json.dumps([r.uri for r in resources], ensure_ascii=False))
        return tools, resources

# 测试：通过 SSE 方式调用天气工具
async def test_sse():
    print("\n" + "="*40)
    print("[5] test_sse (SSETransport)")
    # 连接到 SSE 服务端
    async with Client(SSETransport("http://127.0.0.1:9001/sse")) as client:
        # 获取所有工具
        tools = await client.list_tools()
        print("Tools:", json.dumps([t.name for t in tools], ensure_ascii=False))
        # 调用天气工具
        result = await client.call_tool("get_current_weather", {"province": "北京", "city": "海淀"})
        print("Weather result:", result)
        return result

# 测试：通过 SSE 方式调用 ES 搜索工具
async def test_es_sse():
    print("\n" + "="*40)
    print("[6] test_es_sse (SSETransport ES)")
    async with Client(SSETransport("http://127.0.0.1:9005/sse")) as client:
        # 获取所有工具
        tools = await client.list_tools()
        print("Tools:", json.dumps([t.name for t in tools], ensure_ascii=False))
        # 调用 ES 搜索工具
        result = await client.call_tool("perform_elastic_search", {"query": "哥哥"})
        print("ES result:", result)
        return result

# 主流程：串行执行所有测试，每个测试间隔 1 秒，输出分隔
async def main():
    # await mytest()
    # await asyncio.sleep(1)
    # await test_resource()
    # await asyncio.sleep(1)
    # await test_resource_prompt()
    # await asyncio.sleep(1)
    # await test_list()
    # await asyncio.sleep(1)
    # await test_sse()
    await asyncio.sleep(1)
    await test_es_sse()

if __name__ == "__main__":
    # 启动主测试流程
    asyncio.run(main())