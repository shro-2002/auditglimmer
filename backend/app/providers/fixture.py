"""Fixture providers for DEMO mode. They answer ONLY for bundled synthetic fixture images
(keyed by SHA-256) and refuse everything else with an explicit NO_FIXTURE error.
Fixture outputs are labelled ground truth authored in scripts/make_fixtures.py, not model output.
"""

from __future__ import annotations

import json
import time
from functools import cached_property
from pathlib import Path

from ..errors import ProviderError
from ..reconcile import canonical_type
from .base import CallMeta, CropContext, ExtractionResult, ImageInput, NormalizedMask, SegmentationResult, SegmentedObject
from .muse_meta import parse_evidence_json


class FixtureStore:
    def __init__(self, fixtures_dir: Path) -> None:
        self.dir = fixtures_dir

    @cached_property
    def manifest(self) -> dict:
        path = self.dir / "manifest.json"
        if not path.exists():
            raise ProviderError("no_fixture", f"fixture manifest missing at {path}; run scripts/make_fixtures.py")
        return json.loads(path.read_text())

    def image(self, sha256: str) -> dict:
        for img in self.manifest["images"]:
            if img["sha256"] == sha256:
                return img
        raise ProviderError("no_fixture", "demo mode has fixture data only for bundled demo images; "
                                          "this image needs LIVE mode")

    def concepts(self) -> list[str]:
        return sorted({o["concept"] for img in self.manifest["images"] for o in img["objects"]})


def _objects_from_json(raw: str) -> list[SegmentedObject]:
    return [
        SegmentedObject(o["object_index"], NormalizedMask(
            bounds=tuple(o["bounds"]), raster_w=o["raster_w"], raster_h=o["raster_h"], svg_path=o["svg_path"],
            area_px=o["area_px"], encoding="fixture_polygon"), o.get("confidence"))
        for o in json.loads(raw)
    ]


class FixtureSAMProvider:
    name = "fixture-sam"
    model = "fixture-sam"

    def __init__(self, store: FixtureStore) -> None:
        self._store = store

    def segment_image(self, image: ImageInput, concept: str) -> SegmentationResult:
        started = time.perf_counter()
        img = self._store.image(image.sha256)
        canon = canonical_type(concept)
        known = self._store.concepts()
        if canon not in known:
            raise ProviderError("no_fixture", f"fixture labels exist only for concepts {known}; "
                                              f"'{concept}' needs LIVE mode")
        selected = [o for o in img["objects"] if o["concept"] == canon]
        raw = json.dumps([{k: o[k] for k in ("object_index", "bounds", "raster_w", "raster_h", "svg_path",
                                              "area_px", "confidence")} for o in selected])
        meta = CallMeta(provider=self.name, model=self.model, latency_ms=(time.perf_counter() - started) * 1000,
                        images=1, raw_output=raw, extra={"fixture": True})
        return SegmentationResult(objects=_objects_from_json(raw), meta=meta)

    def normalize_masks(self, raw_output: str) -> list[SegmentedObject]:
        return _objects_from_json(raw_output)

    def health_check(self) -> tuple[bool, str]:
        try:
            return True, f"fixture manifest loaded ({len(self._store.manifest['images'])} images)"
        except ProviderError as exc:
            return False, exc.message


class FixtureMuseProvider:
    name = "fixture-muse"
    model = "fixture-muse"

    def __init__(self, store: FixtureStore) -> None:
        self._store = store

    def extract_visual_evidence(self, crop: ImageInput, context: CropContext) -> ExtractionResult:
        started = time.perf_counter()
        img = self._store.image(context.image_sha256)
        obj = next((o for o in img["objects"] if o["object_index"] == context.object_index), None)
        if obj is None:
            raise ProviderError("no_fixture", "no fixture evidence for this detection")
        muse = obj["muse"]
        if muse["kind"] == "timeout":
            raise ProviderError("timeout", "fixture-simulated provider timeout (failure-mode test case)")
        raw = muse["raw"] if "raw" in muse else json.dumps(muse["evidence"])
        meta = CallMeta(provider=self.name, model=self.model, latency_ms=(time.perf_counter() - started) * 1000,
                        images=1, raw_output=raw, extra={"fixture": True, "case": obj.get("case")})
        return ExtractionResult(evidence=parse_evidence_json(raw), meta=meta)

    def explain_discrepancy(self, facts: list[str]) -> tuple[str, CallMeta]:
        text = "Deterministic summary (fixture provider, no model call): " + " ".join(facts[:6])
        return text, CallMeta(provider=self.name, model=self.model)

    def health_check(self) -> tuple[bool, str]:
        try:
            return True, f"fixture manifest loaded ({len(self._store.manifest['images'])} images)"
        except ProviderError as exc:
            return False, exc.message
