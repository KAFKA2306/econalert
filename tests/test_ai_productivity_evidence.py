import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "research" / "ai-productivity-evidence.json"
PUBLIC = ROOT / "api" / "v1" / "ai-productivity" / "evidence.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_ai_productivity_evidence_types_are_explicit_and_not_composited():
    payload = load(SOURCE)
    records = payload["records"]
    assert payload["contract"]["allowed_evidence_types"] == ["adoption_survey", "measured_productivity_effect"]
    assert {row["evidence_type"] for row in records} == {"adoption_survey", "measured_productivity_effect"}
    assert "must not be combined" in payload["contract"]["rule"]
    assert all(row["source_url"].startswith("https://") for row in records)
    assert all(row["source_tier"].startswith("primary") for row in records)


def test_census_adoption_record_is_not_labeled_productivity_effect():
    payload = load(SOURCE)
    row = next(item for item in payload["records"] if item["id"] == "census-ces-26-25-ai-firm-use")
    assert row["evidence_type"] == "adoption_survey"
    assert row["value"] == 18.0
    assert row["unit"] == "percent_of_firms"
    assert row["employment_weighted_value"] == 32.0
    assert row["reference_period"] == "2025-11 to 2026-01"
    assert "not a measured causal productivity effect" in row["limitation"]


def test_nber_effect_record_preserves_study_scope():
    payload = load(SOURCE)
    row = next(item for item in payload["records"] if item["id"] == "nber-w31161-generative-ai-at-work")
    assert row["evidence_type"] == "measured_productivity_effect"
    assert row["value"] == 14.0
    assert row["unit"] == "percent_increase_average"
    assert row["population"].startswith("5,179 customer support agents")
    assert "not an economy-wide productivity estimate" in row["limitation"]


def test_public_projection_is_read_only_copy_of_research_contract():
    assert load(PUBLIC) == load(SOURCE)
