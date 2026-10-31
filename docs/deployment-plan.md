# Deployment Plan — AuditGlimmer (prepared 2026-10-31; NOT deployed)

Nothing here has been deployed or published. Every public step needs explicit owner approval.

## Requirements actually known

From `docs/hackathon-compliance.md` (official rules page) and the judge's rubric search: a demo is judged
(25%); a hosted URL and public repo are **not found** as requirements. Owner policy on prior projects:
₹0 hosting, no card on file.

## Options compared

| | A. Protected local demo | B. Render-hosted (single backend service) | C. Vercel frontend + Render backend |
|---|---|---|---|
| What runs where | Both servers on the owner's Mac; optional temporary tunnel (Tailscale Funnel) for a reviewer | FastAPI on Render Free; frontend would also need hosting (static export not yet supported: dynamic `[id]` routes) | Next.js on Vercel Hobby, FastAPI on Render Free |
| Persistence | Local disk, durable | Ephemeral: DB + uploads lost on restart/spin-down; DEMO fixtures re-seed | Same as B for backend |
| Live inference | Possible, owner-attended only | Must be OFF (caps reset with disk) | Must be OFF |
| Cold start | none | ~50 s spin-up after 15 min idle (free tier) | same backend cold start |
| Cost | $0 | $0 (free tier; may require card verification → stop per owner policy) | $0 (two accounts, two configs, CORS across origins) |
| Complexity | lowest | medium | highest |
| Abuse surface | none unless tunnel open; gate when open | public URL; gate mandatory | public URLs; gate mandatory |

**Recommendation: A.** It satisfies every known submission requirement (video + optional reviewer access),
keeps live inference attended and capped, and has no data-loss failure mode. B/C add risk (cold starts,
ephemeral data, card checks) without satisfying any confirmed requirement. Revisit only if the submission
form turns out to require a hosted URL — then use B for the backend in DEMO mode plus the frontend on
Vercel (C), both with the access gate.

## A — architecture

```
reviewer browser ──(optional Funnel HTTPS)──> Next.js dev/prod :3000 ──> FastAPI :8000 (DEMO, access code)
                                                                     └─> SQLite + local images (backend/data)
```
Live inference only from the owner's own terminal, with `AUDITGLIMMER_LIVE_APPROVED=1` set per run and
caps lowered (see env table). Replays of genuine live sessions (`ses_34ab4ba56b1b`, `ses_936bef692a74`)
are shown from the DB and labelled "evidence produced in LIVE mode (server now DEMO)" — never as new runs.

## Environment variable inventory (no values)

| Variable | Where | Purpose | Hosted/demo value guidance |
|---|---|---|---|
| `AUDITGLIMMER_MODE` | backend | `demo` \| `live` | `demo` for any shared/hosted run |
| `AUDITGLIMMER_LIVE_APPROVED` | backend | explicit live opt-in | unset/`0` except attended live runs |
| `MODEL_API_KEY` | backend | Meta Model API key (secret) | **absent** from any hosted env |
| `AUDITGLIMMER_ACCESS_CODE` | backend | shared demo gate (≥24 chars, secret) | required whenever reachable beyond localhost |
| `AUDITGLIMMER_CORS_ORIGINS` | backend | comma-separated allowed origins | the frontend origin only |
| `AUDITGLIMMER_DATA_DIR` | backend | SQLite + uploads dir | default `backend/data` |
| `AUDITGLIMMER_DATABASE_URL` | backend | override DB URL | default SQLite in data dir |
| `AUDITGLIMMER_MAX_LIVE_REQUESTS_PER_RUN` / `_USD_PER_RUN` / `_REQUESTS_PER_SESSION` / `_USD_TOTAL` | backend | spend caps | lower for attended live demos (e.g. 4 / 0.05 / 4 / 0.10) |
| `NEXT_PUBLIC_API_BASE` | frontend (build-time, public) | backend URL | never put secrets here |

Template: `deploy/demo.env.example`.

## Storage and database migration plan

- Demo: fresh SQLite per environment; `create_all` on boot; DEMO fixtures loaded via "Start guided demo".
- Keep the live-evidence DB: copy `backend/data/auditglimmer.db*` and `backend/data/raw/` into a dated backup
  before any schema change (`cp -a backend/data backend/data.bak-$(date +%H%M)`).
- Schema changes in this remediation are additive at the API layer only (no new columns) — existing DB works.
- Real production would need Alembic migrations + Postgres + object storage; out of scope.

## Access-control plan

1. Local only (default): no code, bound to 127.0.0.1.
2. Any tunnel/host: set `AUDITGLIMMER_ACCESS_CODE` (generate: `python3 -c "import secrets;print(secrets.token_urlsafe(24))"`),
   share it out-of-band with judges, rotate after judging.
3. LIVE never enabled on a shared surface.

## Rollback

- Code: pre-remediation snapshot `auditglimmer-pre-judge.tgz` (scratchpad). Project is not under git — recommend `git init` + first commit before submission so rollback is `git revert`.
- Data: restore `backend/data.bak-*`.
- Tunnel: `tailscale funnel off` (or stop the process) closes public access immediately.

## Cost estimate

| Item | Monthly | Per demo |
|---|---|---|
| Option A hosting | $0 | $0 |
| DEMO-mode runs | $0 | $0 |
| Attended live run (1 image: 1 SAM + 2 Muse crops) | — | ≈ $0.0025 + 2×≈$0.005 ≈ **$0.013** |
| Option B/C hosting | $0 on free tiers (card check may be required) | $0 |

## Smoke-test plan (run after any start/restart)

1. `curl -s localhost:8000/api/health` → `"mode":"demo"`.
2. `curl -s localhost:8000/api/config` → `live_approved:false`, models `fixture-*`.
3. With gate on: `curl -s -o /dev/null -w "%{http_code}" localhost:8000/api/sessions` → `401`; with `-H "X-Access-Code: …"` → `200`.
4. Browser: landing → "Start guided demo" → run "forklift" → reconciliation shows `COMPETING`/`AMBIGUOUS` flags, no VERIFIED without serial.
5. Report tab shows DRAFT and does not change session status.
6. `cd backend && uv run pytest -q` and `npm --prefix e2e test` pass.
