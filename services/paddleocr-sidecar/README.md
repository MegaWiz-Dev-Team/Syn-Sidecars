# paddleocr-sidecar (Tier 1b)

FastAPI wrapper around [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) — Apache 2.0.

**Used for:** printed Thai / English / mixed Thai+English on standard medical forms. Default fast path.

## Endpoints

| Method | Path | Purpose | Status |
|---|---|---|---|
| GET | `/healthz` | liveness + model loaded check | 🚧 stub |
| GET | `/readyz` | warm-up done | 🚧 stub |
| POST | `/extract` | accept image bytes, return text + bboxes + confidence | 🚧 returns 501 |

Standardized HTTP contract — the smart router can swap engines freely. (Tier 1a chandra-sidecar was retired per B-50a.2; this sidecar's shape is the canonical contract.)

## Languages

PaddleOCR ships official Thai support (`PADDLEOCR_LANG=th`). Default for Syn S1 is Thai-primary with English fallback. Per-call `hint_lang` overrides.

## Risks tracked in Sprint 50 B-50h

PaddleOCR Thai accuracy on hospital forms is unverified — the B-50h test set will measure it. If recall on Thai national IDs / MRN is below 0.95, B-50b's smart router escalates to Tier 1c Typhoon-OCR, then to Gemini Flash if cloud is opted in.
