"""Audit report export (JSON, HTML, CSV). Every decision links back to raw evidence and provider calls."""

from __future__ import annotations

import csv
import html
import io

from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import VERSION, Settings
from .db import AuditSession, ImageRow, LedgerRow, utcnow
from .security import csv_safe
from .services import build_reconciliation, build_trace, get_session_or_404

DISCLAIMER = (
    "This report records visual evidence and deterministic matching outcomes only. A photograph does not prove "
    "legal ownership, asset authenticity, condition or financial value. UNVERIFIED means the asset was not "
    "adequately observed - it is NOT evidence that the asset is missing. Ledger values are reproduced as stated "
    "in the register and are not valuations. Confidence values are model-reported and uncalibrated."
)


def build_report(db: Session, sid: str, settings: Settings, mark_reported: bool = False) -> dict:
    session: AuditSession = get_session_or_404(db, sid)
    recon, det_by_ev = build_reconciliation(db, sid)
    trace = build_trace(db, sid)
    ledger = {r.asset_id: r for r in db.scalars(select(LedgerRow).where(LedgerRow.session_id == sid)).all()}
    images = {i.id: i for i in db.scalars(select(ImageRow).where(ImageRow.session_id == sid)).all()}
    decisions = []
    for d in recon.decisions:
        det = det_by_ev[d.evidence_id]
        ev = det.evidence
        decisions.append({
            **d.model_dump(mode="json"),
            "image": {"id": det.image_id, "filename": images[det.image_id].filename,
                      "sha256": images[det.image_id].sha256},
            "detection": {"id": det.id, "bounds": det.mask["bounds"], "provider_confidence": det.confidence,
                          "provider": det.provider, "model": det.model, "mode": det.mode,
                          "provider_call_id": det.provider_call_id},
            "evidence": {"status": ev.status, "error": ev.error, "provider": ev.provider, "model": ev.model,
                         "provider_call_id": ev.provider_call_id, "fields": ev.evidence},
        })
    assets = []
    for a in recon.assets:
        row = ledger[a.asset_id]
        assets.append({**a.model_dump(mode="json"), "asset_type": row.asset_type, "manufacturer": row.manufacturer,
                       "model": row.model, "serial_number": row.serial_number, "facility_id": row.facility_id,
                       "expected_location": row.expected_location, "ledger_value_as_stated": row.ledger_value,
                       "currency": row.currency, "ledger_source_row": row.source_row})
    # unusable evidence cannot be reviewed (re-extract instead); it is listed, not counted as an open review
    open_reviews = sum(1 for d in recon.decisions
                       if d.review_required and d.review is None and d.decision != "EVIDENCE_UNUSABLE")
    conflicts = sum(1 for d in recon.decisions if "CONFLICTING_REVIEWS" in d.flags)
    final = open_reviews == 0 and conflicts == 0
    if mark_reported and final:  # only a downloaded export with nothing open finalizes; viewing never does
        session.reported_at = utcnow()
    modes = sorted({c.mode for c in trace.provider_calls}) or [settings.mode]
    return {
        "report_version": 2, "generated_at": utcnow(), "app_version": VERSION,
        "report_state": "FINAL" if final else "DRAFT", "open_reviews": open_reviews, "conflicting_reviews": conflicts,
        "mode": settings.mode, "provider_modes_used": modes,
        "demo_notice": "DEMO MODE: fixture providers on synthetic images; no AI model was called."
        if "demo" in modes else None,
        "session": {"id": session.id, "name": session.name, "facility_id": session.facility_id,
                    "created_at": session.created_at, "ledger_sha256": session.ledger_sha256},
        "disclaimer": DISCLAIMER, "summary": recon.summary.model_dump(mode="json"),
        "assets": assets, "decisions": decisions,
        "provider_calls": [c.model_dump(mode="json") for c in trace.provider_calls],
        "latency": [x.model_dump() for x in trace.latency],
        "total_estimated_cost_usd": trace.total_estimated_cost_usd,
    }


def report_csv(report: dict) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["asset_id", "status", "human_confirmed", "reason", "asset_type", "manufacturer", "model",
                "serial_number", "facility_id", "ledger_value_as_stated", "currency", "decision_ids",
                "ledger_source_row"])
    for a in report["assets"]:
        w.writerow([csv_safe(a[k]) for k in ("asset_id", "status", "human_confirmed", "reason", "asset_type",
                                             "manufacturer", "model", "serial_number", "facility_id",
                                             "ledger_value_as_stated", "currency")]
                   + [csv_safe(";".join(a["decision_ids"])), csv_safe(a["ledger_source_row"])])
    w.writerow([])
    w.writerow(["decision_id", "decision", "tier", "matching_rule", "matched_asset_id", "candidate_asset_ids",
                "rule_score", "review_required", "review_action", "reviewer", "flags", "unmatched_fields",
                "image_filename", "image_sha256", "detection_bounds", "evidence_status", "explanation"])
    for d in report["decisions"]:
        review = d.get("review") or {}
        w.writerow([csv_safe(v) for v in (
            d["id"], d["decision"], d["tier"], d["matching_rule"], d["matched_asset_id"],
            ";".join(d["candidate_asset_ids"]), d["match_score"], d["review_required"], review.get("action"),
            review.get("reviewer"), ";".join(d["flags"]), ";".join(d["unmatched_fields"]), d["image"]["filename"],
            d["image"]["sha256"], d["detection"]["bounds"], d["evidence"]["status"], d["explanation"])])
    return buf.getvalue()


