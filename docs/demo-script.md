# Demo Walkthrough (≈ 3 minutes, DEMO mode)

Setup: both servers running (README). Browser at http://localhost:3000, 1440-wide window.

1. **Overview (10 s).** Point at the DEMO badge and "credentials: absent · live approved: no".
   "Everything you see is computed from the database — empty means empty."
2. **New session (10 s).** Name "Q4 collateral inspection", facility `WH-01`.
3. **Ledger (20 s).** *Load demo dataset.* 18 accepted, 2 rejected. Show the issues table:
   missing asset_id, duplicate asset_id, a `=HYPERLINK(...)` cell neutralized, a serial shared by
   two assets. "The register itself is evidence, and it can be wrong."
4. **Visual inspection (60 s) — the showcase.** Concept `industrial generator` → *Run inspection*.
   Live SSE log: 10 detections; one malformed model response and one response that tried to add
   `legal_owner` / `estimated_value_usd` are **rejected by schema**, not trusted.
   Click region 1: serial GN-48213 → VERIFIED, rule R1. Click region 3: plate reads GN-55011, ledger
   says GN-55017 → MISMATCHED. Toggle masks; "the overlay is the SAM geometry in source pixels".
   Run `forklift`: two identical Liftmaster LM-25 with unreadable serials → ambiguous, never
   auto-resolved. One simulated provider timeout → EVIDENCE_UNUSABLE, run still completes.
5. **Reconciliation (25 s).** 2 VERIFIED, 2 MISMATCHED, 6 PROBABLE, 5 UNVERIFIED, 3 NOT_OBSERVABLE.
   "UNVERIFIED is not missing — we inspected that bay and found no adequate evidence."
6. **Review queue (25 s).** Confirm one LM-25 as A-011 (reviewer name + note). Try confirming the
   other LM-25 as A-011 too → 409: one asset cannot be two physical objects.
7. **Report (15 s).** Download HTML: disclaimer, DEMO notice, every decision with image SHA-256 and
   box. CSV opens safely in a spreadsheet.
8. **Observability (15 s).** Provider-call table (status, latency, tokens, estimated cost),
   p50/p95, and the provenance graph Asset ← Decision ← Evidence ← Detection ← Image.

Close: "LIVE mode calls `sam-3.1` and `muse-spark-1.3` with per-run spend caps; it is implemented
and contract-tested but has not yet been run against the real API."
