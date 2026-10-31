"""SAM 3.1 on Meta Model API (Responses API, special-token geometry output).

Wire format and parser: https://dev.meta.ai/docs/sam/reading-segmentation and the official
`meta-sam-parser` package. SAM returns geometry only: it is not OCR and does not establish
asset identity.
"""

from __future__ import annotations

import base64
import io
import time

from meta_sam_parser import (
    CompletedOutcome,
    SegmentationBoxRecord,
    SegmentationMaskRecord,
    decode_mask_to_raster,
    decode_mask_to_svg_path,
    image_segmentation_format,
)
from PIL import Image

from ..config import SAM_MODEL_ID, SAM_USD_PER_IMAGE
from ..errors import ProviderError
from .base import CallMeta, ImageInput, NormalizedMask, SegmentationResult, SegmentedObject
from .meta_http import MetaHttp

MAX_SEND_SIDE = 2048


def _prepare(image: ImageInput) -> tuple[str, float]:
    """Return (data URL, scale back to source px). Downscale very large images before sending."""
    longest = max(image.width, image.height)
    if longest <= MAX_SEND_SIDE:
        return f"data:{image.media_type};base64,{base64.b64encode(image.data).decode()}", 1.0
    factor = MAX_SEND_SIDE / longest
    with Image.open(io.BytesIO(image.data)) as img:
        small = img.convert("RGB").resize((round(image.width * factor), round(image.height * factor)))
        buf = io.BytesIO()
        small.save(buf, format="JPEG", quality=90)
    return f"data:image/jpeg;base64,{base64.b64encode(buf.getvalue()).decode()}", 1.0 / factor


def parse_sam_output(raw_output: str, scale: float = 1.0, width: int | None = None,
                     height: int | None = None) -> list[SegmentedObject]:
    """Parse SAM 3.1 output_text with the official parser into normalized masks.

    Bounds are clamped to the source image; records whose clamped box is empty are dropped.
    """
    parser = image_segmentation_format().create_parser()
    if raw_output:
        parser.push(raw_output)
    finished = parser.finish(CompletedOutcome())
    result = finished.result
    errors = [d for d in getattr(result, "diagnostics", ()) if d.severity == "error"]
    if errors:
        raise ProviderError("invalid_output", f"segmentation output malformed: {errors[0].message}", raw=raw_output[:4000])
    confidences: dict[str, float | None] = {}
    objects: list[SegmentedObject] = []
    for record in result.records:
        if isinstance(record, SegmentationBoxRecord):
            confidences[record.object_id] = record.confidence
        elif isinstance(record, SegmentationMaskRecord):
            raster = decode_mask_to_raster(record.mask)
            b = record.bounds
            bounds = tuple(int(round(v * scale)) for v in (b.left, b.top, b.right, b.bottom))
            if width and height:
                bounds = (max(0, min(bounds[0], width)), max(0, min(bounds[1], height)),
                          max(0, min(bounds[2], width)), max(0, min(bounds[3], height)))
            if bounds[2] <= bounds[0] or bounds[3] <= bounds[1]:
                continue
            box_area = max(1, (bounds[2] - bounds[0]) * (bounds[3] - bounds[1]))
            raster_area = max(1, record.mask.width * record.mask.height)
            mask = NormalizedMask(
                bounds=bounds, raster_w=record.mask.width, raster_h=record.mask.height,
                svg_path=decode_mask_to_svg_path(record.mask),
                area_px=round(sum(raster) * box_area / raster_area), encoding=record.mask.encoding,
            )
            index = int(record.object_id) if record.object_id.isdigit() else 100_000 + len(objects)
            objects.append(SegmentedObject(index, mask, confidences.get(record.object_id, record.confidence)))
    return objects


class MetaSAMProvider:
    name = "meta-sam"
    model = SAM_MODEL_ID

    def __init__(self, http: MetaHttp) -> None:
        self._http = http

    def segment_image(self, image: ImageInput, concept: str) -> SegmentationResult:
        data_url, scale = _prepare(image)
        body = {
            "model": SAM_MODEL_ID,
            "input": [{
                "type": "message", "role": "user",
                "content": [{"type": "input_text", "text": concept}, {"type": "input_image", "image_url": data_url}],
            }],
            "stream": True,
            "metadata": {"include_confidence": "true", "mask_encoding": "one_bit"},
        }
        started = time.perf_counter()
        chunks: list[str] = []
        finalized: list[str] = []  # text from content_part.done / output_text.done / completed output
        event_types: dict[str, int] = {}
        usage: dict = {}
        request_id = None
        with self._http.stream_sse("/responses", body) as events:
            for event in events:
                etype = event.get("type", "")
                event_types[etype] = event_types.get(etype, 0) + 1
                if etype == "response.output_text.delta":
                    chunks.append(event.get("delta") or "")
                elif etype == "response.output_text.done":
                    finalized.append(event.get("text") or "")
                elif etype == "response.content_part.done":
                    part = event.get("part") or {}
                    if part.get("type") == "output_text":
                        finalized.append(part.get("text") or "")
                elif etype == "response.completed":
                    resp = event.get("response") or {}
                    usage, request_id = resp.get("usage") or {}, resp.get("id")
                    if not chunks and not finalized:
                        finalized.extend(c.get("text") or "" for item in resp.get("output") or []
                                         for c in item.get("content") or [] if c.get("type") == "output_text")
                elif etype in {"error", "response.failed", "response.incomplete"}:
                    detail = event.get("error") or (event.get("response") or {}).get("error") or etype
                    raise ProviderError("error", f"segmentation stream ended with {etype}: {str(detail)[:300]}")
        raw = "".join(chunks) or next((t for t in finalized if t), "")
        meta = CallMeta(
            provider=self.name, model=self.model, latency_ms=(time.perf_counter() - started) * 1000,
            images=1, estimated_cost_usd=SAM_USD_PER_IMAGE, raw_output=raw, request_id=request_id,
            extra={"usage": usage, "sent_scale": scale, "event_types": event_types, "raw_chars": len(raw)},
        )
        return SegmentationResult(objects=parse_sam_output(raw, scale, image.width, image.height), meta=meta)

    def normalize_masks(self, raw_output: str) -> list[SegmentedObject]:
        return parse_sam_output(raw_output)

    def health_check(self) -> tuple[bool, str]:
        return True, f"configured for {self.model}; not probed (probing would incur cost)"
