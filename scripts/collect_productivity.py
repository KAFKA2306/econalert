#!/usr/bin/env python3
"""Collect BLS Productivity and Costs bulk time-series data.

The collector discovers series from BLS metadata instead of hard-coding series IDs.
It keeps source hashes, does not infer missing observations, and stores current-series
snapshots by source content so prior source states are not overwritten.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

BASE = "https://download.bls.gov/pub/time.series/pr"
URLS = {
    "series": f"{BASE}/pr.series",
    "sector": f"{BASE}/pr.sector",
    "measure": f"{BASE}/pr.measure",
    "data": f"{BASE}/pr.data.0.Current",
}
TARGET_SECTORS = ("nonfarm business", "manufacturing")
TARGET_MEASURES = (
    "output per hour",
    "output",
    "hours",
    "hourly compensation",
    "unit labor cost",
    "real hourly compensation",
)
CORE_NONFARM = (
    "labor_productivity",
    "output",
    "hours_worked",
    "hourly_compensation",
    "unit_labor_costs",
)


def fetch(url: str) -> bytes:
    req = Request(url, headers={"User-Agent": "economic-releases/1.0 github.com/KAFKA2306/econalert"})
    with urlopen(req, timeout=60) as response:
        return response.read()


def rows(raw: bytes) -> list[dict[str, str]]:
    text = raw.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text), delimiter="\t")
    return [{str(k).strip(): str(v or "").strip() for k, v in row.items()} for row in reader]


def lookup(table: list[dict[str, str]], code_hint: str) -> tuple[str, str]:
    if not table:
        raise ValueError("empty lookup table")
    keys = list(table[0])
    code_key = next((k for k in keys if code_hint in k.lower() and "code" in k.lower()), keys[0])
    name_key = next((k for k in keys if k != code_key and ("name" in k.lower() or "text" in k.lower())), keys[-1])
    return code_key, name_key


def select_series(series_rows: list[dict[str, str]], sectors: list[dict[str, str]], measures: list[dict[str, str]]) -> list[dict[str, str]]:
    sector_code, sector_name = lookup(sectors, "sector")
    measure_code, measure_name = lookup(measures, "measure")
    sector_map = {r[sector_code]: r[sector_name] for r in sectors}
    measure_map = {r[measure_code]: r[measure_name] for r in measures}

    selected: list[dict[str, str]] = []
    for row in series_rows:
        sid = row.get("series_id", row.get("seriesid", ""))
        s_code = row.get("sector_code", "")
        m_code = row.get("measure_code", "")
        s_name = sector_map.get(s_code, "")
        m_name = measure_map.get(m_code, "")
        if not sid:
            continue
        if not any(term in s_name.lower() for term in TARGET_SECTORS):
            continue
        if not any(term in m_name.lower() for term in TARGET_MEASURES):
            continue
        selected.append({
            "series_id": sid,
            "sector_code": s_code,
            "sector": s_name,
            "measure_code": m_code,
            "measure": m_name,
            "seasonal": row.get("seasonal", ""),
            "duration_code": row.get("duration_code", ""),
            "base_year": row.get("base_year", ""),
        })
    return selected


def canonical_measure(name: str) -> str | None:
    value = name.lower()
    if "output per hour" in value or "labor productivity" in value:
        return "labor_productivity"
    if "real hourly compensation" in value:
        return "real_hourly_compensation"
    if "hourly compensation" in value:
        return "hourly_compensation"
    if "unit labor cost" in value:
        return "unit_labor_costs"
    if "hours" in value:
        return "hours_worked"
    if "output" in value:
        return "output"
    return None


def coverage(payload: dict[str, object]) -> dict[str, int]:
    metadata = {row["series_id"]: row for row in payload["series"]}
    periods: dict[str, dict[str, set[tuple[str, str]]]] = {}
    for row in payload["observations"]:
        meta = metadata.get(row["series_id"])
        if not meta or "nonfarm business" not in meta["sector"].lower():
            continue
        measure = canonical_measure(meta["measure"])
        if measure is None:
            continue
        series_periods = periods.setdefault(measure, {}).setdefault(row["series_id"], set())
        if str(row.get("period", "")).upper().startswith("Q"):
            series_periods.add((str(row.get("year", "")), str(row.get("period", ""))))
    return {
        measure: max((len(values) for values in periods.get(measure, {}).values()), default=0)
        for measure in CORE_NONFARM
    }


def validate_coverage(payload: dict[str, object], minimum_quarters: int = 8) -> None:
    counts = coverage(payload)
    short = {measure: count for measure, count in counts.items() if count < minimum_quarters}
    if short:
        raise ValueError(f"nonfarm business quarterly coverage below {minimum_quarters}: {short}")


def collect() -> dict[str, object]:
    raw = {name: fetch(url) for name, url in URLS.items()}
    series_rows = rows(raw["series"])
    sector_rows = rows(raw["sector"])
    measure_rows = rows(raw["measure"])
    selected = select_series(series_rows, sector_rows, measure_rows)
    selected_ids = {row["series_id"] for row in selected}

    observations = []
    for row in rows(raw["data"]):
        sid = row.get("series_id", row.get("seriesid", ""))
        if sid not in selected_ids:
            continue
        observations.append({
            "series_id": sid,
            "year": row.get("year"),
            "period": row.get("period"),
            "value": row.get("value"),
            "footnote_codes": row.get("footnote_codes", ""),
        })

    return {
        "schema_version": 2,
        "publisher": "U.S. Bureau of Labor Statistics",
        "dataset": "Productivity and Costs",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "sources": {
            name: {"url": URLS[name], "sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content)}
            for name, content in raw.items()
        },
        "series": selected,
        "observations": observations,
    }


def source_fingerprint(payload: dict[str, object]) -> str:
    hashes = [f"{name}:{source['sha256']}" for name, source in sorted(payload["sources"].items())]
    return hashlib.sha256("\n".join(hashes).encode()).hexdigest()[:16]


def write_snapshot(payload: dict[str, object], output_dir: Path) -> Path:
    validate_coverage(payload)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{source_fingerprint(payload)}.json"
    if not path.exists():
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("data/official/bls-productivity-current"))
    args = parser.parse_args()
    payload = collect()
    if not payload["series"] or not payload["observations"]:
        raise SystemExit("BLS productivity selection returned no data")
    path = write_snapshot(payload, args.output_dir)
    print(f"wrote {len(payload['series'])} series / {len(payload['observations'])} observations -> {path}")


if __name__ == "__main__":
    main()
