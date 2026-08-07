from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "official" / "bls-cpi-2026-06.json"
OUT = ROOT / "api" / "v1"


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(data: dict) -> None:
    assert data["publisher"] == "U.S. Bureau of Labor Statistics"
    assert data["period"] == "2026-06"
    rows = data["categories_12m_nsa_pct"]
    names = [r["category"] for r in rows]
    assert len(rows) == 38
    assert len(names) == len(set(names))
    assert data["headline"]["all_items_12m_nsa_pct"] == next(r["value"] for r in rows if r["category"] == "All items")
    assert data["headline"]["core_12m_nsa_pct"] == next(r["value"] for r in rows if r["category"] == "All items less food and energy")


def build() -> None:
    data = json.loads(SOURCE.read_text())
    validate(data)
    OUT.mkdir(parents=True, exist_ok=True)

    latest = {
        "schema_version": "1.0",
        "series": "bls-cpi-u",
        "period": data["period"],
        "release_date": data["release_date"],
        "headline": data["headline"],
        "next_release": data["next_release"],
        "source": {"publisher": data["publisher"], "url": data["source_url"], "retrieved_at": data["retrieved_at"]},
    }
    (OUT / "latest.json").write_bytes(canonical_bytes(latest))

    categories = {
        "schema_version": "1.0",
        "series": "bls-cpi-u-12m-nsa-category",
        "period": data["period"],
        "unit": "percent",
        "seasonal_adjustment": "not_seasonally_adjusted",
        "observations": sorted(data["categories_12m_nsa_pct"], key=lambda x: x["category"]),
    }
    lines = ["{", '  "observations": [']
    for i, row in enumerate(categories["observations"]):
        comma = "," if i < len(categories["observations"]) - 1 else ""
        lines.append("    " + json.dumps(row, ensure_ascii=False) + comma)
    lines.extend([
        "  ],",
        f'  "period": {json.dumps(categories["period"])},',
        f'  "schema_version": {json.dumps(categories["schema_version"])},',
        f'  "seasonal_adjustment": {json.dumps(categories["seasonal_adjustment"])},',
        f'  "series": {json.dumps(categories["series"])},',
        f'  "unit": {json.dumps(categories["unit"])}',
        "}",
    ])
    (OUT / "categories.json").write_text("\n".join(lines) + "\n", encoding="utf-8")

    csv_path = OUT / "categories.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["period", "category", "value", "unit", "seasonal_adjustment"])
        writer.writeheader()
        for row in categories["observations"]:
            writer.writerow({"period": data["period"], "category": row["category"], "value": row["value"], "unit": "percent", "seasonal_adjustment": "not_seasonally_adjusted"})

    source_hash = sha256(SOURCE)
    files = {}
    for name in ("latest.json", "categories.json", "categories.csv"):
        p = OUT / name
        files[name] = {"bytes": p.stat().st_size, "sha256": sha256(p)}
    manifest = {
        "api_version": "v1",
        "dataset": "bls-cpi",
        "period": data["period"],
        "release_date": data["release_date"],
        "retrieved_at": data["retrieved_at"],
        "record_count": len(data["categories_12m_nsa_pct"]),
        "source": {"publisher": data["publisher"], "url": data["source_url"], "snapshot": str(SOURCE.relative_to(ROOT)), "sha256": source_hash},
        "rights": {"copyright_url": data["copyright_url"], "terms_url": data["terms_url"], "note": data["rights"]},
        "cache": {"revalidate_seconds": 3600, "validator": "sha256"},
        "files": files,
    }
    (OUT / "manifest.json").write_bytes(canonical_bytes(manifest))


if __name__ == "__main__":
    build()
