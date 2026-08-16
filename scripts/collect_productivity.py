#!/usr/bin/env python3
"""Collect BLS Productivity and Costs bulk time-series data.

The collector discovers series from BLS metadata instead of hard-coding series IDs.
It keeps source hashes and does not infer missing observations.
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


def fetch(url: str) -> bytes:
    req = Request(url, headers={"User-Agent": "econalert/1.0 contact: github.com/KAFKA2306/econalert"})
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
        "schema_version": 1,
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("data/official/bls-productivity-current.json"))
    args = parser.parse_args()
    payload = collect()
    if not payload["series"] or not payload["observations"]:
        raise SystemExit("BLS productivity selection returned no data")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(payload['series'])} series / {len(payload['observations'])} observations -> {args.output}")


if __name__ == "__main__":
    main()
