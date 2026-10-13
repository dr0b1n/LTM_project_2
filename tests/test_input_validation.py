"""Focused tests for Session 2 input validation."""

from copy import deepcopy
from pathlib import Path

import pytest
from pydantic import ValidationError

from finops_demo.loaders import load_policies, load_telemetry
from finops_demo.models import TelemetryDataset

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TELEMETRY_PATH = PROJECT_ROOT / "synthetic_data" / "resources.json"
POLICY_PATH = PROJECT_ROOT / "policies" / "finops_rules.yaml"


def valid_payload() -> dict:
    dataset = load_telemetry(TELEMETRY_PATH)
    return dataset.model_dump(mode="json")


def test_real_telemetry_dataset_validates() -> None:
    dataset = load_telemetry(TELEMETRY_PATH)
    assert dataset.synthetic is True
    assert dataset.record_count == 24
    assert len(dataset.records) == 24


def test_real_policy_file_validates() -> None:
    policies = load_policies(POLICY_PATH)
    assert len(policies.rules) == 4
    assert len(policies.safety_gates) == 4
    assert {rule.rule_id for rule in policies.rules} == {
        "FINOPS-COMPUTE-001",
        "FINOPS-STORAGE-001",
        "FINOPS-SNAPSHOT-001",
        "FINOPS-IP-001",
    }


def test_negative_cost_is_rejected() -> None:
    payload = valid_payload()
    payload["records"][0]["current_monthly_cost"] = -1
    with pytest.raises(ValidationError, match="greater than or equal to 0"):
        TelemetryDataset.model_validate(payload)


def test_timezone_naive_datetime_is_rejected() -> None:
    payload = valid_payload()
    payload["records"][0]["observation_start"] = "2026-08-15T00:00:00"
    with pytest.raises(ValidationError, match="Timezone information is required"):
        TelemetryDataset.model_validate(payload)


def test_duplicate_resource_id_is_rejected() -> None:
    payload = valid_payload()
    duplicate = deepcopy(payload["records"][0])
    payload["records"].append(duplicate)
    payload["record_count"] += 1
    with pytest.raises(ValidationError, match="Duplicate resource_id"):
        TelemetryDataset.model_validate(payload)


def test_record_count_mismatch_is_rejected() -> None:
    payload = valid_payload()
    payload["record_count"] = 999
    with pytest.raises(ValidationError, match="record_count does not match"):
        TelemetryDataset.model_validate(payload)
