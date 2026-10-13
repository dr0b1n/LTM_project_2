"""Focused tests for Session 4 portfolio reporting."""

from __future__ import annotations

import csv
import io
import json
from datetime import UTC, datetime
from pathlib import Path

from finops_demo.loaders import load_policies, load_telemetry
from finops_demo.policy_engine import analyze_files
from finops_demo.reporting import (
    build_report,
    calculate_portfolio_summary,
    findings_to_csv,
    prioritize_findings,
    report_to_json,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TELEMETRY_PATH = PROJECT_ROOT / "synthetic_data" / "resources.json"
POLICY_PATH = PROJECT_ROOT / "policies" / "finops_rules.yaml"


def findings():
    return analyze_files(TELEMETRY_PATH, POLICY_PATH)


def test_portfolio_summary_matches_engine_results() -> None:
    summary = calculate_portfolio_summary(findings())
    records = findings()
    assert summary["resource_count"] == 24
    assert summary["confirmed_monthly_savings"] == 153.50
    assert summary["confirmed_annual_savings"] == 1842.00
    assert summary["actionable_findings"] == 5
    assert summary["protected_resources"] == 6
    assert summary["current_monthly_cost"] == round(
        sum(item.current_monthly_cost for item in records), 2
    )


def test_review_savings_are_separate_from_confirmed_savings() -> None:
    records = findings()
    summary = calculate_portfolio_summary(records)
    expected_review = round(
        sum(
            item.estimated_monthly_savings
            for item in records
            if item.status == "REVIEW_REQUIRED"
        ),
        2,
    )
    assert summary["review_required_monthly_savings"] == expected_review
    assert summary["confirmed_monthly_savings"] == 153.50


def test_priorities_are_descending_and_only_include_waste() -> None:
    prioritized = prioritize_findings(findings())
    savings = [item["estimated_monthly_savings"] for item in prioritized]
    assert savings == sorted(savings, reverse=True)
    assert [item["priority"] for item in prioritized] == list(
        range(1, len(prioritized) + 1)
    )
    assert all(item["status"] == "WASTE_DETECTED" for item in prioritized)


def test_csv_contains_all_resources() -> None:
    rows = list(csv.DictReader(io.StringIO(findings_to_csv(findings()))))
    assert len(rows) == 24
    assert len({row["resource_id"] for row in rows}) == 24


def test_report_is_json_serializable_and_contains_metadata() -> None:
    dataset = load_telemetry(TELEMETRY_PATH)
    policies = load_policies(POLICY_PATH)
    generated_at = datetime(2026, 9, 28, 6, 0, tzinfo=UTC)
    report = build_report(
        findings(),
        dataset_name=dataset.dataset_name,
        policy_version=policies.policy_version,
        generated_at=generated_at,
    )
    decoded = json.loads(report_to_json(report))
    assert decoded["synthetic"] is True
    assert decoded["dataset_name"] == dataset.dataset_name
    assert decoded["policy_version"] == policies.policy_version
    assert decoded["generated_at"] == generated_at.isoformat()
    assert len(decoded["findings"]) == 24
