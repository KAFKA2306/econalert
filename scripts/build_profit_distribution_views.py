#!/usr/bin/env python3
"""Build deterministic distribution views from stored U.S. profit/distribution evidence."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def json_bytes(payload: object) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def load_latest_snapshot(root: Path) -> tuple[Path, dict]:
    candidates = []
    for path in root.glob("*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        candidates.append((str(payload["retrieved_at"]), path, payload))
    if not candidates:
        raise ValueError("no U.S. profit/distribution snapshots found")
    _, path, payload = max(candidates, key=lambda item: item[0])
    return path, payload


def profit_csv_bytes(rows: list[dict]) -> bytes:
    fields = [
        "period",
        "corporate_profits_billion_usd_saar",
        "gdi_billion_usd_saar",
        "corporate_profits_gdi_pct",
        "corporate_profits_yoy_pct",
        "gdi_yoy_pct",
    ]
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    for row in rows:
        writer.writerow({key: row.get(key, "") for key in fields})
    return stream.getvalue().encode("utf-8")


def distribution_csv_bytes(payload: dict) -> bytes:
    sectors = payload["productivity_distribution"]
    metric_names = sorted(
        {
            key
            for rows in sectors.values()
            for row in rows
            for key in row
            if key != "period"
        }
    )
    fields = ["sector", "period", *metric_names]
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    for sector in sorted(sectors):
        for row in sectors[sector]:
            writer.writerow(
                {"sector": sector, **{key: row.get(key, "") for key in fields if key != "sector"}}
            )
    return stream.getvalue().encode("utf-8")


def latest_summary(payload: dict) -> dict:
    profits = payload["corporate_profit_share"][-1]
    nonfarm = payload["productivity_distribution"]["nonfarm_business"][-1]
    nonfinancial = payload["productivity_distribution"]["nonfinancial_corporations"][-1]
    return {
        "schema_version": 1,
        "retrieved_at": payload["retrieved_at"],
        "corporate_profit_share": profits,
        "nonfarm_business": nonfarm,
        "nonfinancial_corporations": nonfinancial,
        "source_fingerprint_sha256": payload["source_fingerprint_sha256"],
    }


def build(snapshot_root: Path, output_dir: Path) -> None:
    snapshot_path, payload = load_latest_snapshot(snapshot_root)
    latest = {
        "schema_version": payload["schema_version"],
        "dataset": payload["dataset"],
        "retrieved_at": payload["retrieved_at"],
        "sources": payload["sources"],
        "formulas": payload["formulas"],
        "summary": latest_summary(payload),
        "corporate_profit_share": payload["corporate_profit_share"],
        "productivity_distribution": payload["productivity_distribution"],
    }
    outputs = {
        "latest.json": json_bytes(latest),
        "summary.json": json_bytes(latest["summary"]),
        "corporate-profit-share.csv": profit_csv_bytes(payload["corporate_profit_share"]),
        "productivity-distribution.csv": distribution_csv_bytes(payload),
    }
    manifest = {
        "schema_version": 1,
        "source_snapshot": str(snapshot_path),
        "source_snapshot_sha256": sha256_bytes(snapshot_path.read_bytes()),
        "retrieved_at": payload["retrieved_at"],
        "corporate_profit_period_start": payload["corporate_profit_share"][0]["period"],
        "corporate_profit_period_end": payload["corporate_profit_share"][-1]["period"],
        "corporate_profit_observation_count": len(payload["corporate_profit_share"]),
        "productivity_period_end": {
            sector: rows[-1]["period"]
            for sector, rows in payload["productivity_distribution"].items()
        },
        "outputs": {
            name: {"bytes": len(content), "sha256": sha256_bytes(content)}
            for name, content in outputs.items()
        },
    }
    outputs["manifest.json"] = json_bytes(manifest)
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, content in outputs.items():
        (output_dir / name).write_bytes(content)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--snapshot-dir",
        type=Path,
        default=Path("data/official/us-profit-distribution-current"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("api/v1/profit-distribution"),
    )
    args = parser.parse_args()
    build(args.snapshot_dir, args.output_dir)


if __name__ == "__main__":
    main()
