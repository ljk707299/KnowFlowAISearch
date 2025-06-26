from fastapi import FastAPI, Request, HTTPException, Query, Depends
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from openai import OpenAI
from openai import AsyncOpenAI
import os
import json
import uuid
import httpx # 导入 httpx 用于异步 HTTP 请求
import urllib.parse
from datetime import datetime
import asyncio
import sqlite3
from contextlib import asynccontextmanager # 导入 asynccontextmanager
from mcp_api import router as mcp_router # 仅导入 MCP 路由
from fastmcp import Client
from fastmcp.client.transports import SSETransport
from dotenv import load_dotenv
from database import get_db_connection, close_db_connection, init_db, insert_sample_data, get_db # 导入 get_db


# 尝试从 .env 文件加载环境变量。
# 如果 .env 文件不存在，此函数会静默地跳过，
# 程序将继续从系统级的环境变量中读取配置。
# 这使得应用既方便本地开发（使用.env），又能无缝部署。
load_dotenv()

# 从环境变量中获取配置
API_KEY = os.getenv("ZHIPUAI_API_KEY")
BASE_URL= os.getenv("ZHIPUAI_BASE_URL")
MODEL_NAME = os.getenv("MODEL_NAME")
 
BOCHAAI_SEARCH_API_KEY = os.getenv("BOCHAAI_SEARCH_API_KEY")

