"""Provider protocols and shared result types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from ..schemas import ModelEvidence


@dataclass(frozen=True)
class NormalizedMask:
    """bounds are half-open source pixels; the raster maps exactly onto bounds."""

    bounds: tuple[int, int, int, int]
    raster_w: int
    raster_h: int
    svg_path: str
    area_px: int
    encoding: str

    def as_dict(self) -> dict:
        return {
            "bounds": list(self.bounds), "raster_w": self.raster_w, "raster_h": self.raster_h,
            "svg_path": self.svg_path, "area_px": self.area_px, "encoding": self.encoding,
        }


@dataclass(frozen=True)
class SegmentedObject:
    object_index: int
    mask: NormalizedMask
    confidence: float | None


@dataclass
class CallMeta:
    """Usage/timing metadata for one provider request (persisted as ProviderCallRow)."""

    provider: str
    model: str
    latency_ms: float = 0.0
    input_tokens: int | None = None
    output_tokens: int | None = None
    images: int = 0
    estimated_cost_usd: float = 0.0
    raw_output: str | None = None
    request_id: str | None = None
    extra: dict = field(default_factory=dict)


@dataclass(frozen=True)
class SegmentationResult:
    objects: list[SegmentedObject]
    meta: CallMeta


@dataclass(frozen=True)
class ExtractionResult:
    evidence: ModelEvidence
    meta: CallMeta


@dataclass(frozen=True)
class ImageInput:
    data: bytes
    media_type: str
    width: int
    height: int
    sha256: str


@dataclass(frozen=True)
class CropContext:
    """Where a crop came from; fixture providers key on it, live providers ignore it."""

    image_sha256: str
    object_index: int
    crop_box: tuple[int, int, int, int]
    concept: str


class SegmentationProvider(Protocol):
    name: str
    model: str

    def segment_image(self, image: ImageInput, concept: str) -> SegmentationResult: ...

    def normalize_masks(self, raw_output: str) -> list[SegmentedObject]: ...

    def health_check(self) -> tuple[bool, str]: ...


class EvidenceExtractionProvider(Protocol):
    name: str
    model: str

    def extract_visual_evidence(self, crop: ImageInput, context: CropContext,
                                purpose: str = "evidence") -> ExtractionResult: ...
    # purpose="confirm": second, independent identifier read for the Tier 1 gate (enhanced view, own prompt)

    def explain_discrepancy(self, facts: list[str]) -> tuple[str, CallMeta]: ...

    def health_check(self) -> tuple[bool, str]: ...
