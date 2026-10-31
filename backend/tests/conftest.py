from __future__ import annotations

import time
from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import PROJECT_ROOT, Settings
from app.main import create_app

FIXTURES = PROJECT_ROOT / "fixtures"


def make_settings(tmp_path: Path, **overrides) -> Settings:
    base = Settings(mode="demo", data_dir=tmp_path / "data", fixtures_dir=FIXTURES,
                    database_url=f"sqlite:///{tmp_path / 'test.db'}")
    return replace(base, **overrides)


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    return TestClient(create_app(make_settings(tmp_path)))


def wait_run(client: TestClient, run_id: str, timeout: float = 20.0) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        run = client.get(f"/api/runs/{run_id}").json()
        if run["status"] in {"succeeded", "partial", "failed"}:
            return run
        time.sleep(0.05)
    raise AssertionError(f"run {run_id} did not finish")


@pytest.fixture
def demo_session(client: TestClient) -> str:
    sid = client.post("/api/sessions", json={"name": "Demo", "facility_id": "WH-01"}).json()["id"]
    assert client.post(f"/api/sessions/{sid}/demo").status_code == 200
    for concept in ("industrial generator", "forklift"):
        run = client.post(f"/api/sessions/{sid}/runs", json={"concept": concept}).json()
        wait_run(client, run["id"])
    return sid
