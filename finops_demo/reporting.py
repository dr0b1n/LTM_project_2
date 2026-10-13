"""Reporting helpers for deterministic synthetic FinOps findings."""

from __future__ import annotations

import csv
import io
import json
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

FindingRecord = Mapping[str, Any]


def _as_record(finding: Any) -> dict[str, Any]:
    """Convert a finding dataclass or mapping to an independent dictionary."""

    if hasattr(finding, "to_dict"):
        record = finding.to_dict()
    elif is_dataclass(finding) and not isinstance(finding, type):
        record = asdict(finding)
    elif isinstance(finding, Mapping):
        record = dict(finding)
    else:
        raise TypeError("Each finding must be a mapping or finding dataclass")
    return record


def normalize_findings(findings: Iterable[Any]) -> list[dict[str, Any]]:
    """Return finding dictionaries and validate fields used by reporting."""

    records = [_as_record(finding) for finding in findings]
    required = {
        "resource_id",
        "cloud_provider",
        "resource_type",
        "matched_policy",
        "status",
        "recommended_action",
        "current_monthly_cost",
        "estimated_monthly_savings",
        "estimated_annual_savings",
        "protected_resource",
        "requires_human_approval",
        "artifact_expected",
        "reason",
        "currency",
    }
    for index, record in enumerate(records):
        missing = required - record.keys()
        if missing:
            names = ", ".join(sorted(missing))
            raise ValueError(f"Finding {index} is missing required fields: {names}")
    return records


def calculate_portfolio_summary(findings: Iterable[Any]) -> dict[str, int | float]:
    """Calculate portfolio metrics while separating confirmed and review savings."""

    records = normalize_findings(findings)
    confirmed = [item for item in records if item["status"] == "WASTE_DETECTED"]
    review = [item for item in records if item["status"] == "REVIEW_REQUIRED"]

    current_cost = round(sum(float(item["current_monthly_cost"]) for item in records), 2)
    confirmed_monthly = round(
        sum(float(item["estimated_monthly_savings"]) for item in confirmed),
        2,
    )
    review_monthly = round(
        sum(float(item["estimated_monthly_savings"]) for item in review),
        2,
    )
    percentage = round(
        confirmed_monthly / current_cost * 100 if current_cost else 0.0,
        2,
    )

    return {
        "resource_count": len(records),
        "current_monthly_cost": current_cost,
        "confirmed_monthly_savings": confirmed_monthly,
        "confirmed_annual_savings": round(confirmed_monthly * 12, 2),
        "review_required_monthly_savings": review_monthly,
        "savings_percentage": percentage,
        "actionable_findings": len(confirmed),
        "review_required_findings": len(review),
        "protected_resources": sum(
            bool(item["protected_resource"]) for item in records
        ),
    }


def aggregate_savings(
    findings: Iterable[Any],
    group_by: str,
    *,
    statuses: set[str] | None = None,
) -> list[dict[str, str | int | float]]:
    """Aggregate monthly savings and resource counts by a finding field."""

    records = normalize_findings(findings)
    if not records:
        return []
    if group_by not in records[0]:
        raise ValueError(f"Unknown grouping field: {group_by}")

    included = statuses if statuses is not None else {"WASTE_DETECTED"}
    grouped: dict[str, dict[str, str | int | float]] = {}
    for item in records:
        if item["status"] not in included:
            continue
        key = str(item[group_by])
        entry = grouped.setdefault(
            key,
            {group_by: key, "resources": 0, "monthly_savings": 0.0},
        )
        entry["resources"] = int(entry["resources"]) + 1
        entry["monthly_savings"] = round(
            float(entry["monthly_savings"])
            + float(item["estimated_monthly_savings"]),
            2,
        )
    return sorted(grouped.values(), key=lambda item: str(item[group_by]))


def prioritize_findings(findings: Iterable[Any]) -> list[dict[str, Any]]:
    """Return waste findings ordered by monthly savings, highest first."""

    records = normalize_findings(findings)
    prioritized = sorted(
        (item for item in records if item["status"] == "WASTE_DETECTED"),
        key=lambda item: (-float(item["estimated_monthly_savings"]), item["resource_id"]),
    )
    return [dict(item, priority=index) for index, item in enumerate(prioritized, 1)]


def build_report(
    findings: Iterable[Any],
    *,
    dataset_name: str,
    policy_version: str,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    """Build one JSON-serializable synthetic review report."""

    records = normalize_findings(findings)
    created = generated_at or datetime.now(UTC)
    if created.tzinfo is None:
        raise ValueError("generated_at must include timezone information")

    return {
        "dataset_name": dataset_name,
        "policy_version": policy_version,
        "synthetic": True,
        "generated_at": created.isoformat(),
        "disclaimer": (
            "Synthetic, non-production findings. Savings are illustrative and "
            "all material recommendations require human review."
        ),
        "summary": calculate_portfolio_summary(records),
        "status_distribution": dict(
            sorted(Counter(item["status"] for item in records).items())
        ),
        "savings_by_cloud": aggregate_savings(records, "cloud_provider"),
        "savings_by_resource_type": aggregate_savings(records, "resource_type"),
        "savings_by_action": aggregate_savings(records, "recommended_action"),
        "prioritized_recommendations": prioritize_findings(records),
        "findings": records,
    }


def report_to_json(report: Mapping[str, Any]) -> str:
    """Serialize a report as readable JSON."""

    return json.dumps(report, indent=2, ensure_ascii=False)


def findings_to_csv(findings: Iterable[Any]) -> str:
    """Serialize all findings as CSV text."""

    records = normalize_findings(findings)
    if not records:
        return ""
    fieldnames = list(records[0].keys())
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(records)
    return stream.getvalue()


def write_report_files(
    report: Mapping[str, Any],
    output_dir: str | Path,
) -> tuple[Path, Path]:
    """Write the JSON report and complete findings CSV."""

    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    json_path = destination / "finops_review_report.json"
    csv_path = destination / "finops_review_report.csv"
    findings = report.get("findings")
    if not isinstance(findings, list):
        raise TypeError("Report findings must be a list")
    json_path.write_text(report_to_json(report), encoding="utf-8")
    csv_path.write_text(findings_to_csv(findings), encoding="utf-8", newline="")
    return json_path, csv_path
