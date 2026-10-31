# Video storyboard (≤ 3 min) — draft, owner records

Holdout run and independently verified (31 Oct) — recording may proceed in DEMO with stored live sessions; a new LIVE take needs owner approval.
Rules: AuditGlimmer is a hackathon prototype, **not production-certified**. DEMO frames show the DEMO badge
("fixture providers, no model call"). Live material is a replay of runs recorded on 31 Oct — say "recorded live",
never "running live now". Cite only verified numbers; no holdout numbers until its results file is verified.

| # | Time | Frame | Voice-over (key line) |
|---|---|---|---|
| 1 | 0:00–0:15 | Overview page | "Lenders audit equipment collateral by sending people to read nameplates. AuditGlimmer turns photos into an auditable reconciliation — and refuses to guess." |
| 2 | 0:15–0:40 | Stored live session: SAM 3.1 masks on a real warehouse/generator photo | "SAM 3.1 finds each piece of equipment and gives us a mask — the geometry. It does not read anything." |
| 3 | 0:40–1:05 | Evidence panel: Muse Spark JSON (serial, maker, uncertainties) | "Muse Spark reads only the crop into a closed schema. It never sees the register, and must flag what it can't read." |
| 4 | 1:05–1:30 | DEMO: A-001 VERIFIED (both reads agree, maker corroborates) next to A-004 (`R2e_CONFIRMATION_SERIAL_DISAGREES`: GN-62040 vs GN-62046 → human review) | "Matching is deterministic. A serial match verifies only if a second, independent read agrees and the maker or model corroborates. Here the reads disagree, so a person decides. It's an experimental safeguard, added after our own study caught a disputed read." |
| 5 | 1:30–1:50 | Nameplate-only close-up: "SAM skipped — whole photo declared…", decision `R2e_WHOLE_PHOTO_ASSOCIATION_UNSUPPORTED` with one suggested candidate | "For a close-up of a plate, SAM is skipped and we say so. A loose plate never proves which unit carries it, so it can only suggest a candidate for review." |
| 6 | 1:50–2:20 | Study page: 26 photos, pre-registered thresholds, the FAILED safety gate | "We pre-registered a study: 69% exact serial reads, no invented serials on negatives — and one unsafe verification. We publish that failure, and the fix." |
| 7 | 2:20–2:40 | Review queue + human confirm with note; report export (DRAFT) | "Everything uncertain goes to a named reviewer. The report states what is verified, by which rule, and what is not evidence of absence." |
| 8 | 2:40–3:00 | Observability: calls, latency, cost (7 SAM + 51 Muse ≈ $0.3235 recorded) | "Every model call is logged with cost and raw output. Two Meta models, distinct jobs, conservative decisions." |

Optional slot (only if the holdout runs and is independently verified): replace #6's last line with the holdout
H1/H2/H4b/H7 numbers and their confidence intervals, kept separate from the original pre-registered result.
