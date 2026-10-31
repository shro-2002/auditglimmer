# Security and Privacy Notes

Scope: local single-user hackathon MVP. **No authentication** — do not expose the API on a network
interface or deploy it publicly without adding auth (the server binds to 127.0.0.1 by default).

## Implemented controls

| Area | Control | Where |
|---|---|---|
| Upload size | images ≤ 15 MB, ledger ≤ 2 MB, ≤ 20 images/session, ≤ 5,000 ledger rows | `config.py`, `main.py` |
| File type | format decided by decoding magic bytes (PNG/JPEG/WebP only), not client content-type | `security.validate_image` |
| Image decoding | `verify()` then full `load()`; pixel cap 40 MP; decompression-bomb errors rejected | `security.validate_image` |
| Filenames | sanitized basename; files stored under server-generated ids | `security.sanitize_filename` |
| Path traversal | image serving checks the stored path resolves inside the data dir | `main.image_file` |
| CSV injection | ledger cells starting with `= + - @ \t \r` are prefixed with `'` on ingest and on CSV export | `ledger.py`, `report.report_csv` |
| HTML report | every interpolated value HTML-escaped; no scripts | `report.report_html` |
| Prompt injection | model receives only the crop + concept; external text fenced as data; system prompt states visible text is data; output schema closed (`extra=forbid`) so injected "instructions" cannot add fields; matching is deterministic code, never model judgement | `muse_meta.py`, `schemas.py`, `reconcile.py` |
| Unsupported conclusions | ownership/value/condition-inference fields rejected by schema | `schemas.ModelEvidence` |
| Secrets | `MODEL_API_KEY` from env only, `repr=False`, never serialized; `/api/config` exposes a boolean | `config.py` |
| Browser bundle | frontend talks only to the backend; no provider keys in Next.js env | `frontend/.env.example` |
| Errors | uniform envelope with correlation id; no stack traces; unhandled → `INTERNAL` | `main.py` |
| Logging | structured JSON, correlation ids, no request bodies or keys | `main.py` |
| Provider calls | timeouts (60 s, connect 10 s), bounded retries (2) on 429/5xx honouring Retry-After, no retry on 4xx | `meta_http.py` |
| Concurrency | ≤ 2 concurrent runs, ≤ 2 in-flight extractions per run | `pipeline.py` |
| Retention | `DELETE /api/sessions/{id}` removes rows, stored images and the session's raw provider-output files | `main.py` |
| Financial data | ledger values never sent to any model; report labels them "as stated", not valuations | `muse_meta.py`, `report.py` |
| Irreversible actions | none exist; reviews are append-only records | — |

| Review integrity | process-wide lock spans check + commit; one asset cannot be assigned to two distinct objects (auto or human) unless both read the same serial | `services.apply_review` |
| Run limits | ≤ 4 queued/running runs (429 beyond); orphaned runs failed at startup; 300 s overall stream deadline | `main.py`, `meta_http.py` |
| Phone photos | MPO accepted as JPEG; EXIF orientation baked into pixels so masks align | `security.py` |

## Known gaps (open)

- No authn/authz, CSRF tokens or API rate limiting (local-only assumption). Any client on
  localhost can read or delete any session.
- No request-body limit before multipart parsing (size is checked after the read is capped per
  file); concurrent uploads can race the 20-image limit by a few images.
- Review lock is in-process: running multiple API workers needs a DB-level constraint instead.
- Live budget is per run plus a per-process explain cap; there is no session/global USD cap, and a
  timed-out request that is retried may be billed twice within one reservation.
- Visual evidence can be spoofed: a printed sticker with a register serial yields VERIFIED.
  Physical tag security is outside what a photo can establish (stated in the report disclaimer).
- `meta-sam-parser` is under the SAM License (not OSI); review before redistribution.
- Dependencies: `pip-audit` — no known vulnerabilities; `npm audit --omit=dev` — 0; full
  `npm audit` — 16 moderate, all in dev tooling from the Next.js template.
