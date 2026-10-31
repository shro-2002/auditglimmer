# Integration Contracts (FROZEN v1 — 2026-10-31; v1.1 clarifications after C1)

These contracts are frozen before parallel implementation (task graph node A3).
Backend owns `backend/app/schemas.py`; the frontend mirrors these shapes in
`frontend/src/lib/types.ts`. Any change requires a coordinator edit to this file first.

Base URL: `http://localhost:8000` (frontend reads `NEXT_PUBLIC_API_BASE`, default
`http://localhost:8000`). All JSON. Every response carries an `X-Correlation-ID`
header; clients may send one. Errors use one envelope:

```json
{ "error": { "code": "VALIDATION_FAILED", "message": "human readable", "details": [], "correlation_id": "..." } }
```

Error codes: `VALIDATION_FAILED` (400/422), `NOT_FOUND` (404), `CONFLICT` (409),
`PAYLOAD_TOO_LARGE` (413), `UNSUPPORTED_MEDIA` (415), `LIVE_NOT_APPROVED` (403),
`PROVIDER_ERROR` (502), `PROVIDER_TIMEOUT` (504), `BUDGET_EXCEEDED` (429), `INTERNAL` (500).

## Mode

`mode` is `"demo"` or `"live"`, fixed per backend process by env `AUDITGLIMMER_MODE`.
Demo mode uses fixture providers ONLY for bundled fixture images; any other image gets an
explicit `NO_FIXTURE` provider error — never invented output. Live mode never falls back to
fixtures. Every provider-produced object carries `provider` and `mode` so the UI can label it.

## Core types (TypeScript notation)

