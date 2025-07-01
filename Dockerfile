# ./Dockerfile
FROM python:3.10-slim

# 安装系统依赖
RUN apt-get update && \
    apt-get install -y --no-install-recommends libmagic1 && \
    rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 安装Python依赖（利用层缓存）
COPY requirements.txt .
ARG SKIP_TORCH_INSTALL=true
RUN pip install --upgrade pip && \
    if [ "$SKIP_TORCH_INSTALL" = "true" ]; then \
      pip install $(grep -v 'torch' requirements.txt); \
    else \
      pip install -r requirements.txt; \
    fi

# 复制代码
COPY . .

# 启动命令
CMD ["streamlit", "run", "app.py"]
