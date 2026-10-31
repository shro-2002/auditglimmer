"""Regression tests for defects found by the blind hackathon judge (docs/judge-review-initial.md, J-01..J-16)."""

from __future__ import annotations

import io

from fastapi.testclient import TestClient
from PIL import Image

from app.main import create_app
from app.reconcile import canonical_type

from .conftest import FIXTURES, make_settings, wait_run

NOTE = "Tag photographed on site; matches register entry."


def _recon(client: TestClient, sid: str) -> dict:
    return client.get(f"/api/sessions/{sid}/reconciliation").json()


def _weak_decision(recon: dict) -> dict:
    return next(d for d in recon["decisions"] if d["decision"] == "WEAK")


def test_j01_human_confirm_gets_its_own_status_not_verified(client: TestClient, demo_session: str) -> None:
    recon = _recon(client, demo_session)
    verified_before = recon["summary"]["by_status"]["VERIFIED"]
    weak = _weak_decision(recon)
    before = {a["asset_id"]: a["status"] for a in recon["assets"]}
    target = next(c for c in weak["candidate_asset_ids"] if before[c] != "MISMATCHED")  # no contrary evidence (V-01)
    r = client.post(f"/api/decisions/{weak['id']}/review",
                    json={"action": "confirm", "asset_id": target, "reviewer": "J. Auditor", "note": NOTE})
    assert r.status_code == 200
    after = _recon(client, demo_session)
    asset = next(a for a in after["assets"] if a["asset_id"] == target)
    assert asset["status"] == "HUMAN_CONFIRMED" and asset["human_confirmed"]
    assert after["summary"]["by_status"]["VERIFIED"] == verified_before
    assert after["summary"]["by_status"]["HUMAN_CONFIRMED"] == 1


def test_j01_confirm_requires_note_and_real_reviewer_name(client: TestClient, demo_session: str) -> None:
    weak = _weak_decision(_recon(client, demo_session))
    target = weak["candidate_asset_ids"][0]
    no_note = client.post(f"/api/decisions/{weak['id']}/review",
                          json={"action": "confirm", "asset_id": target, "reviewer": "J. Auditor"})
    assert no_note.status_code == 400 and "note" in no_note.json()["error"]["message"]
    short_name = client.post(f"/api/decisions/{weak['id']}/review",
                             json={"action": "confirm", "asset_id": target, "reviewer": "x", "note": NOTE})
    assert short_name.status_code == 422


def test_j02_conflicting_reviews_are_flagged_and_kept_in_history(client: TestClient, demo_session: str) -> None:
    weak = _weak_decision(_recon(client, demo_session))
    target = weak["candidate_asset_ids"][0]
    client.post(f"/api/decisions/{weak['id']}/review",
                json={"action": "confirm", "asset_id": target, "reviewer": "Judge One", "note": NOTE})
    client.post(f"/api/decisions/{weak['id']}/review",
                json={"action": "reject", "reviewer": "Judge Three", "note": "not convinced"})
    dec = next(d for d in _recon(client, demo_session)["decisions"] if d["id"] == weak["id"])
    assert [h["reviewer"] for h in dec["review_history"]] == ["Judge One", "Judge Three"]
    assert "CONFLICTING_REVIEWS" in dec["flags"]
    report = client.get(f"/api/sessions/{demo_session}/report", params={"format": "html"}).text
    assert "Judge One" in report and "Judge Three" in report and "CONFLICTING_REVIEWS" in report


def test_j03_second_run_while_one_is_active_is_rejected(tmp_path) -> None:  # noqa: ANN001
    client = TestClient(create_app(make_settings(tmp_path)))
    sid = client.post("/api/sessions", json={"name": "x", "facility_id": "WH-01"}).json()["id"]
    client.post(f"/api/sessions/{sid}/demo")
    app = client.app
    app.state.pipeline.start = lambda run_id: None  # keep the first run queued
    first = client.post(f"/api/sessions/{sid}/runs", json={"concept": "forklift"})
    second = client.post(f"/api/sessions/{sid}/runs", json={"concept": "forklift"})
    assert first.status_code == 202
    assert second.status_code == 409 and second.json()["error"]["code"] == "RUN_IN_PROGRESS"


