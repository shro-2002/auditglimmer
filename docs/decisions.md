# Decisions (ADR log)

Format: context → decision → consequence. Dated 2026-10-31.

**D-01 SQLite typed tables, not Neo4j.** Provenance chain is fixed-depth; identity resolution is
key-based. → SQLAlchemy models; PostgreSQL via URL change. Revisit for cross-session identity
(see ontology.md).

**D-02 Synthetic, self-rendered fixtures.** Demo images must be licence-clean and have exact
masks. → `scripts/make_fixtures.py` renders scenes and masks from the same draw calls (CC0).
Consequence: fixture metrics say nothing about real-photo model quality; labelled everywhere.

**D-03 DEMO fixtures answer only for bundled images.** Prevents a demo from silently "inventing"
results for user photos. → keyed by SHA-256; other images get `no_fixture`.

**D-04 LIVE never falls back.** Missing key or approval → 403 and unhealthy providers.

**D-05 Use the official `meta-sam-parser`.** The wire grammar has base85 masks, sparse ids and
inclusive wire coordinates; hand-parsing is a bug farm. Verified against the documented example
(bounds become half-open, raster W×H equals bounds W×H).

**D-06 Masks rendered as SVG paths in raster space with one transform.** The overlay is an
`<svg viewBox="0 0 W H">` over the `<img>`, so alignment needs no client math (Gate 4).

**D-07 Matching tiers.** Tier 1 unique readable non-conflicting serial (auto); Tier 2 mfr+model or
uncertain/duplicated serial (review); Tier 3 type only (review, never raises asset status); Tier 4
no supported match. MISMATCHED for conflicting identifiers. Min serial length 4 after normalization.
Rule score is a fixed weighting (serial .6, mfr .15, model .15, type .1, −.3 per conflict) — a
display aid, never a probability, never a threshold for auto-matching.

**D-08 Duplicate identifier on several objects blocks auto-verification.** Could be one asset
photographed twice or a cloned tag; a human decides.

**D-09 UNVERIFIED vs NOT_OBSERVABLE.** UNVERIFIED = facility+type was inspected but no adequate
evidence links the asset; NOT_OBSERVABLE = no inspection covered it. Neither means missing.

**D-10 Reconciliation recomputed on read.** Pure function over persisted evidence + reviews;
decision id = `dec_{evidence_id}` so reviews attach stably. Re-running a concept supersedes the
previous run for that concept.

**D-11 Model sees only the crop and the concept.** No ledger values, serials or asset ids are sent
(no financial data, and no anchoring of the transcription). Visible text and the concept are
fenced as data in the prompt.

**D-12 `evidence_references` are server-attached.** The model cannot author provenance.

**D-13 `muse-spark-1.3` Standard mode, not Contributor.** Contributor is ~12× cheaper but allows
Meta to train on uploaded content; audit photos of client collateral should not be shared that way
by default.

**D-14 No Docker Compose.** Two processes (`uvicorn`, `next dev`) on one Mac; compose adds a layer
without a benefit for the demo.

**D-15 Live run caps.** 40 requests and $0.50 estimated per run by default (env-configurable);
pre-call reservation with a conservative per-extraction estimate; actual usage recorded after.
