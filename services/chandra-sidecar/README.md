# chandra-sidecar (Tier 1a)

FastAPI wrapper around [datalab-to/chandra](https://github.com/datalab-to/chandra) — Apache 2.0, the only license-clean tool from the datalab-to family.

**Used for:** handwriting, complex tables, mixed scripts where PaddleOCR's box detection breaks.

## Endpoints

| Method | Path | Purpose | Status |
|---|---|---|---|
| GET | `/healthz` | liveness + model loaded check | 🚧 stub |
| GET | `/readyz` | model warm + GPU/MPS available | 🚧 stub |
| POST | `/extract` | accept image bytes, return text + bboxes + confidence | 🚧 returns 501 |

Day-1 (Sprint 50 B-50a): all engine work returns 501 NotImplemented. The HTTP shape is locked so [Mimir/ro-ai-bridge](https://github.com/MegaWiz-Dev-Team/Mimir) can wire its smart router against the contract while the engine integration ships separately.

## Request / response contract

```http
POST /extract HTTP/1.1
Content-Type: multipart/form-data

file=<binary image>
hint_lang=th       (optional)
return_bboxes=true (optional)
```

```json
{
  "engine": "chandra",
  "engine_version": "0.x.y",
  "extracted_text": "...",
  "bboxes": [
    {"x0":0,"y0":0,"x1":100,"y1":40,"text":"...","confidence":0.94}
  ],
  "confidence": 0.91,
  "latency_ms": 312,
  "warnings": []
}
```

## Run locally

```bash
docker compose up chandra
curl -F file=@sample.jpg http://localhost:8090/extract  # returns 501 today
```
