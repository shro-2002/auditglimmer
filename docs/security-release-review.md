# Security Release Review — 2026-10-31

Scope: release candidate after the live sprint. Earlier independent adversarial review (16
defects, all fixed with regression tests) is summarised in `docs/evaluation-report.md`; controls
are listed in `docs/security.md`.

## New surface this sprint and its controls

| Change | Risk | Control | Test |
|---|---|---|---|
| `POST /api/detections/{id}/extract` (paid per call in LIVE) | double spend, race on unique evidence row | process-wide lock; 409 if evidence exists; 403 if LIVE not approved | `test_concurrent_extract_clicks_spend_once`, `test_segment_only_run_then_extract_selected_region` |
| Segment-only runs (`extract: false`, LIVE default in UI) | — (reduces spend) | — | same |
| Persistent spend caps | runaway spend across sessions/restarts | per-session request cap (12) and all-time USD cap ($1.00) computed from stored ProviderCall rows, on top of per-run caps | `test_live_budget_respects_session_and_total_caps` |
| `.env` loader | secret leakage | file git-ignored, mode 600, real env wins, key never logged or returned (`/api/config` exposes a boolean) | `loader ok` check |
| Real photos | GPS/EXIF privacy | re-encoded without metadata | manual check (`file` shows no EXIF) |
| Manufacturer aliases | over-matching | exact normalized-key table (CAT, JD, MHI) only; never fuzzy | `test_manufacturer_alias_found_in_live_run_narrows_candidates` |

## Launch-blocking assessment

| Severity | Open items | Launch-blocking? |
|---|---|---|
| CRITICAL | none known | — |
| HIGH | **No authentication / authorization.** Any client that can reach the API can read, review or delete any session and trigger paid calls. | **Blocks public deployment.** Not blocking for localhost demo. |
| MEDIUM | Spend caps are estimates; actual billing may differ; timed-out retried requests may bill twice inside one reservation. In-process locks assume a single API worker. No request-body limit before multipart parsing. | No (local, single worker) |
| MEDIUM | Visual spoofing: a printed tag with a register serial would be read and could auto-verify (Tier 1). Physical tag security is outside what a photo proves; the report disclaimer says so. | No (documented limitation) |
| LOW | `meta-sam-parser` SAM License (non-OSI). Dev-only npm advisories (16 moderate). | No |

## Verified this sprint

- `pip-audit`: no known vulnerabilities (earlier run; dependency set unchanged except none added).
- `npm audit --omit=dev`: 0 vulnerabilities (unchanged dependency set).
- Backend tests 81/81, demo browser tests 8/8, axe 0 serious/critical on 3 pages.
- No secrets in repo files: `.env` is ignored; docs and eval JSON contain no key material
  (request IDs kept server-side only).

## Deployment decision

**Do not deploy publicly** until authentication (at minimum a shared demo passcode + per-session
ownership) and a server-side global spend cap independent of the DB are added. Localhost demo is
the supported path.
