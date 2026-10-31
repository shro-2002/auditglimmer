"""End-to-end API journey in DEMO mode (fixture providers on synthetic images)."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from .conftest import FIXTURES, wait_run


def test_full_demo_journey_matches_expected_asset_statuses(client: TestClient, demo_session: str) -> None:
    recon = client.get(f"/api/sessions/{demo_session}/reconciliation").json()
    expected = json.loads((FIXTURES / "manifest.json").read_text())["expected_asset_status"]
    expected["A-022"] = "NOT_OBSERVABLE"
    actual = {a["asset_id"]: a["status"] for a in recon["assets"]}
    assert actual == expected
    assert recon["summary"]["inspected_concepts"] == ["forklift", "generator"]


def test_runs_record_events_detections_and_failures(client: TestClient, demo_session: str) -> None:
    trace = client.get(f"/api/sessions/{demo_session}/trace").json()
    assert [r["status"] for r in trace["runs"]] == ["partial", "partial"]  # each concept has a failure case
    statuses = sorted(c["status"] for c in trace["provider_calls"])
    assert statuses.count("timeout") == 1
    assert statuses.count("invalid_output") == 2
    assert all(c["mode"] == "demo" and c["estimated_cost_usd"] == 0 for c in trace["provider_calls"])
    assert trace["events"][0]["stage"] == "run"


def test_detection_masks_align_with_image_coordinates(client: TestClient, demo_session: str) -> None:
    images = {i["id"]: i for i in client.get(f"/api/sessions/{demo_session}/images").json()}
    manifest = {m["sha256"]: m for m in json.loads((FIXTURES / "manifest.json").read_text())["images"]}
    rows = client.get(f"/api/sessions/{demo_session}/detections").json()
    assert len(rows) == 16
    for row in rows:
        det = row["detection"]
        img = images[det["image_id"]]
        x1, y1, x2, y2 = det["mask"]["bounds"]
        assert 0 <= x1 < x2 <= img["width"] and 0 <= y1 < y2 <= img["height"]
        assert det["mask"]["raster_w"] == x2 - x1 and det["mask"]["raster_h"] == y2 - y1
        truth = next(o for o in manifest[img["sha256"]]["objects"] if o["object_index"] == det["object_index"])
        assert det["mask"]["bounds"] == truth["bounds"]


def test_review_confirm_promotes_asset_and_blocks_double_assignment(client: TestClient, demo_session: str) -> None:
    queue = client.get(f"/api/sessions/{demo_session}/review-queue").json()
    ambiguous = [d for d in queue if "AMBIGUOUS_CANDIDATES" in d["flags"]]
    assert len(ambiguous) == 2 and ambiguous[0]["candidate_asset_ids"] == ["A-010", "A-011", "A-012"]
    first, second = ambiguous
    ok = client.post(f"/api/decisions/{first['id']}/review",
                     json={"action": "confirm", "asset_id": "A-011", "reviewer": "auditor-1", "note": "tag checked on site"})
    assert ok.status_code == 200 and ok.json()["review"]["action"] == "confirm"
    clash = client.post(f"/api/decisions/{second['id']}/review",
                        json={"action": "confirm", "asset_id": "A-011", "reviewer": "auditor-1", "note": "tag checked on site"})
    assert clash.status_code == 409 and clash.json()["error"]["code"] == "CONFLICT"
    not_candidate = client.post(f"/api/decisions/{second['id']}/review",
                                json={"action": "confirm", "asset_id": "A-001", "reviewer": "auditor-1", "note": "tag checked on site"})
    assert not_candidate.status_code == 409
    statuses = {a["asset_id"]: a for a in client.get(f"/api/sessions/{demo_session}/reconciliation").json()["assets"]}
    assert statuses["A-011"]["status"] == "HUMAN_CONFIRMED" and statuses["A-011"]["human_confirmed"] is True


def test_reject_removes_auto_verification(client: TestClient, demo_session: str) -> None:
    recon = client.get(f"/api/sessions/{demo_session}/reconciliation").json()
    verified = next(d for d in recon["decisions"] if d["matched_asset_id"] == "A-001")
    r = client.post(f"/api/decisions/{verified['id']}/review", json={"action": "reject", "reviewer": "auditor-2"})
    assert r.status_code == 200
    statuses = {a["asset_id"]: a["status"] for a in client.get(f"/api/sessions/{demo_session}/reconciliation").json()["assets"]}
    assert statuses["A-001"] == "UNVERIFIED"


def test_reports_include_evidence_uncertainty_and_disclaimer(client: TestClient, demo_session: str) -> None:
    rep = client.get(f"/api/sessions/{demo_session}/report?format=json").json()
    assert "not evidence that the asset is missing" in rep["disclaimer"].lower() or "NOT evidence" in rep["disclaimer"]
    assert rep["demo_notice"]
    for d in rep["decisions"]:
        assert d["image"]["sha256"] and d["detection"]["bounds"] and d["evidence"]["status"]
        assert d["evidence_ids"] == [d["evidence_id"]]
    uncertain = [d for d in rep["decisions"] if d["evidence"]["fields"] and d["evidence"]["fields"]["uncertainties"]]
    assert uncertain
    html = client.get(f"/api/sessions/{demo_session}/report?format=html&download=true")
    assert html.status_code == 200 and "attachment" in html.headers["content-disposition"]
    assert "DEMO MODE" in html.text and "<script" not in html.text.lower()
    csv_text = client.get(f"/api/sessions/{demo_session}/report?format=csv").text
    assert "A-001" in csv_text and "decision_id" in csv_text
    assert client.get(f"/api/sessions/{demo_session}").json()["status"] != "reported"  # open reviews keep it DRAFT


def test_evidence_graph_links_every_decision_to_image(client: TestClient, demo_session: str) -> None:
    g = client.get(f"/api/sessions/{demo_session}/evidence-graph").json()
    types = {n["id"]: n["type"] for n in g["nodes"]}
    edges = {(e["source"], e["type"]): e["target"] for e in g["edges"]}
    decisions = [n for n in g["nodes"] if n["type"] == "Decision"]
    assert len(decisions) == 16
    for d in decisions:
        ev = edges[(d["id"], "DECIDED_FROM")]
        det = edges[(ev, "EXTRACTED_FROM")]
        assert types[edges[(det, "DETECTED_IN")]] == "Image"


def test_rerun_replaces_rather_than_duplicates(client: TestClient, demo_session: str) -> None:
    run = client.post(f"/api/sessions/{demo_session}/runs", json={"concept": "generator"}).json()
    wait_run(client, run["id"])
    assert len(client.get(f"/api/sessions/{demo_session}/detections").json()) == 16


def test_sse_stream_ends(client: TestClient, demo_session: str) -> None:
    runs = client.get(f"/api/sessions/{demo_session}/trace").json()["runs"]
    with client.stream("GET", f"/api/runs/{runs[0]['id']}/events") as resp:
        body = "".join(resp.iter_text())
    assert "event: end" in body and '"stage": "segment"' in body


def test_overview_counts_are_real(client: TestClient, demo_session: str) -> None:
    ov = client.get("/api/overview").json()
    assert ov["sessions"] == 1 and ov["images"] == 3 and ov["assets"] == 18 and ov["detections"] == 16


def test_delete_session_removes_data(client: TestClient, demo_session: str, tmp_path) -> None:  # noqa: ANN001
    assert client.delete(f"/api/sessions/{demo_session}").status_code == 204
    assert client.get(f"/api/sessions/{demo_session}").status_code == 404
    assert not (tmp_path / "data" / "sessions" / demo_session).exists()
    assert list((tmp_path / "data" / "raw").glob("*.txt")) == []  # raw provider outputs purged too
