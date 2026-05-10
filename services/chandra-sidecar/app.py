"""Tier 1a sidecar — handwriting + complex tables.

Registered as engine="chandra-local" in the smart router. v0.1
implementation uses EasyOCR in paragraph mode (group lines into
paragraphs; lower text-detection threshold) tuned for handwritten
clinical notes. See requirements.txt for the rationale on why this isn't
the literal datalab-to/chandra package yet.

The HTTP contract matches paddleocr-sidecar so the smart router can swap
freely between Tier 1a and 1b based on doc_type.
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
log = logging.getLogger("chandra-sidecar")

app = FastAPI(title="Syn chandra-sidecar (handwriting / EasyOCR-backed)", version="0.1.0")

ENGINE_NAME = "chandra"
ENGINE_VERSION = "easyocr-paragraph-1.7.2"
DEFAULT_LANGS = [s.strip() for s in os.getenv("OCR_LANGS", "th,en").split(",") if s.strip()]
# Lower text-detection threshold helps catch faint handwriting strokes.
LOW_TEXT_THRESHOLD = float(os.getenv("OCR_LOW_TEXT", "0.4"))
LINK_THRESHOLD = float(os.getenv("OCR_LINK_THRESHOLD", "0.4"))

_ocr_reader = None
_reader_langs: tuple[str, ...] | None = None


def _get_reader(langs: list[str]):
    global _ocr_reader, _reader_langs
    key = tuple(sorted(langs))
    if _ocr_reader is None or _reader_langs != key:
        import easyocr

        log.info("loading EasyOCR (handwriting mode, langs=%s)", langs)
        _ocr_reader = easyocr.Reader(langs, gpu=False, verbose=False)
        _reader_langs = key
        log.info("EasyOCR ready (handwriting mode, langs=%s)", langs)
    return _ocr_reader


@app.on_event("startup")
async def warmup() -> None:
    if os.getenv("OCR_EAGER_LOAD", "1") == "1":
        try:
            _get_reader(DEFAULT_LANGS)
        except Exception as e:
            log.error("warmup failed: %s", e)


@app.get("/healthz")
def healthz() -> dict:
    return {
        "status": "ok",
        "engine": ENGINE_NAME,
        "engine_version": ENGINE_VERSION,
        "model_loaded": _ocr_reader is not None,
        "default_langs": DEFAULT_LANGS,
        "loaded_langs": list(_reader_langs) if _reader_langs else None,
        "mode": "handwriting (paragraph)",
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
        # paragraph=True: groups detected lines into paragraphs (handwriting
        # often spans multiple visual lines that belong together).
        # low_text + link_threshold tuned for faint strokes.
        result = reader.readtext(
            arr,
            detail=1,
            paragraph=True,
            low_text=LOW_TEXT_THRESHOLD,
            link_threshold=LINK_THRESHOLD,
        )
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

    # In paragraph mode, EasyOCR returns: [[bbox, text], ...] (no per-paragraph
    # confidence). We synthesize a confidence by re-running detail=1 paragraph=False
    # and aggregating, but for v0.1 we just emit None and let the smart router
    # treat that as "engine declined to score" — it falls through to cloud
    # escalation rules instead.
    bboxes_out = []
    text_paragraphs: list[str] = []
    for entry in result:
        # Tolerant unpack: paragraph mode returns 2-tuple; non-paragraph 3-tuple.
        if len(entry) == 2:
            box, text = entry
            conf = None
        elif len(entry) == 3:
            box, text, conf = entry
        else:
            continue
        text_paragraphs.append(text)
        if return_bboxes:
            xs = [pt[0] for pt in box]
            ys = [pt[1] for pt in box]
            bboxes_out.append({
                "x0": float(min(xs)), "y0": float(min(ys)),
                "x1": float(max(xs)), "y1": float(max(ys)),
                "polygon": [[float(p[0]), float(p[1])] for p in box],
                "text": text,
                "confidence": float(conf) if conf is not None else None,
            })

    extracted_text = "\n\n".join(text_paragraphs)

    return JSONResponse(
        content={
            "engine": ENGINE_NAME,
            "engine_version": ENGINE_VERSION,
            "extracted_text": extracted_text,
            "bboxes": bboxes_out if return_bboxes else None,
            "confidence": None,  # paragraph mode — see note above
            "latency_ms": int((time.monotonic() - started) * 1000),
            "warnings": ["paragraph_mode: per-line confidence unavailable"],
        }
    )
