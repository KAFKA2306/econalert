#!/usr/bin/env python3
"""Collect U.S. corporate-profit-share and productivity/distribution evidence."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

FRED_CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=CPROFIT,GDI"
BLS_API_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
BLS_BULK_BASE = "https://download.bls.gov/pub/time.series/pr"
BLS_METADATA_URLS = {
    "measure": f"{BLS_BULK_BASE}/pr.measure",
    "sector": f"{BLS_BULK_BASE}/pr.sector",
    "duration": f"{BLS_BULK_BASE}/pr.duration",
    "series": f"{BLS_BULK_BASE}/pr.series",
}

# Definitions are checked against BLS's official pr.series/pr.measure/pr.sector/pr.duration files on every live run.
BLS_SERIES = {
    "PRS85006091": {
        "sector_code": "8500", "sector": "Nonfarm Business",
        "measure_code": "09", "measure": "Labor productivity (output per hour)",
        "duration_code": "1", "duration": "% Change same quarter 1 year ago",
        "metric": "labor_productivity_yoy_pct",
    },
    "PRS85006092": {
        "sector_code": "8500", "sector": "Nonfarm Business",
        "measure_code": "09", "measure": "Labor productivity (output per hour)",
        "duration_code": "2", "duration": "% Change from previous quarter",
        "metric": "labor_productivity_qoq_annualized_pct",
    },
    "PRS85006101": {
        "sector_code": "8500", "sector": "Nonfarm Business",
        "measure_code": "10", "measure": "Hourly compensation",
        "duration_code": "1", "duration": "% Change same quarter 1 year ago",
        "metric": "hourly_compensation_yoy_pct",
    },
    "PRS85006102": {
        "sector_code": "8500", "sector": "Nonfarm Business",
        "measure_code": "10", "measure": "Hourly compensation",
        "duration_code": "2", "duration": "% Change from previous quarter",
        "metric": "hourly_compensation_qoq_annualized_pct",
    },
    "PRS85006111": {
        "sector_code": "8500", "sector": "Nonfarm Business",
        "measure_code": "11", "measure": "Unit labor costs",
        "duration_code": "1", "duration": "% Change same quarter 1 year ago",
        "metric": "unit_labor_costs_yoy_pct",
    },
    "PRS85006112": {
        "sector_code": "8500", "sector": "Nonfarm Business",
        "measure_code": "11", "measure": "Unit labor costs",
        "duration_code": "2", "duration": "% Change from previous quarter",
        "metric": "unit_labor_costs_qoq_annualized_pct",
    },
    "PRS85006141": {
        "sector_code": "8500", "sector": "Nonfarm Business",
        "measure_code": "14", "measure": "Value-added output price deflator",
        "duration_code": "1", "duration": "% Change same quarter 1 year ago",
        "metric": "value_added_output_price_yoy_pct",
    },
    "PRS85006142": {
        "sector_code": "8500", "sector": "Nonfarm Business",
        "measure_code": "14", "measure": "Value-added output price deflator",
        "duration_code": "2", "duration": "% Change from previous quarter",
        "metric": "value_added_output_price_qoq_annualized_pct",
    },
    "PRS88003091": {
        "sector_code": "8800", "sector": "Nonfinancial Corporations",
        "measure_code": "09", "measure": "Labor productivity (output per hour)",
        "duration_code": "1", "duration": "% Change same quarter 1 year ago",
        "metric": "labor_productivity_yoy_pct",
    },
    "PRS88003092": {
        "sector_code": "8800", "sector": "Nonfinancial Corporations",
        "measure_code": "09", "measure": "Labor productivity (output per hour)",
        "duration_code": "2", "duration": "% Change from previous quarter",
        "metric": "labor_productivity_qoq_annualized_pct",
    },
    "PRS88003111": {
        "sector_code": "8800", "sector": "Nonfinancial Corporations",
        "measure_code": "11", "measure": "Unit labor costs",
        "duration_code": "1", "duration": "% Change same quarter 1 year ago",
        "metric": "unit_labor_costs_yoy_pct",
    },
    "PRS88003112": {
        "sector_code": "8800", "sector": "Nonfinancial Corporations",
        "measure_code": "11", "measure": "Unit labor costs",
        "duration_code": "2", "duration": "% Change from previous quarter",
        "metric": "unit_labor_costs_qoq_annualized_pct",
    },
    "PRS88003141": {
        "sector_code": "8800", "sector": "Nonfinancial Corporations",
        "measure_code": "14", "measure": "Value-added output price deflator",
        "duration_code": "1", "duration": "% Change same quarter 1 year ago",
        "metric": "value_added_output_price_yoy_pct",
    },
    "PRS88003142": {
        "sector_code": "8800", "sector": "Nonfinancial Corporations",
        "measure_code": "14", "measure": "Value-added output price deflator",
        "duration_code": "2", "duration": "% Change from previous quarter",
        "metric": "value_added_output_price_qoq_annualized_pct",
    },
    "PRS88003191": {
        "sector_code": "8800", "sector": "Nonfinancial Corporations",
        "measure_code": "19", "measure": "Unit profits",
        "duration_code": "1", "duration": "% Change same quarter 1 year ago",
        "metric": "unit_profits_yoy_pct",
    },
    "PRS88003192": {
        "sector_code": "8800", "sector": "Nonfinancial Corporations",
        "measure_code": "19", "measure": "Unit profits",
        "duration_code": "2", "duration": "% Change from previous quarter",
        "metric": "unit_profits_qoq_annualized_pct",
    },
}


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def fetch_url(url: str) -> bytes:
    request = Request(
        url,
        headers={"User-Agent": "economic-releases/1.0 github.com/KAFKA2306/econalert"},
    )
    with urlopen(request, timeout=60) as response:
        return response.read()


def fetch_bls(start_year: int, end_year: int) -> bytes:
    body = json.dumps(
        {
            "seriesid": list(BLS_SERIES),
            "startyear": str(start_year),
            "endyear": str(end_year),
        }
    ).encode()
    request = Request(
        BLS_API_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "economic-releases/1.0 github.com/KAFKA2306/econalert",
        },
        method="POST",
    )
    with urlopen(request, timeout=60) as response:
        return response.read()


def parse_tsv(raw: bytes) -> list[dict[str, str]]:
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")), delimiter="\t")
    rows = []
    for row in reader:
        rows.append({str(key).strip(): str(value or "").strip() for key, value in row.items()})
    return rows


def verify_bls_metadata(raws: dict[str, bytes]) -> list[dict[str, str]]:
    measures = {row["measure_code"]: row["measure_text"] for row in parse_tsv(raws["measure"])}
    sectors = {row["sector_code"]: row["sector_name"] for row in parse_tsv(raws["sector"])}
    durations = {row["duration_code"]: row["duration_text"] for row in parse_tsv(raws["duration"])}
    series_rows = {row["series_id"]: row for row in parse_tsv(raws["series"])}
    selected = []
    for series_id, expected in BLS_SERIES.items():
        row = series_rows.get(series_id)
        if row is None:
            raise ValueError(f"BLS metadata missing series {series_id}")
        actual = {
            "sector_code": row["sector_code"],
            "sector": sectors.get(row["sector_code"]),
            "measure_code": row["measure_code"],
            "measure": measures.get(row["measure_code"]),
            "duration_code": row["duration_code"],
            "duration": durations.get(row["duration_code"]),
        }
        expected_identity = {key: expected[key] for key in actual}
        if actual != expected_identity:
            raise ValueError(
                f"BLS metadata changed for {series_id}: expected={expected_identity!r} actual={actual!r}"
            )
        selected.append({"series_id": series_id, **actual, "metric": expected["metric"]})
    return selected


def quarter_from_date(date_text: str) -> str:
    year, month, _ = date_text.split("-")
    quarter_by_month = {"01": 1, "04": 2, "07": 3, "10": 4}
    if month not in quarter_by_month:
        raise ValueError(f"expected quarter-start date, got {date_text}")
    return f"{year}-Q{quarter_by_month[month]}"


def parse_fred(raw: bytes, min_observations: int = 8) -> list[dict[str, float | str]]:
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    required = {"observation_date", "CPROFIT", "GDI"}
    if not required.issubset(reader.fieldnames or []):
        raise ValueError(f"FRED CSV missing columns: {sorted(required - set(reader.fieldnames or []))}")
    base = []
    for row in reader:
        profit = row["CPROFIT"].strip()
        gdi = row["GDI"].strip()
        if profit in {"", "."} or gdi in {"", "."}:
            continue
        profit_value = float(profit)
        gdi_value = float(gdi)
        if profit_value <= 0 or gdi_value <= 0:
            raise ValueError("CPROFIT and GDI must be positive")
        base.append(
            {
                "period": quarter_from_date(row["observation_date"].strip()),
                "corporate_profits_billion_usd_saar": profit_value,
                "gdi_billion_usd_saar": gdi_value,
                "corporate_profits_gdi_pct": round(profit_value / gdi_value * 100.0, 6),
            }
        )
    if len(base) < min_observations:
        raise ValueError(f"expected at least {min_observations} complete CPROFIT/GDI quarters, found {len(base)}")
    for index, row in enumerate(base):
        if index >= 4:
            prior = base[index - 4]
            row["corporate_profits_yoy_pct"] = round(
                (float(row["corporate_profits_billion_usd_saar"])
                 / float(prior["corporate_profits_billion_usd_saar"]) - 1.0) * 100.0,
                6,
            )
            row["gdi_yoy_pct"] = round(
                (float(row["gdi_billion_usd_saar"])
                 / float(prior["gdi_billion_usd_saar"]) - 1.0) * 100.0,
                6,
            )
    return base


def parse_bls(raw: bytes, min_complete_periods: int = 8) -> dict[str, list[dict[str, float | str]]]:
    response = json.loads(raw)
    if response.get("status") != "REQUEST_SUCCEEDED":
        raise ValueError(f"BLS API request failed: {response.get('message')}")
    returned = set()
    by_sector: dict[str, dict[str, dict[str, float | str]]] = {
        "nonfarm_business": {},
        "nonfinancial_corporations": {},
    }
    sector_key = {
        "8500": "nonfarm_business",
        "8800": "nonfinancial_corporations",
    }
    for series in response.get("Results", {}).get("series", []):
        series_id = series.get("seriesID")
        if series_id not in BLS_SERIES:
            continue
        returned.add(series_id)
        definition = BLS_SERIES[series_id]
        metric = definition["metric"]
        target = by_sector[sector_key[definition["sector_code"]]]
        for item in series.get("data", []):
            period_code = str(item.get("period", ""))
            if period_code not in {"Q01", "Q02", "Q03", "Q04"}:
                continue
            period = f"{item['year']}-Q{int(period_code[1:])}"
            row = target.setdefault(period, {"period": period})
            value_text = str(item.get("value", "")).strip()
            if value_text in {"", "."}:
                continue
            row[metric] = float(value_text)
    missing = set(BLS_SERIES) - returned
    if missing:
        raise ValueError(f"BLS API omitted series: {sorted(missing)}")

    result: dict[str, list[dict[str, float | str]]] = {}
    required_by_sector = {
        key: {
            definition["metric"]
            for definition in BLS_SERIES.values()
            if sector_key[definition["sector_code"]] == key
        }
        for key in sector_key.values()
    }
    for key, rows_by_period in by_sector.items():
        required_metrics = required_by_sector[key]
        rows = [
            row
            for row in rows_by_period.values()
            if required_metrics.issubset(row)
        ]
        rows.sort(key=lambda row: str(row["period"]))
        if len(rows) < min_complete_periods:
            raise ValueError(
                f"expected at least {min_complete_periods} complete {key} quarters, found {len(rows)}"
            )
        if key == "nonfarm_business":
            for row in rows:
                ulc = float(row["unit_labor_costs_yoy_pct"])
                price = float(row["value_added_output_price_yoy_pct"])
                row["labor_share_yoy_log_approx_pct"] = round(ulc - price, 6)
                row["labor_share_yoy_from_rounded_rates_pct"] = round(
                    ((1.0 + ulc / 100.0) / (1.0 + price / 100.0) - 1.0) * 100.0,
                    6,
                )
        result[key] = rows
    return result


def source_fingerprint(raws: dict[str, bytes]) -> str:
    digest = hashlib.sha256()
    for name in sorted(raws):
        digest.update(name.encode())
        digest.update(b"\0")
        digest.update(raws[name])
        digest.update(b"\0")
    return digest.hexdigest()


def collect() -> dict[str, object]:
    now = datetime.now(timezone.utc)
    year = now.year
    raws: dict[str, bytes] = {
        "fred_cprofit_gdi": fetch_url(FRED_CSV_URL),
        "bls_api": fetch_bls(year - 3, year),
    }
    metadata_raws = {name: fetch_url(url) for name, url in BLS_METADATA_URLS.items()}
    raws.update({f"bls_{name}": content for name, content in metadata_raws.items()})
    selected_metadata = verify_bls_metadata(metadata_raws)
    return {
        "schema_version": 1,
        "dataset": "U.S. corporate profit share and productivity distribution",
        "retrieved_at": now.isoformat(),
        "source_fingerprint_sha256": source_fingerprint(raws),
        "sources": {
            "fred_cprofit_gdi": {
                "retrieval_provider": "Federal Reserve Bank of St. Louis (FRED)",
                "original_publisher": "U.S. Bureau of Economic Analysis",
                "retrieval_url": FRED_CSV_URL,
                "primary_source_urls": [
                    "https://www.bea.gov/data/income-saving/corporate-profits",
                    "https://www.bea.gov/data/income-saving/gross-domestic-income",
                ],
                "series": {
                    "CPROFIT": {
                        "title": "Corporate Profits with Inventory Valuation Adjustment (IVA) and Capital Consumption Adjustment (CCAdj)",
                        "units": "Billions of Dollars, Seasonally Adjusted Annual Rate",
                    },
                    "GDI": {
                        "title": "Gross Domestic Income",
                        "units": "Billions of Dollars, Seasonally Adjusted Annual Rate",
                    },
                },
                "raw_sha256": sha256_bytes(raws["fred_cprofit_gdi"]),
            },
            "bls_productivity": {
                "publisher": "U.S. Bureau of Labor Statistics",
                "retrieval_url": BLS_API_URL,
                "metadata_urls": BLS_METADATA_URLS,
                "series": selected_metadata,
                "raw_sha256": sha256_bytes(raws["bls_api"]),
                "metadata_sha256": {
                    name: sha256_bytes(content) for name, content in metadata_raws.items()
                },
                "quarterly_change_semantics": "BLS quarterly percent changes are seasonally adjusted annualized rates.",
            },
        },
        "formulas": {
            "corporate_profits_gdi_pct": "100 * CPROFIT / GDI",
            "corporate_profits_yoy_pct": "100 * (CPROFIT_t / CPROFIT_t-4 - 1)",
            "gdi_yoy_pct": "100 * (GDI_t / GDI_t-4 - 1)",
            "labor_share_yoy_log_approx_pct": "unit_labor_costs_yoy_pct - value_added_output_price_yoy_pct",
            "labor_share_yoy_from_rounded_rates_pct": "100 * ((1 + ULC_yoy/100) / (1 + value_added_price_yoy/100) - 1)",
        },
        "corporate_profit_share": parse_fred(raws["fred_cprofit_gdi"]),
        "productivity_distribution": parse_bls(raws["bls_api"]),
    }


def write_snapshot(payload: dict[str, object], output_dir: Path) -> Path:
    observations = payload["corporate_profit_share"]
    if not isinstance(observations, list) or len(observations) < 8:
        raise ValueError("corporate profit snapshot requires at least 8 complete quarters")
    output_dir.mkdir(parents=True, exist_ok=True)
    fingerprint = str(payload["source_fingerprint_sha256"])
    path = output_dir / f"{fingerprint[:16]}.json"
    if not path.exists():
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/official/us-profit-distribution-current"),
    )
    args = parser.parse_args()
    payload = collect()
    path = write_snapshot(payload, args.output_dir)
    latest_profit = payload["corporate_profit_share"][-1]
    print(
        f"wrote {latest_profit['period']} corporate-profits/GDI="
        f"{latest_profit['corporate_profits_gdi_pct']:.3f}% -> {path}"
    )


if __name__ == "__main__":
    main()
