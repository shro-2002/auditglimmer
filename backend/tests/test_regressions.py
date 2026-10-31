"""Regression tests for defects found by the independent adversarial review (D5)."""

from __future__ import annotations

import io
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.db import Database, RunRow, new_id
from app.errors import ProviderError
from app.main import create_app
from app.pipeline import make_crop
from app.providers.base import ImageInput
from app.providers.sam_meta import parse_sam_output
from app.reconcile import LedgerAsset, Observation, Review, reconcile
from app.schemas import ModelEvidence

from .conftest import FIXTURES, make_settings, wait_run
from .test_providers import DOC_SAM_LINE


def _statuses(client: TestClient, sid: str) -> dict:
    return {a["asset_id"]: a for a in client.get(f"/api/sessions/{sid}/reconciliation").json()["assets"]}


def test_concurrent_confirms_cannot_assign_one_asset_twice(client: TestClient, demo_session: str) -> None:
    recon = client.get(f"/api/sessions/{demo_session}/reconciliation").json()
    targets = [d["id"] for d in recon["decisions"] if "A-011" in d["candidate_asset_ids"]]
    assert len(targets) >= 3

    def confirm(did: str) -> int:
        return client.post(f"/api/decisions/{did}/review",
                           json={"action": "confirm", "asset_id": "A-011", "reviewer": "R. Reviewer", "note": "tag read on site matches register"}).status_code

    with ThreadPoolExecutor(max_workers=len(targets)) as pool:
        codes = sorted(pool.map(confirm, targets))
    assert codes.count(200) == 1 and codes.count(409) == len(targets) - 1


def test_rerun_on_subset_keeps_other_images_evidence_and_reviews(client: TestClient, demo_session: str) -> None:
    recon = client.get(f"/api/sessions/{demo_session}/reconciliation").json()
    a002 = next(d for d in recon["decisions"] if d["candidate_asset_ids"] == ["A-002"])
    client.post(f"/api/decisions/{a002['id']}/review", json={"action": "confirm", "asset_id": "A-002", "reviewer": "R. Reviewer", "note": "tag read on site matches register"})
    images = {i["filename"]: i["id"] for i in client.get(f"/api/sessions/{demo_session}/images").json()}
    run = client.post(f"/api/sessions/{demo_session}/runs",
                      json={"concept": "Diesel Generator", "image_ids": [images["bay_b_forklifts.png"]]}).json()
    wait_run(client, run["id"])
    st = _statuses(client, demo_session)
    assert st["A-001"]["status"] == "VERIFIED" and st["A-004"]["status"] == "VERIFIED"
    assert st["A-002"]["status"] == "HUMAN_CONFIRMED" and st["A-002"]["human_confirmed"]


def test_auto_verified_asset_cannot_be_confirmed_to_another_object(tmp_path) -> None:  # noqa: ANN001
    client = TestClient(create_app(make_settings(tmp_path)))
    sid = client.post("/api/sessions", json={"name": "x", "facility_id": "WH-01"}).json()["id"]
    client.post(f"/api/sessions/{sid}/demo")
    ledger = (FIXTURES / "ledger.csv").read_text().replace("A-010,Forklift,Liftmaster", "A-010,Forklift,Hoistline")
    client.post(f"/api/sessions/{sid}/ledger", files={"file": ("l.csv", ledger.encode(), "text/csv")})
    wait_run(client, client.post(f"/api/sessions/{sid}/runs", json={"concept": "forklift"}).json()["id"])
    decisions = client.get(f"/api/sessions/{sid}/reconciliation").json()["decisions"]
    assert any(d["matched_asset_id"] == "A-010" for d in decisions)  # F1 now auto-verified
    weak = next(d for d in decisions if d["decision"] == "WEAK" and "A-010" in d["candidate_asset_ids"])
    r = client.post(f"/api/decisions/{weak['id']}/review", json={"action": "confirm", "asset_id": "A-010", "reviewer": "R. Reviewer", "note": "tag read on site matches register"})
    assert r.status_code == 409


