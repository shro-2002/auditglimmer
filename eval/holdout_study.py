"""Fresh holdout study — two-read Tier 1 gate on new licensed photos. Protocol: docs/holdout-study-protocol.md.

The original 26-photo study (eval/muse_study.py, fixtures/study/) is frozen and is not touched: this file only
imports its pure helpers.

  uv run --project backend python eval/holdout_study.py adjudicate      # reader1 + reader2 -> ground_truth.json
  uv run --project backend python eval/holdout_study.py ledger          # fixtures/holdout/ledger_holdout.csv
  uv run --project backend python eval/holdout_study.py freeze          # sha256 of every frozen input
  uv run --project backend python eval/holdout_study.py dry-run         # offline: DEMO API refuses non-fixture photos
  uv run --project backend python eval/holdout_study.py run --i-approve-spend   # LIVE (owner approval only)
  uv run --project backend python eval/holdout_study.py score           # eval/results/holdout-study.json
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import statistics
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))
from muse_study import LEDGER_COLUMNS, MIN_SERIAL_LEN, decoy_serial, norm, wilson

ROOT = Path(__file__).resolve().parents[1]
HOLD = ROOT / "fixtures" / "holdout"
GT_PATH = HOLD / "ground_truth.json"
LEDGER_PATH = HOLD / "ledger_holdout.csv"
FREEZE_PATH = HOLD / "FROZEN.sha256"
OUT = ROOT / "eval" / "results" / "holdout-study.json"
SESSION_FILE = ROOT / "eval" / "results" / "holdout-study-session.txt"
API = "http://127.0.0.1:8000"
FACILITY = "WH-H"
MAX_USD = 0.30          # hard stop for this study (session spend), checked after every run
CALLS_PER_IMAGE = 2     # first read + at most one confirmation read; no retries beyond transport retries
FROZEN = ["docs/holdout-study-protocol.md", "fixtures/holdout/labels_reader1.json",
          "fixtures/holdout/labels_reader2.json", "fixtures/holdout/ground_truth.json",
          "fixtures/holdout/ledger_holdout.csv", "fixtures/holdout/provenance.json", "eval/holdout_study.py",
          "eval/muse_study.py", "backend/app/reconcile.py", "backend/app/providers/muse_meta.py",
          "backend/app/pipeline.py"]


def images() -> list[Path]:
    return sorted((HOLD / "images").glob("h*.jpg"))


# ---------------- ground truth (same mechanical rule as the original protocol) ----------------

def _readable(label: dict) -> str | None:
    return label["serial"] if label.get("serial") and label.get("serial_confidence") != "none" else None


def adjudicate() -> None:
    r1 = json.loads((HOLD / "labels_reader1.json").read_text())
    r2 = json.loads((HOLD / "labels_reader2.json").read_text())
    assert set(r1) == set(r2) == {p.stem for p in images()}, "both readers must label every image"
    items = {}
    for hid in sorted(r1):
        a, b = _readable(r1[hid]), _readable(r2[hid])
        if a and b and norm(a) == norm(b):
            status, serial = "positive", a
        elif not a and not b:
            status, serial = "negative", None
        else:
            status, serial = "disputed", None
        items[hid] = {"status": status, "serial": serial, "asset_type": r1[hid].get("asset_type"),
                      "manufacturer": r1[hid].get("manufacturer"), "model": r1[hid].get("model"),
                      "distractor_numbers": sorted(set(r1[hid].get("distractor_numbers", []))
                                                   | set(r2[hid].get("distractor_numbers", []))),
                      "reader1_serial": a, "reader2_serial": b}
    GT_PATH.write_text(json.dumps({"adjudication": "docs/holdout-study-protocol.md", "items": items}, indent=1))
    print({s: sum(i["status"] == s for i in items.values()) for s in ("positive", "negative", "disputed")})


def build_ledger() -> None:
    gt, rows = json.loads(GT_PATH.read_text())["items"], []

    def row(asset_id: str, item: dict, serial: str | None, note: str) -> None:
        rows.append({"asset_id": asset_id, "asset_type": item["asset_type"] or "equipment",
                     "manufacturer": item["manufacturer"] or "", "model": item["model"] or "",
                     "serial_number": serial or "", "facility_id": FACILITY, "expected_location": note,
                     "ledger_value": "", "currency": "", "inspection_date": "2026-10-31"})

    for hid, item in gt.items():
        if item["status"] == "positive":
            row(f"T-{hid}", item, item["serial"], "true unit")
            row(f"D-{hid}", item, decoy_serial(item["serial"]), "look-alike decoy (one transposition)")
        for k, number in enumerate(item["distractor_numbers"], 1):
            if norm(number) and len(norm(number)) >= MIN_SERIAL_LEN:
                row(f"X-{hid}-{k}", item, number, "distractor: printed number that is NOT the serial")
        if item["status"] == "disputed":
            for k, reading in enumerate((item["reader1_serial"], item["reader2_serial"]), 1):
                if reading:
                    row(f"U-{hid}-{k}", item, reading, "disputed reading (readers disagree)")
        if item["status"] == "negative" and item["asset_type"]:
            row(f"N-{hid}", item, f"{hid.upper()}-UNSEEN-01", "registered unit whose serial is not visible")
    keys = [norm(r["serial_number"]) for r in rows if r["serial_number"]]
    dupes = {k for k in keys if keys.count(k) > 1}
    rows = [r for r in rows if not (r["asset_id"].startswith("X-") and norm(r["serial_number"]) in dupes)]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=LEDGER_COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    LEDGER_PATH.write_text(buf.getvalue())
    print(f"wrote {len(rows)} ledger rows -> {LEDGER_PATH.relative_to(ROOT)}")


def freeze() -> None:
    lines = [f"{hashlib.sha256((ROOT / p).read_bytes()).hexdigest()}  {p}" for p in FROZEN]
    lines += [f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(ROOT)}" for p in images()]
    FREEZE_PATH.write_text("\n".join(lines) + "\n")
    print(f"froze {len(lines)} files -> {FREEZE_PATH.relative_to(ROOT)}")


def verify_frozen() -> None:
    for line in FREEZE_PATH.read_text().splitlines():
        digest, path = line.split("  ", 1)
        if hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != digest:
            raise SystemExit(f"REFUSED: frozen input changed: {path}")


# ---------------- run ----------------

def _wait(c: httpx.Client, rid: str) -> dict:
    for _ in range(900):
        run = c.get(f"/api/runs/{rid}").json()
        if run["status"] in {"succeeded", "partial", "failed"}:
            return run
        time.sleep(1)
    raise SystemExit(f"run {rid} did not finish")


def _session(c: httpx.Client, name: str) -> tuple[str, dict[str, list[str]]]:
    gt = json.loads(GT_PATH.read_text())["items"]
    sid = c.post("/api/sessions", json={"name": name, "facility_id": FACILITY}).json()["id"]
    c.post(f"/api/sessions/{sid}/ledger", files={"file": (LEDGER_PATH.name, LEDGER_PATH.read_bytes(), "text/csv")}
           ).raise_for_status()
    by_type: dict[str, list[str]] = {}
    for img in images():
        up = c.post(f"/api/sessions/{sid}/images", files={"files": (img.name, img.read_bytes(), "image/jpeg")})
        up.raise_for_status()
        by_type.setdefault(gt[img.stem]["asset_type"] or "generator", []).append(up.json()[0]["id"])
    return sid, by_type


def dry_run() -> None:
    """Offline rehearsal against the DEMO API: proves wiring and that no paid call is possible in DEMO."""
    verify_frozen()
    with httpx.Client(base_url=API, timeout=60) as c:
        if c.get("/api/config").json()["mode"] != "demo":
            raise SystemExit("REFUSED: dry-run needs the DEMO API")
        sid, by_type = _session(c, "e2e holdout dry-run (DEMO, no model calls)")
        for concept, ids in sorted(by_type.items()):
            r = c.post(f"/api/sessions/{sid}/runs", json={"concept": concept, "image_ids": ids,
                                                          "region": "full_frame", "extract": True})
            done = _wait(c, r.json()["id"]) if r.status_code == 202 else {"status": f"HTTP {r.status_code}"}
            print(f"{concept:15s} {len(ids):2d} image(s) -> {done['status']}")
        cost = c.get(f"/api/sessions/{sid}/trace").json()["total_estimated_cost_usd"]
    print(f"dry-run session {sid}: estimated cost ${cost:.4f} (must be 0)")


def run_live() -> None:
    if "--i-approve-spend" not in sys.argv:
        raise SystemExit("REFUSED: pass --i-approve-spend (LIVE Meta calls; owner approval required)")
    verify_frozen()
    with httpx.Client(base_url=API, timeout=120) as c:
        cfg = c.get("/api/config").json()
        if not (cfg["mode"] == "live" and cfg["live_approved"] and cfg["extraction_model"] == "muse-spark-1.3"):
            raise SystemExit(f"REFUSED: API is not in approved LIVE mode: {cfg}")
        sid, by_type = _session(c, "Holdout study — two-read gate (LIVE)")
        SESSION_FILE.write_text(sid + "\n")
        for concept, ids in sorted(by_type.items()):
            r = c.post(f"/api/sessions/{sid}/runs", json={"concept": concept, "image_ids": ids,
                                                          "region": "full_frame", "extract": True})
            r.raise_for_status()
            done = _wait(c, r.json()["id"])
            spent = c.get(f"/api/sessions/{sid}/trace").json()["total_estimated_cost_usd"]
            print(f"{concept:15s} {len(ids):2d} image(s) -> {done['status']:9s} session spend ${spent:.4f}")
            if spent > MAX_USD:
                raise SystemExit(f"STOP: spend ${spent:.4f} above the ${MAX_USD} cap")
    print(f"session {sid}; next: eval/holdout_study.py score")


# ---------------- scoring ----------------

def _outcome(r: dict) -> str:
    """VERIFIED: correct | unsafe. Otherwise a single-candidate suggestion to the reviewer: suggest_correct |
    suggest_wrong; anything else: abstained. Whole-photo regions can never be VERIFIED (D-17)."""
    true = f"T-{r['hid']}"
    if r["decision"] == "VERIFIED":
        return "correct" if r["matched_asset"] == true else "unsafe"
    if len(r["candidates"] or []) == 1:
        return "suggest_correct" if r["candidates"] == [true] else "suggest_wrong"
    return "abstained"


def score() -> None:
    gt = json.loads(GT_PATH.read_text())["items"]
    sid = SESSION_FILE.read_text().strip()
    with httpx.Client(base_url=API, timeout=60) as c:
        names = {i["id"]: Path(i["filename"]).stem for i in c.get(f"/api/sessions/{sid}/images").json()}
        dets = c.get(f"/api/sessions/{sid}/detections").json()
        trace = c.get(f"/api/sessions/{sid}/trace").json()
    calls = {x["id"]: x for x in trace["provider_calls"]}
    rows = []
    for d in dets:
        hid = names[d["detection"]["image_id"]]
        item, rec = gt[hid], d["evidence"] or {}
        ev, conf, dec = rec.get("evidence") or {}, rec.get("confirmation") or {}, d["decision"] or {}
        second = (conf.get("evidence") or {}).get("visible_serial_number")
        call_ids = [rec.get("provider_call_id"), conf.get("provider_call_id")]
        rows.append({
            "hid": hid, "gt_status": item["status"], "gt_serial": item["serial"],
            "read1_serial": ev.get("visible_serial_number"), "read2_serial": second,
            "read2_status": conf.get("status"),
            "reads_agree": bool(conf) and conf.get("status") == "ok" and norm(second) == norm(ev.get("visible_serial_number")),
            "serial_exact": bool(item["serial"]) and norm(ev.get("visible_serial_number")) == norm(item["serial"]),
            "serial_emitted": len(norm(ev.get("visible_serial_number")) or "") >= MIN_SERIAL_LEN,
            "decision": dec.get("decision"), "rule": dec.get("matching_rule"), "matched_asset": dec.get("matched_asset_id"),
            "candidates": dec.get("candidate_asset_ids"),
            "latency_ms": sum(calls[i]["latency_ms"] for i in call_ids if i in calls),
            "cost_usd": sum(calls[i]["estimated_cost_usd"] for i in call_ids if i in calls),
        })
    rows.sort(key=lambda r: r["hid"])
    for r in rows:
        r["outcome"] = _outcome(r)
    pos = [r for r in rows if r["gt_status"] == "positive"]
    verifiable = [r for r in pos if len(norm(r["gt_serial"]) or "") >= MIN_SERIAL_LEN]
    verified = [r for r in rows if r["decision"] == "VERIFIED"]
    correct = [r for r in verified if r["outcome"] == "correct"]
    unsafe = [r for r in verified if r["outcome"] == "unsafe"]
    confirmed = [r for r in rows if r["read2_status"]]
    agree = [r for r in confirmed if r["reads_agree"]]
    k_exact = sum(r["serial_exact"] for r in pos)
    outcomes = ("correct", "unsafe", "suggest_correct", "suggest_wrong", "abstained")
    matrix = {s: {o: sum(r["gt_status"] == s and r["outcome"] == o for r in rows) for o in outcomes}
              for s in ("positive", "negative", "disputed")}
    suggest_ok = [r for r in verifiable if r["outcome"] == "suggest_correct"]
    suggest_bad = [r for r in rows if r["outcome"] == "suggest_wrong"]
    result = {
        "session_id": sid, "protocol": "docs/holdout-study-protocol.md", "frozen": FREEZE_PATH.name,
        "n_images": len(rows), "n_positive": len(pos), "n_verifiable": len(verifiable),
        "metrics": {
            "H1_unsafe_auto_verifications": {"k": len(unsafe), "ids": [r["hid"] for r in unsafe]},
            "H2_serial_exact_on_positives": {"k": k_exact, "n": len(pos), "wilson95": wilson(k_exact, len(pos))},
            "H3_verification_precision": {"k": len(correct), "n": len(verified), "wilson95": wilson(len(correct), len(verified))},
            "H4_correct_verification_yield": {"k": len(correct), "n": len(verifiable),
                                              "wilson95": wilson(len(correct), len(verifiable)),
                                              "note": "0 by design for whole-photo regions (D-17)"},
            "H4b_correct_single_suggestion_yield": {"k": len(suggest_ok), "n": len(verifiable),
                                                    "wilson95": wilson(len(suggest_ok), len(verifiable))},
            "H4c_wrong_single_suggestions": {"k": len(suggest_bad), "ids": [r["hid"] for r in suggest_bad]},
            "H5_abstention_rate_on_verifiable": {"k": sum(r["outcome"] == "abstained" for r in verifiable),
                                                 "n": len(verifiable)},
            "H6_unsafe_rate": {"k": len(unsafe), "n": len(rows), "wilson95": wilson(len(unsafe), len(rows))},
            "H7_two_read": {"second_reads": len(confirmed), "agree": len(agree), "disagree_or_failed": len(confirmed) - len(agree),
                            "gate_blocks_by_rule": {k: sum(r["rule"] == k for r in rows)
                                                    for k in sorted({r["rule"] for r in rows if str(r["rule"]).startswith("R2e_")})}},
            "H8_hallucinated_serial_on_negatives": [r["hid"] for r in rows if r["gt_status"] == "negative" and r["serial_emitted"]],
            "confusion_matrix_gt_status_x_outcome": matrix,
            "decisions": {k: sum(r["decision"] == k for r in rows) for k in sorted({str(r["decision"]) for r in rows})},
            "per_inspection": {"latency_ms_median": statistics.median(r["latency_ms"] for r in rows) if rows else None,
                               "cost_usd_mean": round(sum(r["cost_usd"] for r in rows) / len(rows), 6) if rows else None},
            "estimated_cost_usd_total": trace["total_estimated_cost_usd"],
            "baseline_without_muse": {"correct_auto_verifications": 0, "note": "no visual identifier: every asset "
                                      "needs a field check; benefit = H4 yield at the H1/H6 error rate"},
        },
        "rows": rows,
    }
    OUT.write_text(json.dumps(result, indent=2))
    print(json.dumps(result["metrics"], indent=2))


if __name__ == "__main__":
    {"adjudicate": adjudicate, "ledger": build_ledger, "freeze": freeze, "dry-run": dry_run,
     "run": run_live, "score": score}[sys.argv[1]]()
