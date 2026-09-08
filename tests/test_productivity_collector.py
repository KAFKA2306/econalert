import json
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.build_productivity_views import build
from scripts.collect_productivity import SERIES, parse


def test_public_api_requires_and_parses_eight_complete_quarters():
    series = []
    for series_id in SERIES:
        data = []
        for index in range(8):
            year = 2024 + index // 4
            quarter = index % 4 + 1
            data.append(
                {
                    "year": str(year),
                    "period": f"Q{quarter:02d}",
                    "value": str(index + 0.5),
                    "footnotes": [{"text": "Revised."}] if index == 7 else [{}],
                }
            )
        series.append({"seriesID": series_id, "data": data})
    raw = json.dumps(
        {"status": "REQUEST_SUCCEEDED", "message": [], "Results": {"series": series}}
    ).encode()
    rows = parse(raw)
    assert len(rows) == 8
    assert rows[0]["period"] == "2024-Q1"
    assert rows[-1]["period"] == "2025-Q4"
    assert rows[-1]["labor_productivity"] == 7.5
    assert rows[-1]["footnotes"]["labor_productivity"] == ["Revised."]


def test_seeded_release_vintages_have_complete_primary_source_rows():
    payload = json.loads(
        Path("data/official/bls-productivity-vintages.json").read_text(encoding="utf-8")
    )
    metrics = set(payload["metrics"])
    assert len(payload["releases"]) == 7
    assert payload["releases"][0]["quarter"] == "2024-Q3"
    assert payload["releases"][-1]["quarter"] == "2026-Q1"
    for release in payload["releases"]:
        assert release["source_url"].startswith("https://www.bls.gov/news.release/archives/")
        assert release["source_section"] == "Table B1"
        assert set(release["revised"]) == metrics
        assert set(release["previously_published"]) == metrics


def test_latest_release_metadata_matches_current_q2_revision():
    release = json.loads(Path("data/official/bls-productivity-2026-q2-release.json").read_text())
    assert release["period"] == "2026-Q2"
    assert release["release_date"] == "2026-09-03"
    assert release["release_status"] == "revised"
    assert release["source_url"].endswith("prod2_09032026.htm")
    assert release["headline"] == {
        "labor_productivity": 1.4,
        "output": 1.7,
        "hours_worked": 0.3,
        "hourly_compensation": 2.6,
        "real_hourly_compensation": -3.3,
        "unit_labor_costs": 1.2,
    }
    assert release["revision_context"]["revision_percentage_points"] == {
        "labor_productivity": 0.0,
        "output": 0.0,
        "hours_worked": 0.0,
        "hourly_compensation": -0.1,
        "real_hourly_compensation": -0.2,
        "unit_labor_costs": -0.1,
    }
    assert release["next_release"]["period"] == "2026-Q3"
    assert release["next_release"]["scheduled_at"] == "2026-11-05T08:30:00-05:00"
    assert release["next_release"]["release_status"] == "preliminary"


def test_distribution_views_are_deterministic_for_revised_release():
    vintages = Path("data/official/bls-productivity-vintages.json")
    release_path = Path("data/official/bls-productivity-2026-q2-release.json")
    release = json.loads(release_path.read_text(encoding="utf-8"))
    current_payload = json.loads(Path("api/v1/productivity/latest.json").read_text(encoding="utf-8"))
    current_payload.pop("release", None)
    current_payload["retrieved_at"] = "2026-09-08T00:00:00+00:00"
    current_payload["source_sha256"] = "test-only-revised-q2-fixture"
    for metric, value in release["headline"].items():
        current_payload["observations"][-1][metric] = value

    with (
        TemporaryDirectory() as current_tmp,
        TemporaryDirectory() as first_tmp,
        TemporaryDirectory() as second_tmp,
    ):
        current = Path(current_tmp)
        (current / "fixture.json").write_text(
            json.dumps(current_payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        first = Path(first_tmp)
        second = Path(second_tmp)
        build(current, vintages, first, release_path)
        build(current, vintages, second, release_path)
        assert {p.name: p.read_bytes() for p in first.iterdir()} == {
            p.name: p.read_bytes() for p in second.iterdir()
        }
        manifest = json.loads((first / "manifest.json").read_text(encoding="utf-8"))
        latest = json.loads((first / "latest.json").read_text(encoding="utf-8"))
        revisions = json.loads((first / "revisions.json").read_text(encoding="utf-8"))
        release_output = json.loads((first / "release.json").read_text(encoding="utf-8"))
        assert manifest["observation_count"] >= 8
        assert set(manifest["outputs"]) == {"latest.json", "latest.csv", "revisions.json", "release.json"}
        assert manifest["release_date"] == "2026-09-03"
        assert manifest["release_status"] == "revised"
        assert latest["release"]["release_date"] == "2026-09-03"
        assert latest["release"]["release_status"] == "revised"
        assert latest["release"]["period"] == latest["observations"][-1]["period"] == "2026-Q2"
        assert release_output["headline"]["labor_productivity"] == latest["observations"][-1]["labor_productivity"] == 1.4
        assert release_output["headline"]["hourly_compensation"] == latest["observations"][-1]["hourly_compensation"] == 2.6
        assert release_output["headline"]["real_hourly_compensation"] == latest["observations"][-1]["real_hourly_compensation"] == -3.3
        assert release_output["headline"]["unit_labor_costs"] == latest["observations"][-1]["unit_labor_costs"] == 1.2
        assert len(revisions["revisions"]) == 7
        assert revisions["revisions"][-1]["revision_percentage_points"]["labor_productivity"] == -0.5
