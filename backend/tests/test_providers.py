"""Provider contract and failure-mode tests. Offline: httpx MockTransport, zero network, zero spend."""

from __future__ import annotations

import io
import json

import httpx
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.errors import ProviderError
from app.main import create_app
from app.providers.base import CropContext, ImageInput
from app.providers.meta_http import MetaHttp
from app.providers.muse_meta import MetaMuseProvider, parse_evidence_json
from app.providers.sam_meta import MetaSAMProvider, parse_sam_output

from .conftest import make_settings

# Verbatim example from https://dev.meta.ai/docs/sam/reading-segmentation (video grammar, frame 0).
DOC_SAM_LINE = (
    "<0f>0<|box;x1=211;y1=228;x2=270;y2=254;w=320;h=334|>"
    "<|mask;x=0;y=0;data=27,60,~!!!!M!0c[0o91w?q1!pIH4pPRVp2B3'7`e.ioeAf6-k/#Xd8%dX9x(|>"
    ",1<|box;x1=155;y1=228;x2=202;y2=254;w=320;h=334|>"
    "<|mask;x=0;y=0;data=27,48,~!!!!J!0c[q=Pj_zs=*4C4(/./x#:/`S_GnD`=o3?X{emCgO$y@|>"
)

VALID_EVIDENCE = {
    "observed_object_type": "forklift", "visible_manufacturer": "Liftmaster", "visible_model": "LM-25",
    "visible_serial_number": "FL-7781", "visible_identifiers": [{"kind": "serial", "value": "FL-7781", "readable": True}],
    "visible_condition_observations": [], "uncertainties": [], "model_confidence": 0.8,
}


def _png(w: int = 320, h: int = 334) -> ImageInput:
    buf = io.BytesIO()
    Image.new("RGB", (w, h), (90, 90, 90)).save(buf, format="PNG")
    return ImageInput(buf.getvalue(), "image/png", w, h, "0" * 64)


def _http(handler, retries: int = 2) -> MetaHttp:  # noqa: ANN001
    return MetaHttp("test-key-not-real", 5.0, retries, transport=httpx.MockTransport(handler), sleep=lambda _s: None)


# ---------- SAM wire format ----------

def test_parse_documented_sam_output_into_aligned_masks() -> None:
    objs = parse_sam_output(DOC_SAM_LINE)
    assert [o.object_index for o in objs] == [0, 1]
    first = objs[0].mask
    assert first.bounds == (211, 228, 271, 255)  # wire x2/y2 inclusive -> half-open
    assert (first.raster_w, first.raster_h) == (60, 27) == (first.bounds[2] - first.bounds[0], first.bounds[3] - first.bounds[1])
    assert first.svg_path.startswith("M") and 0 < first.area_px <= 60 * 27
    assert objs[0].confidence is None  # include_confidence absent -> None, never 0


def test_empty_sam_output_is_zero_matches_not_error() -> None:
    assert parse_sam_output("") == []


def test_malformed_sam_output_is_rejected() -> None:
    with pytest.raises(ProviderError) as exc:
        parse_sam_output("<0f>0<|box;x1=1;y1=1|><|mask;x=0;y=0;data=garbage|>")
    assert exc.value.kind == "invalid_output"


def test_meta_sam_provider_streams_and_parses() -> None:
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content)
        seen["auth"] = request.headers["authorization"]
        events = [
            {"type": "response.created", "response": {"id": "resp_1"}},
            {"type": "response.output_text.delta", "delta": DOC_SAM_LINE},
            {"type": "response.completed", "response": {"id": "resp_1", "usage": {"input_tokens": 1}}},
        ]
        body = "".join(f"data: {json.dumps(e)}\n\n" for e in events) + "data: [DONE]\n\n"
        return httpx.Response(200, text=body, headers={"content-type": "text/event-stream"})

    result = MetaSAMProvider(_http(handler)).segment_image(_png(), "button")
    assert seen["body"]["model"] == "sam-3.1" and seen["body"]["stream"] is True
    assert seen["body"]["metadata"] == {"include_confidence": "true", "mask_encoding": "one_bit"}
    content = seen["body"]["input"][0]["content"]
    assert content[0] == {"type": "input_text", "text": "button"}
    assert content[1]["image_url"].startswith("data:image/png;base64,")
    assert seen["auth"] == "Bearer test-key-not-real"
    assert len(result.objects) == 2 and result.meta.images == 1 and result.meta.estimated_cost_usd == 0.0025
    assert result.meta.raw_output == DOC_SAM_LINE


