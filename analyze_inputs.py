"""Run deterministic Session 3 analysis and write a reviewable JSON report."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from finops_demo.loaders import InputLoadError
from finops_demo.policy_engine import analyze_files

PROJECT_ROOT = Path(__file__).resolve().parent
TELEMETRY_PATH = PROJECT_ROOT / "synthetic_data" / "resources.json"
POLICY_PATH = PROJECT_ROOT / "policies" / "finops_rules.yaml"
OUTPUT_PATH = PROJECT_ROOT / "output" / "reports" / "findings.json"


def main() -> int:
    try:
        findings = analyze_files(TELEMETRY_PATH, POLICY_PATH)
    except (InputLoadError, TypeError, ValueError) as exc:
        print("Analysis: FAILED")
        print(exc)
        return 1

    payload = {
        "synthetic": True,
        "note": "Deterministic review-only findings; savings are illustrative.",
        "finding_count": len(findings),
        "findings": [finding.to_dict() for finding in findings],
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    statuses = Counter(finding.status for finding in findings)
    waste_savings = round(
        sum(
            finding.estimated_monthly_savings
            for finding in findings
            if finding.status == "WASTE_DETECTED"
        ),
        2,
    )
    print(f"Analyzed resources: {len(findings)}")
    print("Statuses: " + ", ".join(f"{key}={value}" for key, value in sorted(statuses.items())))
    print(f"Illustrative waste savings: ${waste_savings:,.2f}/month")
    print(f"Report: {OUTPUT_PATH}")
    print("Analysis: PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
