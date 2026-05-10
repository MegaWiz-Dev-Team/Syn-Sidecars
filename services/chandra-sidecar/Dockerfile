# Tier 1a sidecar — B-50a real engine.
#
# Same EasyOCR runtime as paddleocr-sidecar (configured for handwriting).
# Image lands ~5.3GB — same torch-CUDA bloat. B-50a.1 will trim with
# torch-cpu wheels.

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

ENV HOME=/root
RUN mkdir -p /root/.EasyOCR

EXPOSE 8090

HEALTHCHECK --interval=30s --timeout=5s --start-period=120s --retries=3 \
  CMD curl -fsS http://localhost:8090/healthz || exit 1

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8090"]
