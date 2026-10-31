"""Tier 1 confirmation gate (experimental safeguard). Regression cases from the real-photo study (s14) and the
failure modes the gate must and must not cover. Agreement between two reads is supporting evidence, not proof."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.errors import ProviderError
from app.main import create_app
from app.pipeline import needs_confirmation
from app.reconcile import (
    _STANDALONE_PLATE,
    Confirmation,
    LedgerAsset,
    Observation,
    reconcile,
)
from app.schemas import ModelEvidence
from app.services import set_tier1_policy

from .conftest import make_settings, wait_run

F = "F"


def ev(serial: str | None, *, mfr: str | None = "Cumberland", typ: str = "generator",
       uncertain: bool = False) -> ModelEvidence:
    return ModelEvidence(observed_object_type=typ, visible_manufacturer=mfr, visible_model="PX-500",
                         visible_serial_number=serial,
                         uncertainties=[{"field": "visible_serial_number", "note": "?"}] if uncertain else [])


def gen(aid: str, serial: str | None, mfr: str = "Cumberland") -> LedgerAsset:
    return LedgerAsset(f"l-{aid}", aid, "Generator", mfr, "PX-500", serial, F)


def decide(assets, first, second, *, eid="e1", policy="two_read"):
    o = Observation(eid, f"d-{eid}", "i1", F, "generator", "ok", first, None, second)
    decisions, results = reconcile(assets, [o], [], {(F, "generator")}, policy)
    return decisions[0], {r.asset_id: r.status for r in results}


def ok(e: ModelEvidence) -> Confirmation:
    return Confirmation("ok", e)


def test_s14_disagreeing_reads_block_tier1() -> None:
    # study item s14: first read 5735 matched the reader-1 register row; a second read of 5765 must stop Tier 1
    d, status = decide([gen("U-s14-1", "5735")], ev("5735"), ok(ev("5765")))
    assert d.decision == "PROBABLE" and d.review_required and d.matched_asset_id is None
    assert d.matching_rule == "R2e_CONFIRMATION_SERIAL_DISAGREES"
    assert "'5735' vs second read '5765'" in d.explanation
    assert status["U-s14-1"] != "VERIFIED"


def test_agreeing_reads_verify_and_say_agreement_is_not_proof() -> None:
    d, status = decide([gen("A1", "GN-5735")], ev("GN-5735"), ok(ev("gn 5735")))
    assert d.decision == "VERIFIED" and "CONFIRMED_BY_SECOND_READ" in d.flags
    assert "not proof" in d.explanation and status["A1"] == "VERIFIED"


def test_shared_model_mistake_is_not_caught_by_agreement_alone() -> None:
    # both reads say 5765, the plate actually says 5735 (A1). The gate cannot see this; the register checks can
    # only when another field conflicts. Documented limitation, pinned so nobody claims otherwise.
    assets = [gen("A1", "5735"), gen("B1", "5765")]
    d, _ = decide(assets, ev("5765"), ok(ev("5765")))
    assert d.decision == "VERIFIED" and d.matched_asset_id == "B1"
    d, _ = decide([gen("A1", "5735"), gen("B1", "5765", mfr="Brightwater")], ev("5765"), ok(ev("5765")))
    assert d.decision == "MISMATCHED"  # a conflicting register field still stops it
    d, _ = decide(assets, ev("5765"), ok(ev("5765")), policy="human_review")
    assert d.decision == "PROBABLE" and d.matching_rule == "R2e_HUMAN_REVIEW_POLICY"


def test_duplicate_ledger_serial_still_blocks_even_with_agreeing_reads() -> None:
    d, _ = decide([gen("A1", "GN-9000"), gen("A2", "GN-9000")], ev("GN-9000"), ok(ev("GN-9000")))
    assert d.decision == "PROBABLE" and d.matching_rule == "R2b_SERIAL_DUPLICATED_IN_LEDGER"


def test_same_serial_on_two_detections_still_blocks_even_with_agreeing_reads() -> None:
    first = ev("GN-9000")
    obs = [Observation(e, f"d-{e}", e, F, "generator", "ok", first, None, ok(first)) for e in ("e1", "e2")]
    decisions, _ = reconcile([gen("A1", "GN-9000")], obs, [], {(F, "generator")})
    assert all(d.decision == "PROBABLE" and d.matching_rule == "R2d_IDENTIFIER_SEEN_ON_MULTIPLE_OBJECTS"
               for d in decisions)


@pytest.mark.parametrize("second", [
    None,
    Confirmation("error", None, "timeout"),
    Confirmation("invalid", None, "schema"),
    ok(ev(None)),
    ok(ev("GN-1001", uncertain=True)),
    ok(ev("GN1")),  # too short to count as a serial
])
def test_missing_or_unreadable_second_read_blocks_tier1(second: Confirmation | None) -> None:
    d, _ = decide([gen("A1", "GN-1001")], ev("GN-1001"), second)
    assert d.decision == "PROBABLE" and d.review_required
    assert d.matching_rule in {"R2e_CONFIRMATION_MISSING", "R2e_CONFIRMATION_UNREADABLE"}


def test_conflicting_manufacturer_between_reads_blocks_tier1() -> None:
    d, _ = decide([gen("A1", "GN-1001")], ev("GN-1001"), ok(ev("GN-1001", mfr="Brightwater")))
    assert d.matching_rule == "R2e_CONFIRMATION_MANUFACTURER_DISAGREES"
    # a second read that adds the legal suffix or misses the maker is not a conflict
    assert decide([gen("A1", "GN-1001")], ev("GN-1001"), ok(ev("GN-1001", mfr="Cumberland GmbH")))[0].tier == 1
    assert decide([gen("A1", "GN-1001")], ev("GN-1001"), ok(ev("GN-1001", mfr=None)))[0].tier == 1


def test_conflicting_manufacturer_against_register_is_mismatched_before_the_gate() -> None:
    d, _ = decide([gen("A1", "GN-1001", mfr="Brightwater")], ev("GN-1001"), ok(ev("GN-1001")))
    assert d.decision == "MISMATCHED" and "CONFLICTING_MANUFACTURER" in d.flags


def test_conflicting_asset_type_between_reads_blocks_tier1() -> None:
    d, _ = decide([gen("A1", "GN-1001")], ev("GN-1001"), ok(ev("GN-1001", typ="forklift")))
    assert d.matching_rule == "R2e_CONFIRMATION_TYPE_DISAGREES"


@pytest.mark.parametrize("typ", ["generator nameplate", "generator rating plate", "genset serial label"])
def test_standalone_plate_is_not_associated_with_a_unit(typ: str) -> None:
    first = ev("GN-1001", typ=typ)
    d, _ = decide([gen("A1", "GN-1001")], first, ok(first))
    assert d.decision == "PROBABLE" and d.matching_rule == "R2e_SOURCE_ASSOCIATION_UNSUPPORTED"


@pytest.mark.parametrize("typ", ["tractor data plate", "serial label"])
def test_plate_of_other_type_is_stopped_by_the_type_check(typ: str) -> None:
    first = ev("GN-1001", typ=typ)
    d, _ = decide([gen("A1", "GN-1001")], first, ok(first))
    assert d.decision == "MISMATCHED" and "TYPE_CONFLICT" in d.flags


def test_unknown_policy_is_rejected() -> None:
    with pytest.raises(ValueError):
        reconcile([], [], [], set(), "auto")
    with pytest.raises(ValueError):
        make_settings(Path("/tmp/x"), tier1_policy="HUMAN_REVIEW")


# ----- independent-review findings (second read must be checked as strictly as the first) -----

def test_second_read_reporting_a_plate_blocks_tier1() -> None:
    d, _ = decide([gen("A1", "GN-1001")], ev("GN-1001"), ok(ev("GN-1001", typ="generator nameplate")))
    assert d.matching_rule == "R2e_SOURCE_ASSOCIATION_UNSUPPORTED"


def test_second_read_conflicting_with_register_blocks_tier1() -> None:
    d, _ = decide([gen("A1", "GN-1001")], ev("GN-1001", mfr=None), ok(ev("GN-1001", mfr="Brightwater")))
    assert d.matching_rule == "R2e_CONFIRMATION_CONFLICTS_REGISTER"
    other_model = ev("GN-1001").model_copy(update={"visible_model": "ZX-900"})
    d, _ = decide([gen("A1", "GN-1001")], ev("GN-1001"), ok(other_model))
    assert d.matching_rule == "R2e_CONFIRMATION_CONFLICTS_REGISTER" and "CONFLICTING_MODEL" in d.explanation


def test_second_read_seeing_two_serials_blocks_tier1() -> None:
    two = ModelEvidence.model_validate({**ev("GN-1001").model_dump(), "visible_identifiers": [
        {"kind": "serial", "value": "GN-1001", "readable": True}, {"kind": "serial", "value": "GN-7777", "readable": True}]})
    d, _ = decide([gen("A1", "GN-1001")], ev("GN-1001"), ok(two))
    assert d.matching_rule == "R2e_CONFIRMATION_UNREADABLE"


@pytest.mark.parametrize("typ", ["plate compactor", "plate heat exchanger", "label printer", "tag line"])
def test_plate_heuristic_does_not_block_real_equipment_words(typ: str) -> None:
    assert not _STANDALONE_PLATE.search(typ)


def test_needs_confirmation_skips_reads_that_cannot_reach_tier1() -> None:
    assert needs_confirmation(ev("GN-1001"))
    assert not needs_confirmation(ev("GN-1001", uncertain=True))
    assert not needs_confirmation(ev("GN1"))
    blurred = ModelEvidence.model_validate({**ev("GN-1001").model_dump(), "visible_identifiers": [
        {"kind": "serial", "value": "GN-1001", "readable": False}]})
    assert not needs_confirmation(blurred)


def test_live_budget_reserves_room_for_both_reads_on_single_extract(tmp_path) -> None:
    # extract_one must reserve two requests; with one, the second read is always starved (review finding 4)
    from app.pipeline import EST_EXTRACT_USD, Budget

    budget = Budget(True, 2, 2 * EST_EXTRACT_USD)
    budget.reserve(EST_EXTRACT_USD)
    budget.reserve(EST_EXTRACT_USD)
    src = Path(__file__).resolve().parents[1] / "app" / "pipeline.py"
    assert "self.budget_for(session_id, 2, 2 * EST_EXTRACT_USD)" in src.read_text()


def test_failed_second_read_marks_step_failed_and_allows_retry(tmp_path) -> None:
    client = TestClient(create_app(make_settings(tmp_path)))
    pipeline = client.app.state.pipeline
    inner = pipeline.ext

    class FailConfirm:
        name, model = inner.name, inner.model

        def extract_visual_evidence(self, crop, context, purpose="evidence"):
            if purpose == "confirm":
                raise ProviderError("timeout", "simulated second-read timeout")
            return inner.extract_visual_evidence(crop, context, purpose)

    pipeline.ext = FailConfirm()
    sid = client.post("/api/sessions", json={"name": "Gate", "facility_id": "WH-01"}).json()["id"]
    client.post(f"/api/sessions/{sid}/demo")
    run = wait_run(client, client.post(f"/api/sessions/{sid}/runs", json={"concept": "industrial generator"}).json()["id"])
    assert run["status"] == "partial"
    rows = client.get(f"/api/sessions/{sid}/detections").json()
    exact = next(r for r in rows if r["evidence"] and r["evidence"]["evidence"]
                 and r["evidence"]["evidence"]["visible_serial_number"] == "GN-48213")
    assert exact["decision"]["matching_rule"] == "R2e_CONFIRMATION_UNREADABLE"
    assert exact["evidence"]["confirmation"]["status"] == "error"
    pipeline.ext = inner  # retry both reads on the same detection: now confirmed
    assert client.post(f"/api/detections/{exact['detection']['id']}/extract").status_code == 200
    rows = client.get(f"/api/sessions/{sid}/detections").json()
    again = next(r for r in rows if r["detection"]["id"] == exact["detection"]["id"])
    assert again["decision"]["decision"] == "VERIFIED"


# ----- pipeline + API: the second read is made, persisted with provenance and drives the decision -----

class SecondReadOverride:
    """Wraps the fixture extractor; replaces only the confirm read for one serial."""

    def __init__(self, inner, serial: str, replacement: str | None) -> None:
        self.inner, self.serial, self.replacement = inner, serial, replacement
        self.name, self.model = inner.name, inner.model

    def extract_visual_evidence(self, crop, context, purpose="evidence"):
        result = self.inner.extract_visual_evidence(crop, context, purpose)
        if purpose == "confirm" and result.evidence.visible_serial_number == self.serial:
            idents = [i.model_copy(update={"value": self.replacement or "?"}) if i.value == self.serial else i
                      for i in result.evidence.visible_identifiers]
            changed = result.evidence.model_copy(update={"visible_serial_number": self.replacement,
                                                         "visible_identifiers": idents})
            return type(result)(evidence=changed, meta=result.meta)
        return result


def _demo(client: TestClient) -> str:
    sid = client.post("/api/sessions", json={"name": "Gate", "facility_id": "WH-01"}).json()["id"]
    assert client.post(f"/api/sessions/{sid}/demo").status_code == 200
    run = client.post(f"/api/sessions/{sid}/runs", json={"concept": "industrial generator"}).json()
    wait_run(client, run["id"])
    return sid


def test_pipeline_records_second_read_with_provenance(tmp_path) -> None:
    client = TestClient(create_app(make_settings(tmp_path)))
    sid = _demo(client)
    rows = client.get(f"/api/sessions/{sid}/detections").json()
    exact = next(r for r in rows if r["evidence"] and r["evidence"]["evidence"]
                 and r["evidence"]["evidence"]["visible_serial_number"] == "GN-48213")
    conf = exact["evidence"]["confirmation"]
    assert conf["status"] == "ok" and conf["provider_call_id"] and conf["view_ref"] and conf["created_at"]
    assert conf["model"] == "fixture-muse" and "autocontrast" in conf["view"]
    assert (tmp_path / "data" / conf["view_ref"]).is_file()
    assert exact["decision"]["decision"] == "VERIFIED" and "CONFIRMED_BY_SECOND_READ" in exact["decision"]["flags"]
    calls = client.get(f"/api/sessions/{sid}/trace").json()["provider_calls"]
    assert any(c["operation"] == "confirm" and c["id"] == conf["provider_call_id"] for c in calls)
    unreadable = next(r for r in rows if r["evidence"] and r["evidence"]["evidence"]
                      and r["evidence"]["evidence"]["visible_serial_number"] is None)
    assert unreadable["evidence"]["confirmation"] is None  # no serial to confirm: no second call is paid for


@pytest.mark.parametrize("replacement,rule", [
    ("GN-48218", "R2e_CONFIRMATION_SERIAL_DISAGREES"),
    (None, "R2e_CONFIRMATION_UNREADABLE"),
])
def test_pipeline_disagreeing_second_read_blocks_verification(tmp_path, replacement, rule) -> None:
    client = TestClient(create_app(make_settings(tmp_path)))
    pipeline = client.app.state.pipeline
    pipeline.ext = SecondReadOverride(pipeline.ext, "GN-48213", replacement)
    sid = _demo(client)
    rows = client.get(f"/api/sessions/{sid}/detections").json()
    exact = next(r for r in rows if r["evidence"] and r["evidence"]["evidence"]
                 and r["evidence"]["evidence"]["visible_serial_number"] == "GN-48213")
    assert exact["decision"]["decision"] == "PROBABLE" and exact["decision"]["matching_rule"] == rule


def test_human_review_policy_disables_tier1_end_to_end(tmp_path) -> None:
    try:
        client = TestClient(create_app(make_settings(tmp_path, tier1_policy="human_review")))
        sid = _demo(client)
        recon = client.get(f"/api/sessions/{sid}/reconciliation").json()
        assert not any(d["decision"] == "VERIFIED" for d in recon["decisions"])
    finally:
        set_tier1_policy("two_read")  # process-wide setting: never leak into later tests


# ----- D-17 (approved design): whole-photo regions and serial-only reads never auto-verify -----

def test_whole_photo_region_never_establishes_identity() -> None:
    first = ev("GN-1001")
    o = Observation("e1", "d1", "i1", F, "generator", "ok", first, None, ok(first), whole_photo=True)
    d = reconcile([gen("A1", "GN-1001")], [o], [], {(F, "generator")})[0][0]
    assert d.decision == "PROBABLE" and d.matching_rule == "R2e_WHOLE_PHOTO_ASSOCIATION_UNSUPPORTED"
    assert d.candidate_asset_ids == ["A1"]  # still a useful single suggestion for the reviewer


def test_s14_replay_whole_photo_with_agreeing_reads_still_needs_review() -> None:
    # s14 was a whole-photo region whose model type was plain "generator": the plate heuristic could not fire
    first = ev("5735", mfr="Marelli")
    o = Observation("e1", "d1", "i1", F, "generator", "ok", first, None, ok(first), whole_photo=True)
    d = reconcile([gen("U-s14-1", "5735", mfr="Marelli")], [o], [], {(F, "generator")})[0][0]
    assert d.decision != "VERIFIED" and d.review_required


def test_serial_only_read_needs_a_corroborating_attribute() -> None:
    bare = ModelEvidence(observed_object_type="generator", visible_serial_number="GN-1001")
    d, _ = decide([gen("A1", "GN-1001")], bare, ok(bare))
    assert d.matching_rule == "R2e_NO_CORROBORATING_ATTRIBUTE"
    # register row with no maker/model: nothing can corroborate (judge round 3 finding)
    blank = LedgerAsset("l-A1", "A1", "Generator", None, None, "GN-1001", F)
    d, _ = decide([blank], ev("GN-1001"), ok(ev("GN-1001")))
    assert d.matching_rule == "R2e_NO_CORROBORATING_ATTRIBUTE"
    # model alone corroborates
    model_only = ModelEvidence(observed_object_type="generator", visible_model="PX-500", visible_serial_number="GN-1001")
    assert decide([gen("A1", "GN-1001")], model_only, ok(model_only))[0].decision == "VERIFIED"


def test_demo_shows_two_reads_disagreeing(tmp_path) -> None:  # noqa: ANN001
    client = TestClient(create_app(make_settings(tmp_path)))
    sid = client.post("/api/sessions", json={"name": "Gate", "facility_id": "WH-01"}).json()["id"]
    client.post(f"/api/sessions/{sid}/demo")
    wait_run(client, client.post(f"/api/sessions/{sid}/runs", json={"concept": "generator"}).json()["id"])
    rows = client.get(f"/api/sessions/{sid}/detections").json()
    a004 = next(r for r in rows if r["evidence"] and (r["evidence"]["evidence"] or {}).get("visible_serial_number") == "GN-62040")
    assert a004["evidence"]["confirmation"]["evidence"]["visible_serial_number"] == "GN-62046"
    assert a004["decision"]["matching_rule"] == "R2e_CONFIRMATION_SERIAL_DISAGREES" and a004["decision"]["review_required"]
    assert any(r["decision"] and r["decision"]["decision"] == "VERIFIED" for r in rows)  # A-001 still verifies


def test_demo_whole_photo_region_never_verifies(tmp_path) -> None:  # noqa: ANN001
    # judge round 3, T9: a five-generator scene declared as one close-up auto-verified one asset
    client = TestClient(create_app(make_settings(tmp_path)))
    sid = client.post("/api/sessions", json={"name": "Gate", "facility_id": "WH-01"}).json()["id"]
    client.post(f"/api/sessions/{sid}/demo")
    ids = [i["id"] for i in client.get(f"/api/sessions/{sid}/images").json()]
    run = client.post(f"/api/sessions/{sid}/runs", json={"concept": "generator", "image_ids": ids,
                                                          "region": "full_frame", "extract": True}).json()
    wait_run(client, run["id"])
    decisions = client.get(f"/api/sessions/{sid}/reconciliation").json()["decisions"]
    assert decisions and not any(d["decision"] == "VERIFIED" for d in decisions)
