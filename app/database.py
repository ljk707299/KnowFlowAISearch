import sqlite3
import threading
from fastapi import Request

# 使用线程本地存储来管理数据库连接，确保每个线程都有独立的连接
thread_local = threading.local()

def get_db_connection():
    """
    获取当前线程的数据库连接。
    如果连接不存在，则创建一个新的连接并存储在线程本地存储中。
    """
    db = getattr(thread_local, '_database', None)
    if db is None:
        db = thread_local._database = sqlite3.connect('chat_history.db', check_same_thread=False)
        db.row_factory = sqlite3.Row  # 设置 row_factory 以便将行作为类似字典的对象访问
    return db

def close_db_connection(exception=None):
    """
    关闭当前线程的数据库连接。
    """
    db = getattr(thread_local, '_database', None)
    if db is not None:
        db.close()
        thread_local._database = None

def get_db(request: Request) -> sqlite3.Connection:
    """
    FastAPI 依赖项，用于在路由处理函数中获取数据库连接。
    它从请求状态中获取由中间件创建的连接。
    """
    return request.state.db

def init_db():
    """
    初始化数据库，创建所需的表。
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 创建聊天会话表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS chat_sessions (
        id TEXT PRIMARY KEY,
        summary TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # 创建消息表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT,
        role TEXT,
        content TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (session_id) REFERENCES chat_sessions (id)
    )
    ''')
    
    # 创建 MCP 服务器表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS mcp_servers (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        url TEXT NOT NULL,
        description TEXT,
        auth_type TEXT,
        auth_value TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # 创建 MCP 工具表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS mcp_tools (
        id TEXT PRIMARY KEY,
        server_id TEXT,
        name TEXT NOT NULL,
        description TEXT,
        input_schema TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (server_id) REFERENCES mcp_servers(id)
    )
    ''')
    
    # 创建订单表 (为 order_service.py 使用)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_name TEXT NOT NULL,
        price REAL NOT NULL,
        customer_name TEXT NOT NULL,
        sales_name TEXT NOT NULL,
        create_time INTEGER -- 使用 unixepoch 时间戳
    )
    ''')
    
    conn.commit()
    print("数据库初始化完成")

def insert_sample_data():
    """
    向数据库中插入一些示例订单数据，以便于测试。
    只有在订单表为空时才插入数据，防止重复。
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 检查 orders 表是否已有数据
    cursor.execute("SELECT COUNT(*) FROM orders")
    if cursor.fetchone()[0] > 0:
        print("订单表示例数据已存在，跳过插入。")
        return

    print("正在插入示例订单数据...")
    sample_orders = [
        ('笔记本电脑', 7000, '张三', '销售A', 1672502400), # 2023-01-01
        ('智能手机', 4500, '李四', '销售B', 1672588800), # 2023-01-02
        ('显示器', 1500, '张三', '销售A', 1675209600),   # 2023-02-01
        ('键盘', 300, '王五', '销售C', 1675296000),     # 2023-02-02
        ('智能手机', 5000, '张三', '销售B', 1677628800),   # 2023-03-01
        ('鼠标', 200, '李四', '销售A', 1677715200),     # 2023-03-02
        ('笔记本电脑', 8000, '赵六', '销售C', 1677801600), # 2023-03-03
    ]
    
    cursor.executemany(
        "INSERT INTO orders (product_name, price, customer_name, sales_name, create_time) VALUES (?, ?, ?, ?, ?)",
        sample_orders
    )
    conn.commit()
    print("示例订单数据插入完成。") 