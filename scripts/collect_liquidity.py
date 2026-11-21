#!/usr/bin/env python3
"""Track public FRED liquidity observations without conflating frequencies or vintages."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import statistics
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen

# FRED's graph CSV is a public download surface, not its versioned official API.
# Fail closed if the format or availability changes; never substitute estimates.
SERIES = {
    "SOFR": ("percent", "daily", True),
    "DFF": ("percent", "daily", True),
    "BAMLH0A0HYM2": ("percent", "daily", True),
    "BAMLC0A0CM": ("percent", "daily", True),
    "WRESBAL": ("million_usd", "weekly", True),
    "STLFSI4": ("index", "weekly", True),
    "IORB": ("percent", "daily", False),
    "WALCL": ("million_usd", "weekly", False),
    "WTREGEN": ("million_usd_weekly_average", "weekly", False),
    "RRPONTSYD": ("billion_usd", "daily", False),
}


def fetch(series_id: str, today: date) -> tuple[bytes, str]:
    # Fixed query window: a moving cutoff would change the raw hash without new releases.
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}&cosd=2024-01-01"
    request = Request(url, headers={"User-Agent": "econalert-liquidity/1.0 (github.com/KAFKA2306/econalert)"})
    with urlopen(request, timeout=35) as response:
        if "text/html" in response.headers.get("Content-Type", ""):
            raise ValueError(f"FRED did not return CSV: {series_id}")
        raw = response.read(4_000_001)
    if len(raw) > 4_000_000:
        raise ValueError(f"FRED response unexpectedly large: {series_id}")
    return raw, url


def parse_csv(raw: bytes, series_id: str) -> list[dict]:
    try:
        reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
        fields = reader.fieldnames or []
        if len(fields) != 2 or series_id not in fields or not set(fields) & {"DATE", "observation_date"}:
            raise ValueError(f"unexpected FRED CSV header for {series_id}: {fields}")
        date_key = next(k for k in fields if k != series_id)
        observations = []
        for row in reader:
            if not row or row[series_id] in (None, "", "."):
                continue
            observed = date.fromisoformat(row[date_key])
            value = float(row[series_id])
            if not math.isfinite(value):
                raise ValueError(f"nonfinite observation: {series_id} {observed}")
            if observations and observed <= date.fromisoformat(observations[-1]["date"]):
                raise ValueError(f"non-increasing observation dates: {series_id}")
            observations.append({"date": observed.isoformat(), "value": value})
    except (UnicodeDecodeError, TypeError, KeyError) as exc:
        raise ValueError(f"invalid FRED data: {series_id}") from exc
    if len(observations) < 8:
        raise ValueError(f"too few FRED observations: {series_id}")
    return observations[-150:]


def four_week_change(series: dict) -> dict | None:
    rows = series["observations"]
    latest = rows[-1]
    target = date.fromisoformat(latest["date"]) - timedelta(days=28)
    previous = next((r for r in reversed(rows[:-1]) if date.fromisoformat(r["date"]) <= target), None)
    if not previous:
        return None
    return {"from_date": previous["date"], "to_date": latest["date"],
            "difference": round(latest["value"] - previous["value"], 6),
            "percent_change": round((latest["value"] / previous["value"] - 1) * 100, 6) if previous["value"] else None}


def assess(series: dict, today: date) -> dict:
    required = [k for k, (_, _, must_have) in SERIES.items() if must_have]
    stale = [k for k in required if k not in series or series[k]["stale"]]
    if stale:
        return {"status": "unverified", "reason": "required series missing or stale", "missing_or_stale": stale, "signals": []}
    signals = []
    sofr = {r["date"]: r["value"] for r in series["SOFR"]["observations"]}
    dff = {r["date"]: r["value"] for r in series["DFF"]["observations"]}
    matches = sorted(set(sofr) & set(dff))
    if len(matches) >= 21:
        spreads = [round(sofr[d] - dff[d], 6) for d in matches[-21:]]
        # Compare current spread against the PREVIOUS 20 matching days.
        increase_bp = (spreads[-1] - statistics.median(spreads[:-1])) * 100
        if increase_bp >= 10:
            signals.append({"group": "funding", "metric": "SOFR minus DFF", "change_bp_vs_prev20_median": round(increase_bp, 3)})
    hy = four_week_change(series["BAMLH0A0HYM2"])
    if hy and hy["difference"] >= 0.5:
        signals.append({"group": "credit", "metric": "high yield OAS", "change_4w_pp": hy["difference"]})
    reserves = four_week_change(series["WRESBAL"])
    if reserves and reserves["percent_change"] is not None and reserves["percent_change"] <= -5:
        signals.append({"group": "reserves", "metric": "reserve balances", "change_4w_percent": reserves["percent_change"]})
    if series["STLFSI4"]["latest"]["value"] > 0:
        signals.append({"group": "stress", "metric": "STLFSI4", "value": series["STLFSI4"]["latest"]["value"]})
    groups = {x["group"] for x in signals}
    return {"status": "warning" if len(groups) >= 2 else "attention" if groups else "normal",
            "reason": "illustrative screen, not an official crisis threshold", "missing_or_stale": [], "signals": signals}


def collect(today: date | None = None) -> dict:
    today = today or datetime.now(timezone.utc).date()
    now = datetime.now(timezone.utc).isoformat()
    series = {}
    missing = {}
    for series_id, (unit, frequency, required) in SERIES.items():
        try:
            raw, url = fetch(series_id, today)
            rows = parse_csv(raw, series_id)
        except (OSError, ValueError) as exc:
            if required:
                raise
            missing[series_id] = str(exc)
            continue
        observed = date.fromisoformat(rows[-1]["date"])
        series[series_id] = {
            "unit": unit, "frequency": frequency, "source_url": f"https://fred.stlouisfed.org/series/{series_id}",
            "download_url": url, "source_sha256": hashlib.sha256(raw).hexdigest(),
            "observations": rows, "latest": rows[-1],
            "change_4w": four_week_change({"observations": rows}),
            "stale": (today - observed).days > (10 if frequency == "daily" else 21),
        }
    signature = hashlib.sha256(json.dumps({k: v["source_sha256"] for k, v in sorted(series.items())}, sort_keys=True).encode()).hexdigest()
    return {"schema_version": 1, "publisher": "Federal Reserve Bank of St. Louis (FRED); individual source publishers vary",
            "dataset": "US financial market liquidity observations", "retrieved_at": now,
            "observation_cutoff": today.isoformat(), "source_signature": signature,
            "series": series, "optional_missing": missing, "assessment": assess(series, today)}


def store(payload: dict, snapshots: Path, latest: Path) -> bool:
    if latest.exists():
        existing = json.loads(latest.read_text(encoding="utf-8"))
        if existing["source_signature"] == payload["source_signature"]:
            same_freshness = all(
                existing.get("series", {}).get(k, {}).get("stale") == v.get("stale")
                for k, v in payload["series"].items()
            )
            if same_freshness and existing.get("assessment") == payload.get("assessment"):
                return False
    snapshots.mkdir(parents=True, exist_ok=True)
    latest.parent.mkdir(parents=True, exist_ok=True)
    snapshot = snapshots / f"{payload['source_signature'][:16]}.json"
    if not snapshot.exists():
        snapshot.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    public = {**payload, "snapshot_path": snapshot.as_posix(), "snapshot_sha256": hashlib.sha256(snapshot.read_bytes()).hexdigest()}
    latest.write_text(json.dumps(public, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot-dir", type=Path, default=Path("data/official/fred-liquidity"))
    parser.add_argument("--latest", type=Path, default=Path("api/v1/liquidity/latest.json"))
    args = parser.parse_args()
    payload = collect()
    print("liquidity updated" if store(payload, args.snapshot_dir, args.latest) else "liquidity unchanged")


if __name__ == "__main__":
    main()
