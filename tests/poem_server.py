from fastmcp import FastMCP, Context
import requests 

# Initialize poemMCP server
mcp = FastMCP(
    "poemMCP",
    dependencies=["requests"],
    host="127.0.0.1",
    port=9003,
)

# --------------------------------------------------------------------------
# 注意:
# 下方两个工具 (@mcp.tool) 都使用了 `context.sample(...)` 方法。
# 这是一个特殊功能，它会将生成的任务"委托"给一个外部的大语言模型 (LLM)。
# 这意味着，要让这个 poem_server.py 正常工作，必须有一个配置了 LLM 的
# 主应用在运行，并且 fastmcp 知道如何与该 LLM 通信。
# 在本项目的架构中，通常由主应用(main.py)连接到 MCP Agent,
# 并将自身的 LLM 能力通过 Context 传递给 Agent。
# --------------------------------------------------------------------------

# 定义生成诗歌的工具
@mcp.tool(
    name="generate_poem",
    description="根据给定的主题生成一首诗"
)
async def generate_poem(context: Context, topic: str) -> str:
    """
    根据用户提供的主题，调用 LLM 生成一首诗。

    Args:
        context (Context): MCP 上下文对象，由 fastmcp 框架自动注入。
                           它提供了访问底层 LLM 的能力。
        topic (str): 诗歌的主题。

    Returns:
        str: 由 LLM 生成的诗歌内容。
    """
    print(f"接收到作诗请求，主题: {topic}")
    # 使用 context.sample 调用外部 LLM
    # - 第一个参数是用户提示 (Prompt)
    # - system_prompt 是系统提示，用于设定 LLM 的角色或行为
    poem = await context.sample(
        f'请创作一首关于"{topic}"的简短诗歌。',
        system_prompt="你是一位才华横溢的诗人。"
    )
    print(f"生成的诗歌: {poem}")
    return poem




# 定义总结文档的工具
@mcp.tool(
    name="summarize_document",
    description="总结给定的文档"
)
async def summarize_document(context: Context, document: str) -> str:
    """
    对用户提供的文档内容进行总结。

    Args:
        context (Context): MCP 上下文对象。
        document (str): 需要总结的文档原文。

    Returns:
        str: 由 LLM 生成的总结内容。
    """
    print(f"接收到文档总结请求，文档内容: {document[:50]}...")
    response = await context.sample(
        f"请总结以下文档: {document}",
        system_prompt="你是一个乐于助人的摘要生成助手。"
    )
    print(f"生成的摘要: {response}")
    return response


if __name__ == "__main__":
    print("正在启动古诗词与摘要 MCP Agent 服务，监听端口 9003...")
    # 使用 SSE (Server-Sent Events) 协议运行服务
    # 这是一个基于 HTTP 的轻量级协议，非常适合此类应用
    mcp.run(transport="sse")