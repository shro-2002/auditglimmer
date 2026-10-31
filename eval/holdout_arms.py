"""Post-hoc 3-arm comparison on the STORED holdout evidence (no model calls; not pre-registered).

  arm 1  rules without Muse identifiers  (evidence = declared asset type only)
  arm 2  rules + Muse single read        (rule engine exactly as frozen at c7d6206, before the gate)
  arm 3  rules + Muse + two-read gate     (current engine, stored second reads, whole-photo regions)

Same photos, same register, same ground truth and the same Muse outputs for arms 2 and 3, so differences come
from the rules only. Needs the API (DEMO is fine) to serve session ses_63033bcece24.

  uv run --project backend python eval/holdout_arms.py     # writes eval/results/holdout-arms.json
"""

from __future__ import annotations

import csv
import json
import statistics
import subprocess
import sys
import types
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "eval"))
from app import reconcile as current  # noqa: E402
from app.schemas import ModelEvidence  # noqa: E402
from holdout_study import FACILITY, GT_PATH, LEDGER_PATH  # noqa: E402
from muse_study import MIN_SERIAL_LEN, norm, wilson  # noqa: E402

API = "http://127.0.0.1:8000"
SESSION = (ROOT / "eval" / "results" / "holdout-study-session.txt").read_text().strip()
OUT = ROOT / "eval" / "results" / "holdout-arms.json"
BASE_COMMIT = "c7d6206"


def load_engine_at(commit: str) -> types.ModuleType:
    """The rule engine exactly as committed at `commit`, imported beside the current package."""
    source = subprocess.run(["git", "show", f"{commit}:backend/app/reconcile.py"], cwd=ROOT,
                            capture_output=True, text=True, check=True).stdout
    module = types.ModuleType(f"app.reconcile_{commit}")
    module.__package__ = "app"
    sys.modules[module.__name__] = module
    exec(compile(source, f"reconcile@{commit}", "exec"), module.__dict__)  # noqa: S102 - our own committed code
    return module


def load_assets(engine: types.ModuleType) -> list:
    with LEDGER_PATH.open() as f:
        return [engine.LedgerAsset(f"l-{r['asset_id']}", r["asset_id"], r["asset_type"], r["manufacturer"] or None,
                                   r["model"] or None, r["serial_number"] or None, r["facility_id"])
                for r in csv.DictReader(f)]


def outcome(hid: str, dec) -> str:  # noqa: ANN001
    true = f"T-{hid}"
    if dec.decision == "VERIFIED":
        return "correct" if dec.matched_asset_id == true else "unsafe"
    if len(dec.candidate_asset_ids) == 1:
        return "suggest_correct" if dec.candidate_asset_ids == [true] else "suggest_wrong"
    return "abstained"


def run_arm(engine, observations, hid_of) -> dict:  # noqa: ANN001
    decisions, _ = engine.reconcile(load_assets(engine), observations, [], {(FACILITY, o.concept) for o in observations})
    return {hid_of[d.evidence_id]: (d, outcome(hid_of[d.evidence_id], d)) for d in decisions}


