# ---------- 运行时镜像 ----------
FROM python:3.12-slim AS runtime

# 关闭 .pyc 生成 & 开启无缓冲日志
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# ---------- 系统依赖 ----------
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential gcc make \
        libcurl4-openssl-dev libssl-dev libffi-dev \
        libbrotli-dev zlib1g-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# ---------- 复制并安装 Python 依赖 ----------
WORKDIR /app
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

# ---------- 容器元数据 & 默认命令 ----------
EXPOSE 8000
ENV UVICORN_HOST=0.0.0.0 \
    UVICORN_PORT=8000
CMD ["uvicorn", "main:app", \
     "--host", "0.0.0.0", "--port", "8000", \
     "--workers", "1", "--loop", "uvloop", "--proxy-headers"]
