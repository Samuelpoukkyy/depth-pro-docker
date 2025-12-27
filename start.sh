#!/bin/bash
set -e

echo "🚀 Depth Pro 启动脚本"
echo "========================"

# 检查 nvidia-docker
if ! command -v nvidia-smi &> /dev/null; then
    echo "❌ nvidia-smi 未找到"
    exit 1
fi
echo "✅ NVIDIA 驱动正常"

# 自动选择显存最少的 GPU
GPU_ID=$(nvidia-smi --query-gpu=index,memory.used --format=csv,noheader,nounits | \
         sort -t',' -k2 -n | head -1 | cut -d',' -f1 | tr -d ' ')
export NVIDIA_VISIBLE_DEVICES=$GPU_ID
echo "✅ 选择 GPU: $GPU_ID"

# 显示 GPU 信息
nvidia-smi --query-gpu=index,name,memory.used,memory.total --format=csv -i $GPU_ID

# 检查端口
PORT=${PORT:-8500}
if ss -tlnp | grep -q ":$PORT "; then
    echo "❌ 端口 $PORT 已被占用"
    exit 1
fi
export PORT=$PORT

# 创建临时目录
mkdir -p /tmp/depth-pro

# 复制 .env
[ ! -f .env ] && cp .env.example .env 2>/dev/null || true
echo "NVIDIA_VISIBLE_DEVICES=$GPU_ID" > .env
echo "PORT=$PORT" >> .env
echo "GPU_IDLE_TIMEOUT=${GPU_IDLE_TIMEOUT:-60}" >> .env

# 启动服务
echo ""
echo "🔧 启动 Docker 服务..."
docker compose up -d --build

echo ""
echo "========================"
echo "✅ 服务已启动!"
echo "📍 UI:      http://0.0.0.0:$PORT"
echo "📍 API:     http://0.0.0.0:$PORT/api/predict"
echo "📍 Swagger: http://0.0.0.0:$PORT/docs"
echo "📍 GPU:     $GPU_ID"
echo "========================"
