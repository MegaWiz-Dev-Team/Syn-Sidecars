# PaddleOCR sidecar — B-50a real engine.
#
# PaddlePaddle wheels are ~700MB. Final image lands around 1.5GB. CPU-only;
# no CUDA. Models (~150MB) download to /root/.paddleocr on first run unless
# you pre-bake them in B-50a.1.

FROM python:3.10-slim

WORKDIR /app

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        curl \
        libgl1 \
        libglib2.0-0 \
        libgomp1 \
        ca-certificates \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py ./

# Pre-create the cache dir so the warmup at startup writes there cleanly.
ENV HOME=/root
RUN mkdir -p /root/.paddleocr

EXPOSE 8091

# Long start-period covers the first-time model download (~30-90s).
HEALTHCHECK --interval=30s --timeout=5s --start-period=120s --retries=3 \
  CMD curl -fsS http://localhost:8091/healthz || exit 1

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8091"]