def test_same_serial_observations_may_share_an_asset(client: TestClient, demo_session: str) -> None:
    decisions = client.get(f"/api/sessions/{demo_session}/reconciliation").json()["decisions"]
    dup = [d for d in decisions if "DUPLICATE_IDENTIFIER_OBSERVATION" in d["flags"]]
    assert len(dup) == 2
    for d in dup:
        r = client.post(f"/api/decisions/{d['id']}/review", json={"action": "confirm", "asset_id": "A-007", "reviewer": "R. Reviewer", "note": "tag read on site matches register"})
        assert r.status_code == 200


def test_bad_mask_bounds_are_clamped_or_rejected() -> None:
    img = ImageInput(b"", "image/png", 100, 100, "x")
    with pytest.raises(ProviderError):
        make_crop(img, (50, 50, 40, 60))
    with pytest.raises(ProviderError):
        make_crop(img, (200, 200, 300, 300))
    objs = parse_sam_output(DOC_SAM_LINE, width=230, height=334)
    assert objs[0].mask.bounds[2] == 230  # clamped
    assert len(parse_sam_output(DOC_SAM_LINE, width=150, height=334)) == 0  # both boxes fully outside


def test_unexpected_extraction_crash_isolated_to_one_detection(tmp_path) -> None:  # noqa: ANN001
    app = create_app(make_settings(tmp_path))
    client = TestClient(app)
    original = app.state.pipeline.ext.extract_visual_evidence

    def flaky(crop, context):  # noqa: ANN001, ANN202
        if context.object_index == 1:
            raise RuntimeError("boom")
        return original(crop, context)

    app.state.pipeline.ext.extract_visual_evidence = flaky
    sid = client.post("/api/sessions", json={"name": "x", "facility_id": "WH-01"}).json()["id"]
    client.post(f"/api/sessions/{sid}/demo")
    run = wait_run(client, client.post(f"/api/sessions/{sid}/runs", json={"concept": "generator"}).json()["id"])
    assert run["status"] == "partial" and run["detections"] == 10
    assert len(client.get(f"/api/sessions/{sid}/detections").json()) == 10


def test_explain_is_traced(client: TestClient, demo_session: str) -> None:
    did = client.get(f"/api/sessions/{demo_session}/reconciliation").json()["decisions"][0]["id"]
    assert client.post(f"/api/decisions/{did}/explain").status_code == 200
    ops = [c["operation"] for c in client.get(f"/api/sessions/{demo_session}/trace").json()["provider_calls"]]
    assert "explain" in ops


def test_failed_segmentation_does_not_count_as_inspected(client: TestClient) -> None:
    sid = client.post("/api/sessions", json={"name": "x", "facility_id": "WH-02"}).json()["id"]
    csv_text = "asset_id,asset_type,facility_id,serial_number\nB-1,Generator,WH-02,GN-1234\n"
    client.post(f"/api/sessions/{sid}/ledger", files={"file": ("l.csv", csv_text.encode(), "text/csv")})
    buf = io.BytesIO()
    Image.new("RGB", (32, 32)).save(buf, format="PNG")
    client.post(f"/api/sessions/{sid}/images", files={"files": ("p.png", buf.getvalue(), "image/png")})
    wait_run(client, client.post(f"/api/sessions/{sid}/runs", json={"concept": "generator"}).json()["id"])
    assert _statuses(client, sid)["B-1"]["status"] == "NOT_OBSERVABLE"


def test_interrupted_runs_reset_on_startup_and_queue_is_capped(tmp_path) -> None:  # noqa: ANN001
    settings = make_settings(tmp_path)
    client = TestClient(create_app(settings))
    sid = client.post("/api/sessions", json={"name": "x", "facility_id": "WH-01"}).json()["id"]
    client.post(f"/api/sessions/{sid}/demo")
    other = client.post("/api/sessions", json={"name": "y", "facility_id": "WH-01"}).json()["id"]
    db = Database(settings.database_url)
    with db.session() as s:
        for _ in range(4):  # global cap: queued runs in another session still count
            s.add(RunRow(id=new_id("run"), session_id=other, concept="x", status="queued", image_ids=[], mode="demo",
                         correlation_id="t"))
    r = client.post(f"/api/sessions/{sid}/runs", json={"concept": "forklift"})
    assert r.status_code == 429
    restarted = TestClient(create_app(settings))
    runs = restarted.get(f"/api/sessions/{other}/trace").json()["runs"]
    assert runs and all(x["status"] == "failed" and "interrupted" in x["error"] for x in runs)


