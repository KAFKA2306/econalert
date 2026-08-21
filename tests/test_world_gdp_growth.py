from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "data/official/world-bank-world-gdp-growth-2025.json"
PUBLIC = ROOT / "api/v1/world-gdp-growth.json"


def test_world_gdp_growth_snapshot_and_public_view_match() -> None:
    snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    public = json.loads(PUBLIC.read_text(encoding="utf-8"))

    assert snapshot["publisher"] == "World Bank"
    assert snapshot["dataset"] == "World Development Indicators"
    assert snapshot["indicator"]["id"] == "NY.GDP.MKTP.KD.ZG"
    assert snapshot["indicator"]["name"] == "GDP growth (annual %)"
    assert snapshot["geography"] == {"id": "1W", "name": "World"}
    assert snapshot["observation"] == {
        "period": "2025",
        "value": 2.9,
        "unit": "percent",
        "precision_note": "The cited World Bank DataBank page displays the World value rounded to one decimal place. No additional precision is inferred.",
    }
    assert snapshot["api_response_materialized"] is False

    assert public["indicator_id"] == snapshot["indicator"]["id"]
    assert public["indicator_name"] == snapshot["indicator"]["name"]
    assert public["geography"] == snapshot["geography"]["name"]
    assert public["period"] == snapshot["observation"]["period"]
    assert public["value"] == snapshot["observation"]["value"]
    assert public["unit"] == snapshot["observation"]["unit"]
    assert public["source"]["publisher"] == snapshot["publisher"]
    assert public["source"]["dataset"] == snapshot["dataset"]
    assert public["source"]["url"] == snapshot["source_url"]
    assert public["source"]["snapshot"] == str(SNAPSHOT.relative_to(ROOT))
