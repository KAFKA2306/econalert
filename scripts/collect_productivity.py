#!/usr/bin/env python3
"""Collect current BLS nonfarm-business productivity series through the Public Data API."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

API_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
SERIES = {
    "PRS85006092": "labor_productivity",
    "PRS85006042": "output",
    "PRS85006032": "hours_worked",
    "PRS85006102": "hourly_compensation",
    "PRS85006152": "real_hourly_compensation",
    "PRS85006112": "unit_labor_costs",
}


def fetch(start_year: int, end_year: int) -> bytes:
    body = json.dumps(
        {"seriesid": list(SERIES), "startyear": str(start_year), "endyear": str(end_year)}
    ).encode()
    request = Request(
        API_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "economic-releases/1.0 github.com/KAFKA2306/econalert",
        },
        method="POST",
    )
    with urlopen(request, timeout=60) as response:
        return response.read()


def parse(raw: bytes) -> list[dict[str, object]]:
    response = json.loads(raw)
    if response.get("status") != "REQUEST_SUCCEEDED":
        raise ValueError(f"BLS API request failed: {response.get('message')}")
    by_period: dict[str, dict[str, object]] = {}
    returned = set()
    for series in response.get("Results", {}).get("series", []):
        series_id = series.get("seriesID")
        if series_id not in SERIES:
            continue
        returned.add(series_id)
        metric = SERIES[series_id]
        for item in series.get("data", []):
            period = str(item.get("period", ""))
            if not period.startswith("Q"):
                continue
            key = f"{item['year']}-Q{int(period[1:])}"
            row = by_period.setdefault(key, {"period": key})
            row[metric] = float(item["value"])
            footnotes = [note.get("text") for note in item.get("footnotes", []) if note.get("text")]
            if footnotes:
                row.setdefault("footnotes", {})[metric] = footnotes
    missing_series = set(SERIES) - returned
    if missing_series:
        raise ValueError(f"BLS API omitted series: {sorted(missing_series)}")
    required = set(SERIES.values())
    observations = [row for row in by_period.values() if required.issubset(row)]
    observations.sort(key=lambda row: row["period"])
    if len(observations) < 8:
        raise ValueError(f"expected at least 8 complete quarters, found {len(observations)}")
    return observations


def collect() -> dict[str, object]:
    year = datetime.now(timezone.utc).year
    raw = fetch(year - 2, year)
    observations = parse(raw)
    return {
        "schema_version": 2,
        "publisher": "U.S. Bureau of Labor Statistics",
        "dataset": "Productivity and Costs",
        "sector": "Nonfarm business",
        "rate_basis": "percent change from previous quarter at annual rate",
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "source_url": API_URL,
        "series": SERIES,
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "observations": observations,
    }


def write_snapshot(payload: dict[str, object], output_dir: Path) -> Path:
    if len(payload["observations"]) < 8:
        raise ValueError("current productivity snapshot requires at least 8 quarters")
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{str(payload['source_sha256'])[:16]}.json"
    if not path.exists():
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("data/official/bls-productivity-current"))
    args = parser.parse_args()
    payload = collect()
    path = write_snapshot(payload, args.output_dir)
    print(f"wrote {len(payload['observations'])} quarters -> {path}")


if __name__ == "__main__":
    main()
