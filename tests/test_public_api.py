import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_build_and_integrity():
    subprocess.run([sys.executable, "scripts/build_public_api.py"], cwd=ROOT, check=True)
    api = ROOT / "api" / "v1"
    manifest = json.loads((api / "manifest.json").read_text())
    categories = json.loads((api / "categories.json").read_text())
    latest = json.loads((api / "latest.json").read_text())
    with (api / "categories.csv").open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert latest["period"] == "2026-07"
    assert latest["release_date"] == "2026-08-12"
    assert latest["headline"] == {
        "all_items_12m_nsa_pct": 3.4,
        "all_items_index_nsa": 333.918,
        "all_items_index_reference_base": "1982-84=100",
        "all_items_monthly_sa_pct": 0.1,
        "core_12m_nsa_pct": 2.5,
        "core_monthly_sa_pct": 0.2,
    }
    assert latest["detail_status"] == "headline_only"
    assert manifest["latest_period"] == "2026-07"
    assert manifest["category_period"] == "2026-06"
    assert manifest["category_freshness"] == "older_detail_vintage_than_latest_headline"
    assert categories["period"] == "2026-06"
    assert categories["freshness"] == "older_detail_vintage_than_latest_headline"
    assert manifest["record_count"] == 38 == len(categories["observations"]) == len(rows)
    for name, meta in manifest["files"].items():
        payload = (api / name).read_bytes()
        assert len(payload) == meta["bytes"]
        assert hashlib.sha256(payload).hexdigest() == meta["sha256"]


def test_detailed_category_snapshot_remains_internally_consistent():
    categories = json.loads((ROOT / "api/v1/categories.json").read_text())
    source = json.loads((ROOT / "data/official/bls-cpi-2026-06.json").read_text())
    values = {x["category"]: x["value"] for x in categories["observations"]}
    assert categories["period"] == source["period"]
    assert source["headline"]["all_items_12m_nsa_pct"] == values["All items"]
    assert source["headline"]["core_12m_nsa_pct"] == values["All items less food and energy"]
