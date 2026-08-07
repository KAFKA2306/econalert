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
    with (api / "categories.csv").open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert manifest["record_count"] == 38 == len(categories["observations"]) == len(rows)
    for name, meta in manifest["files"].items():
        payload = (api / name).read_bytes()
        assert len(payload) == meta["bytes"]
        assert hashlib.sha256(payload).hexdigest() == meta["sha256"]


def test_headline_matches_categories():
    latest = json.loads((ROOT / "api/v1/latest.json").read_text())
    categories = json.loads((ROOT / "api/v1/categories.json").read_text())
    values = {x["category"]: x["value"] for x in categories["observations"]}
    assert latest["headline"]["all_items_12m_nsa_pct"] == values["All items"]
    assert latest["headline"]["core_12m_nsa_pct"] == values["All items less food and energy"]
