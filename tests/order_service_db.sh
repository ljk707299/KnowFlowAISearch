#!/bin/bash

# 设置脚本在遇到错误时立即退出
set -e

# 定位数据库文件路径，脚本应该在项目根目录运行
DB_FILE="chat_history.db"

# 检查数据库文件是否存在
if [ ! -f "$DB_FILE" ]; then
    echo "错误: 数据库文件 $DB_FILE 未找到。"
    echo "请先运行一次主应用(main.py)来自动创建数据库文件，然后再运行此脚本。"
    exit 1
fi

# 使用 sqlite3 命令行工具执行 SQL
# HERE Document (<<'EOF') 用于将多行文本作为命令的输入
sqlite3 "$DB_FILE" <<'EOF'
-- 彻底重建 orders 表，确保结构和插入语句一致
DROP TABLE IF EXISTS orders;
CREATE TABLE orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name TEXT NOT NULL,
    price REAL NOT NULL,
    customer_name TEXT NOT NULL,
    sales_name TEXT NOT NULL,
    create_time TEXT NOT NULL
);

-- 插入假数据
INSERT INTO orders (product_name, price, customer_name, sales_name, create_time) VALUES
('AI智能音箱', 299.00, '张三', '王小明', '2024-01-15 10:30:00'),
('高清网络摄像头', 199.50, '李四', '陈大勇', '2024-01-20 14:00:00'),
('蓝牙无线耳机', 499.00, '王五', '王小明', '2024-02-05 09:00:00'),
('智能手环Pro', 350.00, '赵六', '李丽', '2024-02-11 18:45:00'),
('AI智能音箱', 299.00, '孙七', '陈大勇', '2024-03-02 11:10:00'),
('便携式显示器', 1299.00, '张三', '李丽', '2024-03-08 20:05:00'),
('机械键盘', 599.00, '周八', '王小明', '2024-04-16 16:20:00'),
('高清网络摄像头', 199.50, '吴九', '陈大勇', '2024-04-22 13:00:00'),
('蓝牙无线耳机', 499.00, '张三', '李丽', '2024-05-01 10:00:00'),
('智能手环Pro', 350.00, '钱十', '王小明', '2024-05-15 12:30:00');
EOF

echo "✅ 数据库 'orders' 表已重建并填充了10条示例数据。"
echo "📍 数据库文件位于: $DB_FILE" 
