"""Generate JSON and CSV review reports from deterministic FinOps findings."""

from __future__ import annotations

from pathlib import Path

from finops_demo.loaders import InputLoadError, load_policies, load_telemetry
from finops_demo.policy_engine import analyze_files
from finops_demo.reporting import build_report, write_report_files

PROJECT_ROOT = Path(__file__).resolve().parent
TELEMETRY_PATH = PROJECT_ROOT / "synthetic_data" / "resources.json"
POLICY_PATH = PROJECT_ROOT / "policies" / "finops_rules.yaml"
OUTPUT_DIR = PROJECT_ROOT / "output" / "reports"


def main() -> int:
    """Generate both report formats and print a concise summary."""

    try:
        dataset = load_telemetry(TELEMETRY_PATH)
        policies = load_policies(POLICY_PATH)
        findings = analyze_files(TELEMETRY_PATH, POLICY_PATH)
        report = build_report(
            findings,
            dataset_name=dataset.dataset_name,
            policy_version=policies.policy_version,
        )
        json_path, csv_path = write_report_files(report, OUTPUT_DIR)
    except (InputLoadError, KeyError, OSError, TypeError, ValueError) as exc:
        print("Report generation: FAILED")
        print(exc)
        return 1

    summary = report["summary"]
    print(f"Resources reported: {summary['resource_count']}")
    print(
        "Confirmed illustrative savings: "
        f"${summary['confirmed_monthly_savings']:,.2f}/month"
    )
    print(
        "Potential savings pending review: "
        f"${summary['review_required_monthly_savings']:,.2f}/month"
    )
    print(f"JSON report: {json_path}")
    print(f"CSV report: {csv_path}")
    print("Report generation: PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
