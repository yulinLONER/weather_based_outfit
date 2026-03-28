# 使用轻量级 Python 镜像
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量，防止 Python 生成 .pyc 文件
ENV PYTHONDONTWRITEBYTECODE 1
# 确保输出实时打印到控制台
ENV PYTHONUNBUFFERED 1

# 安装系统依赖 (如有需要可添加)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖清单并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目所有文件到容器中
COPY . .

# 暴露 Flask 运行端口 (与 app_web.py 一致)
EXPOSE 5001

# 设置容器启动命令 (使用 app_web.py)
CMD ["python", "web/app_web.py"]
