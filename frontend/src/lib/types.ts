// Mirror of docs/integration-contracts.md (FROZEN v1 — 2026-10-31). Do not diverge.

export type Mode = "demo" | "live";
export type ISO = string;

export interface ApiErrorEnvelope {
  error: {
    code: ErrorCode;
    message: string;
    details: unknown[];
    correlation_id: string;
  };
}
export type ErrorCode =
  | "VALIDATION_FAILED"
  | "NOT_FOUND"
  | "CONFLICT"
  | "PAYLOAD_TOO_LARGE"
  | "UNSUPPORTED_MEDIA"
  | "LIVE_NOT_APPROVED"
  | "PROVIDER_ERROR"
  | "PROVIDER_TIMEOUT"
  | "BUDGET_EXCEEDED"
  | "RUN_IN_PROGRESS"
  | "UNAUTHORIZED"
  | "INTERNAL";

export interface ConfigInfo {
  mode: Mode;
  live_approved: boolean;
  credentials_present: boolean;
  segmentation_model: string;
  extraction_model: string;
  max_live_requests_per_run: number;
  max_upload_mb: number;
  version: string;
}

export interface Health {
  status: "ok";
  mode: Mode;
  providers: {
    segmentation: { ok: boolean; detail: string };
    extraction: { ok: boolean; detail: string };
  };
}

export type SessionStatus = "draft" | "ready" | "inspected" | "reported";
export interface Session {
  id: string;
  name: string;
  facility_id: string;
  created_at: ISO;
  ledger_count: number;
  image_count: number;
  run_count: number;
  status: SessionStatus;
}
export interface SessionCreate {
  name: string;
  facility_id: string;
}

export interface LedgerRecord {
  id: string;
  asset_id: string;
  asset_type: string;
  manufacturer: string | null;
  model: string | null;
  serial_number: string | null;
  facility_id: string;
  expected_location: string | null;
  ledger_value: number | null;
  currency: string | null;
  inspection_date: string | null;
  source_row: number;
}
export interface LedgerIssue {
  row: number;
  field: string | null;
  severity: "error" | "warning";
  code: string;
  message: string;
}
export interface LedgerUploadResult {
  accepted: number;
  rejected: number;
  issues: LedgerIssue[];
  file_sha256: string;
  archived_reviews?: number;
  records: LedgerRecord[];
}

export interface ImageAsset {
  id: string;
  filename: string;
  sha256: string;
  width: number;
  height: number;
  facility_id: string;
  uploaded_at: ISO;
  url: string;
  fixture: boolean;
}

export interface Mask {
  bounds: [number, number, number, number];
  raster_w: number;
  raster_h: number;
  svg_path: string;
  area_px: number;
  encoding: "lossless" | "one_bit" | "fixture_polygon" | "full_frame";
}
export interface Detection {
  id: string;
  run_id: string;
  image_id: string;
  concept: string;
  object_index: number;
  mask: Mask;
  confidence: number | null;
  provider: string;
  model: string;
  mode: Mode;
}

export interface VisibleIdentifier {
  kind: "serial" | "asset_tag" | "model" | "other";
  value: string;
  readable: boolean;
}
export interface Uncertainty {
  field: string | null;
  note: string;
}
export interface EvidenceReference {
  detection_id: string;
  image_id: string;
  image_sha256: string;
  crop_box: [number, number, number, number];
}
export interface VisualEvidence {
  observed_object_type: string;
  visible_manufacturer: string | null;
  visible_model: string | null;
  visible_serial_number: string | null;
  visible_identifiers: VisibleIdentifier[];
  visible_condition_observations: string[];
  uncertainties: Uncertainty[];
  evidence_references: EvidenceReference[];
  model_confidence: number | null;
}
export interface EvidenceRecord {
  id: string;
  detection_id: string;
  status: "ok" | "invalid" | "error";
  evidence: VisualEvidence | null;
  error: string | null;
  provider: string;
  model: string;
  mode: Mode;
  provider_call_id: string | null;
}

export type Decision =
  | "VERIFIED"
  | "PROBABLE"
  | "WEAK"
  | "MISMATCHED"
  | "NOT_IN_REGISTER"
  | "EVIDENCE_UNUSABLE";
export interface MatchDecision {
  id: string;
  evidence_id: string;
  detection_id: string;
  image_id: string;
  decision: Decision;
  tier: 1 | 2 | 3 | 4 | null;
  matching_rule: string;
  evidence_ids: string[];
  candidate_asset_ids: string[];
  matched_asset_id: string | null;
  match_score: number;
  review_required: boolean;
  explanation: string;
  unmatched_fields: string[];
  flags: string[];
  /** Latest review; full chronology (oldest → newest) is in review_history. */
  review: ReviewAction | null;
  review_history: ReviewAction[];
}
export type AssetStatus =
  | "VERIFIED"
  | "HUMAN_CONFIRMED"
  | "PROBABLE"
  | "MISMATCHED"
  | "UNVERIFIED"
  | "NOT_OBSERVABLE";
