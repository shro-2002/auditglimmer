"""Deterministic, explainable reconciliation of visual evidence against an asset register.

Pure functions only: same inputs -> same outputs. No model calls. Rules (docs/decisions.md D-07):
  Tier 1  VERIFIED     unique readable serial == exactly one ledger serial, no conflicting fields
  Tier 2  PROBABLE     manufacturer+model match (or uncertain/duplicated serial) -> human review
  Tier 3  WEAK         asset type only -> human review
  Tier 4  NOT_IN_REGISTER  no supported match
  MISMATCHED           identifiers conflict with the best candidate -> human review
Ambiguous matches are never resolved automatically. Absence of evidence -> UNVERIFIED, never MISSING.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .schemas import ModelEvidence

MIN_SERIAL_LEN = 4
MAX_WEAK_CANDIDATES = 10
SCORE_SERIAL = 0.6
SCORE_MANUFACTURER = 0.15
SCORE_MODEL = 0.15
SCORE_TYPE = 0.1
CONFLICT_PENALTY = 0.3

TYPE_SYNONYMS = {
    "generator": "generator", "industrial generator": "generator", "genset": "generator",
    "diesel generator": "generator", "standby generator": "generator", "power generator": "generator",
    "forklift": "forklift", "fork lift": "forklift", "forklift truck": "forklift", "lift truck": "forklift",
    "counterbalance forklift": "forklift", "air compressor": "compressor", "compressor": "compressor",
    "pallet racking": "racking", "racking": "racking", "storage rack": "racking", "alternator": "generator",
    "electric motor": "electric motor", "induction motor": "electric motor", "motor": "electric motor",
    "outboard motor": "outboard motor", "outboard engine": "outboard motor",
    "engine": "engine", "aircraft engine": "engine", "aviation engine": "engine", "diesel engine": "engine",
    "excavator": "excavator", "hydraulic excavator": "excavator", "tractor": "tractor",
    "transformer": "transformer", "load interrupter": "switchgear", "switchgear": "switchgear",
}

_NON_ALNUM = re.compile(r"[\W_]+")  # unicode-aware: keeps letters like Ü, drops separators


def norm_id(value: str | None) -> str | None:
    """Identifier normalization: uppercase, drop separators. 'gn-482 13' == 'GN48213'."""
    if not value:
        return None
    key = _NON_ALNUM.sub("", value.upper())
    return key or None


def norm_text(value: str | None) -> str | None:
    if not value:
        return None
    key = _NON_ALNUM.sub("", value.upper())
    return key or None


# Brand abbreviations commonly printed on equipment vs. legal names in registers (normalized keys).
MANUFACTURER_ALIASES = {"CAT": "CATERPILLAR", "JD": "JOHNDEERE", "MHI": "MITSUBISHIHEAVYINDUSTRIES"}


def norm_manufacturer(value: str | None) -> str | None:
    key = norm_text(value)
    return MANUFACTURER_ALIASES.get(key, key) if key else None


_LEGAL_SUFFIXES = {"GMBH", "AG", "KG", "CO", "CORP", "CORPORATION", "INC", "LTD", "LLC", "SA", "SPA", "BV", "NV",
                   "PLC", "COMPANY", "OHG", "MBH"}


def _maker_tokens(value: str | None) -> list[str]:
    tokens = [t for t in _NON_ALNUM.split((value or "").upper()) if t]
    return [t for t in tokens if t not in _LEGAL_SUFFIXES]


def same_manufacturer(observed: str | None, registered: str | None) -> bool:
    """Plates print the full maker line ("ANTON PILLER KG", "Pratt & Whitney Aircraft"); registers keep the short
    name. Match when the register's words start the plate's maker line (legal suffixes ignored) or aliases agree."""
    a, b = norm_manufacturer(observed), norm_manufacturer(registered)
    if not (a and b):
        return False
    if a == b:
        return True
    plate, register = _maker_tokens(observed), _maker_tokens(registered)
    distinctive = len(register) >= 2 or len("".join(register)) >= 3
    # one direction only: the plate may add words after the register name, never the reverse
    return bool(register) and distinctive and plate[:len(register)] == register


def canonical_type(value: str | None) -> str | None:
    if not value:
        return None
    phrase = " ".join(value.lower().replace("-", " ").split())
    if phrase in TYPE_SYNONYMS:
        return TYPE_SYNONYMS[phrase]
    singular = " ".join(w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith("ss") else w
                        for w in phrase.split())
    if singular in TYPE_SYNONYMS:
        return TYPE_SYNONYMS[singular]
    phrase = singular
    for synonym, canon in sorted(TYPE_SYNONYMS.items(), key=lambda kv: -len(kv[0])):
        if re.search(rf"\b{re.escape(synonym)}\b", phrase):
            return canon
    return phrase


@dataclass(frozen=True)
class LedgerAsset:
    ledger_record_id: str
    asset_id: str
    asset_type: str
    manufacturer: str | None
    model: str | None
    serial_number: str | None
    facility_id: str


@dataclass(frozen=True)
class Observation:
    evidence_id: str
    detection_id: str
    image_id: str
    facility_id: str
    concept: str
    status: str  # ok | invalid | error
    evidence: ModelEvidence | None
    error: str | None = None


@dataclass(frozen=True)
class Review:
    decision_id: str
    action: str  # confirm | reject
    asset_id: str | None


@dataclass
class DecisionResult:
    id: str
    evidence_id: str
    detection_id: str
    image_id: str
    decision: str
    tier: int | None
    matching_rule: str
    candidate_asset_ids: list[str]
    matched_asset_id: str | None
    match_score: float
    review_required: bool
    explanation: str
    unmatched_fields: list[str]
    flags: list[str] = field(default_factory=list)

    @property
    def evidence_ids(self) -> list[str]:
        return [self.evidence_id]


@dataclass(frozen=True)
class AssetResult:
    asset_id: str
    ledger_record_id: str
    status: str
    decision_ids: list[str]
    reason: str
    human_confirmed: bool


def decision_id_for(evidence_id: str) -> str:
    return f"dec_{evidence_id}"


def _serial_state(ev: ModelEvidence) -> tuple[str | None, bool]:
    """Return (normalized serial, is_uncertain)."""
    serial = norm_id(ev.visible_serial_number)
    if not serial or len(serial) < MIN_SERIAL_LEN:
        return None, False
    uncertain = any(u.field == "visible_serial_number" for u in ev.uncertainties)
    for ident in ev.visible_identifiers:
        if ident.kind == "serial" and norm_id(ident.value) == serial and not ident.readable:
            uncertain = True
    return serial, uncertain


def _observed_type(obs: Observation) -> str | None:
    if obs.evidence and obs.evidence.observed_object_type:
        return canonical_type(obs.evidence.observed_object_type)
    return canonical_type(obs.concept)


def _compare(ev: ModelEvidence, obs_type: str | None, asset: LedgerAsset) -> tuple[float, list[str], list[str]]:
    """Score one candidate. Returns (score, conflict flags, unmatched fields)."""
    score, conflicts, unmatched = 0.0, [], []
    serial = norm_id(ev.visible_serial_number)
    asset_serial = norm_id(asset.serial_number)
    if serial and asset_serial and serial == asset_serial:
        score += SCORE_SERIAL
    elif serial and asset_serial:
        conflicts.append("CONFLICTING_SERIAL")
        unmatched.append("serial_number")
    else:
        unmatched.append("serial_number")
    for attr, ev_value, weight, flag in (
        ("manufacturer", ev.visible_manufacturer, SCORE_MANUFACTURER, "CONFLICTING_MANUFACTURER"),
        ("model", ev.visible_model, SCORE_MODEL, "CONFLICTING_MODEL"),
    ):
        norm = norm_manufacturer if attr == "manufacturer" else norm_text
        a, b = norm(ev_value), norm(getattr(asset, attr))
        same = same_manufacturer(ev_value, asset.manufacturer) if attr == "manufacturer" else a == b
        if a and b and same:
            score += weight
        elif a and b:
            conflicts.append(flag)
            unmatched.append(attr)
        else:
            unmatched.append(attr)
    if obs_type and obs_type == canonical_type(asset.asset_type):
        score += SCORE_TYPE
    else:
        conflicts.append("TYPE_CONFLICT")
        unmatched.append("asset_type")
    score -= CONFLICT_PENALTY * len(conflicts)
    return round(max(0.0, min(1.0, score)), 3), conflicts, unmatched


def _decide(obs: Observation, assets: list[LedgerAsset]) -> DecisionResult:
    did = decision_id_for(obs.evidence_id)
    base = dict(id=did, evidence_id=obs.evidence_id, detection_id=obs.detection_id, image_id=obs.image_id)
    if obs.status != "ok" or obs.evidence is None:
        return DecisionResult(
            **base, decision="EVIDENCE_UNUSABLE", tier=None, matching_rule="R0_EXTRACTION_FAILED",
            candidate_asset_ids=[], matched_asset_id=None, match_score=0.0, review_required=False,
            explanation=f"No usable structured evidence ({obs.status}): {obs.error or 'unknown error'}. "
                        "No match is attempted on unvalidated output.",
            unmatched_fields=["serial_number", "manufacturer", "model", "asset_type"], flags=["EXTRACTION_FAILED"],
        )
    ev = obs.evidence
    obs_type = _observed_type(obs)
    flags: list[str] = []
    if obs_type != canonical_type(obs.concept):
        flags.append("TYPE_DISAGREES_WITH_CONCEPT")
    serial, uncertain = _serial_state(ev)
    other_serials = {
        key for i in ev.visible_identifiers
        if i.kind == "serial" and i.readable and (key := norm_id(i.value)) and len(key) >= MIN_SERIAL_LEN
    } - {serial}
    if serial and other_serials:
        uncertain = True
        flags.append("MULTIPLE_SERIALS_VISIBLE")
    pool = [a for a in assets if a.facility_id == obs.facility_id]
    if serial:
        hits = [a for a in assets if norm_id(a.serial_number) == serial]
        if hits:
            return _serial_hit(obs, ev, obs_type, hits, uncertain, flags, base)
        if uncertain:  # an uncertain reading that matches nothing is not evidence of an unregistered serial
            return _no_serial(obs, ev, obs_type, pool, flags + ["SERIAL_UNCERTAIN"], base)
        return _serial_miss(obs, ev, obs_type, pool, flags, base)
    return _no_serial(obs, ev, obs_type, pool, flags, base)


def _serial_hit(obs, ev, obs_type, hits, uncertain, flags, base) -> DecisionResult:  # noqa: ANN001
    ids = [a.asset_id for a in hits]
    if len(hits) > 1:
        score, _, unmatched = _compare(ev, obs_type, hits[0])
        return DecisionResult(
            **base, decision="PROBABLE", tier=2, matching_rule="R2b_SERIAL_DUPLICATED_IN_LEDGER",
            candidate_asset_ids=ids, matched_asset_id=None, match_score=score, review_required=True,
            explanation=f"Visible serial matches {len(hits)} ledger assets ({', '.join(ids)}). "
                        "The register itself is contradictory, so no automatic match is made.",
            unmatched_fields=unmatched, flags=flags + ["DUPLICATE_SERIAL_IN_LEDGER"],
        )
    asset = hits[0]
    score, conflicts, unmatched = _compare(ev, obs_type, asset)
    if asset.facility_id != obs.facility_id:
        conflicts.append("FACILITY_MISMATCH")
    if conflicts:
        return DecisionResult(
            **base, decision="MISMATCHED", tier=None, matching_rule="R5_SERIAL_MATCH_WITH_CONFLICTS",
            candidate_asset_ids=[asset.asset_id], matched_asset_id=None, match_score=score, review_required=True,
            explanation=f"Visible serial matches {asset.asset_id}, but other identifiers conflict "
                        f"({', '.join(sorted(set(conflicts)))}). Requires human review.",
            unmatched_fields=unmatched, flags=flags + sorted(set(conflicts)),
        )
    if uncertain:
        return DecisionResult(
            **base, decision="PROBABLE", tier=2, matching_rule="R2c_SERIAL_UNCERTAIN",
            candidate_asset_ids=[asset.asset_id], matched_asset_id=None, match_score=score, review_required=True,
            explanation=f"Serial reading matches {asset.asset_id} but the extraction marked it uncertain. "
                        "Uncertain identifiers never auto-verify.",
            unmatched_fields=unmatched, flags=flags + ["SERIAL_UNCERTAIN"],
        )
    return DecisionResult(
        **base, decision="VERIFIED", tier=1, matching_rule="R1_UNIQUE_SERIAL_MATCH",
        candidate_asset_ids=[asset.asset_id], matched_asset_id=asset.asset_id, match_score=score,
        review_required=False,
        explanation=f"Readable visible serial uniquely matches {asset.asset_id}; manufacturer, model and type "
                    "do not conflict. Verified by identifier evidence only — not proof of ownership, condition or value.",
        unmatched_fields=unmatched, flags=flags,
    )


def _mfr_model_matches(ev: ModelEvidence, obs_type: str | None, pool: list[LedgerAsset]) -> list[LedgerAsset]:
    mfr, mdl = norm_manufacturer(ev.visible_manufacturer), norm_text(ev.visible_model)
    if not (mfr and mdl):
        return []
    return [
        a for a in pool
        if same_manufacturer(ev.visible_manufacturer, a.manufacturer) and norm_text(a.model) == mdl
        and canonical_type(a.asset_type) == obs_type
    ]


def _serial_miss(obs, ev, obs_type, pool, flags, base) -> DecisionResult:  # noqa: ANN001
    mm = _mfr_model_matches(ev, obs_type, pool)
    if mm:
        score, _, unmatched = _compare(ev, obs_type, mm[0])
        return DecisionResult(
            **base, decision="MISMATCHED", tier=None, matching_rule="R6_SERIAL_NOT_IN_REGISTER_MODEL_MATCHES",
            candidate_asset_ids=[a.asset_id for a in mm], matched_asset_id=None, match_score=score,
            review_required=True,
            explanation="Manufacturer and model match register entries, but the readable visible serial does not "
                        "match any ledger serial. Possible ledger error or different unit.",
            unmatched_fields=unmatched, flags=flags + ["CONFLICTING_SERIAL"],
        )
    return DecisionResult(
        **base, decision="NOT_IN_REGISTER", tier=4, matching_rule="R4_UNREGISTERED_SERIAL",
        candidate_asset_ids=[], matched_asset_id=None, match_score=0.0, review_required=True,
        explanation="Readable serial and manufacturer/model match no register entry. Observed object appears "
                    "absent from the register.",
        unmatched_fields=["serial_number", "manufacturer", "model"], flags=flags + ["OBSERVED_NOT_IN_REGISTER"],
    )


def _no_serial(obs, ev, obs_type, pool, flags, base) -> DecisionResult:  # noqa: ANN001
    mm = _mfr_model_matches(ev, obs_type, pool)
    if mm:
        score, _, unmatched = _compare(ev, obs_type, mm[0])
        ambiguous = len(mm) > 1
        return DecisionResult(
            **base, decision="PROBABLE", tier=2,
            matching_rule="R2a_MANUFACTURER_MODEL_AMBIGUOUS" if ambiguous else "R2_MANUFACTURER_MODEL_UNIQUE",
            candidate_asset_ids=[a.asset_id for a in mm], matched_asset_id=None, match_score=score,
            review_required=True,
            explanation=(f"No readable serial. Manufacturer and model match {len(mm)} register assets; "
                         "similar-looking units cannot be told apart automatically.") if ambiguous else
                        (f"No readable serial. Manufacturer and model match {mm[0].asset_id} only. "
                         "Without a unique identifier this is a probable match pending review."),
            unmatched_fields=unmatched, flags=flags + (["AMBIGUOUS_CANDIDATES"] if ambiguous else []),
        )
    typed = [a for a in pool if canonical_type(a.asset_type) == obs_type]
    if typed:
        mfr = norm_manufacturer(ev.visible_manufacturer)
        same_mfr = [a for a in typed if mfr and same_manufacturer(ev.visible_manufacturer, a.manufacturer)]
        typed = (same_mfr or typed)[:MAX_WEAK_CANDIDATES]
        supported = f"asset type ({obs_type}) and manufacturer ({ev.visible_manufacturer})" if same_mfr \
            else f"asset type ({obs_type})"
        score, _, unmatched = _compare(ev, obs_type, typed[0])
        return DecisionResult(
            **base, decision="WEAK", tier=3, matching_rule="R3_TYPE_ONLY",
            candidate_asset_ids=[a.asset_id for a in typed], matched_asset_id=None, match_score=score,
            review_required=True,
            explanation=f"Only the {supported} is supported by visible evidence; "
                        f"{len(typed)} register assets are possible. Weak similarity — human review required.",
            unmatched_fields=unmatched, flags=flags,
        )
    return DecisionResult(
        **base, decision="NOT_IN_REGISTER", tier=4, matching_rule="R4_NO_SUPPORTED_MATCH",
        candidate_asset_ids=[], matched_asset_id=None, match_score=0.0, review_required=True,
        explanation=f"No register asset of type '{obs_type}' at facility {obs.facility_id} is supported by the evidence.",
        unmatched_fields=["serial_number", "manufacturer", "model", "asset_type"],
        flags=flags + ["OBSERVED_NOT_IN_REGISTER"],
    )


def _flag_duplicate_observations(decisions: list[DecisionResult], observations: list[Observation]) -> None:
    """Same identifier read on several detected objects: never auto-verify any of them."""
    by_serial: dict[str, list[DecisionResult]] = {}
    obs_by_id = {o.evidence_id: o for o in observations}
    for dec in decisions:
        obs = obs_by_id[dec.evidence_id]
        if obs.evidence is None:
            continue
        serial, _ = _serial_state(obs.evidence)
        if serial:
            by_serial.setdefault(serial, []).append(dec)
    for group in by_serial.values():
        if len(group) < 2:
            continue
        for dec in group:
            dec.flags.append("DUPLICATE_IDENTIFIER_OBSERVATION")
            if dec.decision == "VERIFIED":
                dec.decision, dec.tier, dec.review_required = "PROBABLE", 2, True
                dec.matched_asset_id = None
                dec.matching_rule = "R2d_IDENTIFIER_SEEN_ON_MULTIPLE_OBJECTS"
                dec.explanation = (
                    f"Serial matches {dec.candidate_asset_ids[0]}, but the same identifier was read on "
                    f"{len(group)} detected objects (re-photographed asset or duplicated tag). Review required."
                )


def _flag_competing_claims(decisions: list[DecisionResult], observations: list[Observation]) -> None:
    """Several distinct objects whose only candidate is the same ledger asset: one asset cannot be two objects."""
    obs_by_id = {o.evidence_id: o for o in observations}
    by_asset: dict[str, list[DecisionResult]] = {}
    for dec in decisions:
        target = dec.matched_asset_id or (dec.candidate_asset_ids[0] if len(dec.candidate_asset_ids) == 1 else None)
        if target:
            by_asset.setdefault(target, []).append(dec)
    for asset_id, group in by_asset.items():
        serials = {(_serial_state(obs_by_id[d.evidence_id].evidence)[0] if obs_by_id[d.evidence_id].evidence else None)
                   for d in group}
        if len(group) < 2 or (len(serials) == 1 and None not in serials):
            continue  # same identifier read twice = same physical asset photographed twice
        for dec in group:
            dec.flags.append("COMPETING_FOR_ASSET")
            dec.explanation += (f" {len(group)} distinct detected objects point to {asset_id}; "
                                "at most one of them can be that asset.")


def reconcile(
    assets: list[LedgerAsset],
    observations: list[Observation],
    reviews: list[Review],
    inspected: set[tuple[str, str]],
) -> tuple[list[DecisionResult], list[AssetResult]]:
    """inspected: {(facility_id, canonical_type)} covered by at least one inspection run."""
    ordered = sorted(observations, key=lambda o: (o.image_id, o.detection_id))
    decisions = [_decide(o, assets) for o in ordered]
    _flag_duplicate_observations(decisions, ordered)
    _flag_competing_claims(decisions, ordered)
    latest = {r.decision_id: r for r in reviews}
    return decisions, _asset_results(assets, decisions, latest, inspected)


_RANK = {"HUMAN": 5, "VERIFIED": 4, "MISMATCHED": 3, "PROBABLE": 2}


def _asset_results(assets, decisions, latest, inspected) -> list[AssetResult]:  # noqa: ANN001
    results = []
    for asset in sorted(assets, key=lambda a: a.asset_id):
        best, best_rank, linked, human, contrary = None, 0, [], False, []
        for dec in decisions:
            if asset.asset_id not in dec.candidate_asset_ids:
                continue
            linked.append(dec.id)
            review = latest.get(dec.id)
            if review and review.action == "reject" and review.asset_id in (None, asset.asset_id):
                continue  # a reject naming another asset leaves this candidate link intact
            if review and review.action == "confirm" and review.asset_id:
                if review.asset_id == asset.asset_id:
                    best, best_rank, human = "HUMAN_CONFIRMED", _RANK["HUMAN"], True
                continue
            if dec.decision == "MISMATCHED" and review is None:
                contrary.append(dec.id)
            rank = _RANK.get(dec.decision, 0)
            if rank > best_rank:
                best, best_rank = dec.decision, rank
        if human and contrary:  # a human assertion never hides unresolved conflicting evidence
            reason = (f"Human-confirmed, but conflicting identifier evidence is unresolved "
                      f"({', '.join(contrary)}); resolve before relying on it.")
            results.append(AssetResult(asset.asset_id, asset.ledger_record_id, "MISMATCHED", linked, reason, True))
            continue
        if best:
            reason = {
                "HUMAN_CONFIRMED": "Asserted by a named human reviewer (see review note); "
                                   "not an automatic identifier match.",
                "VERIFIED": "Unique identifier match (Tier 1).",
                "MISMATCHED": "Evidence links to this asset but identifiers conflict; review.",
                "PROBABLE": "Probable match pending human review; see the linked decision for the rule applied.",
            }[best]
            results.append(AssetResult(asset.asset_id, asset.ledger_record_id, best, linked, reason, human))
            continue
        covered = (asset.facility_id, canonical_type(asset.asset_type)) in inspected
        status = "UNVERIFIED" if covered else "NOT_OBSERVABLE"
        reason = (
            "Its facility and asset type were inspected, but no adequate visual evidence links to it. "
            "Not evidence that the asset is missing."
            if covered else "No inspection covered this asset's facility and type."
        )
        results.append(AssetResult(asset.asset_id, asset.ledger_record_id, status, linked, reason, False))
    return results