# 检查关键配置是否存在
if not all([API_KEY, BASE_URL, MODEL_NAME]):
    raise ValueError("关键环境变量 (ZHIPUAI_API_KEY, ZHIPUAI_BASE_URL, MODEL_NAME) 未设置。请检查您的 .env 文件或系统环境变量。")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI 的 lifespan 事件处理器。
    在应用启动时初始化数据库并插入示例数据。
    """
    # 应用启动时执行
    print("应用启动...")
    init_db()
    insert_sample_data()
    yield
    # 应用关闭时执行 (如果需要可以添加关闭逻辑)
    print("应用关闭。")

# Initialize FastAPI app
app = FastAPI(
    title="KnowFlow AI Search",
    description="一个集成了AI搜索和MCP协议的智能问答应用",
    lifespan=lifespan # 使用新的 lifespan 事件处理器
)

# 注册 MCP 管理相关的 API 路由
# 这一行代码将 mcp_api.py 文件中定义的所有 API 端点 (如 /api/mcp/servers)
# 整合到主应用中。前端的 MCP 管理页面 (mcp.html) 正是通过调用这些接口
# 来实现对外部工具服务器的增删改查和刷新操作。
app.include_router(mcp_router)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.middleware("http")
async def db_session_middleware(request: Request, call_next):
    """
    中间件，用于管理每个请求的数据库连接。
    在请求开始时获取连接，在请求结束时关闭连接。
    """
    try:
        request.state.db = get_db_connection()
        response = await call_next(request)
    finally:
        close_db_connection()
    return response

# Initialize AI client
ai_client = OpenAI(
    api_key = API_KEY,
    base_url = BASE_URL
)

async_ai_client = AsyncOpenAI(
    api_key = API_KEY,
    base_url = BASE_URL
)

# Perform web search (optional, retained for flexibility)
# https://open.bochaai.com/overview
async def perform_web_search(query: str):
    """
    执行网络搜索。
    使用 httpx 异步请求 BochaAI 的搜索 API。
    参考文档: https://bocha-ai.feishu.cn/wiki/RXEOw02rFiwzGSkd9mUcqoeAnNK
    """
    if not BOCHAAI_SEARCH_API_KEY:
        return "BOCHAAI_SEARCH_API_KEY 未配置，无法执行网络搜索"
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {BOCHAAI_SEARCH_API_KEY}'
    }
    payload = {
        "query": query,
        "freshness": "noLimit",
        "summary": True,
        "count": 10
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post("https://api.bochaai.com/v1/web-search", headers=headers, json=payload, timeout=30.0)
            response.raise_for_status()  # 如果状态码不是 2xx，则引发异常
            json_data = response.json()
            print(f"bochaai search response: {json_data}")
            return str(json_data)
        except httpx.HTTPStatusError as e:
            return f"搜索失败，状态码: {e.response.status_code}, 响应: {e.response.text}"
        except httpx.RequestError as e:
            return f"执行网络搜索时出错: {str(e)}"
        except json.JSONDecodeError as e:
            return f"搜索结果JSON解析失败: {str(e)}"

async def save_chat_message(db: sqlite3.Connection, session_id: str, role: str, content: str):
    """
    将单条聊天消息保存到数据库。
    """
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
        (session_id, role, content, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    )
    db.commit()

async def create_new_chat_session(db: sqlite3.Connection, session_id: str, query: str, response: str):
    """
    创建新的聊天会话并保存初始消息。
    """
    cursor = db.cursor()
    summary = query[:50] + ("..." if len(query) > 50 else "")
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute(
        "INSERT INTO chat_sessions (id, summary, created_at, updated_at) VALUES (?, ?, ?, ?)",
        (session_id, summary, now, now)
    )
    await save_chat_message(db, session_id, "user", query)
    await save_chat_message(db, session_id, "assistant", response)
    db.commit()

async def add_message_to_session(db: sqlite3.Connection, session_id: str, query: str, response: str):
    """
    向现有会话中添加用户和助手的消息。
    """
    await save_chat_message(db, session_id, "user", query)
    await save_chat_message(db, session_id, "assistant", response)
    # 更新会话的 updated_at 时间戳
    cursor = db.cursor()
    cursor.execute(
        "UPDATE chat_sessions SET updated_at = ? WHERE id = ?",
        (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), session_id)
    )
    db.commit()

@app.get("/", include_in_schema=False)
async def root():
    """
    根路径，重定向到聊天页面。
    """
    return FileResponse("static/chat.html")

@app.get("/mcp", include_in_schema=False)
async def mcp_management():
    """
    MCP 管理页面。
    """
    return FileResponse("static/mcp.html")

async def process_stream_request(query: str, session_id: str = None, web_search: bool = False, agent_mode: bool = False):
    """
    处理流式聊天请求的核心逻辑。
    注意: 此函数为异步生成器，独立管理数据库连接，以兼容 StreamingResponse。
    """
    db = None
    try:
        # 为此流式请求独立创建数据库连接
        db = sqlite3.connect('chat_history.db')
        db.row_factory = sqlite3.Row
        
        # 确定是新会话还是现有会话
        is_new_session = session_id is None
        if is_new_session:
            session_id = str(uuid.uuid4()) # 为新会话生成唯一ID

        # 准备消息历史
        history_messages = []
        if not is_new_session:
            cursor = db.cursor()
            cursor.execute("SELECT role, content FROM messages WHERE session_id = ? ORDER BY created_at ASC", (session_id,))
            rows = cursor.fetchall()
            for row in rows:
                history_messages.append({"role": row["role"], "content": row["content"]})

        # 根据是否启用网络搜索来构建上下文
        if web_search:
            print("正在执行网络搜索...")
            web_results = await perform_web_search(query)
            
            # 检查网络搜索是否返回了已知的错误信息
            error_prefixes = ["BOCHAAI_SEARCH_API_KEY 未配置", "搜索失败", "执行网络搜索时出错", "搜索结果JSON解析失败"]
            if any(web_results.startswith(prefix) for prefix in error_prefixes):
                print(f"网络搜索失败: {web_results}")
                # 如果是错误，直接将错误信息作为消息返回给前端，并终止处理
                yield f"data: {json.dumps({'content': f'网络搜索功能异常: {web_results}'})}\n\n"
                yield f"data: {json.dumps({'event': 'done', 'session_id': session_id})}\n\n"
                return # 终止生成器

            # 将搜索结果作为上下文，添加到历史消息的最前面
            history_messages.insert(0, {"role": "system", "content": f"网络搜索结果: {web_results}"})

        # 将当前用户查询添加到消息历史中
        history_messages.append({"role": "user", "content": query})

        async def generate_simple_response():
            """
            生成简单的文本响应（无工具调用）。
            """
            response_stream = ai_client.chat.completions.create(
                model=MODEL_NAME,
                messages=history_messages,
                stream=True
            )
            
            full_response = ""
            for chunk in response_stream:
                content = chunk.choices[0].delta.content or ""
                full_response += content
                yield f"data: {json.dumps({'content': content})}\n\n"
                await asyncio.sleep(0.01)
            
            if is_new_session:
                await create_new_chat_session(db, session_id, query, full_response)
            else:
                await add_message_to_session(db, session_id, query, full_response)
                
            print(f"完整响应: {full_response}")

        async def generate_with_tools():
            """
            使用工具生成响应。
            """
            print("进入 Agent 模式...")
            # 这里是主应用与 MCP API 模块的间接交互点。
            # Agent 模式启动后，首先从数据库中查询所有通过 MCP 管理页面注册的工具。
            # 这些工具数据是由 mcp_api.py 中的接口负责写入和管理的。
            cursor = db.cursor()
            cursor.execute("SELECT t.*, s.url FROM mcp_tools t JOIN mcp_servers s ON t.server_id = s.id")
            tools = [dict(row) for row in cursor.fetchall()]
            
            if not tools:
                yield f"data: {json.dumps({'content': '没有可用的工具。'})}\n\n"
                return

            tool_descriptions = "\n".join([
                f"- 工具名: {tool['name']}\n  描述: {tool['description']}\n  输入格式: {tool['input_schema']}"
                for tool in tools
            ])

            # 2. 构建 Prompt, 让 LLM 决定是否使用工具
            agent_prompt = f"""
            你是一个智能助手，能够理解用户的问题并决定是否需要调用外部工具来回答。
            
            可用工具列表:
            {tool_descriptions}
            
            用户问题: "{query}"

            请判断是否需要以及使用哪个工具。如果需要，请仅返回一个 JSON 对象，格式如下：
            {{
              "tool_name": "工具名",
              "parameters": {{ "参数1": "值1", "参数2": "值2" }}
            }}
            如果不需要任何工具，请直接回答用户的问题。
            """
            
            try:
                # 3. 调用 LLM (使用异步客户端)
                response = await async_ai_client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[{"role": "user", "content": agent_prompt}],
                    # 部分模型支持强制JSON输出，可以提高稳定性
                    # response_format={"type": "json_object"} 
                )
                decision = response.choices[0].message.content.strip()
                print(f"LLM决策: {decision}")

                # 4. 解析决策并执行工具
                try:
                    decision_json = json.loads(decision)
                    tool_name = decision_json.get("tool_name")
                    parameters = decision_json.get("parameters")
                    
                    # 寻找要调用的工具
                    target_tool = next((t for t in tools if t['name'] == tool_name), None)

                    if target_tool and parameters is not None:
                        # 调用工具
                        async with Client(SSETransport(target_tool['url'])) as client: 
                            tool_result = await client.call_tool(tool_name, parameters)
                        
                        # 5. 将工具结果交给 LLM 进行最终回答
                        final_prompt = f"工具 {tool_name} 的执行结果是: {tool_result}\n\n请基于这个结果，回答用户最初的问题: '{query}'"
                        final_stream = ai_client.chat.completions.create(
                            model=MODEL_NAME,
                            messages=[{"role": "user", "content": final_prompt}],
                            stream=True
                        )
                        final_answer = ""
                        for chunk in final_stream:
                            content = chunk.choices[0].delta.content or ""
                            final_answer += content
                            yield f"data: {json.dumps({'content': content})}\n\n"
                        
                    else: # 如果LLM返回了JSON但格式不正确
                        final_answer = decision
                        yield f"data: {json.dumps({'content': decision})}\n\n"

                except (json.JSONDecodeError, AttributeError):
                    # 如果LLM的回答不是JSON，直接作为最终答案
                    final_answer = decision
                    yield f"data: {json.dumps({'content': decision})}\n\n"

                # 6. 保存最终的问答到数据库
                if is_new_session:
                    await create_new_chat_session(db, session_id, query, final_answer)
                else:
                    await add_message_to_session(db, session_id, query, final_answer)

            except Exception as e:
                error_message = f"Agent模式处理时发生错误: {e}"
                print(error_message)
                yield f"data: {json.dumps({'error': error_message})}\n\n"


        try:
            if agent_mode:
                async for data in generate_with_tools():
                     yield data
            else:
                async for data in generate_simple_response():
                    yield data
        except Exception as e:
            error_message = f"处理流式请求时发生错误: {str(e)}"
            print(error_message)
            yield f"data: {json.dumps({'error': error_message})}\n\n"
        finally:
            # 响应结束时发送一个特殊事件
            yield f"data: {json.dumps({'event': 'done', 'session_id': session_id})}\n\n"

    finally:
        if db:
            db.close()
            print("流式请求处理完毕，数据库连接已关闭。")

@app.get("/api/stream")
async def stream(
    query: str,
    session_id: str = Query(None),
    web_search: bool = Query(False),
    agent_mode: bool = Query(False)
):
    """
    流式聊天 API 端点。
    接收用户查询并以流式响应返回 AI 的回答。
    """
    return StreamingResponse(
        process_stream_request(query, session_id, web_search, agent_mode),
        media_type="text/event-stream"
    )

@app.get("/api/chat/history")
async def get_chat_history(db: sqlite3.Connection = Depends(get_db)):
    """
    获取所有聊天会话的历史记录。
    """
    cursor = db.cursor()
    cursor.execute("SELECT id, summary, created_at, updated_at FROM chat_sessions ORDER BY updated_at DESC")
    sessions = [dict(row) for row in cursor.fetchall()]
    return sessions

@app.get("/api/chat/session/{session_id}")
async def get_session(session_id: str, db: sqlite3.Connection = Depends(get_db)):
    """
    获取指定会话的详细信息和消息历史。
    """
    cursor = db.cursor()
    
    # 获取会话信息
    cursor.execute("SELECT id, summary, created_at, updated_at FROM chat_sessions WHERE id = ?", (session_id,))
    session_info = cursor.fetchone()
    if not session_info:
        raise HTTPException(status_code=404, detail="会话未找到")
        
    # 获取消息历史
    cursor.execute("SELECT role, content, created_at FROM messages WHERE session_id = ? ORDER BY created_at ASC", (session_id,))
    messages = [dict(row) for row in cursor.fetchall()]
    
    return {"session": dict(session_info), "messages": messages}

@app.delete("/api/chat/session/{session_id}")
async def delete_session(session_id: str, db: sqlite3.Connection = Depends(get_db)):
    """
    删除指定的聊天会话及其所有消息。
    """
    cursor = db.cursor()
    # 首先删除关联的消息
    cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
    # 然后删除会话本身
    cursor.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
    if cursor.rowcount == 0:
        db.commit() # 即使会话未找到，也应提交删除消息的操作
        raise HTTPException(status_code=404, detail="会话未找到")
    db.commit()
    return {"message": "会话已成功删除"}

@app.get("/api/chat/export/{session_id}")
async def export_session(session_id: str, db: sqlite3.Connection = Depends(get_db)):
    """
    以 JSON 格式导出指定聊天会话的内容。
    """
    cursor = db.cursor()
    cursor.execute("SELECT role, content, created_at FROM messages WHERE session_id = ? ORDER BY created_at ASC", (session_id,))
    messages = [dict(row) for row in cursor.fetchall()]
    
    if not messages:
        raise HTTPException(status_code=404, detail="会话未找到或无消息")
        
    # 创建导出文件名
    filename = f"chat_session_{session_id}.json"
    # 将消息保存到临时文件
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(messages, f, ensure_ascii=False, indent=4)
        
    # 使用 FileResponse 返回文件，并在后台删除
    return FileResponse(filename, media_type='application/json', filename=filename)

@app.get("/api/health", summary="健康检查", tags=["system"])
def health_check():
    """
    提供一个简单的健康检查端点，用于监控服务状态。
    """
    return {"status": "ok"}


if __name__ == "__main__":
    # 应用启动时会自动初始化数据库，此处无需操作
    import uvicorn
    # 使用 uvicorn 启动应用
    # 在生产环境中，建议使用 gunicorn + uvicorn worker
    uvicorn.run(app, host="0.0.0.0", port=8000)