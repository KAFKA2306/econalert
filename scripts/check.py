from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable


def run(*args: str) -> None:
    subprocess.run(args, cwd=ROOT, check=True)


def contract_report(snapshot: str, output: str, expected: dict[str, object]) -> None:
    run(
        PYTHON,
        "scripts/contract_escalation.py",
        "contracts/synthetic-demo.json",
        snapshot,
        "--as-of-date",
        "2026-08-15",
        "--output",
        output,
    )
    report = json.loads(Path(output).read_text(encoding="utf-8"))
    assert report["status"] == "READY_FOR_HUMAN_REVIEW"
    assert report["source"]["series_id"] == "CUUR0000SA0"
    for key, value in expected.items():
        section, field = key.split(".", 1)
        assert report[section][field] == value, (key, report[section][field], value)
    assert report["decision"]["notice"]["state"] == "NOT_DUE"
    assert report["decision"]["notice"]["notice_deadline"] == "2026-09-02"


def main() -> None:
    python_files = [
        "scripts/build_public_api.py",
        "scripts/contract_escalation.py",
        "scripts/collect_productivity.py",
        "scripts/build_productivity_views.py",
        "scripts/check.py",
        *[str(path.relative_to(ROOT)) for path in sorted((ROOT / "tests").glob("test_*.py"))],
    ]
    run(PYTHON, "-m", "py_compile", *python_files)
    run(PYTHON, "scripts/build_public_api.py")
    run(PYTHON, "-m", "pytest", "-q")

    contract_report(
        "data/synthetic/cpi-index-demo.json",
        "/tmp/contract-escalation-report.json",
        {
            "calculation.raw_percent_change": 5.0,
            "calculation.adjustment_percent": 4.0,
        },
    )
    contract_report(
        "data/official/bls-cpi-u-all-items-index-2025-06-2026-06.json",
        "/tmp/official-contract-escalation-report.json",
        {
            "calculation.base_index": 322.561,
            "calculation.comparison_index": 333.952,
            "calculation.raw_percent_change": 3.53142506,
            "calculation.adjustment_percent": 3.53142506,
        },
    )

    run("git", "diff", "--exit-code", "--", "api/v1")
    for path in ("api/v1/manifest.json", "api/v1/latest.json", "api/v1/categories.json"):
        json.loads((ROOT / path).read_text(encoding="utf-8"))
    status = subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True)
    if status.strip():
        raise SystemExit(f"working tree is not clean after checks:\n{status}")


if __name__ == "__main__":
    main()
