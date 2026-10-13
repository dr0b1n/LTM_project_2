"""Focused checks for repeatable Terraform validation evidence."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_PATH = (
    PROJECT_ROOT / "output" / "reports" / "terraform_validation_results.json"
)


def load_evidence() -> list[dict]:
    if not EVIDENCE_PATH.is_file():
        pytest.skip("Terraform validation evidence has not been generated")
    payload = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8-sig"))
    assert isinstance(payload, list)
    return payload


def test_validation_evidence_has_five_unique_resources() -> None:
    rows = load_evidence()
    assert len(rows) == 5
    assert len({row["ResourceDirectory"] for row in rows}) == 5


def test_all_terraform_checks_pass() -> None:
    rows = load_evidence()
    required_true = {
        "TerraformFmt",
        "TerraformInit",
        "TerraformValidate",
        "TFLint",
        "DryRunPresent",
        "ApprovalRequiredPresent",
        "OverallPassed",
    }
    for row in rows:
        assert all(row[field] is True for field in required_true)
        assert row["UnsafeContentFound"] is False


def test_evidence_records_hash_lifecycle() -> None:
    rows = load_evidence()
    for row in rows:
        assert len(row["GenerationSha256"]) == 64
        assert len(row["PreFormatSha256"]) == 64
        assert len(row["PostFormatSha256"]) == 64
        assert isinstance(row["FormattingChangedFile"], bool)
