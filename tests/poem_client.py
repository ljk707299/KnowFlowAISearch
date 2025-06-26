import asyncio
import os
import json
from dotenv import load_dotenv
from openai import OpenAI
from fastmcp import Client
from fastmcp.client.sampling import SamplingHandler
from mcp.types import SamplingMessage, TextContent
from mcp.shared.context import RequestContext # 用于类型提示

# --- 1. 配置和初始化 ---

# 加载 .env 文件中的环境变量，方便本地开发
load_dotenv()

# 从环境变量中获取 LLM (大语言模型) 的配置
# 这个客户端脚本需要直接调用 LLM，所以必须配置 API Key
API_KEY = os.getenv("ZHIPUAI_API_KEY")
BASE_URL = os.getenv("ZHIPUAI_BASE_URL")
MODEL_NAME = os.getenv("MODEL_NAME")

# 检查配置是否存在
if not all([API_KEY, BASE_URL, MODEL_NAME]):
    raise ValueError("请确保 .env 文件或环境变量中已配置 ZHIPUAI_API_KEY, ZHIPUAI_BASE_URL, 和 MODEL_NAME")

# 初始化 OpenAI 客户端，用于与 LLM 服务通信
ai_client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

# --- 2. 客户端采样处理器 (Client-Side Sampling Handler) ---

async def my_llm_handler(messages: list[SamplingMessage], params, context: RequestContext) -> str:
    """
    这是一个核心函数，作为客户端的"采样处理器"。
    当 MCP 服务器 (poem_server.py) 调用 `context.sample()` 时，请求会发送到这里。
    这个函数负责调用真实的 LLM，并将结果返回给服务器。
    
    这是一种"反向调用"或"委托计算"的模式，服务器只负责逻辑编排，
    而客户端（通常是主应用）负责执行资源密集型的 LLM 调用。

    Args:
        messages (list[SamplingMessage]): 从服务器传递过来的消息历史。
        params: 从服务器传递过来的采样参数 (如 max_tokens, temperature 等)。
        context (RequestContext): 包含请求上下文信息的对象 (如 request_id)。

    Returns:
        str: LLM 生成的文本内容。
    """
    print("-" * 50)
    print(f"收到来自服务器的采样请求 (ID: {context.request_id})")
    
    # 打印收到的消息，方便调试
    for msg in messages:
        if isinstance(msg.content, TextContent):
            print(f"  - Role: {msg.role}, Content: '{msg.content.text[:70]}...'")

    try:
        # 调用大语言模型
        response = ai_client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": m.role, "content": m.content.text} for m in messages if isinstance(m.content, TextContent)],
            # 可以根据需要从 params 中获取更多参数
            # max_tokens=params.max_tokens,
            # temperature=params.temperature,
        )
        # 提取并返回 LLM 生成的文本
        result_text = response.choices[0].message.content
        print(f"  > LLM 返回结果: '{result_text[:70]}...'")
        return result_text
    except Exception as e:
        error_message = f"调用 LLM 时出错: {e}"
        print(f"  > 错误: {error_message}")
        # 在发生错误时，将错误信息返回给服务器，而不是让程序崩溃
        return error_message

# --- 3. 主执行函数 ---

async def main():
    """
    主函数，演示如何连接到 poem_server 并调用其工具。
    """
    # MCP 服务器的地址
    SERVER_URL = "http://localhost:9003/sse"
    print(f"正在连接到 MCP 服务器: {SERVER_URL}")

    # 使用 `async with` 创建客户端
    # - `sampling_handler=my_llm_handler`: 这是最关键的一步，将我们的采样处理器
    #   注册给客户端，使其能够响应服务器的 `context.sample()` 调用。
    try:
        async with Client(SERVER_URL, sampling_handler=my_llm_handler) as client:
            # --- 测试 1: 调用 'generate_poem' 工具 ---
            print("\n" + "="*20 + " 测试 1: 生成诗歌 " + "="*20)
            poem_result = await client.call_tool("generate_poem", {"topic": "月光下的故乡"})
            # 工具调用的结果通常是一个列表，包含一个或多个结果对象
            # 我们需要检查列表是否非空，并访问第一个元素的 .text 属性
            if isinstance(poem_result, list) and poem_result and hasattr(poem_result[0], 'text'):
                print("\n生成的诗歌:")
                print(poem_result[0].text)
            else:
                print(f"未能获取有效的诗歌内容: {poem_result}")

            # --- 测试 2: 调用 'summarize_document' 工具 ---
            print("\n" + "="*20 + " 测试 2: 总结文档 " + "="*20)
            document = "在浩瀚的宇宙中，地球是目前已知唯一孕育了生命的星球。它的蓝色海洋、绿色陆地和白色云层构成了一幅美丽的画卷。然而，随着工业化的发展，环境问题日益严峻，保护地球家园已成为全人类共同的责任。"
            summary_result = await client.call_tool("summarize_document", {"document": document})
            if isinstance(summary_result, list) and summary_result and hasattr(summary_result[0], 'text'):
                print("\n生成的摘要:")
                print(summary_result[0].text)
            else:
                print(f"未能获取有效的摘要内容: {summary_result}")

    except Exception as e:
        print(f"\n连接到服务器或调用工具时发生错误: {e}")
        print("请确保 'poem_server.py' 正在运行，并且监听在 9003 端口。")


# 运行主异步函数
if __name__ == "__main__":
    asyncio.run(main())