"""Real-photo Muse Spark effectiveness study — ledger builder, LIVE runner and scorer.

Protocol: docs/muse-study-protocol.md (frozen, sha256 recorded before any paid call).

  uv run --project backend python eval/muse_study.py ledger            # build fixtures/study/ledger_study.csv
  uv run --project backend python eval/muse_study.py run --i-approve-spend   # LIVE: one Muse call per image
  uv run --project backend python eval/muse_study.py score             # writes eval/results/muse-study.json

`run` refuses unless the API reports LIVE mode with live approval, and stops before any call if the
pre-registered call or dollar cap could be exceeded. SAM is never called (full-frame regions).
"""

from __future__ import annotations

import csv
import io
import json
import math
import re
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "fixtures" / "study"
GT_PATH = STUDY / "ground_truth.json"
LEDGER_PATH = STUDY / "ledger_study.csv"
OUT = ROOT / "eval" / "results" / "muse-study.json"
SESSION_FILE = ROOT / "eval" / "results" / "muse-study-session.txt"
API = "http://127.0.0.1:8000"
FACILITY = "WH-S"
MAX_CALLS = 30
MAX_USD = 0.30
MIN_SERIAL_LEN = 4  # mirrors app.reconcile.MIN_SERIAL_LEN
LEDGER_COLUMNS = ["asset_id", "asset_type", "manufacturer", "model", "serial_number", "facility_id",
                  "expected_location", "ledger_value", "currency", "inspection_date"]


def norm(value: str | None) -> str | None:
    key = re.sub(r"[\W_]+", "", (value or "").upper())
    return key or None


def decoy_serial(serial: str) -> str:
    """A look-alike register serial: swap the last two characters (or bump the last digit if equal).

    Works on the normalized identifier so the decoy can never normalize back to the true serial.
    """
    serial = norm(serial) or serial
    if len(serial) >= 2 and serial[-1] != serial[-2]:
        return serial[:-2] + serial[-1] + serial[-2]
    last = serial[-1]
    return serial[:-1] + (str((int(last) + 1) % 10) if last.isdigit() else "X")


def load_gt() -> dict:
    return json.loads(GT_PATH.read_text())


# ---------------- ledger ----------------

def build_ledger() -> None:
    """True row + look-alike decoy for every positive; distractor rows that only a misread would match."""
    gt, rows = load_gt(), []

    def row(asset_id: str, item: dict, serial: str | None, note: str) -> None:
        rows.append({"asset_id": asset_id, "asset_type": item["asset_type"] or "equipment",
                     "manufacturer": item["manufacturer"] or "", "model": item["model"] or "",
                     "serial_number": serial or "", "facility_id": FACILITY, "expected_location": note,
                     "ledger_value": "", "currency": "", "inspection_date": "2026-10-31"})

    for sid, item in gt["items"].items():
        if item["status"] == "positive":
            row(f"T-{sid}", item, item["serial"], "true unit")
            row(f"D-{sid}", item, decoy_serial(item["serial"]), "look-alike decoy (one transposition)")
        for k, number in enumerate(item.get("distractor_numbers", []), 1):
            row(f"X-{sid}-{k}", item, number, "distractor: number printed on the photo that is NOT the serial")
        if item["status"] == "disputed":  # both readings registered: any VERIFIED here counts as unsafe (S1)
            for k, reading in enumerate((item["reader1_serial"], item["reader2_serial"]), 1):
                if reading:
                    row(f"U-{sid}-{k}", item, reading, "disputed reading (readers disagree)")
        if item["status"] == "negative" and item["asset_type"]:
            row(f"N-{sid}", item, f"{sid.upper()}-UNSEEN-01", "registered unit whose serial is not visible")
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=LEDGER_COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    serials = [norm(r["serial_number"]) for r in rows if r["serial_number"]]
    assert len(serials) == len(set(serials)), "ledger serials must be unique after normalization"
    LEDGER_PATH.write_text(buf.getvalue())
    print(f"wrote {len(rows)} ledger rows -> {LEDGER_PATH.relative_to(ROOT)}")


# ---------------- LIVE run ----------------

def _wait(c: httpx.Client, rid: str) -> dict:
    for _ in range(900):
        run = c.get(f"/api/runs/{rid}").json()
        if run["status"] in {"succeeded", "partial", "failed"}:
            return run
        time.sleep(1)
    raise SystemExit(f"run {rid} did not finish")


def run_live() -> None:
    if "--i-approve-spend" not in sys.argv:
        raise SystemExit("REFUSED: pass --i-approve-spend (LIVE Meta calls)")
    gt = load_gt()
    images = sorted((STUDY / "images").glob("s*.jpg"))
    if len(images) > MAX_CALLS:
        raise SystemExit(f"REFUSED: {len(images)} images exceeds the {MAX_CALLS}-call cap")
    with httpx.Client(base_url=API, timeout=120) as c:
        cfg = c.get("/api/config").json()
        if not (cfg["mode"] == "live" and cfg["live_approved"] and cfg["extraction_model"] == "muse-spark-1.3"):
            raise SystemExit(f"REFUSED: API is not in approved LIVE mode: {cfg}")
        sid = c.post("/api/sessions", json={"name": "Real-photo Muse Spark study (LIVE)",
                                            "facility_id": FACILITY}).json()["id"]
        SESSION_FILE.write_text(sid + "\n")
        r = c.post(f"/api/sessions/{sid}/ledger", files={"file": ("ledger_study.csv", LEDGER_PATH.read_bytes(), "text/csv")})
        r.raise_for_status()
        by_type: dict[str, list[str]] = {}
        for img in images:
            up = c.post(f"/api/sessions/{sid}/images", files={"files": (img.name, img.read_bytes(), "image/jpeg")})
            up.raise_for_status()
            concept = gt["items"][img.stem]["asset_type"] or "generator"
            by_type.setdefault(concept, []).append(up.json()[0]["id"])
        for concept, ids in sorted(by_type.items()):
            run = c.post(f"/api/sessions/{sid}/runs", json={"concept": concept, "image_ids": ids,
                                                            "region": "full_frame", "extract": True})
            run.raise_for_status()
            done = _wait(c, run.json()["id"])
            spent = c.get(f"/api/sessions/{sid}/trace").json()["total_estimated_cost_usd"]
            print(f"{concept:15s} {len(ids):2d} image(s) -> {done['status']:9s} session spend ${spent:.4f}")
            if spent > MAX_USD:
                raise SystemExit(f"STOP: spend ${spent:.4f} above the ${MAX_USD} cap")
    print(f"session {sid}; next: eval/muse_study.py score")


