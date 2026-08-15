#!/usr/bin/env python3
"""Deterministic CPI contract-escalation calculation boundary.

This module does not choose a CPI series or interpret legal text. A contract profile
must explicitly name the series and observation periods. The source snapshot must
match that series exactly. Notice timing is only calculated when the profile provides
an explicit adjustment date and notice lead time.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any

READY = "READY_FOR_HUMAN_REVIEW"
WAITING = "WAITING_FOR_RELEASE"
MISSING_TERM = "MISSING_CONTRACT_TERM"
SOURCE_MISMATCH = "SOURCE_MISMATCH"

NOTICE_NOT_CONFIGURED = "NOT_CONFIGURED"
NOTICE_NOT_DUE = "NOT_DUE"
NOTICE_DUE = "DUE"
NOTICE_WINDOW_PASSED = "WINDOW_PASSED"


def _canonical_sha(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def _missing(profile: dict[str, Any], fields: tuple[str, ...]) -> list[str]:
    return [name for name in fields if profile.get(name) in (None, "")]


def _notice_decision(profile: dict[str, Any], as_of_date: str | None) -> dict[str, Any]:
    adjustment_raw = profile.get("adjustment_date")
    lead_raw = profile.get("notice_lead_days")
    if adjustment_raw in (None, "") or lead_raw in (None, ""):
        return {
            "state": NOTICE_NOT_CONFIGURED,
            "as_of_date": as_of_date,
            "adjustment_date": adjustment_raw,
            "notice_lead_days": lead_raw,
            "notice_deadline": None,
            "days_until_notice_deadline": None,
        }

    try:
        adjustment = date.fromisoformat(str(adjustment_raw))
        lead_days = int(lead_raw)
        if lead_days < 0:
            raise ValueError("negative notice lead")
        observed = date.fromisoformat(as_of_date) if as_of_date else None
    except (TypeError, ValueError):
        return {
            "state": MISSING_TERM,
            "reason": "invalid_notice_timing",
            "as_of_date": as_of_date,
            "adjustment_date": adjustment_raw,
            "notice_lead_days": lead_raw,
            "notice_deadline": None,
            "days_until_notice_deadline": None,
        }

    deadline = adjustment - timedelta(days=lead_days)
    state = NOTICE_NOT_CONFIGURED
    days_until = None
    if observed is not None:
        days_until = (deadline - observed).days
        if observed < deadline:
            state = NOTICE_NOT_DUE
        elif observed == deadline:
            state = NOTICE_DUE
        else:
            state = NOTICE_WINDOW_PASSED

    return {
        "state": state,
        "as_of_date": as_of_date,
        "adjustment_date": adjustment.isoformat(),
        "notice_lead_days": lead_days,
        "notice_deadline": deadline.isoformat(),
        "days_until_notice_deadline": days_until,
    }


def calculate(
    profile: dict[str, Any],
    snapshot: dict[str, Any],
    snapshot_sha256: str,
    *,
    as_of_date: str | None = None,
) -> dict[str, Any]:
    """Calculate one contract adjustment without guessing missing terms or data."""
    required = ("contract_id", "series_id", "base_period", "comparison_period", "formula", "clause_verified")
    missing = _missing(profile, required)
    if missing or profile.get("clause_verified") is not True:
        return _report(profile, snapshot, snapshot_sha256, MISSING_TERM, reason="missing_or_unverified_contract_term", missing=missing, as_of_date=as_of_date)

    if profile["formula"] != "percent_change":
        return _report(profile, snapshot, snapshot_sha256, MISSING_TERM, reason="unsupported_formula", as_of_date=as_of_date)

    notice = _notice_decision(profile, as_of_date)
    if notice["state"] == MISSING_TERM:
        return _report(profile, snapshot, snapshot_sha256, MISSING_TERM, reason="invalid_notice_timing", as_of_date=as_of_date)

    if snapshot.get("series_id") != profile["series_id"]:
        return _report(profile, snapshot, snapshot_sha256, SOURCE_MISMATCH, reason="series_id_mismatch", as_of_date=as_of_date)

    observations = {str(item.get("period")): item.get("value") for item in snapshot.get("observations", [])}
    base_period = str(profile["base_period"])
    comparison_period = str(profile["comparison_period"])
    if base_period not in observations:
        return _report(profile, snapshot, snapshot_sha256, MISSING_TERM, reason="base_observation_missing", as_of_date=as_of_date)
    if comparison_period not in observations:
        return _report(profile, snapshot, snapshot_sha256, WAITING, reason="comparison_observation_not_released", as_of_date=as_of_date)

    try:
        base = float(observations[base_period])
        comparison = float(observations[comparison_period])
    except (TypeError, ValueError):
        return _report(profile, snapshot, snapshot_sha256, MISSING_TERM, reason="non_numeric_observation", as_of_date=as_of_date)
    if base <= 0:
        return _report(profile, snapshot, snapshot_sha256, MISSING_TERM, reason="invalid_base_observation", as_of_date=as_of_date)

    raw_percent = (comparison / base - 1.0) * 100.0
    adjusted_percent = raw_percent
    floor = profile.get("floor_percent")
    cap = profile.get("cap_percent")
    if floor is not None and cap is not None and float(floor) > float(cap):
        return _report(profile, snapshot, snapshot_sha256, MISSING_TERM, reason="floor_exceeds_cap", as_of_date=as_of_date)
    if floor is not None:
        adjusted_percent = max(adjusted_percent, float(floor))
    if cap is not None:
        adjusted_percent = min(adjusted_percent, float(cap))

    expression = f"(({comparison:.12g} / {base:.12g}) - 1) * 100"
    report = _report(profile, snapshot, snapshot_sha256, READY, reason="calculation_ready", as_of_date=as_of_date)
    report["calculation"].update({
        "base_index": base,
        "comparison_index": comparison,
        "raw_percent_change": round(raw_percent, 8),
        "floor_percent": floor,
        "cap_percent": cap,
        "adjustment_percent": round(adjusted_percent, 8),
        "expression": expression,
    })
    report["calculation_revision"] = _canonical_sha({
        "profile": profile,
        "snapshot_sha256": snapshot_sha256,
        "calculation": report["calculation"],
        "decision": report["decision"],
    })
    return report


def _report(
    profile: dict[str, Any],
    snapshot: dict[str, Any],
    snapshot_sha256: str,
    status: str,
    *,
    reason: str,
    missing: list[str] | None = None,
    as_of_date: str | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": "contract-escalation-report.v2",
        "contract_id": profile.get("contract_id"),
        "status": status,
        "reason": reason,
        "missing_fields": missing or [],
        "contract_profile": {
            "series_id": profile.get("series_id"),
            "base_period": profile.get("base_period"),
            "comparison_period": profile.get("comparison_period"),
            "formula": profile.get("formula"),
        },
        "source": {
            "publisher": snapshot.get("publisher"),
            "series_id": snapshot.get("series_id"),
            "series_title": snapshot.get("series_title"),
            "source_url": snapshot.get("source_url"),
            "retrieved_at": snapshot.get("retrieved_at"),
            "snapshot_sha256": snapshot_sha256,
        },
        "calculation": {},
        "decision": {
            "notice": _notice_decision(profile, as_of_date),
            "interpretation": "Mechanical timing only; confirm the contract clause and legal requirements before action.",
        },
        "disclaimer": "Calculation evidence for human review; not legal advice or a price recommendation.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("profile", type=Path)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--as-of-date", help="ISO date used only for deterministic notice-window classification")
    args = parser.parse_args()
    profile = json.loads(args.profile.read_text(encoding="utf-8"))
    snapshot_bytes = args.snapshot.read_bytes()
    snapshot = json.loads(snapshot_bytes)
    result = calculate(
        profile,
        snapshot,
        hashlib.sha256(snapshot_bytes).hexdigest(),
        as_of_date=args.as_of_date,
    )
    text = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0 if result["status"] == READY else 2


if __name__ == "__main__":
    raise SystemExit(main())
