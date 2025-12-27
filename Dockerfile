FROM nvidia/cuda:12.1.0-cudnn8-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app/src

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 python3-pip python3.10-venv git wget curl \
    libgl1-mesa-glx libglib2.0-0 libsm6 libxext6 libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip3 install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cu121 && \
    pip3 install --no-cache-dir timm numpy pillow_heif \
    flask flask-cors flasgger gunicorn \
    fastmcp pillow matplotlib

COPY src/ ./src/
COPY checkpoints/ ./checkpoints/
COPY data/ ./data/
COPY app.py mcp_server.py gpu_manager.py ./
COPY templates/ ./templates/
COPY static/ ./static/

EXPOSE 8500

ENV GPU_IDLE_TIMEOUT=60
ENV PORT=8500

CMD ["gunicorn", "-b", "0.0.0.0:8500", "-w", "1", "--threads", "4", "--timeout", "300", "app:app"]
