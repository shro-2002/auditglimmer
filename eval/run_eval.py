"""Reproducible evaluation of the AuditGlimmer pipeline against labelled fixtures.

FIXTURE MODE ONLY: segmentation and extraction come from authored fixture labels, so these numbers
measure the reconciliation engine, validation, provenance and error handling - NOT SAM 3.1 or Muse
Spark quality. No live-model quality claim may be derived from this output.

Run: uv run --project backend python eval/run_eval.py
Writes eval/results/fixture-eval.json
"""

from __future__ import annotations

import json
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from fastapi.testclient import TestClient  # noqa: E402

from app.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402

CONCEPTS = ("industrial generator", "forklift")


def wait(client: TestClient, run_id: str) -> dict:
    for _ in range(400):
        run = client.get(f"/api/runs/{run_id}").json()
        if run["status"] in {"succeeded", "partial", "failed"}:
            return run
        time.sleep(0.05)
    raise RuntimeError("run timed out")


def ratio(num: int, den: int) -> float | None:
    return round(num / den, 4) if den else None


def main() -> dict:
    manifest = json.loads((ROOT / "fixtures" / "manifest.json").read_text())
    truth = {(img["sha256"], o["object_index"]): o for img in manifest["images"] for o in img["objects"]}
    with tempfile.TemporaryDirectory() as tmp:
        settings = Settings(mode="demo", data_dir=Path(tmp) / "data", fixtures_dir=ROOT / "fixtures",
                            database_url=f"sqlite:///{Path(tmp) / 'eval.db'}")
        client = TestClient(create_app(settings))
        sid = client.post("/api/sessions", json={"name": "eval", "facility_id": "WH-01"}).json()["id"]
        client.post(f"/api/sessions/{sid}/demo")
        runs = [wait(client, client.post(f"/api/sessions/{sid}/runs", json={"concept": c}).json()["id"])
                for c in CONCEPTS]
        images = {i["id"]: i for i in client.get(f"/api/sessions/{sid}/images").json()}
        rows = client.get(f"/api/sessions/{sid}/detections").json()
        recon = client.get(f"/api/sessions/{sid}/reconciliation").json()
        trace = client.get(f"/api/sessions/{sid}/trace").json()
        report = client.get(f"/api/sessions/{sid}/report?format=json").json()

    per_detection, auto, auto_correct, wrong_auto, review, cand_hit, labelled, usable_labelled = [], 0, 0, 0, 0, 0, 0, 0
    bounds_exact = 0
    for row in rows:
        det, dec, ev = row["detection"], row["decision"], row["evidence"]
        gt = truth[(images[det["image_id"]]["sha256"], det["object_index"])]
        bounds_exact += det["mask"]["bounds"] == gt["bounds"]
        true_id = gt["true_asset_id"]
        is_auto = dec["decision"] == "VERIFIED"
        auto += is_auto
        if is_auto and dec["matched_asset_id"] == true_id:
            auto_correct += 1
        elif is_auto:
            wrong_auto += 1
        review += dec["review_required"]
        if true_id:
            labelled += 1
            if ev and ev["status"] == "ok":
                usable_labelled += 1
            if true_id in dec["candidate_asset_ids"]:
                cand_hit += 1
        per_detection.append({"case": gt["case"], "true_asset_id": true_id, "decision": dec["decision"],
                              "rule": dec["matching_rule"], "candidates": dec["candidate_asset_ids"],
                              "review_required": dec["review_required"], "evidence_status": ev["status"] if ev else None})

    unregistered = [p for p in per_detection if p["true_asset_id"] is None]
    expected = manifest["expected_asset_status"]
    actual = {a["asset_id"]: a["status"] for a in recon["assets"]}
    status_hits = sum(actual.get(k) == v for k, v in expected.items())
    prov_fields = 0
    for d in report["decisions"]:
        complete = bool(d["image"]["sha256"] and d["detection"]["bounds"] and d["detection"]["provider_call_id"]
                        and d["evidence"]["provider_call_id"] and d["evidence_ids"])
        if d["evidence"]["status"] == "ok":
            complete = complete and bool(d["evidence"]["fields"]["evidence_references"])
        prov_fields += complete
    extract_calls = [c for c in trace["provider_calls"] if c["operation"] == "extract"]
    invalid_cases = {"malformed_provider_response", "unsupported_model_conclusion"}
    invalid_expected = sum(1 for p in per_detection if p["case"] in invalid_cases)
    invalid_caught = sum(1 for p in per_detection if p["case"] in invalid_cases and p["evidence_status"] == "invalid")
    timeouts = sum(1 for p in per_detection if p["case"] == "provider_timeout" and p["evidence_status"] == "error")

    results = {
        "mode": "FIXTURE (demo) - measures engine/validation/provenance, NOT model quality",
        "dataset": {"images": len(manifest["images"]), "detections": len(rows), "ledger_assets": len(expected),
                    "license": manifest["license"]},
        "runs": [{"concept": r["concept"], "status": r["status"], "detections": r["detections"]} for r in runs],
        "metrics": {
            "auto_match_count": auto,
            "auto_match_precision": ratio(auto_correct, auto),
            "false_automatic_match_rate": ratio(wrong_auto, len(rows)),
            "candidate_recall_all_labelled": ratio(cand_hit, labelled),
            "candidate_recall_usable_evidence": ratio(cand_hit, usable_labelled),
            "human_review_rate": ratio(review, len(rows)),
            "unregistered_objects_flagged": f"{sum(p['decision'] == 'NOT_IN_REGISTER' for p in unregistered)}/{len(unregistered)}",
            "asset_status_agreement_with_labels": f"{status_hits}/{len(expected)}",
            "provenance_completeness": ratio(prov_fields, len(report["decisions"])),
            "schema_valid_extractions": f"{sum(c['status'] == 'ok' for c in extract_calls)}/{len(extract_calls)}",
            "invalid_outputs_rejected": f"{invalid_caught}/{invalid_expected}",
            "timeouts_recovered_as_unusable": f"{timeouts}/1",
            "fixture_mask_bounds_exact": f"{bounds_exact}/{len(rows)} (identity check of the overlay path, not SAM IoU)",
            "end_to_end_runs_completed": f"{sum(r['status'] in {'succeeded', 'partial'} for r in runs)}/{len(runs)}",
            "latency_ms_fixture": trace["latency"],
            "estimated_cost_usd": trace["total_estimated_cost_usd"],
        },
        "not_measured": [
            "SAM 3.1 segmentation quality (no live calls; needs MODEL_API_KEY + spend approval)",
            "Muse Spark extraction accuracy on real nameplates",
            "Live latency and actual billed cost",
        ],
        "per_detection": per_detection,
    }
    out = ROOT / "eval" / "results" / "fixture-eval.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2))
    print(json.dumps(results["metrics"], indent=2))
    return results


if __name__ == "__main__":
    main()
