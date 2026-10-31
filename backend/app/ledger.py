"""CSV asset-register parsing and validation. Ledger text is evidence, never instructions."""

from __future__ import annotations

import csv
import io
import math
import re
from dataclasses import dataclass, field
from datetime import date

from .errors import ApiError
from .schemas import LedgerIssue
from .security import neutralize_csv_cell, sha256_bytes

REQUIRED_COLUMNS = ("asset_id", "asset_type", "facility_id")
KNOWN_COLUMNS = (
    "asset_id", "asset_type", "manufacturer", "model", "serial_number", "facility_id",
    "expected_location", "ledger_value", "currency", "inspection_date",
)
FIELD_LIMITS = {
    "asset_id": 80, "asset_type": 80, "manufacturer": 80, "model": 80, "serial_number": 80,
    "facility_id": 40, "expected_location": 200, "currency": 3,
}
_ASSET_ID = re.compile(r"^[A-Za-z0-9._/-]{1,80}$")
_CURRENCY = re.compile(r"^[A-Z]{3}$")


@dataclass
class ParsedLedger:
    rows: list[dict]
    issues: list[LedgerIssue]
    rejected: int
    sha256: str
    warnings_by_row: dict[int, list[str]] = field(default_factory=dict)


def _issue(row: int, fld: str | None, severity: str, code: str, message: str) -> LedgerIssue:
    return LedgerIssue(row=row, field=fld, severity=severity, code=code, message=message)


def _clean(raw: str | None) -> str | None:
    if raw is None:
        return None
    value = raw.strip()
    return value or None


def parse_ledger(data: bytes, max_rows: int, max_bytes: int) -> ParsedLedger:
    if len(data) > max_bytes:
        raise ApiError(413, "PAYLOAD_TOO_LARGE", f"ledger exceeds {max_bytes // (1024 * 1024)} MB")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ApiError(400, "VALIDATION_FAILED", "ledger must be UTF-8 encoded CSV") from exc
    if "\x00" in text:
        raise ApiError(400, "VALIDATION_FAILED", "ledger contains NUL bytes; not a text CSV")
    reader = csv.DictReader(io.StringIO(text))
    header = [h.strip().lower() for h in (reader.fieldnames or [])]
    missing = [c for c in REQUIRED_COLUMNS if c not in header]
    if missing:
        raise ApiError(400, "VALIDATION_FAILED", f"missing required columns: {', '.join(missing)}",
                       [{"field": c, "issue": "required column"} for c in missing])
    reader.fieldnames = header
    issues: list[LedgerIssue] = [
        _issue(1, col, "warning", "UNKNOWN_COLUMN", f"column '{col}' ignored")
        for col in header if col not in KNOWN_COLUMNS
    ]
    try:
        rows, rejected = _read_rows(reader, max_rows, issues)
    except csv.Error as exc:
        raise ApiError(400, "VALIDATION_FAILED", f"malformed CSV: {exc}") from exc
    issues.extend(_cross_row_checks(rows))
    return ParsedLedger(rows=rows, issues=issues, rejected=rejected, sha256=sha256_bytes(data))


def _read_rows(reader: csv.DictReader, max_rows: int, issues: list[LedgerIssue]) -> tuple[list[dict], int]:
    rows: list[dict] = []
    rejected = 0
    seen_ids: dict[str, int] = {}
    for index, raw in enumerate(reader, start=1):
        if index > max_rows:
            raise ApiError(400, "VALIDATION_FAILED", f"ledger exceeds {max_rows} rows")
        record, row_issues = _validate_row(raw, index)
        if record and record["asset_id"] in seen_ids:
            row_issues.append(_issue(index, "asset_id", "error", "DUPLICATE_ASSET_ID",
                                     f"asset_id duplicates row {seen_ids[record['asset_id']]}"))
            record = None
        issues.extend(row_issues)
        if record is None:
            rejected += 1
            continue
        seen_ids[record["asset_id"]] = index
        rows.append(record)
    return rows, rejected


