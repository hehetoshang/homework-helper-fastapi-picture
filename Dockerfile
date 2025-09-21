# FastAPI 向量搜索微服务 Dockerfile

# ====== 第一阶段：构建环境 ======
FROM python:3.9-slim-buster AS builder

# 设置工作目录
WORKDIR /app

# 设置Python环境变量
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# 安装Python依赖
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ====== 第二阶段：运行环境 ======
FROM python:3.9-slim-buster

# 设置工作目录
WORKDIR /app

# 创建非root用户
RUN useradd -m -u 1000 appuser
USER appuser

# 从构建阶段复制依赖
COPY --from=builder --chown=appuser:appuser /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages
COPY --from=builder --chown=appuser:appuser /usr/local/bin /usr/local/bin

# 复制项目代码
COPY --chown=appuser:appuser . .

# 设置环境变量
ENV PYTHONPATH=/app
ENV MILVUS_HOST=milvus-standalone
ENV MILVUS_PORT=19530
ENV APP_HOST=0.0.0.0
ENV APP_PORT=8000
ENV DEBUG=False

# 暴露端口
EXPOSE 8000

# 配置健康检查
HEALTHCHECK --interval=30s --timeout=3s \
    CMD curl -f http://localhost:8000/health || exit 1

# 设置资源限制（通过Docker运行时参数配置）

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "${APP_HOST}", "--port", "${APP_PORT}", "--workers", "${WORKERS:-4}"]