def test_sam_stream_error_event_raises() -> None:
    def handler(_r: httpx.Request) -> httpx.Response:
        body = 'data: {"type": "error", "error": {"code": "server_shutting_down"}}\n\n'
        return httpx.Response(200, text=body, headers={"content-type": "text/event-stream"})

    with pytest.raises(ProviderError, match="server_shutting_down"):
        MetaSAMProvider(_http(handler)).segment_image(_png(), "button")


# ---------- Muse structured output ----------

def test_parse_valid_evidence() -> None:
    ev = parse_evidence_json(json.dumps(VALID_EVIDENCE))
    assert ev.visible_serial_number == "FL-7781"


@pytest.mark.parametrize("raw, fragment", [
    ('{"observed_object_type": "gen', "not valid JSON"),
    (json.dumps({**VALID_EVIDENCE, "legal_owner": "Bank"}), "legal_owner"),
    (json.dumps({**VALID_EVIDENCE, "estimated_value_usd": 1}), "estimated_value_usd"),
    (json.dumps({**VALID_EVIDENCE, "model_confidence": 7}), "model_confidence"),
    (json.dumps({k: v for k, v in VALID_EVIDENCE.items() if k != "observed_object_type"}), "observed_object_type"),
])
def test_invalid_or_unsupported_evidence_rejected(raw: str, fragment: str) -> None:
    with pytest.raises(ProviderError) as exc:
        parse_evidence_json(raw)
    assert exc.value.kind == "invalid_output" and fragment in exc.value.message


def _chat(content: str, finish: str = "stop") -> dict:
    return {"id": "chat_1", "choices": [{"message": {"content": content}, "finish_reason": finish}],
            "usage": {"prompt_tokens": 1000, "completion_tokens": 200}}


def test_meta_muse_request_shape_and_cost() -> None:
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json=_chat(json.dumps(VALID_EVIDENCE)))

    ctx = CropContext("0" * 64, 1, (0, 0, 10, 10), "forklift")
    result = MetaMuseProvider(_http(handler)).extract_visual_evidence(_png(64, 64), ctx)
    body = seen["body"]
    assert body["model"] == "muse-spark-1.3" and body["reasoning_effort"] == "low"
    assert body["response_format"]["type"] == "json_schema"
    assert body["response_format"]["json_schema"]["schema"]["additionalProperties"] is False
    assert "ledger" not in json.dumps(body).lower()  # no financial register data leaves the backend
    assert result.meta.input_tokens == 1000 and result.meta.estimated_cost_usd == pytest.approx(0.00125 + 0.00085)


def test_truncated_extraction_is_invalid_output() -> None:
    def handler(_r: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_chat('{"observed_object_type": "for', finish="length"))

    with pytest.raises(ProviderError) as exc:
        MetaMuseProvider(_http(handler)).extract_visual_evidence(_png(64, 64), CropContext("0" * 64, 1, (0, 0, 1, 1), "x"))
    assert exc.value.kind == "invalid_output" and "truncated" in exc.value.message


# ---------- transport retries / errors ----------

