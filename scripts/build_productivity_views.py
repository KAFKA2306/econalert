#!/usr/bin/env python3
"""Build deterministic distribution files from stored BLS productivity evidence."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path

METRICS = (
    "labor_productivity",
    "output",
    "hours_worked",
    "hourly_compensation",
    "real_hourly_compensation",
    "unit_labor_costs",
)
DEFAULT_RELEASE = Path("data/official/bls-productivity-2026-q2-release.json")


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def load_latest_snapshot(root: Path) -> tuple[Path, dict]:
    candidates = []
    for path in root.glob("*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        candidates.append((str(payload["retrieved_at"]), path, payload))
    if not candidates:
        raise ValueError("no BLS productivity current snapshots found")
    _, path, payload = max(candidates, key=lambda item: item[0])
    return path, payload


def build_revisions(vintages: dict) -> dict:
    rows = []
    for release in vintages["releases"]:
        revised = release["revised"]
        previous = release["previously_published"]
        rows.append(
            {
                "quarter": release["quarter"],
                "release_date": release["release_date"],
                "source_url": release["source_url"],
                "source_section": release["source_section"],
                "revision_percentage_points": {
                    metric: round(float(revised[metric]) - float(previous[metric]), 10)
                    for metric in METRICS
                },
            }
        )
    return {
        "schema_version": 1,
        "publisher": vintages["publisher"],
        "dataset": vintages["dataset"],
        "sector": vintages["sector"],
        "rate_basis": vintages["rate_basis"],
        "revisions": rows,
    }


def csv_bytes(payload: dict) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=("period", *METRICS))
    writer.writeheader()
    for row in payload["observations"]:
        writer.writerow({key: row.get(key, "") for key in writer.fieldnames})
    return stream.getvalue().encode("utf-8")


def json_bytes(payload: dict) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def validate_release(release: dict, latest_observation: dict) -> None:
    if release["publisher"] != "U.S. Bureau of Labor Statistics":
        raise ValueError("unexpected productivity release publisher")
    if release["period"] != latest_observation["period"]:
        raise ValueError(
            f"release period {release['period']} does not match latest observation {latest_observation['period']}"
        )
    if release["rate_basis"] != "percent change from previous quarter at annual rate":
        raise ValueError("productivity release rate basis mismatch")
    for metric in METRICS:
        if float(release["headline"][metric]) != float(latest_observation[metric]):
            raise ValueError(f"release headline does not match current observation: {metric}")


def build(current_root: Path, vintages_path: Path, output_dir: Path, release_path: Path = DEFAULT_RELEASE) -> None:
    snapshot_path, current = load_latest_snapshot(current_root)
    vintages = json.loads(vintages_path.read_text(encoding="utf-8"))
    release = json.loads(release_path.read_text(encoding="utf-8"))
    latest_observation = current["observations"][-1]
    validate_release(release, latest_observation)
    revisions = build_revisions(vintages)

    latest = {
        "schema_version": 2,
        "publisher": current["publisher"],
        "dataset": current["dataset"],
        "sector": current["sector"],
        "rate_basis": current["rate_basis"],
        "retrieved_at": current["retrieved_at"],
        "source_url": current["source_url"],
        "source_sha256": current["source_sha256"],
        "release": {
            "period": release["period"],
            "release_date": release["release_date"],
            "release_status": release["release_status"],
            "source_url": release["source_url"],
            "verified_on": release["verified_on"],
            "next_release": release["next_release"],
        },
        "series": current["series"],
        "observations": current["observations"],
    }

    outputs = {
        "latest.json": json_bytes(latest),
        "latest.csv": csv_bytes(latest),
        "revisions.json": json_bytes(revisions),
        "release.json": json_bytes(release),
    }
    manifest = {
        "schema_version": 2,
        "source_snapshot": str(snapshot_path),
        "source_snapshot_sha256": sha256_bytes(snapshot_path.read_bytes()),
        "release_evidence": str(release_path),
        "release_evidence_sha256": sha256_bytes(release_path.read_bytes()),
        "historical_vintages": str(vintages_path),
        "historical_vintages_sha256": sha256_bytes(vintages_path.read_bytes()),
        "period_start": latest["observations"][0]["period"],
        "period_end": latest["observations"][-1]["period"],
        "release_date": release["release_date"],
        "release_status": release["release_status"],
        "observation_count": len(latest["observations"]),
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
    parser.add_argument("--current-dir", type=Path, default=Path("data/official/bls-productivity-current"))
    parser.add_argument("--vintages", type=Path, default=Path("data/official/bls-productivity-vintages.json"))
    parser.add_argument("--release", type=Path, default=DEFAULT_RELEASE)
    parser.add_argument("--output-dir", type=Path, default=Path("api/v1/productivity"))
    args = parser.parse_args()
    build(args.current_dir, args.vintages, args.output_dir, args.release)


if __name__ == "__main__":
    main()