```ts
type Mode = "demo" | "live";
type ISO = string; // ISO 8601 UTC

interface ConfigInfo {
  mode: Mode;
  live_approved: boolean;           // AUDITGLIMMER_LIVE_APPROVED=1 and key present
  credentials_present: boolean;     // never the value
  segmentation_model: string;       // "sam-3.1" | "fixture-sam"
  extraction_model: string;         // "muse-spark-1.3" | "fixture-muse"
  max_live_requests_per_run: number;
  max_upload_mb: number;
  version: string;
}

interface Session {
  id: string; name: string; facility_id: string; created_at: ISO;
  ledger_count: number; image_count: number; run_count: number;
  status: "draft" | "ready" | "inspected" | "reported";
}
interface SessionCreate { name: string; facility_id: string }   // 1..120 chars, facility 1..40 [A-Za-z0-9_-]

interface LedgerRecord {
  id: string;            // internal row id
  asset_id: string; asset_type: string; manufacturer: string | null; model: string | null;
  serial_number: string | null; facility_id: string; expected_location: string | null;
  ledger_value: number | null; currency: string | null; inspection_date: string | null;
  source_row: number;    // 1-based CSV data row (provenance)
}
interface LedgerIssue { row: number; field: string | null; severity: "error" | "warning"; code: string; message: string }
interface LedgerUploadResult {
  accepted: number; rejected: number; issues: LedgerIssue[];
  file_sha256: string; records: LedgerRecord[];
}

interface ImageAsset {
  id: string; filename: string; sha256: string; width: number; height: number;
  facility_id: string; uploaded_at: ISO; url: string;   // url = /api/images/{id}/file
  fixture: boolean;     // true = bundled synthetic demo image
}

interface Mask {
  bounds: [number, number, number, number]; // x1,y1,x2,y2 source px, half-open (x2,y2 exclusive)
  raster_w: number; raster_h: number;       // mask raster size; maps onto bounds
  svg_path: string;   // path in raster coords; render with
                      // transform="translate(x1 y1) scale((x2-x1)/raster_w (y2-y1)/raster_h)"
  area_px: number;    // foreground pixel count in raster (scaled to source px)
  encoding: "lossless" | "one_bit" | "fixture_polygon";
}
interface Detection {
  id: string; run_id: string; image_id: string; concept: string;
  object_index: number;                 // provider object id
  mask: Mask; confidence: number | null; // provider-reported, uncalibrated
  provider: string; model: string; mode: Mode;
}

interface VisibleIdentifier { kind: "serial" | "asset_tag" | "model" | "other"; value: string; readable: boolean }
interface Uncertainty { field: string | null; note: string }
interface EvidenceReference { detection_id: string; image_id: string; image_sha256: string; crop_box: [number, number, number, number] }
interface VisualEvidence {               // validated with Pydantic, extra fields forbidden
  observed_object_type: string;
  visible_manufacturer: string | null;
  visible_model: string | null;
  visible_serial_number: string | null;
  visible_identifiers: VisibleIdentifier[];
  visible_condition_observations: string[];
  uncertainties: Uncertainty[];
  evidence_references: EvidenceReference[];  // attached server-side, never model-authored
  model_confidence: number | null;           // model-reported, uncalibrated, 0..1
}
interface EvidenceRecord {
  id: string; detection_id: string; status: "ok" | "invalid" | "error";
  evidence: VisualEvidence | null; error: string | null;
  provider: string; model: string; mode: Mode; provider_call_id: string | null;
}

type Decision =
  | "VERIFIED"            // Tier 1, unique identifier match
  | "PROBABLE"            // Tier 2, needs review
  | "WEAK"                // Tier 3, needs review
  | "MISMATCHED"          // conflicting identifiers, needs review
  | "NOT_IN_REGISTER"     // Tier 4, observed object with no supported match
  | "EVIDENCE_UNUSABLE";  // extraction failed / invalid
interface MatchDecision {
  id: string; evidence_id: string; detection_id: string; image_id: string;
  decision: Decision; tier: 1 | 2 | 3 | 4 | null; matching_rule: string;
  evidence_ids: string[]; candidate_asset_ids: string[]; matched_asset_id: string | null; // values are LedgerRecord.asset_id
  match_score: number;            // 0..1 deterministic rule score, NOT a probability
  review_required: boolean; explanation: string; unmatched_fields: string[];
  flags: string[];                // e.g. DUPLICATE_SERIAL_IN_LEDGER, SAME_SERIAL_MULTIPLE_OBJECTS, CONFLICTING_MANUFACTURER
  review: ReviewAction | null;    // latest human action
}
type AssetStatus = "VERIFIED" | "PROBABLE" | "MISMATCHED" | "UNVERIFIED" | "NOT_OBSERVABLE";
interface AssetResult {
  asset_id: string; ledger_record_id: string; status: AssetStatus;
  decision_ids: string[]; reason: string; human_confirmed: boolean;
}
interface ReconciliationSummary {
  assets_total: number; by_status: Record<AssetStatus, number>;
  decisions_total: number; by_decision: Record<Decision, number>;
  review_required: number; reviewed: number; inspected_concepts: string[];
}
interface Reconciliation { session_id: string; computed_at: ISO; summary: ReconciliationSummary; decisions: MatchDecision[]; assets: AssetResult[] }

interface ReviewAction { id: string; decision_id: string; action: "confirm" | "reject"; asset_id: string | null; reviewer: string; note: string; created_at: ISO }
interface ReviewCreate { action: "confirm" | "reject"; asset_id?: string | null; reviewer: string; note?: string }

interface Run {
  id: string; session_id: string; concept: string; status: "queued" | "running" | "succeeded" | "partial" | "failed";
  image_ids: string[]; started_at: ISO | null; finished_at: ISO | null;
  detections: number; evidence_ok: number; evidence_failed: number; error: string | null; mode: Mode;
}
interface RunCreate { concept: string; image_ids?: string[] }   // concept 2..60 chars, short noun phrase
interface RunEvent { run_id: string; seq: number; ts: ISO; stage: "segment" | "extract" | "reconcile" | "run"; status: "started" | "progress" | "done" | "error"; message: string; image_id?: string; detection_id?: string; latency_ms?: number }

interface ProviderCall {
  id: string; run_id: string | null; provider: string; model: string; mode: Mode; operation: "segment" | "extract" | "explain";
  status: "ok" | "error" | "timeout" | "invalid_output"; latency_ms: number; started_at: ISO;
  input_tokens: number | null; output_tokens: number | null; images: number;
  estimated_cost_usd: number; error: string | null; raw_output_ref: string | null; correlation_id: string;
}
interface Trace { session_id: string; runs: Run[]; events: RunEvent[]; provider_calls: ProviderCall[]; latency: { operation: string; count: number; p50_ms: number; p95_ms: number; max_ms: number }[]; total_estimated_cost_usd: number }

interface GraphNode { id: string; type: "LedgerAsset" | "Image" | "Detection" | "Evidence" | "Decision" | "Review"; label: string; data: Record<string, unknown> }
interface GraphEdge { source: string; target: string; type: "DEPICTED_IN" | "DETECTED_IN" | "EXTRACTED_FROM" | "DECIDED_FROM" | "CANDIDATE_FOR" | "MATCHED_TO" | "REVIEWED_BY"; data: Record<string, unknown> }
interface EvidenceGraph { nodes: GraphNode[]; edges: GraphEdge[] }

interface Overview {   // computed from DB; zeros when empty — never placeholder numbers
  sessions: number; assets: number; images: number; detections: number;
  by_status: Record<AssetStatus, number>; review_pending: number; runs: number;
  recent_sessions: Session[]; mode: Mode;
}
```

