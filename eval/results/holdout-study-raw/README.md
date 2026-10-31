# Holdout study — raw provider outputs (LIVE, 31 Oct 2026, session ses_63033bcece24)

- `call_*.txt`: exact text returned by `muse-spark-1.3` for each call (14 first reads, 5 second reads).
- `call_*.view.jpg`: the enhanced view sent for each second read. These are derivatives of the photos in
  `fixtures/holdout/images/` and carry the same licence and attribution (see `fixtures/holdout/LICENSES.md`).
- `provider_calls.json`: the SQLite `provider_calls` rows for the session (model, operation, status, latency,
  tokens, estimated cost, request correlation id). No API key or credential is stored in any row.