export interface AssetResult {
  asset_id: string;
  ledger_record_id: string;
  status: AssetStatus;
  decision_ids: string[];
  reason: string;
  human_confirmed: boolean;
}
export interface ReconciliationSummary {
  assets_total: number;
  by_status: Record<AssetStatus, number>;
  decisions_total: number;
  by_decision: Record<Decision, number>;
  review_required: number;
  reviewed: number;
  inspected_concepts: string[];
}
export interface Reconciliation {
  session_id: string;
  computed_at: ISO;
  summary: ReconciliationSummary;
  decisions: MatchDecision[];
  assets: AssetResult[];
}

export interface ReviewAction {
  id: string;
  decision_id: string;
  action: "confirm" | "reject";
  asset_id: string | null;
  reviewer: string;
  note: string;
  created_at: ISO;
}
export interface ReviewCreate {
  action: "confirm" | "reject";
  asset_id?: string | null;
  reviewer: string;
  note?: string;
}

export type RunStatus = "queued" | "running" | "succeeded" | "partial" | "failed";
export interface Run {
  id: string;
  session_id: string;
  concept: string;
  status: RunStatus;
  image_ids: string[];
  started_at: ISO | null;
  finished_at: ISO | null;
  detections: number;
  evidence_ok: number;
  evidence_failed: number;
  error: string | null;
  mode: Mode;
}
export interface RunCreate {
  concept: string;
  image_ids?: string[];
  /** false = segment only; extract per selected region later (spend control in LIVE). */
  extract?: boolean;
  /** full_frame = the auditor declares the whole photo one object (close-up nameplate); SAM is not called. */
  region?: "sam" | "full_frame";
}
export interface RunEvent {
  run_id: string;
  seq: number;
  ts: ISO;
  stage: "segment" | "extract" | "reconcile" | "run";
  status: "started" | "progress" | "done" | "error";
  message: string;
  image_id?: string | null;
  detection_id?: string | null;
  latency_ms?: number | null;
}

export interface ProviderCall {
  id: string;
  run_id: string | null;
  provider: string;
  model: string;
  mode: Mode;
  operation: "segment" | "extract" | "explain";
  status: "ok" | "error" | "timeout" | "invalid_output";
  latency_ms: number;
  started_at: ISO;
  input_tokens: number | null;
  output_tokens: number | null;
  images: number;
  estimated_cost_usd: number;
  error: string | null;
  raw_output_ref: string | null;
  correlation_id: string;
}
export interface LatencyStat {
  operation: string;
  count: number;
  p50_ms: number;
  p95_ms: number;
  max_ms: number;
}
export interface Trace {
  session_id: string;
  runs: Run[];
  events: RunEvent[];
  provider_calls: ProviderCall[];
  latency: LatencyStat[];
  total_estimated_cost_usd: number;
}

export type GraphNodeType =
  | "LedgerAsset"
  | "Image"
  | "Detection"
  | "Evidence"
  | "Decision"
  | "Review";
export interface GraphNode {
  id: string;
  type: GraphNodeType;
  label: string;
  data: Record<string, unknown>;
}
export interface GraphEdge {
  source: string;
  target: string;
  type:
    | "DEPICTED_IN"
    | "DETECTED_IN"
    | "EXTRACTED_FROM"
    | "DECIDED_FROM"
    | "CANDIDATE_FOR"
    | "MATCHED_TO"
    | "REVIEWED_BY";
  data: Record<string, unknown>;
}
export interface EvidenceGraph {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface Overview {
  sessions: number;
  assets: number;
  images: number;
  detections: number;
  by_status: Record<AssetStatus, number>;
  review_pending: number;
  runs: number;
  recent_sessions: Session[];
  /** Sessions that hold genuine LIVE Meta outputs; shown as recorded evidence, never re-run. */
  live_evidence_sessions?: Session[];
  mode: Mode;
}

export interface DemoLoadResult {
  ledger: LedgerUploadResult;
  images: ImageAsset[];
}

export interface DetectionBundle {
  detection: Detection;
  evidence: EvidenceRecord | null;
  decision: MatchDecision | null;
}

export interface Explanation {
  explanation: string;
  grounded_facts: string[];
  provider: string;
  mode: Mode;
}

/** Subset of GET /report?format=json (report_version 2) the UI reads. */
export interface ReportSummary {
  report_version: number;
  report_state: "DRAFT" | "FINAL";
  open_reviews: number;
  conflicting_reviews: number;
  mode: Mode;
  provider_modes_used: Mode[];
  summary: ReconciliationSummary;
}
