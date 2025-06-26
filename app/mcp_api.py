from fastapi import APIRouter, HTTPException, Depends
import sqlite3
# import requests # 未使用，予以删除
import uuid
import json
from datetime import datetime
from fastmcp import Client
from fastmcp.client.transports import SSETransport
from database import get_db # 导入 get_db 依赖项

# 创建一个 FastAPI APIRouter 实例
# - prefix="/api/mcp": 所有此路由下的路径都会自动添加 /api/mcp 前缀
# - tags=["mcp"]: 在 FastAPI 自动生成的 API 文档中，将这些接口归类到 "mcp" 标签下
router = APIRouter(prefix="/api/mcp", tags=["mcp"])

async def fetch_and_store_mcp_tools(db: sqlite3.Connection, server_id: str, server_url: str, auth_type: str, auth_value: str):
    """
    连接到指定的 MCP 服务器，获取其提供的所有工具，并将这些工具信息存储到本地数据库。

    这是一个核心的辅助函数，用于在创建、更新或刷新 MCP 服务器时同步工具信息。

    Args:
        db (sqlite3.Connection): 数据库连接对象。
        server_id (str): MCP 服务器在数据库中的唯一ID。
        server_url (str): MCP 服务器的 URL 地址 (例如 "http://127.0.0.1:9001")。
        auth_type (str): 认证类型 (当前未使用)。
        auth_value (str): 认证值 (当前未使用)。
    """
    try:
        # 使用 fastmcp 客户端和 SSETransport 连接到目标服务器
        # SSETransport 适用于通过 Server-Sent Events (SSE) 协议通信的 MCP 服务器
        async with Client(SSETransport(server_url)) as client:
            # 调用客户端的 list_tools 方法，获取工具列表
            tools = await client.list_tools()
            print(f"从 {server_url} 获取到的工具: {tools}")

        cursor = db.cursor()
        # 在插入新工具前，先删除该服务器之前存储的所有旧工具，以保证数据同步
        cursor.execute("DELETE FROM mcp_tools WHERE server_id = ?", (server_id,))

        # 遍历获取到的每个工具，并将其信息插入到 mcp_tools 表中
        for tool in tools:
            cursor.execute(
                """
                INSERT INTO mcp_tools (id, server_id, name, description, input_schema, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),  # 为每个工具生成一个唯一的ID
                    server_id,          # 关联到对应的服务器ID
                    tool.name,          # 工具名称
                    tool.description,   # 工具描述
                    json.dumps(tool.inputSchema), # 工具的输入参数定义 (JSON格式)
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S') # 创建时间
                )
            )
        # 提交数据库事务，使更改生效
        db.commit()
    except Exception as e:
        # 如果在获取或存储过程中发生任何异常，打印错误日志
        # 这有助于调试，例如服务器地址不通、服务器返回格式错误等问题
        print(f"从 {server_url} 获取或存储工具时出错: {str(e)}")

@router.post("/servers", summary="创建MCP服务器")
async def create_mcp_server(server: dict, db: sqlite3.Connection = Depends(get_db)):
    """
    注册一个新的 MCP 服务器。

    接收服务器的基本信息，将其存入数据库，并立即调用 `fetch_and_store_mcp_tools`
    来获取该服务器上的工具列表。
    """
    server_id = str(uuid.uuid4())
    try:
        cursor = db.cursor()
        # 将 MCP 服务器的信息插入到 mcp_servers 表中
        cursor.execute(
            """
            INSERT INTO mcp_servers (id, name, url, description, auth_type, auth_value, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                server_id,
                server["name"],
                server["url"],
                server.get("description", ""),
                server.get("auth_type", "none"),
                server.get("auth_value", ""),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            )
        )
        db.commit()

        # 服务器信息入库后，立即获取并存储其工具
        await fetch_and_store_mcp_tools(
            db, server_id, server["url"], server.get("auth_type", "none"), server.get("auth_value", "")
        )

        return {"id": server_id, "message": "MCP 服务器创建成功"}
    except Exception as e:
        # 如果发生数据库错误或其他异常，返回 500 错误
        raise HTTPException(status_code=500, detail=f"创建 MCP 服务器失败: {str(e)}")

@router.get("/servers", summary="列出所有MCP服务器")
async def list_mcp_servers(db: sqlite3.Connection = Depends(get_db)):
    """
    获取所有已注册的 MCP 服务器列表。
    """
    try:
        cursor = db.cursor()
        cursor.execute("SELECT id, name, url, description, auth_type, auth_value, created_at, updated_at FROM mcp_servers")
        # 将查询结果从元组列表转换为字典列表，方便前端处理
        servers = [dict(row) for row in cursor.fetchall()]
        return servers
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"列出 MCP 服务器失败: {str(e)}")

