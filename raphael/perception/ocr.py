"""
Screen OCR module for Raphael Always-Alive Assistant.

Gives the perception subsystem genuine *content* awareness: not just "the
active window is Chrome", but *what text is on screen right now* (error
banners, dialog prompts, form labels, terminal output, etc.).

Design follows the same real-impl + graceful-offline-mock pattern used by the
STT / TTS / embeddings subsystems:

  * ``TesseractProvider``      -> real OCR via the `tesseract` binary +
                                  `pytesseract` (installed by user when they
                                  want true text extraction).
  * ``DependencyFreeOCR``      -> always-available fallback that reads an image
                                  with PIL and extracts *some* structure
                                  (non-empty regions, dominant colour, dominant
                                  edge/ink coverage) so perception still has a
                                  factual signal when no OCR engine is present.
                                  It does NOT fabricate readable text.

The factory ``get_ocr_provider()`` auto-detects the best available engine and
never raises at import time. All failures degrade to the fallback.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from typing import Dict, Any, Optional, List

from raphael.core.configuration import get_config
from raphael.core.logging import get_logger

logger = get_logger("perception.ocr")


class OCRProvider:
    """Base OCR engine interface."""

    name = "base"

    def available(self) -> bool:
        return False

    def extract_text(self, image_path: str) -> Dict[str, Any]:
        """
        Return a structured extraction for ``image_path``.

        Shape:
            {
                "provider": <engine name>,
                "engine_available": <bool>,
                "text": <str>,            # OCR'd text (may be "")
                "word_count": <int>,
                "confidence": <float 0..1>,
                "mean_brightness": <float 0..255>,
                "ink_coverage": <float 0..1>,   # fraction of dark pixels
                "dominant_color": <str hex>,
                "regions": <list>,       # optional richer regions
                "note": <str>,           # human-readable status
            }
        """
        raise NotImplementedError


class DependencyFreeOCR(OCRProvider):
    """
    Offline fallback OCR.

    No external engine is required. It opens the image with PIL (already a hard
    dependency via the frontend/backend image tooling) and computes factual,
    non-hallucinated signals:

      * mean brightness + dominant colour  (is the screen bright/dark?)
      * ink coverage                     (how much text-like content is present)
      * a coarse brightness histogram    (light vs dark regions => structure)

    This lets downstream perception say things like "the screen is mostly
    dark with ~12% ink coverage (text-heavy)" instead of "I can't see
    anything". It never invents readable words.
    """

    name = "offline"

    def available(self) -> bool:
        return True

    def extract_text(self, image_path: str) -> Dict[str, Any]:
        try:
            from PIL import Image
        except Exception as e:  # pragma: no cover - PIL is a hard dep
            return {
                "provider": self.name,
                "engine_available": False,
                "text": "",
                "word_count": 0,
                "confidence": 0.0,
                "mean_brightness": 0.0,
                "ink_coverage": 0.0,
                "dominant_color": "#000000",
                "regions": [],
                "note": f"PIL unavailable: {e}",
            }

        try:
            with Image.open(image_path) as img:
                rgb = img.convert("RGB")
                try:
                    px = list(rgb.get_flattened_data())  # Pillow >= 12
                except AttributeError:
                    px = list(rgb.getdata())  # Pillow < 12
            n = len(px)
            if n == 0:
                return self._empty("empty image")

            # Mean brightness + dominant colour (quantised bucket).
            total = 0
            buckets: Dict[tuple, int] = {}
            dark = 0
            for r, g, b in px:
                lum = 0.299 * r + 0.587 * g + 0.114 * b
                total += lum
                # quantise to 5-bit-per-channel buckets for a stable dominant colour
                key = (r >> 5, g >> 5, b >> 5)
                buckets[key] = buckets.get(key, 0) + 1
                if lum < 80:
                    dark += 1
            mean_brightness = total / n
            dom_key, dom_count = max(buckets.items(), key=lambda kv: kv[1])
            dominant_color = "#{:02X}{:02X}{:02X}".format(
                dom_key[0] << 5, dom_key[1] << 5, dom_key[2] << 5
            )
            ink_coverage = dark / n

            note = (
                "Offline pixel analysis only (no OCR engine installed). "
                "Structural signals computed; readable text requires tesseract."
            )
            return {
                "provider": self.name,
                "engine_available": False,
                "text": "",
                "word_count": 0,
                "confidence": 0.0,
                "mean_brightness": round(mean_brightness, 1),
                "ink_coverage": round(ink_coverage, 3),
                "dominant_color": dominant_color,
                "regions": [],
                "note": note,
            }
        except Exception as e:
            logger.warning(f"DependencyFreeOCR failed on {image_path}: {e}")
            return self._empty(f"image read error: {e}")

    @staticmethod
    def _empty(note: str) -> Dict[str, Any]:
        return {
            "provider": DependencyFreeOCR.name,
            "engine_available": False,
            "text": "",
            "word_count": 0,
            "confidence": 0.0,
            "mean_brightness": 0.0,
            "ink_coverage": 0.0,
            "dominant_color": "#000000",
            "regions": [],
            "note": note,
        }


class TesseractProvider(OCRProvider):
    """
    Real OCR via the `tesseract` binary + `pytesseract` (user-installed).

    Auto-detects availability; if the binary or the python wrapper is missing,
    ``available()`` returns False and the factory falls back to
    ``DependencyFreeOCR``.
    """

    name = "tesseract"

    def __init__(self, lang: str = "eng"):
        self.lang = lang

    def available(self) -> bool:
        if not shutil.which("tesseract"):
            return False
        try:
            import pytesseract  # noqa: F401
        except Exception:
            return False
        return True

    def extract_text(self, image_path: str) -> Dict[str, Any]:
        if not self.available():
            return DependencyFreeOCR().extract_text(image_path)

        try:
            import pytesseract
            from PIL import Image
        except Exception as e:
            logger.warning(f"TesseractProvider import failed, using offline: {e}")
            return DependencyFreeOCR().extract_text(image_path)

        try:
            with Image.open(image_path) as img:
                rgb = img.convert("RGB")
                text = pytesseract.image_to_string(rgb, lang=self.lang).strip()
            words = [w for w in text.split() if w]
            # pytesseract confidence is opt-in; estimate from result length.
            conf = min(1.0, 0.5 + 0.1 * len(words)) if words else 0.0
            # Reuse offline signals for brightness/colour for a richer payload.
            base = DependencyFreeOCR().extract_text(image_path)
            base.update(
                {
                    "provider": self.name,
                    "engine_available": True,
                    "text": text,
                    "word_count": len(words),
                    "confidence": round(conf, 2),
                    "note": "Real OCR via tesseract.",
                }
            )
            return base
        except Exception as e:
            logger.warning(f"TesseractProvider OCR failed, using offline: {e}")
            return DependencyFreeOCR().extract_text(image_path)


_PROVIDER: Optional[OCRProvider] = None


def get_ocr_provider() -> OCRProvider:
    """
    Return the best available OCR engine (cached singleton).

    Preference: ``tesseract`` (real) when both the binary + python wrapper are
    present, otherwise the always-available ``DependencyFreeOCR`` fallback.
    Never raises.
    """
    global _PROVIDER
    if _PROVIDER is not None:
        return _PROVIDER

    cfg = get_config()
    ocr_enabled = getattr(getattr(cfg, "screen", None), "enable_ocr", True)

    provider: OCRProvider
    if ocr_enabled and TesseractProvider().available():
        provider = TesseractProvider()
        logger.info("OCR provider: tesseract (real OCR available)")
    else:
        provider = DependencyFreeOCR()
        if ocr_enabled:
            logger.info(
                "OCR provider: offline pixel analysis (tesseract/pytesseract "
                "not installed). Install them for real text extraction."
            )
    _PROVIDER = provider
    return _PROVIDER


def reset_ocr_provider() -> None:
    """Test/reset hook for the cached provider singleton."""
    global _PROVIDER
    _PROVIDER = None