def _validate_row(raw: dict, index: int) -> tuple[dict | None, list[LedgerIssue]]:
    issues: list[LedgerIssue] = []
    record: dict = {"source_row": index}
    for col in KNOWN_COLUMNS:
        value = _clean(raw.get(col))
        if value is not None:
            value, neutralized = neutralize_csv_cell(value)
            if neutralized and not (col == "ledger_value" and _is_number(value.lstrip("'"))):
                issues.append(_issue(index, col, "warning", "FORMULA_NEUTRALIZED",
                                     "cell began with a formula character; stored as text"))
            limit = FIELD_LIMITS.get(col)
            if limit and len(value) > limit:
                issues.append(_issue(index, col, "warning", "TRUNCATED", f"value truncated to {limit} chars"))
                value = value[:limit]
        record[col] = value
    for col in REQUIRED_COLUMNS:
        if not record.get(col):
            issues.append(_issue(index, col, "error", "REQUIRED_FIELD_MISSING", f"{col} is required"))
    if record.get("asset_id") and not _ASSET_ID.match(record["asset_id"]):
        issues.append(_issue(index, "asset_id", "error", "INVALID_ASSET_ID", "asset_id has unsupported characters"))
    record["ledger_value"] = _parse_value(record.get("ledger_value"), index, issues)
    currency = record.get("currency")
    if currency and not _CURRENCY.match(currency.upper()):
        issues.append(_issue(index, "currency", "warning", "INVALID_CURRENCY", "currency is not ISO 4217; ignored"))
        record["currency"] = None
    elif currency:
        record["currency"] = currency.upper()
    record["inspection_date"] = _parse_date(record.get("inspection_date"), index, issues)
    if not record.get("serial_number"):
        issues.append(_issue(index, "serial_number", "warning", "NO_SERIAL",
                             "no serial number: this asset cannot reach Tier 1 verification"))
    if any(i.severity == "error" for i in issues):
        return None, issues
    return record, issues


def _is_number(value: str) -> bool:
    """Any float literal (incl. inf/nan) is a number, not a formula; finiteness is checked in _parse_value."""
    try:
        float(value.replace(",", ""))
    except ValueError:
        return False
    return True


def _parse_value(value: str | None, index: int, issues: list[LedgerIssue]) -> float | None:
    if value is None:
        return None
    try:
        number = float(value.lstrip("'").replace(",", ""))
    except ValueError:
        issues.append(_issue(index, "ledger_value", "warning", "INVALID_NUMBER", "ledger_value is not a number; ignored"))
        return None
    if not math.isfinite(number):
        issues.append(_issue(index, "ledger_value", "warning", "INVALID_NUMBER",
                             "ledger_value is not a finite number (NaN/overflow); ignored"))
        return None
    if number < 0:
        issues.append(_issue(index, "ledger_value", "warning", "NEGATIVE_VALUE", "negative ledger_value recorded as stated"))
    return number


def _parse_date(value: str | None, index: int, issues: list[LedgerIssue]) -> str | None:
    if value is None:
        return None
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        issues.append(_issue(index, "inspection_date", "warning", "INVALID_DATE", "inspection_date not YYYY-MM-DD; ignored"))
        return None


def _cross_row_checks(rows: list[dict]) -> list[LedgerIssue]:
    from .reconcile import norm_id  # local import: reconcile owns normalization rules

    issues: list[LedgerIssue] = []
    by_serial: dict[str, list[dict]] = {}
    for row in rows:
        key = norm_id(row.get("serial_number"))
        if key:
            by_serial.setdefault(key, []).append(row)
    for group in by_serial.values():
        if len(group) > 1:
            ids = ", ".join(r["asset_id"] for r in group)
            for row in group:
                issues.append(_issue(row["source_row"], "serial_number", "warning", "DUPLICATE_SERIAL",
                                     f"serial shared by assets {ids}; matches will require review"))
    return issues