def test_j04_non_finite_ledger_values_are_flagged(client: TestClient) -> None:
    sid = client.post("/api/sessions", json={"name": "x", "facility_id": "WH-01"}).json()["id"]
    csv = ("asset_id,asset_type,facility_id,ledger_value\n"
           "Z-1,Forklift,WH-01,1e309\nZ-2,Forklift,WH-01,NaN\nZ-3,Forklift,WH-01,-500\n")
    body = client.post(f"/api/sessions/{sid}/ledger", files={"file": ("l.csv", csv, "text/csv")}).json()
    codes = {(i["row"], i["code"]) for i in body["issues"]}
    assert (1, "INVALID_NUMBER") in codes and (2, "INVALID_NUMBER") in codes
    assert (3, "FORMULA_NEUTRALIZED") not in codes  # J-13: a negative number is a number, not a formula
    assert {r["asset_id"]: r["ledger_value"] for r in body["records"]}["Z-3"] == -500


def test_j05_viewing_report_does_not_mark_session_reported(client: TestClient, demo_session: str) -> None:
    for fmt in ("json", "html", "csv"):
        client.get(f"/api/sessions/{demo_session}/report", params={"format": fmt})
    assert client.get(f"/api/sessions/{demo_session}").json()["status"] != "reported"
    draft = client.get(f"/api/sessions/{demo_session}/report").json()
    assert draft["report_state"] == "DRAFT" and draft["open_reviews"] > 0
    client.get(f"/api/sessions/{demo_session}/report", params={"format": "html", "download": "true"})
    assert client.get(f"/api/sessions/{demo_session}").json()["status"] != "reported"  # open reviews block final


def test_j06_two_objects_competing_for_one_asset_are_flagged(tmp_path) -> None:  # noqa: ANN001
    client = TestClient(create_app(make_settings(tmp_path)))
    sid = client.post("/api/sessions", json={"name": "x", "facility_id": "WH-01"}).json()["id"]
    client.post(f"/api/sessions/{sid}/demo")
    # keep only one Liftmaster LM-25 row and drop its serial so both lookalikes compete for it
    rows = (FIXTURES / "ledger.csv").read_text().splitlines()
    header = rows[0].split(",")
    serial_col = header.index("serial_number")
    kept = [rows[0]]
    seen_lm25 = False
    for line in rows[1:]:
        cells = line.split(",")
        if "LM-25" in line:
            if seen_lm25:
                continue
            seen_lm25 = True
            cells[serial_col] = ""
        kept.append(",".join(cells))
    client.post(f"/api/sessions/{sid}/ledger", files={"file": ("l.csv", "\n".join(kept) + "\n", "text/csv")})
    wait_run(client, client.post(f"/api/sessions/{sid}/runs", json={"concept": "forklift"}).json()["id"])
    recon = _recon(client, sid)
    competing = [d for d in recon["decisions"] if "COMPETING_FOR_ASSET" in d["flags"]]
    assert len(competing) >= 2


def test_j10_facility_mismatch_warned_at_upload(client: TestClient) -> None:
    sid = client.post("/api/sessions", json={"name": "x", "facility_id": "WH-01"}).json()["id"]
    csv = "asset_id,asset_type,facility_id\nZ-1,Forklift,WH-01\nZ-2,Forklift,WH-02\n"
    body = client.post(f"/api/sessions/{sid}/ledger", files={"file": ("l.csv", csv, "text/csv")}).json()
    assert any(i["code"] == "FACILITY_MISMATCH" and i["row"] == 2 for i in body["issues"])


def test_j12_concept_is_canonicalised_before_reaching_the_model(client: TestClient) -> None:
    assert canonical_type("forklifts") == "forklift"
    sid = client.post("/api/sessions", json={"name": "x", "facility_id": "WH-01"}).json()["id"]
    client.post(f"/api/sessions/{sid}/demo")
    run = client.post(f"/api/sessions/{sid}/runs", json={"concept": "generator worth $1M owned by borrower"}).json()
    assert run["concept"] == "generator"
    wait_run(client, run["id"])
    unknown = client.post(f"/api/sessions/{sid}/runs", json={"concept": "golden retriever"})
    assert unknown.status_code == 400


def test_j13_oversized_image_gets_accurate_message(client: TestClient) -> None:
    sid = client.post("/api/sessions", json={"name": "x", "facility_id": "WH-01"}).json()["id"]
    Image.MAX_IMAGE_PIXELS, saved = 1000, Image.MAX_IMAGE_PIXELS
    try:
        buf = io.BytesIO()
        Image.new("RGB", (100, 100)).save(buf, "PNG")
        r = client.post(f"/api/sessions/{sid}/images", files={"files": ("big.png", buf.getvalue(), "image/png")})
    finally:
        Image.MAX_IMAGE_PIXELS = saved
    assert r.status_code == 413 and "pixel" in r.json()["error"]["message"]


