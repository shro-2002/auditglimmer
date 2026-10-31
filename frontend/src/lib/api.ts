import type {
  ApiErrorEnvelope,
  ConfigInfo,
  DemoLoadResult,
  DetectionBundle,
  EvidenceGraph,
  ImageAsset,
  LedgerRecord,
  LedgerUploadResult,
  MatchDecision,
  Overview,
  Reconciliation,
  ReportSummary,
  ReviewCreate,
  Run,
  RunCreate,
  Session,
  SessionCreate,
  Trace,
} from "./types";

export const API_BASE = (
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000"
).replace(/\/+$/, "");

/** Absolute URL for an API path (also used for <img src>, EventSource and downloads). */
export function apiUrl(path: string): string {
  return `${API_BASE}${path}`;
}

const ACCESS_CODE_KEY = "auditglimmer.access-code";
/** Fired on any 401 UNAUTHORIZED so the access-code prompt can open. */
export const UNAUTHORIZED_EVENT = "auditglimmer:unauthorized";

/** Hosted-demo access code (sessionStorage). Storage can throw in private mode; treat that as "no code". */
export function getAccessCode(): string {
  try {
    return typeof window === "undefined" ? "" : (window.sessionStorage.getItem(ACCESS_CODE_KEY) ?? "");
  } catch {
    return "";
  }
}

export function setAccessCode(code: string): void {
  try {
    if (code) window.sessionStorage.setItem(ACCESS_CODE_KEY, code);
    else window.sessionStorage.removeItem(ACCESS_CODE_KEY);
  } catch {
    // Storage unavailable: the code cannot persist, and the next 401 re-opens the prompt.
  }
}

function authHeaders(): Record<string, string> {
  const code = getAccessCode();
  return code ? { "X-Access-Code": code } : {};
}

/**
 * Replacing a register that has human reviews needs explicit consent: the server answers 409
 * LEDGER_HAS_REVIEWS, we ask, and only then re-send with replace=true (reviews are archived server-side).
 */
export async function withReplaceConsent<T>(send: (replace: boolean) => Promise<T>): Promise<T> {
  try {
    return await send(false);
  } catch (err) {
    if (err instanceof ApiError && err.code === "LEDGER_HAS_REVIEWS" &&
        window.confirm(`${err.message}\n\nArchive the existing reviews and replace the register?`)) {
      return send(true);
    }
    throw err;
  }
}

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly correlationId: string | null;
  readonly details: unknown[];

  constructor(opts: {
    status: number;
    code: string;
    message: string;
    correlationId?: string | null;
    details?: unknown[];
    cause?: unknown;
  }) {
    super(opts.message, { cause: opts.cause });
    this.name = "ApiError";
    this.status = opts.status;
    this.code = opts.code;
    this.correlationId = opts.correlationId ?? null;
    this.details = opts.details ?? [];
  }
}

function isEnvelope(body: unknown): body is ApiErrorEnvelope {
  return (
    typeof body === "object" &&
    body !== null &&
    "error" in body &&
    typeof (body as ApiErrorEnvelope).error?.message === "string"
  );
}

async function toApiError(res: Response): Promise<ApiError> {
  const headerId = res.headers.get("X-Correlation-ID");
  const body: unknown = await res.json().catch(() => null);
  if (isEnvelope(body)) {
    return new ApiError({
      status: res.status,
      code: body.error.code,
      message: body.error.message,
      correlationId: body.error.correlation_id ?? headerId,
      details: body.error.details,
    });
  }
  return new ApiError({
    status: res.status,
    code: "HTTP_" + res.status,
    message: `Request failed with HTTP ${res.status}`,
    correlationId: headerId,
  });
}

/** Every API call goes through here: adds the access code and turns failures into ApiError. */
async function send(path: string, init?: RequestInit, accept = "application/json"): Promise<Response> {
  let res: Response;
  try {
    res = await fetch(apiUrl(path), {
      ...init,
      headers: { Accept: accept, ...authHeaders(), ...init?.headers },
    });
  } catch (err) {
    throw new ApiError({
      status: 0,
      code: "NETWORK",
      message: `Cannot reach the AuditGlimmer API at ${API_BASE}.`,
      cause: err,
    });
  }
  if (res.ok) return res;
  const error = await toApiError(res);
  if (error.status === 401 && typeof window !== "undefined") window.dispatchEvent(new Event(UNAUTHORIZED_EVENT));
  throw error;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await send(path, init);
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

const FILENAME_PATTERN = /filename="?([^";]+)"?/;

/** Fetch with the access-code header, then save via an object URL (a plain <a download> cannot send headers). */
async function downloadFile(path: string, fallbackName: string): Promise<void> {
  const res = await send(path, undefined, "*/*");
  const name = FILENAME_PATTERN.exec(res.headers.get("Content-Disposition") ?? "")?.[1] ?? fallbackName;
  const href = URL.createObjectURL(await res.blob());
  const anchor = document.createElement("a");
  anchor.href = href;
  anchor.download = name;
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(href);
}

