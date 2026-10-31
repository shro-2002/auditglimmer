"""Pydantic v2 models mirroring docs/integration-contracts.md (frozen v1)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Mode = Literal["demo", "live"]
Decision = Literal["VERIFIED", "PROBABLE", "WEAK", "MISMATCHED", "NOT_IN_REGISTER", "EVIDENCE_UNUSABLE"]
AssetStatus = Literal["VERIFIED", "HUMAN_CONFIRMED", "PROBABLE", "MISMATCHED", "UNVERIFIED", "NOT_OBSERVABLE"]
ASSET_STATUSES: tuple[str, ...] = ("VERIFIED", "HUMAN_CONFIRMED", "PROBABLE", "MISMATCHED", "UNVERIFIED", "NOT_OBSERVABLE")
DECISIONS: tuple[str, ...] = ("VERIFIED", "PROBABLE", "WEAK", "MISMATCHED", "NOT_IN_REGISTER", "EVIDENCE_UNUSABLE")


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---------- visual evidence (model output contract) ----------

class VisibleIdentifier(Strict):
    kind: Literal["serial", "asset_tag", "model", "other"]
    value: str = Field(max_length=300)  # real plates: Muse may transcribe a whole line (study s02, 170 chars)
    readable: bool


class Uncertainty(Strict):
    field: str | None = Field(default=None, max_length=60)
    note: str = Field(max_length=300)


class EvidenceReference(Strict):
    detection_id: str
    image_id: str
    image_sha256: str
    crop_box: tuple[int, int, int, int]


class ModelEvidence(Strict):
    """Exactly what the vision model may author. Extra keys (ownership, value, ...) are rejected."""

    observed_object_type: str = Field(min_length=1, max_length=80)
    visible_manufacturer: str | None = Field(default=None, max_length=80)
    visible_model: str | None = Field(default=None, max_length=80)
    visible_serial_number: str | None = Field(default=None, max_length=80)
    visible_identifiers: list[VisibleIdentifier] = Field(default_factory=list, max_length=20)
    visible_condition_observations: list[str] = Field(default_factory=list, max_length=20)
    uncertainties: list[Uncertainty] = Field(default_factory=list, max_length=20)
    model_confidence: float | None = Field(default=None, ge=0.0, le=1.0)

    @field_validator("visible_condition_observations")
    @classmethod
    def _short_observations(cls, value: list[str]) -> list[str]:
        for item in value:
            if len(item) > 300:
                raise ValueError("condition observation longer than 300 characters")
        return value


class VisualEvidence(ModelEvidence):
    evidence_references: list[EvidenceReference] = Field(default_factory=list)


def model_evidence_json_schema() -> dict:
    """JSON Schema sent as response_format to the extraction model (non-recursive)."""
    nullable_str = {"type": ["string", "null"]}
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "observed_object_type": {"type": "string"},
            "visible_manufacturer": nullable_str,
            "visible_model": nullable_str,
            "visible_serial_number": nullable_str,
            "visible_identifiers": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "kind": {"type": "string", "enum": ["serial", "asset_tag", "model", "other"]},
                        "value": {"type": "string"},
                        "readable": {"type": "boolean"},
                    },
                    "required": ["kind", "value", "readable"],
                },
            },
            "visible_condition_observations": {"type": "array", "items": {"type": "string"}},
            "uncertainties": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {"field": nullable_str, "note": {"type": "string"}},
                    "required": ["field", "note"],
                },
            },
            "model_confidence": {"type": ["number", "null"]},
        },
        "required": [
            "observed_object_type", "visible_manufacturer", "visible_model", "visible_serial_number",
            "visible_identifiers", "visible_condition_observations", "uncertainties", "model_confidence",
        ],
    }


# ---------- API shapes ----------

class ConfigInfo(BaseModel):
    mode: Mode
    live_approved: bool
    credentials_present: bool
    segmentation_model: str
    extraction_model: str
    max_live_requests_per_run: int
    max_upload_mb: int
    version: str


class SessionCreate(Strict):
    name: str = Field(min_length=1, max_length=120)
    facility_id: str = Field(min_length=1, max_length=40, pattern=r"^[A-Za-z0-9_-]+$")


class SessionOut(BaseModel):
    id: str
    name: str
    facility_id: str
    created_at: str
    ledger_count: int
    image_count: int
    run_count: int
    status: Literal["draft", "ready", "inspected", "reported"]


class LedgerRecordOut(BaseModel):
    id: str
    asset_id: str
    asset_type: str
    manufacturer: str | None
    model: str | None
    serial_number: str | None
    facility_id: str
    expected_location: str | None
    ledger_value: float | None
    currency: str | None
    inspection_date: str | None
    source_row: int


class LedgerIssue(BaseModel):
    row: int
    field: str | None
    severity: Literal["error", "warning"]
    code: str
    message: str


class LedgerUploadResult(BaseModel):
    accepted: int
    rejected: int
    issues: list[LedgerIssue]
    file_sha256: str
    records: list[LedgerRecordOut]
    archived_reviews: int = 0


class ImageOut(BaseModel):
    id: str
    filename: str
    sha256: str
    width: int
    height: int
    facility_id: str
    uploaded_at: str
    url: str
    fixture: bool


class MaskOut(BaseModel):
    bounds: tuple[int, int, int, int]
    raster_w: int
    raster_h: int
    svg_path: str
    area_px: int
    encoding: Literal["lossless", "one_bit", "fixture_polygon", "full_frame"]


class DetectionOut(BaseModel):
    id: str
    run_id: str
    image_id: str
    concept: str
    object_index: int
    mask: MaskOut
    confidence: float | None
    provider: str
    model: str
    mode: Mode


class EvidenceRecordOut(BaseModel):
    id: str
    detection_id: str
    status: Literal["ok", "invalid", "error"]
    evidence: VisualEvidence | None
    error: str | None
    provider: str
    model: str
    mode: Mode
    provider_call_id: str | None
    # Tier 1 gate second read (experimental safeguard); raw provenance dict as recorded by the pipeline
    confirmation: dict | None = None


class ReviewCreate(Strict):
    action: Literal["confirm", "reject"]
    asset_id: str | None = Field(default=None, max_length=80)
    reviewer: str = Field(min_length=2, max_length=80)
    note: str = Field(default="", max_length=1000)

    @field_validator("reviewer")
    @classmethod
    def _named(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if len(cleaned) < 2 or not any(ch.isalpha() for ch in cleaned):
            raise ValueError("reviewer must be a real name or staff id")
        return cleaned


class ReviewOut(BaseModel):
    id: str
    decision_id: str
    action: Literal["confirm", "reject"]
    asset_id: str | None
    reviewer: str
    note: str
    created_at: str


class MatchDecisionOut(BaseModel):
    id: str
    evidence_id: str
    detection_id: str
    image_id: str
    decision: Decision
    tier: int | None
    matching_rule: str
    evidence_ids: list[str]
    candidate_asset_ids: list[str]
    matched_asset_id: str | None
    match_score: float
    review_required: bool
    explanation: str
    unmatched_fields: list[str]
    flags: list[str]
    review: ReviewOut | None
    review_history: list[ReviewOut] = []


class AssetResultOut(BaseModel):
    asset_id: str
    ledger_record_id: str
    status: AssetStatus
    decision_ids: list[str]
    reason: str
    human_confirmed: bool


class ReconciliationSummary(BaseModel):
    assets_total: int
    by_status: dict[str, int]
    decisions_total: int
    by_decision: dict[str, int]
    review_required: int
    reviewed: int
    inspected_concepts: list[str]


class ReconciliationOut(BaseModel):
    session_id: str
    computed_at: str
    summary: ReconciliationSummary
    decisions: list[MatchDecisionOut]
    assets: list[AssetResultOut]


class RunCreate(Strict):
    concept: str = Field(min_length=2, max_length=60)
    image_ids: list[str] | None = Field(default=None, max_length=20)
    extract: bool = True  # False = segment only; extract per region later (spend control in LIVE)
    # full_frame: the auditor declares the whole photo one object (close-up nameplate); SAM is not called
    region: Literal["sam", "full_frame"] = "sam"

    @field_validator("concept")
    @classmethod
    def _noun_phrase(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if any(ch in cleaned for ch in "<>|{}\\`"):
            raise ValueError("concept must be a short noun phrase without markup characters")
        if len(cleaned.split()) > 6:
            raise ValueError("concept must be a short noun phrase (max 6 words)")
        return cleaned


class RunOut(BaseModel):
    id: str
    session_id: str
    concept: str
    status: Literal["queued", "running", "succeeded", "partial", "failed"]
    image_ids: list[str]
    started_at: str | None
    finished_at: str | None
    detections: int
    evidence_ok: int
    evidence_failed: int
    error: str | None
    mode: Mode


class RunEventOut(BaseModel):
    run_id: str
    seq: int
    ts: str
    stage: Literal["segment", "extract", "reconcile", "run"]
    status: Literal["started", "progress", "done", "error"]
    message: str
    image_id: str | None = None
    detection_id: str | None = None
    latency_ms: float | None = None


class ProviderCallOut(BaseModel):
    id: str
    run_id: str | None
    provider: str
    model: str
    mode: Mode
    operation: Literal["segment", "extract", "confirm", "explain"]
    status: Literal["ok", "error", "timeout", "invalid_output"]
    latency_ms: float
    started_at: str
    input_tokens: int | None
    output_tokens: int | None
    images: int
    estimated_cost_usd: float
    error: str | None
    raw_output_ref: str | None
    correlation_id: str


class LatencyStat(BaseModel):
    operation: str
    count: int
    p50_ms: float
    p95_ms: float
    max_ms: float


class TraceOut(BaseModel):
    session_id: str
    runs: list[RunOut]
    events: list[RunEventOut]
    provider_calls: list[ProviderCallOut]
    latency: list[LatencyStat]
    total_estimated_cost_usd: float


class GraphNode(BaseModel):
    id: str
    type: Literal["LedgerAsset", "Image", "Detection", "Evidence", "Decision", "Review"]
    label: str
    data: dict


class GraphEdge(BaseModel):
    source: str
    target: str
    type: Literal["DEPICTED_IN", "DETECTED_IN", "EXTRACTED_FROM", "DECIDED_FROM", "CANDIDATE_FOR", "MATCHED_TO", "REVIEWED_BY"]
    data: dict


class EvidenceGraphOut(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]


class OverviewOut(BaseModel):
    sessions: int
    assets: int
    images: int
    detections: int
    by_status: dict[str, int]
    review_pending: int
    runs: int
    recent_sessions: list[SessionOut]
    live_evidence_sessions: list[SessionOut] = []  # sessions holding genuine LIVE provider outputs (replayable)
    mode: Mode