## Endpoints

| Method | Path | Body / Query | Returns |
|---|---|---|---|
| GET | `/api/health` | – | `{status:"ok", mode, providers:{segmentation:{ok,detail}, extraction:{ok,detail}}}` |
| GET | `/api/config` | – | `ConfigInfo` |
| GET | `/api/overview` | – | `Overview` |
| GET | `/api/sessions` | – | `Session[]` |
| POST | `/api/sessions` | `SessionCreate` | `Session` (201) |
| GET | `/api/sessions/{sid}` | – | `Session` |
| DELETE | `/api/sessions/{sid}` | – | 204, deletes rows and stored files |
| POST | `/api/sessions/{sid}/demo` | – | `{ledger: LedgerUploadResult, images: ImageAsset[]}` (demo mode only, else 403) |
| POST | `/api/sessions/{sid}/ledger` | multipart `file` (.csv ≤ 2 MB) | `LedgerUploadResult` (replaces ledger) |
| GET | `/api/sessions/{sid}/ledger` | – | `LedgerRecord[]` |
| POST | `/api/sessions/{sid}/images` | multipart field `files`, repeated (png/jpeg/webp ≤ 15 MB each, ≤ 20 per session) | `ImageAsset[]` |
| GET | `/api/sessions/{sid}/images` | – | `ImageAsset[]` |
| GET | `/api/images/{iid}/file` | – | image bytes |
| POST | `/api/sessions/{sid}/runs` | `RunCreate` | `Run` (202) |
| GET | `/api/runs/{rid}` | – | `Run` |
| GET | `/api/runs/{rid}/events` | SSE `text/event-stream`; each `data:` is `RunEvent`; final event `event: end` | stream |
| GET | `/api/sessions/{sid}/detections` | `?image_id=` | `{detection: Detection, evidence: EvidenceRecord \| null, decision: MatchDecision \| null}[]` |
| GET | `/api/sessions/{sid}/reconciliation` | – | `Reconciliation` (recomputed deterministically) |
| GET | `/api/sessions/{sid}/review-queue` | – | `MatchDecision[]` where `review_required && !review` |
| POST | `/api/decisions/{did}/review` | `ReviewCreate` | `MatchDecision` (409 if the same evidence is already confirmed to another asset, or the asset already confirmed to other evidence of a different object) |
| GET | `/api/sessions/{sid}/report` | `?format=json\|html\|csv` | report (attachment for html/csv) |
| GET | `/api/sessions/{sid}/trace` | – | `Trace` |
| GET | `/api/sessions/{sid}/evidence-graph` | – | `EvidenceGraph` |
| POST | `/api/decisions/{did}/explain` | – | `{explanation: string, grounded_facts: string[], provider, mode}` |

## Invariants the frontend may rely on

1. Mask overlay: an `<svg viewBox="0 0 {image.width} {image.height}">` laid exactly over the
   `<img>` renders masks aligned with no further math.
2. `match_score` is a rule score; label it "rule score", never "probability".
3. `confidence` / `model_confidence` are provider-reported and uncalibrated; label as such.
4. `UNVERIFIED` means "not adequately observed", never "missing".
5. Any object with `mode:"demo"` must render a visible DEMO badge.

## v1.1 clarifications (integration C1, no shape changes)

- `candidate_asset_ids` / `matched_asset_id` / `ReviewCreate.asset_id` carry `LedgerRecord.asset_id`.
- Image upload multipart field name is `files` (repeat it per file).
- `ImageAsset.url` is server-relative; clients prefix the API base.
- Ledger validation issues are returned only by the upload/demo response (not re-fetchable in v1).
- The JSON report shape is defined by `backend/app/report.py::build_report` (keys: session, summary,
  assets, decisions[image, detection, evidence], provider_calls, latency, disclaimer, demo_notice).