def test_malformed_csv_is_400_not_500(client: TestClient) -> None:
    sid = client.post("/api/sessions", json={"name": "x", "facility_id": "WH-01"}).json()["id"]
    body = "asset_id,asset_type,facility_id\nA,Gen," + "x" * 140_000 + "\n"
    r = client.post(f"/api/sessions/{sid}/ledger", files={"file": ("l.csv", body.encode(), "text/csv")})
    assert r.status_code == 400 and "malformed CSV" in r.json()["error"]["message"]


def test_500_keeps_correlation_id(tmp_path, monkeypatch) -> None:  # noqa: ANN001
    import app.main as main_module

    def boom(*_a, **_k):  # noqa: ANN002, ANN003, ANN202
        raise RuntimeError("secret internal detail")

    monkeypatch.setattr(main_module, "build_overview", boom)
    client = TestClient(create_app(make_settings(tmp_path)), raise_server_exceptions=False)
    r = client.get("/api/overview", headers={"x-correlation-id": "trace-me-123"})
    assert r.status_code == 500 and r.headers["x-correlation-id"] == "trace-me-123"
    assert r.json()["error"]["correlation_id"] == "trace-me-123" and "secret" not in r.text


def test_ledger_reupload_voids_reviews(client: TestClient, demo_session: str) -> None:
    decisions = client.get(f"/api/sessions/{demo_session}/reconciliation").json()["decisions"]
    a002 = next(d for d in decisions if d["candidate_asset_ids"] == ["A-002"])
    client.post(f"/api/decisions/{a002['id']}/review", json={"action": "confirm", "asset_id": "A-002", "reviewer": "R. Reviewer", "note": "tag read on site matches register"})
    client.post(f"/api/sessions/{demo_session}/ledger", params={"replace": "true"},  # explicit replace (N-01)
                files={"file": ("l.csv", (FIXTURES / "ledger.csv").read_bytes(), "text/csv")})
    st = _statuses(client, demo_session)
    assert st["A-002"]["status"] == "PROBABLE" and not st["A-002"]["human_confirmed"]


def test_json_report_preview_does_not_mark_reported(client: TestClient, demo_session: str) -> None:
    client.get(f"/api/sessions/{demo_session}/report?format=json")
    assert client.get(f"/api/sessions/{demo_session}").json()["status"] == "inspected"


def test_exif_rotated_photo_is_normalized(client: TestClient) -> None:
    img = Image.new("RGB", (60, 20), (200, 10, 10))
    exif = img.getexif()
    exif[0x0112] = 6  # rotate 90 CW on display
    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif)
    sid = client.post("/api/sessions", json={"name": "x", "facility_id": "WH-01"}).json()["id"]
    out = client.post(f"/api/sessions/{sid}/images", files={"files": ("phone.jpg", buf.getvalue(), "image/jpeg")}).json()
    assert (out[0]["width"], out[0]["height"]) == (20, 60)


def _ev(serial: str | None, idents: list | None = None, uncertain: bool = False) -> ModelEvidence:
    return ModelEvidence(observed_object_type="generator", visible_manufacturer="Cumberland", visible_model="PX-500",
                         visible_serial_number=serial, visible_identifiers=idents or [],
                         uncertainties=[{"field": "visible_serial_number", "note": "?"}] if uncertain else [])


def test_second_different_serial_blocks_auto_verification() -> None:
    assets = [LedgerAsset("l1", "A1", "Generator", "Cumberland", "PX-500", "SERX1", "F")]
    ev = _ev("SERX1", [{"kind": "serial", "value": "OTHER777", "readable": True}])
    decisions, _ = reconcile(assets, [Observation("e1", "d1", "i1", "F", "generator", "ok", ev)], [], {("F", "generator")})
    assert decisions[0].decision == "PROBABLE" and "MULTIPLE_SERIALS_VISIBLE" in decisions[0].flags


