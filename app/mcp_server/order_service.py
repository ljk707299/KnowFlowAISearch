from fastmcp import FastMCP
import sqlite3
from contextlib import contextmanager
import os

# 创建 FastMCP 服务器实例
# "orderMcp" 是此服务的唯一名称
# host 和 port 参数已被弃用，应在启动时通过 uvicorn 或 mcp.run() 指定
mcp = FastMCP("orderMcp")

# 统一数据库路径，确保无论从哪里启动都能找到正确的数据库
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'chat_history.db'))

@contextmanager
def db_cursor():
    """
    一个上下文管理器，用于安全地处理数据库连接和游标。
    它能确保连接在使用后被正确关闭，并在出错时回滚事务。
    """
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        yield conn.cursor()
        conn.commit()  # 操作成功，提交事务
    except sqlite3.Error as e:
        print(f"数据库操作时发生错误: {e}")
        if conn:
            conn.rollback()  # 操作失败，回滚事务
        # 将数据库异常包装成对LLM更友好的字符串返回
        raise Exception(f"数据库操作失败: {e}")
    finally:
        if conn:
            conn.close()

@mcp.tool(description="获取指定月份的销售总额")
def get_monthly_sales_total(month: int) -> str:
    """
    查询指定月份的总销售额。
    """
    if not (1 <= month <= 12):
        return "无效的月份，请输入1到12之间的数字。"
    
    month_str = f"{month:02d}"
    
    try:
        with db_cursor() as cursor:
            query = """
            SELECT SUM(price) as total_sales
            FROM orders
            WHERE strftime('%m', datetime(create_time, 'unixepoch')) = ?
            """
            cursor.execute(query, (month_str,))
            result = cursor.fetchone()
            
            if result is None or result["total_sales"] is None:
                return f"{month}月没有销售记录。"
            return f"{month}月的销售总额为: {result['total_sales']:.2f}元"
    except Exception as e:
        return str(e)

@mcp.tool(description="获取消费最高的用户")
def get_highest_spending_customer() -> str:
    """
    查询消费总额最高的用户及其消费金额。
    """
    try:
        with db_cursor() as cursor:
            query = """
            SELECT customer_name, SUM(price) as total_consumption
            FROM orders
            GROUP BY customer_name
            ORDER BY total_consumption DESC
            LIMIT 1
            """
            cursor.execute(query)
            result = cursor.fetchone()
            if result is None:
                return "未找到任何客户消费记录。"
            return f"消费最高的用户是: {result['customer_name']}，总消费额为: {result['total_consumption']:.2f}元"
    except Exception as e:
        return str(e)


@mcp.tool(description="获取最受欢迎的产品（基于订单数量）")
def get_most_popular_product() -> str:
    """
    查询被购买次数最多的产品（即订单数量最多的产品）。
    """
    try:
        with db_cursor() as cursor:
            query = """
            SELECT product_name, COUNT(*) as order_count
            FROM orders
            GROUP BY product_name
            ORDER BY order_count DESC
            LIMIT 1
            """
            cursor.execute(query)
            result = cursor.fetchone()
            if result is None:
                return "未找到任何产品销售记录。"
            return f"最受欢迎的产品是: {result['product_name']}，总订单数量为: {result['order_count']}单"
    except Exception as e:
        return str(e)

@mcp.tool(description="获取销售员排行榜（基于总销售额）")
def get_salesperson_ranking(limit: int = 5) -> str:
    """
    查询销售额最高的销售员排行榜，可以指定返回的条目数。
    """
    if limit <= 0:
        return "排行榜条目数必须为正整数。"
    
    try:
        with db_cursor() as cursor:
            query = """
            SELECT sales_name, SUM(price) as total_sales
            FROM orders
            GROUP BY sales_name
            ORDER BY total_sales DESC
            LIMIT ? 
            """
            cursor.execute(query, (limit,))
            results = cursor.fetchall()
            if not results:
                return "未找到任何销售员记录。"
            
            ranking = "销售员业绩排行榜:\n" + "\n".join(
                [f"第{i+1}名: {row['sales_name']} - 销售额: {row['total_sales']:.2f}元" for i, row in enumerate(results)]
            )
            return ranking
    except Exception as e:
        return str(e)

# 创建一个可以通过 SSE (Server-Sent Events) 访问的 FastAPI 应用
app = mcp.sse_app()

if __name__ == "__main__":
    # 这种方式允许我们通过 `python order_service.py` 直接运行此服务进行快速测试
    # mcp.run() 会使用 uvicorn 在指定的 host 和 port 上启动服务
    mcp.run(transport="sse", host="127.0.0.1", port=9002)