@router.get("/servers/{server_id}", summary="获取特定MCP服务器信息")
async def get_mcp_server(server_id: str, db: sqlite3.Connection = Depends(get_db)):
    """
    根据服务器 ID 获取其详细信息。
    """
    try:
        cursor = db.cursor()
        cursor.execute("SELECT id, name, url, description, auth_type, auth_value, created_at, updated_at FROM mcp_servers WHERE id = ?", (server_id,))
        server = cursor.fetchone()
        if not server:
            # 如果数据库中找不到对应ID的服务器，返回 404 错误
            raise HTTPException(status_code=404, detail="MCP 服务器未找到")
        return dict(server)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取 MCP 服务器信息失败: {str(e)}")

@router.put("/servers/{server_id}", summary="更新MCP服务器信息")
async def update_mcp_server(server_id: str, server: dict, db: sqlite3.Connection = Depends(get_db)):
    """
    更新一个已存在的 MCP 服务器的信息。

    更新数据库中的记录后，会重新调用 `fetch_and_store_mcp_tools` 来刷新工具列表。
    """
    try:
        cursor = db.cursor()
        cursor.execute(
            """
            UPDATE mcp_servers
            SET name = ?, url = ?, description = ?, auth_type = ?, auth_value = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                server["name"],
                server["url"],
                server.get("description", ""),
                server.get("auth_type", "none"),
                server.get("auth_value", ""),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                server_id
            )
        )
        if cursor.rowcount == 0:
            # 如果更新影响的行数为 0，说明该 ID 不存在
            raise HTTPException(status_code=404, detail="MCP 服务器未找到")

        db.commit()

        # 重新获取并存储工具
        await fetch_and_store_mcp_tools(
            db, server_id, server["url"], server.get("auth_type", "none"), server.get("auth_value", "")
        )

        return {"message": "MCP 服务器更新成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新 MCP 服务器失败: {str(e)}")

@router.delete("/servers/{server_id}", summary="删除MCP服务器")
async def delete_mcp_server(server_id: str, db: sqlite3.Connection = Depends(get_db)):
    """
    删除一个 MCP 服务器及其所有关联的工具。

    这是一个级联删除操作，确保数据的一致性。
    """
    try:
        cursor = db.cursor()
        # 1. 首先删除 mcp_tools 表中与该服务器关联的所有工具
        cursor.execute("DELETE FROM mcp_tools WHERE server_id = ?", (server_id,))
        # 2. 然后删除 mcp_servers 表中该服务器本身的记录
        cursor.execute("DELETE FROM mcp_servers WHERE id = ?", (server_id,))
        if cursor.rowcount == 0:
            # 如果删除服务器记录时影响行数为0，说明服务器本就不存在
            raise HTTPException(status_code=404, detail="MCP 服务器未找到")
        db.commit()
        return {"message": "MCP 服务器已成功删除"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除 MCP 服务器失败: {str(e)}")

@router.post("/servers/{server_id}/refresh-tools", summary="刷新服务器工具列表")
async def refresh_mcp_server_tools(server_id: str, db: sqlite3.Connection = Depends(get_db)):
    """
    手动触发，为一个已注册的 MCP 服务器刷新其工具列表。

    当 MCP Agent 服务更新了工具后，可以通过调用此接口来同步。
    """
    try:
        cursor = db.cursor()
        # 先从数据库中根据ID查出服务器的 URL
        cursor.execute("SELECT url, auth_type, auth_value FROM mcp_servers WHERE id = ?", (server_id,))
        server = cursor.fetchone()
        if not server:
            raise HTTPException(status_code=404, detail="MCP 服务器未找到")

        # 调用核心函数来刷新工具
        await fetch_and_store_mcp_tools(db, server_id, server["url"], server["auth_type"], server["auth_value"])

        return {"message": "工具列表已刷新"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"刷新工具列表失败: {str(e)}")

@router.get("/tools", summary="列出所有工具")
async def list_tools(server_id: str = None, db: sqlite3.Connection = Depends(get_db)):
    """
    获取所有已存储在本地数据库中的工具。

    支持通过 `server_id` 查询参数进行过滤，只返回特定服务器的工具。
    """
    try:
        cursor = db.cursor()
        if server_id:
            # 如果提供了 server_id，则查询该服务器下的工具
            cursor.execute("SELECT id, server_id, name, description, input_schema, created_at FROM mcp_tools WHERE server_id = ?", (server_id,))
        else:
            # 否则，查询所有工具
            cursor.execute("SELECT id, server_id, name, description, input_schema, created_at FROM mcp_tools")
        tools = [dict(row) for row in cursor.fetchall()]
        return tools
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"列出工具失败: {str(e)}")

async def get_mcp_server_details(server_id: str, db: sqlite3.Connection) -> dict:
    """
    这是一个供项目内部其他 Python 模块调用的异步辅助函数。
    它不作为 API 端点暴露给外部。
    根据服务器 ID 从数据库中获取其完整的详细信息。

    Args:
        server_id (str): 服务器ID。
        db (sqlite3.Connection): 数据库连接。

    Returns:
        dict: 包含服务器信息的字典，如果未找到则返回 None。
    """
    cursor = db.cursor()
    cursor.execute("SELECT * FROM mcp_servers WHERE id = ?", (server_id,))
    server = cursor.fetchone()
    return dict(server) if server else None