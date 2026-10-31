# Deployment Readiness — AuditGlimmer (audited 2026-10-31, post-remediation code)

Scope: the actual code in `backend/app` and `frontend/`, not prior docs. Verdict per area:
READY / CONDITIONAL / NOT READY for a *public* host.

| Area | Finding (evidence) | Verdict |
|---|---|---|
| Authentication | None by default. New optional gate `AUDITGLIMMER_ACCESS_CODE` (≥24 chars, `hmac.compare_digest`) protects every `/api/*` except `/api/health` (`main.py` `access_gate`). One shared code, no per-user accounts. | CONDITIONAL (gate required for any host) |
| Authorization / reviewer identity | `reviewer` is a free-text field (now ≥2 chars incl. a letter). Anyone holding the code can review, override or `DELETE /api/sessions/{sid}`. | NOT READY for real audit use; acceptable for a judge demo with a shared code |
| Session isolation | `GET /api/sessions` lists all sessions to every caller; no tenant/owner column. | NOT READY for multi-tenant; acceptable single-tenant demo |
| SQLite persistence | `create_all` on boot, no migrations (`db.py:178`). WAL file in `backend/data`. Schema changes = new DB. | CONDITIONAL (demo only) |
| Uploaded image storage | Local disk `backend/data/sessions/<sid>/images`; 41 MB today. Render Free disk is ephemeral: everything lost on redeploy/restart/spin-down. | CONDITIONAL — acceptable only if demo data is re-seeded on boot (DEMO fixtures are) |
| Secrets | `MODEL_API_KEY` read from env/.env, never serialized (`Settings._api_key` repr=False). `.env` is git-ignored. `.env` currently contains `AUDITGLIMMER_MODE=live` + `AUDITGLIMMER_LIVE_APPROVED` — a bare restart goes LIVE. Launch entry now pins DEMO. | CONDITIONAL — never ship `.env`; hosted env must omit the key |
| CORS | Explicit allow-list; now configurable via `AUDITGLIMMER_CORS_ORIGINS` (comma list). No wildcard. | READY |
| API exposure | Full OpenAPI at `/docs` + `/openapi.json`; `DELETE` exposed; `POST /api/decisions/{id}/explain` can call Muse in LIVE (process cap 20). | CONDITIONAL (gate covers it) |
| Meta API spend caps | Per-run (40 req / $0.50), per-session (12 req), all-time ($1.00) — all computed from the SQLite `provider_calls` table, so the all-time cap **resets when an ephemeral disk resets**. Also the two scripted calls bypassed the DB. | NOT READY for hosted LIVE — hosted must run DEMO (no key present) |
| Rate limiting | None (only `MAX_ACTIVE_RUNS=4` global, 1 active run per session). | NOT READY for public; acceptable behind the code gate |
| Resource exhaustion | Upload limits: 15 MB/image, 20 images/session, 2 MB / 5000-row ledger, pixel caps (decompression bomb → 413). No cap on number of sessions / total disk. | CONDITIONAL |
| Error handling | Uniform error envelope with correlation id; unhandled → 500 without stack (`main.py`). | READY |
| Health checks | `/api/health` (provider readiness, mode). No `/ready` split. | READY for demo |
| Migrations | None. | CONDITIONAL (fresh DB per deploy) |
| Operational logging | JSON logs per request with correlation id; no secrets logged; access code never logged (query string not logged). | READY |
| Image licensing | 4 PD photos + 1 CC BY-SA (nameplate) with attribution in `fixtures/real/LICENSES.md`; synthetic fixture PNGs generated locally. Any public deployment/video showing the nameplate must carry the CC BY-SA attribution. | CONDITIONAL |
| Public demo abuse | Without the gate: anyone could upload arbitrary images (stored on disk), delete sessions, flood runs. With LIVE + key: real spend. | Mitigated only by: DEMO mode + access gate + no key in hosted env |

## Bottom line

- **Hosted LIVE inference: NOT READY** (DB-backed caps reset with ephemeral storage; no per-user auth).
- **Protected DEMO hosting: technically possible** with the access gate and no API key in the environment.
- **Local protected demo (for judging video): READY.**
