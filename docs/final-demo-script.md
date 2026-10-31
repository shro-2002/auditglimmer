# Final Demo Script — 3:00 (confirm the official maximum before recording)

Record the REAL app in LIVE mode. Budget for one take: 1 SAM call + 2 Muse calls ≈ $0.012
(within the approved $1.00 cap; the app enforces session/total caps). Never cut in footage from
fixture mode while narrating it as live; the DEMO/LIVE badge is always on screen.

## Setup (before recording)

1. `.env` has `AUDITGLIMMER_MODE=live`, key, `AUDITGLIMMER_LIVE_APPROVED=1`.
2. Start API: `cd auditglimmer && uv run --project backend uvicorn app.main:create_app --factory --app-dir backend --host 127.0.0.1 --port 8000`
3. Start UI: `cd auditglimmer/frontend && npm run dev`; browser 1440×900, zoom 100%, dark OS theme.
4. Have `fixtures/real/ledger_real.csv` and `fixtures/real/army_forklifts_row.jpg` ready.
5. Screen recorder at 1080p, 30 fps; microphone check.

## Scenes

| Time | Scene | On screen | Narration (draft) |
|---|---|---|---|
| 0:00–0:15 | Hook | Inspection tab: real photo with SAM masks on two forklifts, evidence panel showing "HYSTER" | "A bank's register says two Hyster forklifts are at this dock. A photo shows two forklifts. Which is which — and what can the photo actually prove?" |
| 0:15–0:35 | Problem | Overview, then Ledger tab with 7 rows | "Collateral inspections are manual: find each asset, read plates, reconcile against the books. AuditGlimmer assists that work — it never certifies ownership or value." |
| 0:35–1:05 | Live SAM | Upload photo, concept `forklift`, Run (LIVE defaults to segment-only: "Extract evidence for every detection" is unchecked), SSE log, masks appear | "SAM 3.1 on Meta's Model API returns pixel masks for every forklift. These are the real returned masks, drawn in source-pixel coordinates." |
| 1:05–1:40 | Live Muse | Click region 2 → Extract evidence → structured fields | "Muse Spark 1.3 reads only this crop and returns schema-validated JSON: 'HYSTER' is visible, the serial is not — and it says so instead of guessing. No ledger values are ever sent to the model." |
| 1:40–2:05 | Reconcile + uncertainty | Reconciliation tab, decision panel | "Deterministic rules, not the model, decide. A brand alone can't separate two identical Hysters, so nothing is auto-matched; both go to review. Assets we didn't photograph are UNVERIFIED — not missing." |
| 2:05–2:25 | Human review | Review queue: confirm R-002 for the Hyster region; try the same asset on the other forklift → 409 | "The inspector decides. And the system refuses to assign one asset to two physical objects." |
| 2:25–2:45 | Audit trail | Report download (HTML), Observability: provider-call table with sam-3.1 / muse-spark-1.3, latency, cost; provenance graph | "Every conclusion traces back to an image hash, a mask, and the exact Meta calls behind it — with cost: about a cent for this whole inspection." |
| 2:45–3:00 | Evidence + impact | Slide/text: evaluation numbers | "On our small live test set SAM found 4 of 4 named objects; Muse returned valid JSON 5 of 5 times with zero invented serials or ownership claims. It's built to make inspectors faster without letting AI overclaim." |

Adversarial beat (optional, swap into 1:40): the 1954 generator photo — Muse ignores the archive
caption "BC-260" even though the register lists it as a serial, so the misleading entry is not verified.

## Accuracy guardrails for narration

Say "small live test set (5 images)", "assistant-labelled", "estimated cost". Do not say
"reduces audit time by X%" — no baseline was measured.
