"""Upload validation, filename sanitizing, CSV-injection mitigation, prompt-injection fencing."""

from __future__ import annotations

import hashlib
import io
import re
from dataclasses import dataclass

from PIL import Image, ImageOps, UnidentifiedImageError

from .errors import ApiError

ALLOWED_IMAGE_FORMATS = {"PNG": "image/png", "JPEG": "image/jpeg", "MPO": "image/jpeg", "WEBP": "image/webp"}
MAX_IMAGE_PIXELS = 40_000_000
MAX_IMAGE_SIDE = 12_000
CSV_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")
_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


def sanitize_filename(name: str, fallback: str = "upload") -> str:
    base = name.replace("\\", "/").rsplit("/", 1)[-1]
    base = _SAFE_NAME.sub("_", base).strip("._")[:120]
    return base or fallback


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class ValidatedImage:
    data: bytes
    width: int
    height: int
    media_type: str
    extension: str
    sha256: str


def validate_image(data: bytes, max_bytes: int) -> ValidatedImage:
    """Decode-verify the image; magic bytes, not the client's content-type, decide the format."""
    if len(data) == 0:
        raise ApiError(400, "VALIDATION_FAILED", "empty file")
    if len(data) > max_bytes:
        raise ApiError(413, "PAYLOAD_TOO_LARGE", f"image exceeds {max_bytes // (1024 * 1024)} MB")
    try:
        with Image.open(io.BytesIO(data)) as probe:
            fmt = probe.format or ""
            width, height = probe.size
            probe.verify()
        if fmt not in ALLOWED_IMAGE_FORMATS:
            raise ApiError(415, "UNSUPPORTED_MEDIA", f"unsupported image format {fmt or 'unknown'}; use PNG, JPEG or WebP")
        if width * height > MAX_IMAGE_PIXELS or max(width, height) > MAX_IMAGE_SIDE:
            raise ApiError(413, "PAYLOAD_TOO_LARGE", f"image is {width}x{height} pixels; max {MAX_IMAGE_SIDE} px per side "
                                                     f"and {MAX_IMAGE_PIXELS:,} pixels total")
        with Image.open(io.BytesIO(data)) as full:
            full.load()  # second pass: verify() does not decode pixel data
        data, width, height, fmt = _apply_exif_orientation(data, width, height, fmt)
    except ApiError:
        raise
    except Image.DecompressionBombError as exc:
        raise ApiError(413, "PAYLOAD_TOO_LARGE", "image pixel count exceeds the decoder safety limit") from exc
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as exc:
        raise ApiError(415, "UNSUPPORTED_MEDIA", "file is not a decodable image") from exc
    return ValidatedImage(
        data=data, width=width, height=height, media_type=ALLOWED_IMAGE_FORMATS[fmt],
        extension={"PNG": "png", "JPEG": "jpg", "MPO": "jpg", "WEBP": "webp"}[fmt], sha256=sha256_bytes(data),
    )


def _apply_exif_orientation(data: bytes, width: int, height: int, fmt: str) -> tuple[bytes, int, int, str]:
    """Bake EXIF rotation into pixels so stored geometry matches what browsers display (mask alignment)."""
    with Image.open(io.BytesIO(data)) as img:
        orientation = img.getexif().get(0x0112, 1)
        if orientation in (1, None):
            return data, width, height, fmt
        fixed = ImageOps.exif_transpose(img)
        buf = io.BytesIO()
        fixed.convert("RGB").save(buf, format="JPEG", quality=95)
        return buf.getvalue(), fixed.width, fixed.height, "JPEG"


def neutralize_csv_cell(value: str) -> tuple[str, bool]:
    """Prefix formula-leading cells so spreadsheet apps treat them as text (OWASP CSV injection)."""
    if value and value.startswith(CSV_FORMULA_PREFIXES):
        return "'" + value, True
    return value, False


def csv_safe(value: object) -> str:
    text = "" if value is None else str(value)
    return neutralize_csv_cell(text)[0]


def fence_untrusted(text: str, limit: int = 400) -> str:
    """Render external text (OCR/visible text, ledger fields) as quoted data inside prompts."""
    cleaned = text.replace("\u0000", "").replace("<<<", "‹‹‹").replace(">>>", "›››")[:limit]
    return f"<<<{cleaned}>>>"