function postJson<T>(path: string, body?: unknown): Promise<T> {
  return request<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

const sid = (id: string) => `/api/sessions/${encodeURIComponent(id)}`;

export const api = {
  config: () => request<ConfigInfo>("/api/config"),
  overview: () => request<Overview>("/api/overview"),
  sessions: () => request<Session[]>("/api/sessions"),
  createSession: (body: SessionCreate) => postJson<Session>("/api/sessions", body),
  session: (id: string) => request<Session>(sid(id)),
  loadDemo: (id: string, replace = false) => postJson<DemoLoadResult>(`${sid(id)}/demo${replace ? "?replace=true" : ""}`),
  uploadLedger: (id: string, file: File, replace = false) => {
    const form = new FormData();
    form.append("file", file);
    return request<LedgerUploadResult>(`${sid(id)}/ledger${replace ? "?replace=true" : ""}`, { method: "POST", body: form });
  },
  ledger: (id: string) => request<LedgerRecord[]>(`${sid(id)}/ledger`),
  uploadImages: (id: string, files: File[]) => {
    const form = new FormData();
    for (const file of files) form.append("files", file);
    return request<ImageAsset[]>(`${sid(id)}/images`, { method: "POST", body: form });
  },
  images: (id: string) => request<ImageAsset[]>(`${sid(id)}/images`),
  createRun: (id: string, body: RunCreate) => postJson<Run>(`${sid(id)}/runs`, body),
  extractDetection: (detectionId: string) =>
    postJson<DetectionBundle>(`/api/detections/${encodeURIComponent(detectionId)}/extract`, {}),
  run: (runId: string) => request<Run>(`/api/runs/${encodeURIComponent(runId)}`),
  detections: (id: string) => request<DetectionBundle[]>(`${sid(id)}/detections`),
  reconciliation: (id: string) => request<Reconciliation>(`${sid(id)}/reconciliation`),
  reviewQueue: (id: string) => request<MatchDecision[]>(`${sid(id)}/review-queue`),
  review: (decisionId: string, body: ReviewCreate) =>
    postJson<MatchDecision>(`/api/decisions/${encodeURIComponent(decisionId)}/review`, body),
  /** Viewing is side-effect free; only downloadReport (download=true) can finalize the session. */
  report: (id: string) => request<ReportSummary>(`${sid(id)}/report?format=json`),
  reportHtml: async (id: string) => (await send(`${sid(id)}/report?format=html`, undefined, "text/html")).text(),
  downloadReport: (id: string, format: "html" | "csv") =>
    downloadFile(`${sid(id)}/report?format=${format}&download=true`, `auditglimmer-${id}.${format}`),
  trace: (id: string) => request<Trace>(`${sid(id)}/trace`),
  evidenceGraph: (id: string) => request<EvidenceGraph>(`${sid(id)}/evidence-graph`),
};

/** <img> cannot send headers; the backend accepts ?access_code= on image files only. */
function withAccessCode(url: string): string {
  const code = getAccessCode();
  if (!code) return url;
  return `${url}${url.includes("?") ? "&" : "?"}access_code=${encodeURIComponent(code)}`;
}

export const urls = {
  // ponytail: EventSource cannot send X-Access-Code; behind the gate RunProgress falls back to polling.
  runEvents: (runId: string) => apiUrl(`/api/runs/${encodeURIComponent(runId)}/events`),
  /** ImageAsset.url is a server-relative path; resolve it against the API base. */
  image: (asset: Pick<ImageAsset, "url">) =>
    withAccessCode(/^https?:\/\//.test(asset.url) ? asset.url : apiUrl(asset.url)),
};

export const queryKeys = {
  config: ["config"] as const,
  overview: ["overview"] as const,
  sessions: ["sessions"] as const,
  session: (id: string) => ["session", id] as const,
  ledger: (id: string) => ["session", id, "ledger"] as const,
  images: (id: string) => ["session", id, "images"] as const,
  detections: (id: string) => ["session", id, "detections"] as const,
  reconciliation: (id: string) => ["session", id, "reconciliation"] as const,
  reviewQueue: (id: string) => ["session", id, "review-queue"] as const,
  report: (id: string) => ["session", id, "report"] as const,
  reportHtml: (id: string) => ["session", id, "report", "html"] as const,
  trace: (id: string) => ["session", id, "trace"] as const,
  graph: (id: string) => ["session", id, "graph"] as const,
};

/** Every session-scoped query shares the ["session", id] prefix, so one call refreshes them all. */
export function invalidateSession(client: { invalidateQueries: (f: { queryKey: readonly unknown[] }) => unknown }, id: string) {
  client.invalidateQueries({ queryKey: ["session", id] });
  client.invalidateQueries({ queryKey: queryKeys.overview });
}
