"""Ledger validation, upload security and API input validation."""

from __future__ import annotations

import io

from fastapi.testclient import TestClient
from PIL import Image

from app.ledger import parse_ledger
from app.security import csv_safe, sanitize_filename

from .conftest import FIXTURES

MB = 1024 * 1024


def test_fixture_ledger_validation_issues() -> None:
    parsed = parse_ledger((FIXTURES / "ledger.csv").read_bytes(), 5000, 2 * MB)
    codes = {(i.row, i.code) for i in parsed.issues}
    assert parsed.rejected == 2 and len(parsed.rows) == 18
    assert (18, "REQUIRED_FIELD_MISSING") in codes and (20, "DUPLICATE_ASSET_ID") in codes
    assert (19, "FORMULA_NEUTRALIZED") in codes and (19, "NEGATIVE_VALUE") in codes and (19, "INVALID_DATE") in codes
    assert any(c == "DUPLICATE_SERIAL" for _, c in codes)
    a22 = next(r for r in parsed.rows if r["asset_id"] == "A-022")
    assert a22["expected_location"].startswith("'=") and a22["currency"] == "USD"


def test_missing_required_columns_rejected(client: TestClient) -> None:
    sid = client.post("/api/sessions", json={"name": "x", "facility_id": "WH-01"}).json()["id"]
    r = client.post(f"/api/sessions/{sid}/ledger", files={"file": ("l.csv", b"name,value\na,1\n", "text/csv")})
    assert r.status_code == 400 and r.json()["error"]["code"] == "VALIDATION_FAILED"
    r = client.post(f"/api/sessions/{sid}/ledger", files={"file": ("l.txt", b"asset_id\n", "text/plain")})
    assert r.status_code == 415
    r = client.post(f"/api/sessions/{sid}/ledger", files={"file": ("l.csv", b"\xff\xfe\x00bad", "text/csv")})
    assert r.status_code == 400


def test_image_validation(client: TestClient) -> None:
    sid = client.post("/api/sessions", json={"name": "x", "facility_id": "WH-01"}).json()["id"]
    fake = client.post(f"/api/sessions/{sid}/images", files={"files": ("x.png", b"<?php echo 1; ?>", "image/png")})
    assert fake.status_code == 415
    gif = io.BytesIO()
    Image.new("RGB", (4, 4)).save(gif, format="GIF")
    assert client.post(f"/api/sessions/{sid}/images", files={"files": ("x.gif", gif.getvalue(), "image/gif")}).status_code == 415
    png = io.BytesIO()
    Image.new("RGB", (8, 8)).save(png, format="PNG")
    ok = client.post(f"/api/sessions/{sid}/images", files={"files": ("../../etc/pass wd.png", png.getvalue(), "image/png")})
    assert ok.status_code == 200 and ok.json()[0]["filename"] == "pass_wd.png"
    dup = client.post(f"/api/sessions/{sid}/images", files={"files": ("again.png", png.getvalue(), "image/png")})
    assert dup.json()[0]["id"] == ok.json()[0]["id"]  # same bytes deduplicated by sha256


def test_oversize_image_rejected(tmp_path) -> None:  # noqa: ANN001
    from app.main import create_app

    from .conftest import make_settings

    client = TestClient(create_app(make_settings(tmp_path, max_upload_mb=1)))
    sid = client.post("/api/sessions", json={"name": "x", "facility_id": "WH-01"}).json()["id"]
    big = b"\x89PNG\r\n\x1a\n" + b"0" * (MB + 10)
    r = client.post(f"/api/sessions/{sid}/images", files={"files": ("b.png", big, "image/png")})
    assert r.status_code == 413 and r.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"


def test_request_validation_and_error_envelope(client: TestClient) -> None:
    r = client.post("/api/sessions", json={"name": "x", "facility_id": "bad id!"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "VALIDATION_FAILED"
    assert r.headers["x-correlation-id"] == r.json()["error"]["correlation_id"]
    sid = client.post("/api/sessions", json={"name": "x", "facility_id": "WH-01"}).json()["id"]
    for concept in ("<|box;x1=1|>", "a very long concept phrase with too many words"):
        assert client.post(f"/api/sessions/{sid}/runs", json={"concept": concept}).status_code == 422
    assert client.post(f"/api/sessions/{sid}/runs", json={"concept": "forklift"}).status_code == 400  # no images
    assert client.get("/api/sessions/nope").status_code == 404
    assert client.post("/api/decisions/dec_nope/review", json={"action": "reject", "reviewer": "Al"}).status_code == 404
    assert client.get("/api/sessions/x/report?format=exe").status_code == 422


def test_correlation_id_echo_and_sanitized(client: TestClient) -> None:
    assert client.get("/api/health", headers={"x-correlation-id": "abc-123"}).headers["x-correlation-id"] == "abc-123"
    assert client.get("/api/health", headers={"x-correlation-id": "bad\nid"}).headers["x-correlation-id"] != "bad\nid"


def test_helpers() -> None:
    assert sanitize_filename("..\\..\\x/../a b?.jpg") == "a_b_.jpg"
    assert csv_safe("=SUM(A1)") == "'=SUM(A1)" and csv_safe("+1") == "'+1" and csv_safe("ok") == "ok"
    assert csv_safe(None) == ""
