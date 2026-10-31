"""Select providers by mode. LIVE never falls back to fixtures; unapproved LIVE is blocked loudly."""

from __future__ import annotations

from ..config import Settings
from ..errors import ProviderError
from .base import CallMeta, CropContext, ExtractionResult, ImageInput, SegmentationResult, SegmentedObject
from .fixture import FixtureMuseProvider, FixtureSAMProvider, FixtureStore
from .meta_http import MetaHttp
from .muse_meta import MetaMuseProvider
from .sam_meta import MetaSAMProvider, parse_sam_output


class BlockedSAM:
    name = "meta-sam"

    def __init__(self, reason: str, model: str) -> None:
        self.reason, self.model = reason, model

    def segment_image(self, image: ImageInput, concept: str) -> SegmentationResult:
        raise ProviderError("not_approved", self.reason)

    def normalize_masks(self, raw_output: str) -> list[SegmentedObject]:
        return parse_sam_output(raw_output)

    def health_check(self) -> tuple[bool, str]:
        return False, self.reason


class BlockedMuse:
    name = "meta-muse"

    def __init__(self, reason: str, model: str) -> None:
        self.reason, self.model = reason, model

    def extract_visual_evidence(self, crop: ImageInput, context: CropContext) -> ExtractionResult:
        raise ProviderError("not_approved", self.reason)

    def explain_discrepancy(self, facts: list[str]) -> tuple[str, CallMeta]:
        raise ProviderError("not_approved", self.reason)

    def health_check(self) -> tuple[bool, str]:
        return False, self.reason


def build_providers(settings: Settings):  # noqa: ANN201 - returns (SegmentationProvider, EvidenceExtractionProvider)
    if settings.mode == "demo":
        store = FixtureStore(settings.fixtures_dir)
        return FixtureSAMProvider(store), FixtureMuseProvider(store)
    from ..config import MUSE_MODEL_ID, SAM_MODEL_ID

    if not settings.credentials_present:
        reason = "LIVE mode: MODEL_API_KEY is not set"
        return BlockedSAM(reason, SAM_MODEL_ID), BlockedMuse(reason, MUSE_MODEL_ID)
    if not settings.live_approved:
        reason = "LIVE mode: paid inference not approved (set AUDITGLIMMER_LIVE_APPROVED=1 after reviewing docs/cost-control.md)"
        return BlockedSAM(reason, SAM_MODEL_ID), BlockedMuse(reason, MUSE_MODEL_ID)
    http = MetaHttp(settings.api_key(), settings.provider_timeout_s, settings.provider_max_retries)
    return MetaSAMProvider(http), MetaMuseProvider(http)
