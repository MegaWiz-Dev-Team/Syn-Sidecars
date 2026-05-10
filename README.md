# Syn-Sidecars

Thin FastAPI wrappers around upstream open-source OCR libraries — used by Asgard's **Syn** OCR pipeline (Tier 1a/1b classifiers).

License: Apache 2.0 (matches upstream library licenses).

## Components

### `services/paddleocr-sidecar/` — Tier 1b
FastAPI wrapper around [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) (Apache 2.0).

**Used for:** printed Thai / English / mixed Thai+English on standard medical forms. Default fast path in Syn's 4-tier hybrid OCR strategy.

### `services/chandra-sidecar/` — Tier 1a
FastAPI wrapper around [datalab-to/chandra](https://github.com/datalab-to/chandra) (Apache 2.0).

**Used for:** handwriting, complex tables, mixed scripts where PaddleOCR's box detection breaks. Chandra is the only license-clean tool from the datalab-to family.

## Why a separate public repo?

Asgard is **AGPL-3.0 + Commercial open-core**. The Syn umbrella repo holds business-orchestration logic (proprietary) — but the OCR sidecars themselves are thin wrappers around Apache 2.0 upstream tools and have no business-specific logic.

Splitting into this repo lets:
- Apache 2.0 license stay clean (no AGPL contamination)
- Community contributors PR sidecar improvements without signing CLA for proprietary glue
- Other projects reuse Syn-Sidecars independently of Asgard

## Building

Each sidecar is a self-contained Docker build:

```bash
docker build -t syn-paddleocr-sidecar services/paddleocr-sidecar/
docker build -t syn-chandra-sidecar services/chandra-sidecar/
```

## Asgard integration

These sidecars are pulled and orchestrated by Asgard's [Syn API](https://github.com/MegaWiz-Dev-Team/Syn) (private). The router decision logic for which tier to dispatch lives inside [Mimir's ro-ai-bridge](https://github.com/MegaWiz-Dev-Team/Mimir) per the Syn smart-router spec.

## Related

- [Asgard](https://github.com/MegaWiz-Dev-Team/Asgard) — umbrella platform
- [Syn](https://github.com/MegaWiz-Dev-Team/Syn) — proprietary orchestration (private)
- [Mimir](https://github.com/MegaWiz-Dev-Team/Mimir) — RAG/knowledge platform with smart-router
