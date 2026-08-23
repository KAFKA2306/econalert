from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LATEST_SOURCE = ROOT / "data" / "official" / "bls-cpi-2026-07.json"
CATEGORY_SOURCE = ROOT / "data" / "official" / "bls-cpi-2026-06.json"
AI_RESEARCH_SOURCE = ROOT / "data" / "research" / "ai-productivity-evidence.json"
OUT = ROOT / "api" / "v1"


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_latest(data: dict) -> None:
    assert data["publisher"] == "U.S. Bureau of Labor Statistics"
    assert data["period"] == "2026-07"
    assert data["release_date"] == "2026-08-12"
    assert data["detail_status"] == "headline_only"
    assert data["headline"]["all_items_monthly_sa_pct"] == 0.1
    assert data["headline"]["all_items_12m_nsa_pct"] == 3.4
    assert data["headline"]["core_monthly_sa_pct"] == 0.2
    assert data["headline"]["core_12m_nsa_pct"] == 2.5


def validate_categories(data: dict) -> None:
    assert data["publisher"] == "U.S. Bureau of Labor Statistics"
    rows = data["categories_12m_nsa_pct"]
    names = [r["category"] for r in rows]
    assert len(rows) == 38
    assert len(names) == len(set(names))
    assert data["headline"]["all_items_12m_nsa_pct"] == next(r["value"] for r in rows if r["category"] == "All items")
    assert data["headline"]["core_12m_nsa_pct"] == next(r["value"] for r in rows if r["category"] == "All items less food and energy")


def validate_ai_research(data: dict) -> None:
    allowed = ["adoption_survey", "measured_productivity_effect"]
    assert data["contract"]["allowed_evidence_types"] == allowed
    assert "must not be combined" in data["contract"]["rule"]
    records = data["records"]
    assert {row["evidence_type"] for row in records} == set(allowed)
    assert all(row["source_url"].startswith("https://") for row in records)
    assert all(row["limitation"] for row in records)


def build() -> None:
    latest_source = json.loads(LATEST_SOURCE.read_text())
    category_source = json.loads(CATEGORY_SOURCE.read_text())
    ai_research = json.loads(AI_RESEARCH_SOURCE.read_text())
    validate_latest(latest_source)
    validate_categories(category_source)
    validate_ai_research(ai_research)
    OUT.mkdir(parents=True, exist_ok=True)

    latest = {
        "schema_version": "2.0",
        "series": "bls-cpi-u",
        "period": latest_source["period"],
        "release_date": latest_source["release_date"],
        "headline": latest_source["headline"],
        "detail_status": latest_source["detail_status"],
        "next_release": latest_source["next_release"],
        "source": {
            "publisher": latest_source["publisher"],
            "url": latest_source["source_url"],
            "schedule_url": latest_source["schedule_url"],
            "verified_on": latest_source["verified_on"],
        },
    }
    (OUT / "latest.json").write_bytes(canonical_bytes(latest))

    categories = {
        "schema_version": "1.0",
        "series": "bls-cpi-u-12m-nsa-category",
        "period": category_source["period"],
        "unit": "percent",
        "seasonal_adjustment": "not_seasonally_adjusted",
        "freshness": "older_detail_vintage_than_latest_headline",
        "observations": sorted(category_source["categories_12m_nsa_pct"], key=lambda x: x["category"]),
    }
    lines = ["{", '  "freshness": "older_detail_vintage_than_latest_headline",', '  "observations": [']
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
            writer.writerow({"period": category_source["period"], "category": row["category"], "value": row["value"], "unit": "percent", "seasonal_adjustment": "not_seasonally_adjusted"})

    ai_out = OUT / "ai-productivity"
    ai_out.mkdir(parents=True, exist_ok=True)
    (ai_out / "evidence.json").write_bytes(canonical_bytes(ai_research))
    ai_index = {
        "schema_version": 1,
        "dataset": "ai-productivity-research-evidence",
        "record_count": len(ai_research["records"]),
        "evidence_types": ai_research["contract"]["allowed_evidence_types"],
        "source": {
            "snapshot": str(AI_RESEARCH_SOURCE.relative_to(ROOT)),
            "sha256": sha256(AI_RESEARCH_SOURCE),
        },
        "files": {"evidence": "evidence.json"},
    }
    (ai_out / "index.json").write_bytes(canonical_bytes(ai_index))

    files = {}
    for name in ("latest.json", "categories.json", "categories.csv"):
        p = OUT / name
        files[name] = {"bytes": p.stat().st_size, "sha256": sha256(p)}
    manifest = {
        "api_version": "v1",
        "dataset": "bls-cpi",
        "latest_period": latest_source["period"],
        "latest_release_date": latest_source["release_date"],
        "category_period": category_source["period"],
        "category_freshness": "older_detail_vintage_than_latest_headline",
        "verified_on": latest_source["verified_on"],
        "record_count": len(category_source["categories_12m_nsa_pct"]),
        "sources": {
            "latest_headline": {
                "publisher": latest_source["publisher"],
                "url": latest_source["source_url"],
                "snapshot": str(LATEST_SOURCE.relative_to(ROOT)),
                "sha256": sha256(LATEST_SOURCE),
            },
            "detailed_categories": {
                "publisher": category_source["publisher"],
                "url": category_source["source_url"],
                "snapshot": str(CATEGORY_SOURCE.relative_to(ROOT)),
                "sha256": sha256(CATEGORY_SOURCE),
            },
        },
        "rights": {"copyright_url": latest_source["copyright_url"], "terms_url": latest_source["terms_url"], "note": latest_source["rights"]},
        "cache": {"revalidate_seconds": 3600, "validator": "sha256"},
        "files": files,
    }
    (OUT / "manifest.json").write_bytes(canonical_bytes(manifest))


if __name__ == "__main__":
    build()
