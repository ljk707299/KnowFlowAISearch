# 使用官方 Python 3.10-slim 作为基础镜像，这是一个轻量级的版本
FROM python:3.10-slim

# 设置容器内的工作目录
WORKDIR /app

# 更新 pip 到最新版本，以确保兼容性和安全性
RUN pip install --upgrade pip

# 复制依赖文件到工作目录
COPY requirements.txt .
# 安装 Python 依赖，--no-cache-dir 选项可以减少镜像体积
RUN pip install --no-cache-dir -r requirements.txt 

# 安装 Supervisor 用于进程管理
RUN apt-get update && apt-get install -y supervisor
# 创建 Supervisor 配置目录
RUN mkdir -p /etc/supervisor
# 复制 Supervisor 配置文件到容器内
COPY supervisord.conf /etc/supervisor/supervisord.conf

# 复制当前目录下的所有文件（应用代码）到容器的工作目录
COPY . .

# 声明容器需要暴露的端口
# FastAPI 主应用端口
EXPOSE 8000
# 天气服务 MCP 端口
EXPOSE 9001
# 订单服务 MCP 端口
EXPOSE 9002

# 设置容器启动时执行的命令
# 使用 supervisord 来启动和管理所有服务（FastAPI, Weather MCP, Order MCP）
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/supervisord.conf"]