def test_retries_429_then_succeeds() -> None:
    calls = {"n": 0}

    def handler(_r: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(429, json={"error": {"message": "slow down"}}, headers={"retry-after": "1"})
        return httpx.Response(200, json={"ok": True})

    body, _ = _http(handler).post_json("/chat/completions", {})
    assert body == {"ok": True} and calls["n"] == 3


def test_400_is_permanent_and_not_retried() -> None:
    calls = {"n": 0}

    def handler(_r: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(400, json={"error": {"message": "bad schema"}})

    with pytest.raises(ProviderError, match="HTTP 400: bad schema"):
        _http(handler).post_json("/chat/completions", {})
    assert calls["n"] == 1


def test_retries_are_bounded() -> None:
    calls = {"n": 0}

    def handler(_r: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(503, json={"error": {"code": "service_overloaded"}})

    with pytest.raises(ProviderError):
        _http(handler, retries=2).post_json("/x", {})
    assert calls["n"] == 3


def test_timeout_becomes_timeout_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    with pytest.raises(ProviderError) as exc:
        _http(handler, retries=1).post_json("/x", {})
    assert exc.value.kind == "timeout"


def test_missing_key_refuses_to_build_client() -> None:
    with pytest.raises(ProviderError) as exc:
        MetaHttp("", 5.0, 1)
    assert exc.value.kind == "not_approved"


# ---------- mode guarantees ----------

def test_live_mode_without_approval_blocks_runs_and_never_falls_back(tmp_path) -> None:  # noqa: ANN001
    client = TestClient(create_app(make_settings(tmp_path, mode="live")))
    cfg = client.get("/api/config").json()
    assert cfg["mode"] == "live" and cfg["live_approved"] is False and cfg["credentials_present"] is False
    assert cfg["segmentation_model"] == "sam-3.1"
    sid = client.post("/api/sessions", json={"name": "L", "facility_id": "WH-01"}).json()["id"]
    assert client.post(f"/api/sessions/{sid}/demo").status_code == 403
    run = client.post(f"/api/sessions/{sid}/runs", json={"concept": "forklift"})
    assert run.status_code == 403 and run.json()["error"]["code"] == "LIVE_NOT_APPROVED"
    health = client.get("/api/health").json()
    assert health["providers"]["segmentation"]["ok"] is False


def test_demo_mode_refuses_non_fixture_images(client: TestClient) -> None:
    sid = client.post("/api/sessions", json={"name": "U", "facility_id": "WH-01"}).json()["id"]
    buf = io.BytesIO()
    Image.new("RGB", (64, 48), (10, 120, 200)).save(buf, format="PNG")
    up = client.post(f"/api/sessions/{sid}/images", files={"files": ("photo.png", buf.getvalue(), "image/png")})
    assert up.status_code == 200
    from .conftest import wait_run

    run = wait_run(client, client.post(f"/api/sessions/{sid}/runs", json={"concept": "forklift"}).json()["id"])
    assert run["status"] == "failed" and run["detections"] == 0
    calls = client.get(f"/api/sessions/{sid}/trace").json()["provider_calls"]
    assert calls[0]["status"] == "error" and "no_fixture" in calls[0]["error"]


def test_demo_unknown_concept_is_explicit(client: TestClient) -> None:
    sid = client.post("/api/sessions", json={"name": "C", "facility_id": "WH-01"}).json()["id"]
    client.post(f"/api/sessions/{sid}/demo")
    from .conftest import wait_run

    run = wait_run(client, client.post(f"/api/sessions/{sid}/runs", json={"concept": "excavator"}).json()["id"])
    assert run["status"] == "failed"  # supported type, but no fixture covers it in DEMO
    events = client.get(f"/api/sessions/{sid}/trace").json()["events"]
    assert any("needs LIVE mode" in e["message"] for e in events)
    unsupported = client.post(f"/api/sessions/{sid}/runs", json={"concept": "golden retriever"})
    assert unsupported.status_code == 400 and "forklift" in unsupported.json()["error"]["message"]


def test_sam_text_only_in_content_part_done_is_parsed() -> None:
    """Live API may finalize the lane with response.content_part.done (meta-sam-parser docs)."""

    def handler(_r: httpx.Request) -> httpx.Response:
        events = [
            {"type": "response.content_part.done", "part": {"type": "output_text", "text": DOC_SAM_LINE}},
            {"type": "response.completed", "response": {"id": "r", "usage": {"images_processed": 1}}},
        ]
        body = "".join(f"data: {json.dumps(e)}\n\n" for e in events)
        return httpx.Response(200, text=body, headers={"content-type": "text/event-stream"})

    result = MetaSAMProvider(_http(handler)).segment_image(_png(), "button")
    assert len(result.objects) == 2 and result.meta.extra["event_types"]["response.content_part.done"] == 1
