"""Focused Session 3 tests against the prepared ground-truth fixture."""

from __future__ import annotations

import json
from pathlib import Path

from finops_demo.loaders import load_policies, load_telemetry
from finops_demo.policy_engine import analyze_files, evaluate_resource

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TELEMETRY_PATH = PROJECT_ROOT / "synthetic_data" / "resources.json"
POLICY_PATH = PROJECT_ROOT / "policies" / "finops_rules.yaml"
EXPECTED_PATH = PROJECT_ROOT / "expected_findings" / "expected_findings.json"


def test_all_findings_match_ground_truth_core_fields() -> None:
    actual = {
        finding.resource_id: finding
        for finding in analyze_files(TELEMETRY_PATH, POLICY_PATH)
    }
    expected_payload = json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))
    expected = {item["resource_id"]: item for item in expected_payload["findings"]}

    assert actual.keys() == expected.keys()
    for resource_id, expected_finding in expected.items():
        finding = actual[resource_id]
        assert finding.matched_policy == expected_finding["matched_policy"]
        assert finding.status == expected_finding["status"]
        assert finding.recommended_action == expected_finding["recommended_action"]
        assert finding.estimated_monthly_savings == expected_finding["estimated_monthly_savings"]
        assert finding.estimated_annual_savings == expected_finding["estimated_annual_savings"]
        assert finding.protected_resource == expected_finding["protected_resource"]
        assert finding.artifact_expected == expected_finding["artifact_expected"]


def test_protected_resource_overrides_idle_compute() -> None:
    dataset = load_telemetry(TELEMETRY_PATH)
    policies = load_policies(POLICY_PATH)
    resource = next(item for item in dataset.records if item.resource_id == "aws-prod-ec2-003")
    finding = evaluate_resource(resource, policies)
    assert finding.status == "PROTECTED"
    assert finding.recommended_action == "NO_ACTION"
    assert finding.estimated_monthly_savings == 0


def test_missing_owner_overrides_optimization() -> None:
    dataset = load_telemetry(TELEMETRY_PATH)
    policies = load_policies(POLICY_PATH)
    resource = next(item for item in dataset.records if item.resource_id == "aws-dev-ec2-005")
    finding = evaluate_resource(resource, policies)
    assert finding.matched_policy == "SAFETY-003"
    assert finding.status == "REVIEW_REQUIRED"


def test_threshold_boundary_is_inclusive() -> None:
    dataset = load_telemetry(TELEMETRY_PATH)
    policies = load_policies(POLICY_PATH)
    resource = next(item for item in dataset.records if item.resource_id == "aws-dev-ec2-022")
    finding = evaluate_resource(resource, policies)
    assert resource.cpu_utilization_average == 3.0
    assert resource.observation_days == 14
    assert finding.status == "WASTE_DETECTED"
    assert finding.estimated_monthly_savings == 25.0


def test_zero_savings_does_not_create_waste_finding() -> None:
    dataset = load_telemetry(TELEMETRY_PATH)
    policies = load_policies(POLICY_PATH)
    resource = next(item for item in dataset.records if item.resource_id == "azure-dev-vm-021")
    finding = evaluate_resource(resource, policies)
    assert finding.status == "NO_WASTE_DETECTED"
    assert finding.recommended_action == "NO_ACTION"
    assert finding.artifact_expected is False
