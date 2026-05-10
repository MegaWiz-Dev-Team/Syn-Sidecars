"""Tier 1b sidecar — printed Thai/English fast path.

Registered as engine="paddleocr-local" in the smart router for audit-row
stability, but the implementation uses EasyOCR (see requirements.txt for
the rationale). The HTTP contract matches the chandra-sidecar so the
smart router can swap freely.
"""

from __future__ import annotations

import io
import logging
import os
import time

import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from PIL import Image

logging.basicConfig(level=os.getenv("LOG_LEVEL", "info").upper())
log = logging.getLogger("paddleocr-sidecar")

app = FastAPI(title="Syn paddleocr-sidecar (EasyOCR-backed)", version="0.1.0")

ENGINE_NAME = "paddleocr"  # contract identifier — see requirements.txt note
ENGINE_VERSION = "easyocr-1.7.2"
DEFAULT_LANGS = [s.strip() for s in os.getenv("OCR_LANGS", "th,en").split(",") if s.strip()]

_ocr_reader = None
_reader_langs: tuple[str, ...] | None = None


def _get_reader(langs: list[str]):
    """Return an EasyOCR reader for the requested language set, lazy-loading
    on first call. Re-creates only when the language tuple changes."""
    global _ocr_reader, _reader_langs
    key = tuple(sorted(langs))
    if _ocr_reader is None or _reader_langs != key:
        import easyocr  # heavy import deferred

        log.info("loading EasyOCR model (langs=%s) — first call may take 60-120s", langs)
        # gpu=False on CPU-only nodes; download_enabled=True to fetch
        # the recognition model on first run if not present.
        _ocr_reader = easyocr.Reader(langs, gpu=False, verbose=False)
        _reader_langs = key
        log.info("EasyOCR model ready (langs=%s)", langs)
    return _ocr_reader


@app.on_event("startup")
async def warmup() -> None:
    if os.getenv("OCR_EAGER_LOAD", "1") == "1":
        try:
            _get_reader(DEFAULT_LANGS)
        except Exception as e:
            log.error("warmup failed (engine will load on first /extract): %s", e)


@app.get("/healthz")
def healthz() -> dict:
    return {
        "status": "ok",
        "engine": ENGINE_NAME,
        "engine_version": ENGINE_VERSION,
        "model_loaded": _ocr_reader is not None,
        "default_langs": DEFAULT_LANGS,
        "loaded_langs": list(_reader_langs) if _reader_langs else None,
    }


@app.get("/readyz")
def readyz() -> JSONResponse:
    if _ocr_reader is None:
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "reason": "model not loaded yet"},
        )
    return JSONResponse(content={"status": "ready", "langs": list(_reader_langs or [])})


@app.post("/extract")
async def extract(
    file: UploadFile = File(...),
    hint_lang: str | None = Form(default=None),
    return_bboxes: bool = Form(default=True),
) -> JSONResponse:
    started = time.monotonic()
    payload = await file.read()
    if not payload:
        raise HTTPException(status_code=400, detail="empty file")

    # Resolve langs: hint_lang can be a comma-separated string ("th,en") or
    # a single code; otherwise the default set wins.
    if hint_lang:
        langs = [s.strip() for s in hint_lang.split(",") if s.strip()]
    else:
        langs = DEFAULT_LANGS

    log.info(
        "extract: filename=%s bytes=%d langs=%s return_bboxes=%s",
        file.filename, len(payload), langs, return_bboxes,
    )

    try:
        img = Image.open(io.BytesIO(payload)).convert("RGB")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"cannot decode image: {e}")
    arr = np.array(img)

    try:
        reader = _get_reader(langs)
        # EasyOCR returns: [[bbox(4 corners), text, confidence], ...]
        # detail=1 ensures bboxes; paragraph=False keeps line-level granularity.
        result = reader.readtext(arr, detail=1, paragraph=False)
    except Exception as e:
        log.exception("EasyOCR failed")
        return JSONResponse(
            status_code=500,
            content={
                "engine": ENGINE_NAME,
                "engine_version": ENGINE_VERSION,
                "error": "engine_error",
                "message": str(e),
                "latency_ms": int((time.monotonic() - started) * 1000),
            },
        )

    bboxes_out = []
    text_lines: list[str] = []
    confidences: list[float] = []
    for box, text, conf in result:
        text_lines.append(text)
        confidences.append(float(conf))
        if return_bboxes:
            xs = [pt[0] for pt in box]
            ys = [pt[1] for pt in box]
            bboxes_out.append({
                "x0": float(min(xs)), "y0": float(min(ys)),
                "x1": float(max(xs)), "y1": float(max(ys)),
                "polygon": [[float(p[0]), float(p[1])] for p in box],
                "text": text,
                "confidence": float(conf),
            })

    extracted_text = "\n".join(text_lines)
    avg_conf = float(np.mean(confidences)) if confidences else None

    return JSONResponse(
        content={
            "engine": ENGINE_NAME,
            "engine_version": ENGINE_VERSION,
            "extracted_text": extracted_text,
            "bboxes": bboxes_out if return_bboxes else None,
            "confidence": avg_conf,
            "latency_ms": int((time.monotonic() - started) * 1000),
            "warnings": [],
        }
    )