def main() -> None:
    gt = json.loads(GT_PATH.read_text())["items"]
    old = load_engine_at(BASE_COMMIT)
    with httpx.Client(base_url=API, timeout=60) as c:
        names = {i["id"]: Path(i["filename"]).stem for i in c.get(f"/api/sessions/{SESSION}/images").json()}
        rows = c.get(f"/api/sessions/{SESSION}/detections").json()
        calls = {x["id"]: x for x in c.get(f"/api/sessions/{SESSION}/trace").json()["provider_calls"]}
    arms: dict[str, list] = {"1_no_muse": [], "2_muse_single_read": [], "3_muse_two_read_gate": []}
    hid_of, cost, latency = {}, {"2": [], "3": []}, {"2": [], "3": []}
    for r in rows:
        rec, det = r["evidence"], r["detection"]
        ev_id, hid = rec["id"], names[det["image_id"]]
        hid_of[ev_id] = hid
        first = ModelEvidence.model_validate({k: v for k, v in rec["evidence"].items() if k != "evidence_references"})
        conf = rec.get("confirmation")
        second = current.Confirmation(conf["status"], ModelEvidence.model_validate(conf["evidence"])
                                      if conf.get("evidence") else None, conf.get("error")) if conf else None
        args = (ev_id, det["id"], det["image_id"], FACILITY, det["concept"], "ok")
        arms["1_no_muse"].append(current.Observation(*args, ModelEvidence(observed_object_type=det["concept"]),
                                                     whole_photo=True))
        arms["2_muse_single_read"].append(old.Observation(*args, first))
        arms["3_muse_two_read_gate"].append(current.Observation(*args, first, None, second, whole_photo=True))
        first_call, second_call = calls[rec["provider_call_id"]], calls.get((conf or {}).get("provider_call_id"))
        cost["2"].append(first_call["estimated_cost_usd"])
        latency["2"].append(first_call["latency_ms"])
        cost["3"].append(first_call["estimated_cost_usd"] + (second_call or {}).get("estimated_cost_usd", 0.0))
        latency["3"].append(first_call["latency_ms"] + (second_call or {}).get("latency_ms", 0.0))
    engines = {"1_no_muse": current, "2_muse_single_read": old, "3_muse_two_read_gate": current}
    verifiable = [h for h, i in gt.items() if i["status"] == "positive" and len(norm(i["serial"]) or "") >= MIN_SERIAL_LEN]
    result = {"session_id": SESSION, "post_hoc": True, "arm2_engine_commit": BASE_COMMIT,
              "note": "Post-hoc analysis of stored outputs; not pre-registered. Arms differ only in rules.", "arms": {}}
    for name, observations in arms.items():
        res = run_arm(engines[name], observations, hid_of)
        count = lambda kind, ids=None: sum(1 for h, (_, o) in res.items() if o == kind and (ids is None or h in ids))  # noqa: E731
        key = name[0]
        result["arms"][name] = {
            "correct_verifications": {"k": count("correct"), "n": len(verifiable),
                                      "wilson95": wilson(count("correct"), len(verifiable))},
            "unsafe_verifications": {"k": count("unsafe"), "ids": sorted(h for h, (_, o) in res.items() if o == "unsafe"),
                                     "wilson95": wilson(count("unsafe"), len(res))},
            "correct_single_suggestions": count("suggest_correct", verifiable),
            "abstentions_on_verifiable": count("abstained", verifiable),
            "decisions": {k: sum(d.decision == k for d, _ in res.values()) for k in sorted({d.decision for d, _ in res.values()})},
            "muse_calls": {"1": 0, "2": len(cost["2"]), "3": len(cost["2"]) + sum(1 for r in rows if (r["evidence"].get("confirmation") or {}).get("provider_call_id"))}[key],
            "cost_usd": 0.0 if key == "1" else round(sum(cost[key]), 6),
            "latency_ms_median_per_inspection": 0.0 if key == "1" else round(statistics.median(latency[key]), 1),
            "per_item": {h: {"decision": d.decision, "rule": d.matching_rule, "outcome": o} for h, (d, o) in sorted(res.items())},
        }
    OUT.write_text(json.dumps(result, indent=2))
    for name, a in result["arms"].items():
        print(f"{name:22s} correct {a['correct_verifications']['k']}/{len(verifiable)} unsafe {a['unsafe_verifications']['k']} "
              f"{a['unsafe_verifications']['ids']} suggest {a['correct_single_suggestions']} abstain {a['abstentions_on_verifiable']} "
              f"calls {a['muse_calls']} ${a['cost_usd']} p50 {a['latency_ms_median_per_inspection']} ms")


if __name__ == "__main__":
    main()
