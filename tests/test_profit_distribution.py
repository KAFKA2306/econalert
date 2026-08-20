import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from scripts.build_profit_distribution_views import build
from scripts.collect_profit_distribution import (
    BLS_SERIES,
    parse_bls,
    parse_fred,
    verify_bls_metadata,
    write_snapshot,
)


def metadata_fixture():
    measures = (
        "measure_code\tmeasure_text\tdisplay_level\tselectable\tsort_sequence\n"
        "09\tLabor productivity (output per hour)\t0\tT\t1\n"
        "10\tHourly compensation\t0\tT\t5\n"
        "11\tUnit labor costs\t0\tT\t7\n"
        "14\tValue-added output price deflator\t0\tT\t9\n"
        "19\tUnit profits\t0\tT\t21\n"
    ).encode()
    sectors = (
        "sector_code\tsector_name\tdisplay_level\tselectable\tsort_sequence\n"
        "8500\tNonfarm Business\t0\tT\t1\n"
        "8800\tNonfinancial Corporations\t0\tT\t3\n"
    ).encode()
    durations = (
        "duration_code\tduration_text\tdisplay_level\tselectable\tsort_sequence\n"
        "1\t% Change same quarter 1 year ago\t0\tT\t1\n"
        "2\t% Change from previous quarter\t0\tT\t2\n"
    ).encode()
    lines = [
        "series_id\tsector_code\tclass_code\tmeasure_code\tduration_code\tseasonal\tbase_year\tfootnote_codes\tbegin_year\tbegin_period\tend_year\tend_period"
    ]
    for series_id, definition in BLS_SERIES.items():
        class_code = "6" if definition["sector_code"] == "8500" else "3"
        lines.append(
            "\t".join(
                [
                    series_id,
                    definition["sector_code"],
                    class_code,
                    definition["measure_code"],
                    definition["duration_code"],
                    "S",
                    "-",
                    "",
                    "1947",
                    "Q01",
                    "2026",
                    "Q02",
                ]
            )
        )
    return {
        "measure": measures,
        "sector": sectors,
        "duration": durations,
        "series": ("\n".join(lines) + "\n").encode(),
    }


def test_bls_series_contract_matches_official_metadata_shape():
    selected = verify_bls_metadata(metadata_fixture())
    assert len(selected) == len(BLS_SERIES)
    by_id = {row["series_id"]: row for row in selected}
    assert by_id["PRS85006141"]["measure"] == "Value-added output price deflator"
    assert by_id["PRS88003192"]["measure"] == "Unit profits"


def test_bls_metadata_change_fails_closed():
    raws = metadata_fixture()
    raws["measure"] = raws["measure"].replace(b"Unit profits", b"Renamed profits")
    with pytest.raises(ValueError, match="metadata changed"):
        verify_bls_metadata(raws)


def test_fred_profit_share_and_yoy_calculation():
    raw = b"""observation_date,CPROFIT,GDI
2025-01-01,3922.871,29895.650
2025-04-01,3929.661,30244.878
2025-07-01,4105.221,30789.434
2025-10-01,4352.096,31199.940
2026-01-01,4426.485,31574.222
"""
    rows = parse_fred(raw, min_observations=5)
    latest = rows[-1]
    assert latest["period"] == "2026-Q1"
    assert latest["corporate_profits_gdi_pct"] == pytest.approx(14.019300, abs=1e-6)
    assert latest["corporate_profits_yoy_pct"] == pytest.approx(12.837893, abs=1e-6)
    assert latest["gdi_yoy_pct"] == pytest.approx(5.614770, abs=1e-6)


def bls_fixture(quarters=8):
    series = []
    for series_id, definition in BLS_SERIES.items():
        data = []
        for index in range(quarters):
            year = 2024 + index // 4
            quarter = index % 4 + 1
            value = float(index + 1)
            if definition["metric"] == "unit_labor_costs_yoy_pct" and index == quarters - 1:
                value = 1.4 if definition["sector_code"] == "8500" else -0.2
            if definition["metric"] == "value_added_output_price_yoy_pct" and index == quarters - 1:
                value = 4.9 if definition["sector_code"] == "8500" else 2.4
            if definition["metric"] == "unit_profits_qoq_annualized_pct" and index == quarters - 1:
                value = 18.6
            if definition["metric"] == "unit_profits_yoy_pct" and index == quarters - 1:
                value = 6.8
            data.append(
                {
                    "year": str(year),
                    "period": f"Q{quarter:02d}",
                    "value": str(value),
                    "footnotes": [{}],
                }
            )
        data.append({"year": "2025", "period": "Q05", "value": "999", "footnotes": [{}]})
        series.append({"seriesID": series_id, "data": data})
    return json.dumps(
        {"status": "REQUEST_SUCCEEDED", "message": [], "Results": {"series": series}}
    ).encode()


def test_bls_distribution_parses_only_quarters_and_derives_labor_share_change():
    payload = parse_bls(bls_fixture())
    nonfarm = payload["nonfarm_business"]
    assert len(nonfarm) == 8
    assert nonfarm[-1]["period"] == "2025-Q4"
    assert nonfarm[-1]["labor_share_yoy_log_approx_pct"] == pytest.approx(-3.5)
    assert nonfarm[-1]["labor_share_yoy_from_rounded_rates_pct"] == pytest.approx(
        -3.336511, abs=1e-6
    )
    nonfinancial = payload["nonfinancial_corporations"][-1]
    assert nonfinancial["unit_profits_qoq_annualized_pct"] == 18.6
    assert nonfinancial["unit_profits_yoy_pct"] == 6.8


def test_bls_missing_series_fails_closed():
    payload = json.loads(bls_fixture())
    payload["Results"]["series"].pop()
    with pytest.raises(ValueError, match="omitted series"):
        parse_bls(json.dumps(payload).encode())


def test_snapshot_and_views_are_content_addressed_and_deterministic():
    profits = parse_fred(
        b"""observation_date,CPROFIT,GDI
2024-01-01,3500,28000
2024-04-01,3600,28200
2024-07-01,3700,28400
2024-10-01,3800,28600
2025-01-01,3900,29000
2025-04-01,4000,29500
2025-07-01,4100,30000
2025-10-01,4200,30500
""",
        min_observations=8,
    )
    payload = {
        "schema_version": 1,
        "dataset": "U.S. corporate profit share and productivity distribution",
        "retrieved_at": "2026-08-21T00:00:00+00:00",
        "source_fingerprint_sha256": "a" * 64,
        "sources": {"fixture": {"raw_sha256": "b" * 64}},
        "formulas": {"corporate_profits_gdi_pct": "100 * CPROFIT / GDI"},
        "corporate_profit_share": profits,
        "productivity_distribution": parse_bls(bls_fixture()),
    }
    with TemporaryDirectory() as snapshot_tmp, TemporaryDirectory() as first_tmp, TemporaryDirectory() as second_tmp:
        snapshot_dir = Path(snapshot_tmp)
        path = write_snapshot(payload, snapshot_dir)
        assert path.name == f"{'a' * 16}.json"
        build(snapshot_dir, Path(first_tmp))
        build(snapshot_dir, Path(second_tmp))
        first = {p.name: p.read_bytes() for p in Path(first_tmp).iterdir()}
        second = {p.name: p.read_bytes() for p in Path(second_tmp).iterdir()}
        assert first == second
        summary = json.loads(first["summary.json"])
        assert summary["corporate_profit_share"]["period"] == "2025-Q4"
        assert set(first) == {
            "latest.json",
            "summary.json",
            "corporate-profit-share.csv",
            "productivity-distribution.csv",
            "manifest.json",
        }