def test_uncertain_unmatched_serial_falls_back_instead_of_not_in_register() -> None:
    assets = [LedgerAsset("l1", "A1", "Generator", "Cumberland", "PX-500", "GN-1111", "F")]
    obs = Observation("e1", "d1", "i1", "F", "generator", "ok", _ev("GN-1117", uncertain=True))
    decisions, _ = reconcile(assets, [obs], [], {("F", "generator")})
    assert decisions[0].decision == "PROBABLE" and "SERIAL_UNCERTAIN" in decisions[0].flags


def test_reject_naming_one_asset_keeps_other_candidates() -> None:
    assets = [LedgerAsset(f"l{i}", f"A{i}", "Generator", "Cumberland", "PX-500", None, "F") for i in (1, 2)]
    obs = Observation("e1", "d1", "i1", "F", "generator", "ok", _ev(None))
    _, results = reconcile(assets, [obs], [Review("dec_e1", "reject", "A1")], {("F", "generator")})
    by_id = {r.asset_id: r.status for r in results}
    assert by_id == {"A1": "UNVERIFIED", "A2": "PROBABLE"}


def test_segment_only_run_then_extract_selected_region(client: TestClient) -> None:
    sid = client.post("/api/sessions", json={"name": "x", "facility_id": "WH-01"}).json()["id"]
    client.post(f"/api/sessions/{sid}/demo")
    run = wait_run(client, client.post(f"/api/sessions/{sid}/runs",
                                       json={"concept": "generator", "extract": False}).json()["id"])
    assert run["status"] == "succeeded" and run["detections"] == 10 and run["evidence_ok"] == 0
    rows = client.get(f"/api/sessions/{sid}/detections").json()
    assert all(r["evidence"] is None and r["decision"] is None for r in rows)
    calls = client.get(f"/api/sessions/{sid}/trace").json()["provider_calls"]
    assert {c["operation"] for c in calls} == {"segment"}  # no extraction spend until a region is chosen
    target = next(r["detection"]["id"] for r in rows if r["detection"]["object_index"] == 1)
    out = client.post(f"/api/detections/{target}/extract").json()
    assert out["evidence"]["status"] == "ok" and out["decision"]["decision"] == "VERIFIED"
    assert client.post(f"/api/detections/{target}/extract").status_code == 409
    assert client.post("/api/detections/det_nope/extract").status_code == 404


def test_live_budget_respects_session_and_total_caps(tmp_path) -> None:  # noqa: ANN001
    from app.db import AuditSession, ProviderCallRow, utcnow

    settings = make_settings(tmp_path, mode="live", max_live_requests_per_session=2, max_live_usd_total=0.01)
    app = create_app(settings)
    db = app.state.db
    with db.session() as s:
        s.add(AuditSession(id="ses_a", name="a", facility_id="F"))
        s.add(ProviderCallRow(id="c1", session_id="ses_a", provider="meta-sam", model="sam-3.1", mode="live",
                              operation="segment", status="ok", latency_ms=1, started_at=utcnow(),
                              estimated_cost_usd=0.009, correlation_id="t"))
    budget = app.state.pipeline.budget_for("ses_a", 40, 0.5)
    assert budget.max_requests == 1 and abs(budget.max_usd - 0.001) < 1e-9
    from app.pipeline import BudgetExceeded

    with pytest.raises(BudgetExceeded):
        budget.reserve(0.0025)  # exceeds remaining all-time USD


def test_concurrent_extract_clicks_spend_once(client: TestClient) -> None:
    sid = client.post("/api/sessions", json={"name": "x", "facility_id": "WH-01"}).json()["id"]
    client.post(f"/api/sessions/{sid}/demo")
    wait_run(client, client.post(f"/api/sessions/{sid}/runs", json={"concept": "generator", "extract": False}).json()["id"])
    did = client.get(f"/api/sessions/{sid}/detections").json()[0]["detection"]["id"]
    with ThreadPoolExecutor(max_workers=4) as pool:
        codes = sorted(pool.map(lambda _: client.post(f"/api/detections/{did}/extract").status_code, range(4)))
    assert codes.count(200) == 1 and codes.count(409) == 3
    extracts = [c for c in client.get(f"/api/sessions/{sid}/trace").json()["provider_calls"] if c["operation"] == "extract"]
    assert len(extracts) == 1