def test_j16_access_code_gate_when_configured(tmp_path) -> None:  # noqa: ANN001
    code = "judge-demo-access-code-0123456789"
    client = TestClient(create_app(make_settings(tmp_path, access_code=code)))
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/sessions").status_code == 401
    assert client.get("/api/sessions", headers={"X-Access-Code": "wrong"}).status_code == 401
    assert client.get("/api/sessions", headers={"X-Access-Code": code}).status_code == 200
    assert client.get("/api/sessions", params={"access_code": code}).status_code == 401  # query only where needed
    assert client.get("/api/runs/run_nope/events", params={"access_code": code}).status_code == 404  # passed gate


def test_j05_download_finalizes_only_when_every_decision_is_reviewed(client: TestClient, demo_session: str) -> None:
    for d in _recon(client, demo_session)["decisions"]:
        if d["review_required"] and d["review"] is None and d["decision"] != "EVIDENCE_UNUSABLE":
            client.post(f"/api/decisions/{d['id']}/review",
                        json={"action": "reject", "reviewer": "J. Auditor", "note": "insufficient evidence"})
    report = client.get(f"/api/sessions/{demo_session}/report", params={"format": "html", "download": "true"})
    assert "<b>FINAL</b>" in report.text
    assert client.get(f"/api/sessions/{demo_session}").json()["status"] == "reported"


# ---------- ROLE C verifier findings (V-01..V-05) ----------

def test_v01_human_confirm_does_not_hide_open_contrary_evidence(client: TestClient, demo_session: str) -> None:
    recon = _recon(client, demo_session)
    pairs = [(c, a, o) for c in recon["decisions"] if c["decision"] == "MISMATCHED"
             for a in c["candidate_asset_ids"] for o in recon["decisions"]
             if o["id"] != c["id"] and a in o["candidate_asset_ids"] and o["decision"] != "EVIDENCE_UNUSABLE"]
    contrary, target, other = sorted(pairs, key=lambda t: (t[1], t[0]["id"], t[2]["id"]))[0]
    r = client.post(f"/api/decisions/{other['id']}/review",
                    json={"action": "confirm", "asset_id": target, "reviewer": "J. Auditor", "note": NOTE})
    assert r.status_code == 200
    asset = next(a for a in _recon(client, demo_session)["assets"] if a["asset_id"] == target)
    assert asset["status"] == "MISMATCHED" and asset["human_confirmed"] and contrary["id"] in asset["reason"]


def test_v02_conflict_clears_when_reviewers_converge(client: TestClient, demo_session: str) -> None:
    weak = _weak_decision(_recon(client, demo_session))
    target = weak["candidate_asset_ids"][0]
    url = f"/api/decisions/{weak['id']}/review"
    client.post(url, json={"action": "confirm", "asset_id": target, "reviewer": "Judge One", "note": NOTE})
    client.post(url, json={"action": "reject", "reviewer": "Judge Three", "note": "not convinced"})
    client.post(url, json={"action": "reject", "reviewer": "Judge One", "note": "agree after second look"})
    dec = next(d for d in _recon(client, demo_session)["decisions"] if d["id"] == weak["id"])
    assert "CONFLICTING_REVIEWS" not in dec["flags"] and len(dec["review_history"]) == 3


def test_v03_concurrent_run_posts_create_one_run(tmp_path) -> None:  # noqa: ANN001
    from concurrent.futures import ThreadPoolExecutor

    client = TestClient(create_app(make_settings(tmp_path)))
    sid = client.post("/api/sessions", json={"name": "x", "facility_id": "WH-01"}).json()["id"]
    client.post(f"/api/sessions/{sid}/demo")
    client.app.state.pipeline.start = lambda run_id: None  # keep runs queued
    with ThreadPoolExecutor(max_workers=10) as pool:
        codes = list(pool.map(lambda _: client.post(f"/api/sessions/{sid}/runs", json={"concept": "forklift"})
                              .status_code, range(10)))
    assert codes.count(202) == 1 and codes.count(409) == 9


