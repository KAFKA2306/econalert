#!/usr/bin/env python3
"""Deterministic CPI contract-escalation calculation boundary.

This module does not choose a CPI series or interpret legal text. A contract profile
must explicitly name the series and observation periods. The source snapshot must
match that series exactly.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

READY = "READY_FOR_HUMAN_REVIEW"
WAITING = "WAITING_FOR_RELEASE"
MISSING_TERM = "MISSING_CONTRACT_TERM"
SOURCE_MISMATCH = "SOURCE_MISMATCH"


def _canonical_sha(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def _missing(profile: dict[str, Any], fields: tuple[str, ...]) -> list[str]:
    return [name for name in fields if profile.get(name) in (None, "")]


def calculate(profile: dict[str, Any], snapshot: dict[str, Any], snapshot_sha256: str) -> dict[str, Any]:
    """Calculate one contract adjustment without guessing missing terms or data."""
    required = ("contract_id", "series_id", "base_period", "comparison_period", "formula", "clause_verified")
    missing = _missing(profile, required)
    if missing or profile.get("clause_verified") is not True:
        return _report(profile, snapshot, snapshot_sha256, MISSING_TERM, reason="missing_or_unverified_contract_term", missing=missing)

    if profile["formula"] != "percent_change":
        return _report(profile, snapshot, snapshot_sha256, MISSING_TERM, reason="unsupported_formula")

    if snapshot.get("series_id") != profile["series_id"]:
        return _report(profile, snapshot, snapshot_sha256, SOURCE_MISMATCH, reason="series_id_mismatch")

    observations = {str(item.get("period")): item.get("value") for item in snapshot.get("observations", [])}
    base_period = str(profile["base_period"])
    comparison_period = str(profile["comparison_period"])
    if base_period not in observations:
        return _report(profile, snapshot, snapshot_sha256, MISSING_TERM, reason="base_observation_missing")
    if comparison_period not in observations:
        return _report(profile, snapshot, snapshot_sha256, WAITING, reason="comparison_observation_not_released")

    try:
        base = float(observations[base_period])
        comparison = float(observations[comparison_period])
    except (TypeError, ValueError):
        return _report(profile, snapshot, snapshot_sha256, MISSING_TERM, reason="non_numeric_observation")
    if base <= 0:
        return _report(profile, snapshot, snapshot_sha256, MISSING_TERM, reason="invalid_base_observation")

    raw_percent = (comparison / base - 1.0) * 100.0
    adjusted_percent = raw_percent
    floor = profile.get("floor_percent")
    cap = profile.get("cap_percent")
    if floor is not None:
        adjusted_percent = max(adjusted_percent, float(floor))
    if cap is not None:
        adjusted_percent = min(adjusted_percent, float(cap))
    if floor is not None and cap is not None and float(floor) > float(cap):
        return _report(profile, snapshot, snapshot_sha256, MISSING_TERM, reason="floor_exceeds_cap")

    expression = f"(({comparison:.12g} / {base:.12g}) - 1) * 100"
    report = _report(profile, snapshot, snapshot_sha256, READY, reason="calculation_ready")
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
    })
    return report


def _report(profile: dict[str, Any], snapshot: dict[str, Any], snapshot_sha256: str, status: str, *, reason: str, missing: list[str] | None = None) -> dict[str, Any]:
    return {
        "schema_version": "contract-escalation-report.v1",
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
        "disclaimer": "Calculation evidence for human review; not legal advice or a price recommendation.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("profile", type=Path)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    profile = json.loads(args.profile.read_text(encoding="utf-8"))
    snapshot_bytes = args.snapshot.read_bytes()
    snapshot = json.loads(snapshot_bytes)
    result = calculate(profile, snapshot, hashlib.sha256(snapshot_bytes).hexdigest())
    text = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0 if result["status"] == READY else 2


if __name__ == "__main__":
    raise SystemExit(main())