def _e(value: object) -> str:
    return html.escape("" if value is None else str(value))


def _review_cell(d: dict) -> str:
    """Full, ordered review history: a later review never hides an earlier one."""
    rows = d.get("review_history") or []
    if not rows:
        return "<small>not reviewed</small>"
    items = "".join(
        f"<li>{_e(r['created_at'][:19])} <b>{_e(r['action'])}</b>{' ' + _e(r['asset_id']) if r.get('asset_id') else ''}"
        f" by {_e(r['reviewer'])}{': <i>' + _e(r['note']) + '</i>' if r.get('note') else ''}</li>" for r in rows)
    return f"<ol>{items}</ol>"


def report_html(report: dict) -> str:
    s = report["summary"]
    status_rows = "".join(f"<tr><td>{_e(k)}</td><td>{v}</td></tr>" for k, v in s["by_status"].items())
    asset_rows = "".join(
        f"<tr><td>{_e(a['asset_id'])}</td><td class='st {_e(a['status'])}'>{_e(a['status'])}"
        f"{' (human)' if a['human_confirmed'] else ''}</td><td>{_e(a['asset_type'])}</td>"
        f"<td>{_e(a['manufacturer'])} {_e(a['model'])}</td><td>{_e(a['serial_number'])}</td>"
        f"<td>{_e(a['reason'])}</td><td>{_e(', '.join(a['decision_ids']))}</td></tr>" for a in report["assets"])
    dec_rows = "".join(
        f"<tr><td>{_e(d['id'])}</td><td>{_e(d['decision'])}</td><td>{_e(d['matching_rule'])}</td>"
        f"<td>{_e(d['matched_asset_id'] or ', '.join(d['candidate_asset_ids']))}</td><td>{d['match_score']}</td>"
        f"<td>{_e(d['image']['filename'])}<br><small>{_e(d['image']['sha256'][:16])}... bounds "
        f"{_e(d['detection']['bounds'])}</small></td><td>{_e(d['evidence']['status'])}"
        f"{'<br><small>' + _e(d['evidence']['error']) + '</small>' if d['evidence']['error'] else ''}</td>"
        f"<td>{_e(', '.join(d['flags']))}</td><td>{_e(d['explanation'])}</td>"
        f"<td>{_review_cell(d)}</td></tr>"
        for d in report["decisions"])
    state = (f"<p class='demo'><b>DRAFT</b> &mdash; {report['open_reviews']} decision(s) await review, "
             f"{report['conflicting_reviews']} have conflicting reviews. Not a final audit record.</p>"
             if report["report_state"] == "DRAFT" else "<p class='disc'><b>FINAL</b> &mdash; all decisions reviewed.</p>")
    demo = f"<p class='demo'>{_e(report['demo_notice'])}</p>" if report["demo_notice"] else ""
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>AuditGlimmer report {_e(report['session']['name'])}</title>
<style>body{{font:14px/1.45 system-ui,sans-serif;margin:24px;color:#111}}table{{border-collapse:collapse;width:100%;margin:12px 0}}
td,th{{border:1px solid #ccc;padding:4px 6px;vertical-align:top;text-align:left}}th{{background:#f1f3f5}}
.demo{{background:#fff3cd;border:1px solid #e0b100;padding:8px}}.disc{{background:#eef6f8;padding:8px;border-left:4px solid #0a8a9a}}
small{{color:#555}}</style></head><body>
<h1>AuditGlimmer audit report</h1>
<p>Session <b>{_e(report['session']['name'])}</b> ({_e(report['session']['id'])}) &middot; facility {_e(report['session']['facility_id'])}
&middot; generated {_e(report['generated_at'])} &middot; evidence produced in {_e(' + '.join(report['provider_modes_used']).upper())} mode (server now {_e(report['mode'].upper())}) &middot; ledger sha256 {_e(report['session']['ledger_sha256'])}</p>
{state}{demo}<p class="disc">{_e(report['disclaimer'])}</p>
<h2>Summary</h2><table><tr><th>Asset status</th><th>Count</th></tr>{status_rows}</table>
<p>Decisions: {s['decisions_total']} &middot; review required: {s['review_required']} &middot; reviewed: {s['reviewed']}
&middot; inspected concepts: {_e(', '.join(s['inspected_concepts']))} &middot; estimated provider cost: ${report['total_estimated_cost_usd']}</p>
<h2>Assets</h2><table><tr><th>Asset</th><th>Status</th><th>Type</th><th>Mfr / model (ledger)</th><th>Serial (ledger)</th><th>Reason</th><th>Decisions</th></tr>{asset_rows}</table>
<h2>Decisions and source evidence</h2><table><tr><th>Decision</th><th>Outcome</th><th>Rule</th><th>Asset(s)</th><th>Rule score</th><th>Source image</th><th>Evidence</th><th>Flags</th><th>Explanation</th><th>Review</th></tr>{dec_rows}</table>
<p><small>Rule score is a deterministic weighting of matched fields, not a probability. Full provider call log and raw-output references are in the JSON export.</small></p>
</body></html>"""