# ---------------- scoring ----------------

def wilson(k: int, n: int) -> list[float] | None:
    if n == 0:
        return None
    z, p = 1.96, k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [round(max(0.0, centre - half), 3), round(min(1.0, centre + half), 3)]


def score() -> None:
    gt = load_gt()["items"]
    sid = SESSION_FILE.read_text().strip()
    with httpx.Client(base_url=API, timeout=60) as c:
        images = {i["id"]: Path(i["filename"]).stem for i in c.get(f"/api/sessions/{sid}/images").json()}
        dets = c.get(f"/api/sessions/{sid}/detections").json()
        trace = c.get(f"/api/sessions/{sid}/trace").json()
    rows = []
    for d in dets:
        study_id = images[d["detection"]["image_id"]]
        item, ev = gt[study_id], (d["evidence"] or {}).get("evidence") or {}
        dec = d["decision"] or {}
        read = ev.get("visible_serial_number")
        accepted = {norm(s) for s in [item.get("serial"), *item.get("serial_alternates", [])] if s}
        rows.append({
            "study_id": study_id, "gt_status": item["status"], "gt_serial": item.get("serial"),
            "muse_serial": read, "muse_manufacturer": ev.get("visible_manufacturer"), "muse_model": ev.get("visible_model"),
            "muse_type": ev.get("observed_object_type"), "evidence_status": (d["evidence"] or {}).get("status"),
            "serial_exact": bool(read) and norm(read) in accepted,
            "serial_emitted": bool(norm(read)) and len(norm(read)) >= MIN_SERIAL_LEN,
            "distractor_read": bool(read) and norm(read) in {norm(x) for x in item.get("distractor_numbers", [])},
            "uncertainty_on_serial": any(u.get("field") == "visible_serial_number" for u in ev.get("uncertainties", [])),
            "decision": dec.get("decision"), "rule": dec.get("matching_rule"),
            "matched_asset": dec.get("matched_asset_id"), "candidates": dec.get("candidate_asset_ids"),
            "flags": dec.get("flags"),
        })
    rows.sort(key=lambda r: r["study_id"])
    verifiable = [r for r in rows if r["gt_status"] == "positive" and len(norm(r["gt_serial"]) or "") >= MIN_SERIAL_LEN]
    positives = [r for r in rows if r["gt_status"] == "positive"]
    negatives = [r for r in rows if r["gt_status"] == "negative"]
    verified = [r for r in rows if r["decision"] == "VERIFIED"]
    false_verified = [r for r in verified if r["matched_asset"] != f"T-{r['study_id']}"]
    correct_verified = [r for r in verified if r["matched_asset"] == f"T-{r['study_id']}"]
    k_exact = sum(r["serial_exact"] for r in positives)
    halluc = [r for r in negatives if r["serial_emitted"]]
    calls = [x for x in trace["provider_calls"] if x["operation"] == "extract"]
    result = {
        "session_id": sid, "protocol": "docs/muse-study-protocol.md",
        "n_images": len(rows), "n_positive": len(positives), "n_verifiable": len(verifiable),
        "n_negative": len(negatives), "n_disputed": sum(r["gt_status"] == "disputed" for r in rows),
        "metrics": {
            "serial_exact_on_positives": {"k": k_exact, "n": len(positives), "rate": round(k_exact / len(positives), 3)
                                          if positives else None, "wilson95": wilson(k_exact, len(positives))},
            "hallucinated_serial_on_negatives": {"k": len(halluc), "n": len(negatives), "ids": [r["study_id"] for r in halluc]},
            "distractor_read_as_serial": [r["study_id"] for r in rows if r["distractor_read"]],
            "false_auto_verifications": {"k": len(false_verified), "ids": [r["study_id"] for r in false_verified]},
            "correct_auto_verifications": {"k": len(correct_verified), "n_verifiable": len(verifiable),
                                           "wilson95": wilson(len(correct_verified), len(verifiable))},
            "decisions": {k: sum(r["decision"] == k for r in rows) for k in sorted({str(r["decision"]) for r in rows})},
            "extract_calls": len(calls), "extract_errors": sum(x["status"] != "ok" for x in calls),
            "estimated_cost_usd": trace["total_estimated_cost_usd"],
            "latency_ms_p50": sorted(x["latency_ms"] for x in calls)[len(calls) // 2] if calls else None,
        },
        "baseline_without_muse": "0 automatic verifications possible: with no visual evidence the rule engine has no "
                                 "identifier to match, so every asset stays UNVERIFIED and goes to a field check.",
        "rows": rows,
    }
    OUT.write_text(json.dumps(result, indent=2))
    print(json.dumps(result["metrics"], indent=2))


if __name__ == "__main__":
    {"ledger": build_ledger, "run": run_live, "score": score}[sys.argv[1]]()