def test_v05_negative_infinity_is_not_called_a_formula(client: TestClient) -> None:
    sid = client.post("/api/sessions", json={"name": "x", "facility_id": "WH-01"}).json()["id"]
    csv = "asset_id,asset_type,facility_id,ledger_value\nZ-1,Forklift,WH-01,-inf\nZ-2,Forklift,WH-01,-1e309\n"
    body = client.post(f"/api/sessions/{sid}/ledger", files={"file": ("l.csv", csv, "text/csv")}).json()
    codes = {(i["row"], i["code"]) for i in body["issues"]}
    assert (1, "INVALID_NUMBER") in codes and (2, "INVALID_NUMBER") in codes
    assert not any(c == "FORMULA_NEUTRALIZED" for _, c in codes)


# ---------- final-judge finding N-01 (fixed after final judging; not re-judged) ----------

def _confirm_one(client: TestClient, sid: str) -> None:
    recon = _recon(client, sid)
    before = {a["asset_id"]: a["status"] for a in recon["assets"]}
    weak = _weak_decision(recon)
    target = next(c for c in weak["candidate_asset_ids"] if before[c] != "MISMATCHED")
    assert client.post(f"/api/decisions/{weak['id']}/review",
                       json={"action": "confirm", "asset_id": target, "reviewer": "J. Auditor", "note": NOTE}
                       ).status_code == 200


def test_n01_all_rejected_ledger_changes_nothing(client: TestClient, demo_session: str) -> None:
    _confirm_one(client, demo_session)
    bad = "asset_id,asset_type,facility_id\n,Forklift,WH-01\n"
    r = client.post(f"/api/sessions/{demo_session}/ledger", files={"file": ("l.csv", bad, "text/csv")})
    assert r.status_code == 400 and r.json()["error"]["code"] == "LEDGER_EMPTY"
    assert _recon(client, demo_session)["summary"]["by_status"]["HUMAN_CONFIRMED"] == 1


def test_n01_replacing_ledger_with_reviews_requires_explicit_replace_and_archives(client: TestClient,
                                                                                demo_session: str) -> None:
    _confirm_one(client, demo_session)
    data = (FIXTURES / "ledger.csv").read_bytes()
    url = f"/api/sessions/{demo_session}/ledger"
    r = client.post(url, files={"file": ("l.csv", data, "text/csv")})
    assert r.status_code == 409 and r.json()["error"]["code"] == "LEDGER_HAS_REVIEWS"
    assert _recon(client, demo_session)["summary"]["by_status"]["HUMAN_CONFIRMED"] == 1
    assert client.post(f"/api/sessions/{demo_session}/demo").status_code == 409  # demo reload guarded too
    ok = client.post(url, params={"replace": "true"}, files={"file": ("l.csv", data, "text/csv")})
    assert ok.status_code == 200 and ok.json()["archived_reviews"] == 1
    archive = client.app.state.settings.data_dir / "sessions" / demo_session / "review-archive"
    assert len(list(archive.glob("*.json"))) == 1 and "J. Auditor" in next(archive.glob("*.json")).read_text()


# ---------- full-frame region (close-up nameplates; Muse study) ----------

def test_full_frame_run_skips_sam_and_extracts_whole_image(tmp_path) -> None:  # noqa: ANN001
    client = TestClient(create_app(make_settings(tmp_path)))
    sid = client.post("/api/sessions", json={"name": "x", "facility_id": "WH-01"}).json()["id"]
    client.post(f"/api/sessions/{sid}/demo")
    img = client.get(f"/api/sessions/{sid}/images").json()[0]
    run = client.post(f"/api/sessions/{sid}/runs",
                      json={"concept": "generator", "image_ids": [img["id"]], "region": "full_frame"}).json()
    wait_run(client, run["id"])
    trace = client.get(f"/api/sessions/{sid}/trace").json()
    assert not [c for c in trace["provider_calls"] if c["run_id"] == run["id"] and c["operation"] == "segment"]
    dets = [d for d in client.get(f"/api/sessions/{sid}/detections").json()
            if d["detection"]["provider"] == "full-frame"]
    assert len(dets) == 1 and dets[0]["detection"]["mask"]["bounds"] == [0, 0, img["width"], img["height"]]
    assert any("SAM not called" in e["message"] for e in trace["events"])


def test_n03_test_sessions_do_not_push_real_sessions_off_overview(client: TestClient) -> None:
    real = client.post("/api/sessions", json={"name": "Lender audit", "facility_id": "WH-01"}).json()["id"]
    for i in range(10):
        client.post("/api/sessions", json={"name": f"e2e run {i}", "facility_id": "WH-01"})
    overview = client.get("/api/overview").json()
    assert real in [s["id"] for s in overview["recent_sessions"]]
    assert overview["live_evidence_sessions"] == []  # DEMO-only database has no live evidence
