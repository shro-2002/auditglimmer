"""Approved, bounded LIVE evaluation through the running AuditGlimmer API (real Meta calls).

Budget approved by the owner on 2026-10-31: <= 5 SAM + 5 Muse calls in total, $1.00 cap.
This script uses at most 4 SAM + 2 Muse calls through the app and 1 direct Muse call (nameplate);
the UI journey (e2e/tests/live-journey.spec.ts) uses the remaining 1 SAM + 2 Muse.

Run (API must be running in LIVE mode):
  uv run --project backend python eval/live_eval.py --i-approve-spend
Writes eval/results/live-eval.json and overlay PNGs under eval/results/live-overlays/.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
import time
from pathlib import Path

import httpx
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
REAL = ROOT / "fixtures" / "real"
OUT = ROOT / "eval" / "results"
API = "http://127.0.0.1:8000"
MAX_SAM, MAX_MUSE = 4, 2

SAM_CASES = [  # (case, image, concept, expected instances per assistant labels)
    ("single_machine", "usace_cat_generator.jpg", "generator", 1),
    ("absent_object", "usace_cat_generator.jpg", "forklift", 0),
    ("ambiguous_concept", "fema_forklift_generators.jpg", "machine", None),
    ("scale_and_view", "fema_distribution_warehouse.jpg", "forklift", 1),
]


def wait_run(c: httpx.Client, rid: str) -> dict:
    for _ in range(600):
        run = c.get(f"/api/runs/{rid}").json()
        if run["status"] in {"succeeded", "partial", "failed"}:
            return run
        time.sleep(0.5)
    raise RuntimeError("run timeout")


def overlay(image_path: Path, rows: list[dict], dest: Path) -> None:
    img = Image.open(image_path).convert("RGB")
    draw = ImageDraw.Draw(img, "RGBA")
    for row in rows:
        x1, y1, x2, y2 = row["detection"]["mask"]["bounds"]
        draw.rectangle([x1, y1, x2, y2], outline=(45, 212, 191, 255), width=6)
        draw.text((x1 + 8, y1 + 8), f"#{row['detection']['object_index']} c={row['detection']['confidence']}",
                  fill=(255, 255, 0, 255))
    img.thumbnail((1200, 1200))
    img.save(dest, quality=85)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--i-approve-spend", action="store_true")
    if not ap.parse_args().i_approve_spend:
        print("REFUSED: pass --i-approve-spend (paid calls).")
        return 2
    c = httpx.Client(base_url=API, timeout=300)
    cfg = c.get("/api/config").json()
    assert cfg["mode"] == "live" and cfg["live_approved"], f"API not in approved LIVE mode: {cfg}"
    sid = c.post("/api/sessions", json={"name": "Live eval (real photos)", "facility_id": "WH-R"}).json()["id"]
    c.post(f"/api/sessions/{sid}/ledger",
           files={"file": ("ledger_real.csv", (REAL / "ledger_real.csv").read_bytes(), "text/csv")})
    names = sorted({case[1] for case in SAM_CASES})
    files = [("files", (n, (REAL / n).read_bytes(), "image/jpeg")) for n in names]
    images = {i["filename"]: i for i in c.post(f"/api/sessions/{sid}/images", files=files).json()}
    (OUT / "live-overlays").mkdir(parents=True, exist_ok=True)
    results: dict = {"session_id": sid, "config": cfg, "sam_cases": [], "muse_cases": []}
    sam_calls = muse_calls = 0
    for case, fname, concept, expected in SAM_CASES:
        if sam_calls >= MAX_SAM:
            break
        img = images[fname]
        run = wait_run(c, c.post(f"/api/sessions/{sid}/runs",
                                 json={"concept": concept, "image_ids": [img["id"]], "extract": False}).json()["id"])
        sam_calls += 1
        rows = [r for r in c.get(f"/api/sessions/{sid}/detections").json()
                if r["detection"]["run_id"] == run["id"]]
        overlay(REAL / fname, rows, OUT / "live-overlays" / f"{case}.jpg")
        results["sam_cases"].append({
            "case": case, "image": fname, "concept": concept, "expected_instances": expected,
            "run_status": run["status"], "run_error": run["error"], "detections": len(rows),
            "boxes": [r["detection"]["mask"]["bounds"] for r in rows],
            "confidence": [r["detection"]["confidence"] for r in rows],
            "mask_encoding": [r["detection"]["mask"]["encoding"] for r in rows],
            "detection_ids": [r["detection"]["id"] for r in rows]})
        print(case, run["status"], len(rows), "detections")
    # Muse on the single best detection of two cases (user-style region selection)
    for case_name in ("single_machine", "scale_and_view"):
        case = next((x for x in results["sam_cases"] if x["case"] == case_name and x["detection_ids"]), None)
        if case is None or muse_calls >= MAX_MUSE:
            continue
        best = max(range(len(case["detection_ids"])), key=lambda i: case["confidence"][i] or 0)
        did = case["detection_ids"][best]
        resp = c.post(f"/api/detections/{did}/extract")
        muse_calls += 1
        body = resp.json()
        results["muse_cases"].append({"case": case_name, "detection_id": did, "http_status": resp.status_code,
                                      "evidence": body.get("evidence"), "decision": body.get("decision"),
                                      "error": body.get("error")})
        print("muse", case_name, resp.status_code)
    results["trace"] = c.get(f"/api/sessions/{sid}/trace").json()
    results["reconciliation"] = c.get(f"/api/sessions/{sid}/reconciliation").json()
    results["calls_used"] = {"sam_via_app": sam_calls, "muse_via_app": muse_calls}
    (OUT / "live-eval.json").write_text(json.dumps(results, indent=2))
    print("estimated cost:", results["trace"]["total_estimated_cost_usd"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
