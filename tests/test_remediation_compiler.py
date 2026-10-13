"""Focused tests for safe Session 5 proposal generation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from finops_demo.policy_engine import analyze_files
from finops_demo.remediation_compiler import (
    generate_artifact,
    generate_eligible_artifacts,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TELEMETRY_PATH = PROJECT_ROOT / "synthetic_data" / "resources.json"
POLICY_PATH = PROJECT_ROOT / "policies" / "finops_rules.yaml"
TEMPLATE_DIR = PROJECT_ROOT / "templates" / "terraform"


def findings():
    return analyze_files(TELEMETRY_PATH, POLICY_PATH)


def test_all_eligible_findings_generate_artifacts(tmp_path: Path) -> None:
    eligible = [item for item in findings() if item.artifact_expected]
    artifacts = generate_eligible_artifacts(
        findings(), template_dir=TEMPLATE_DIR, output_dir=tmp_path
    )
    assert len(artifacts) == len(eligible) == 5
    assert all(Path(item.artifact_path).is_file() for item in artifacts)
    manifest = json.loads((tmp_path / "artifact_manifest.json").read_text())
    assert manifest["artifact_count"] == 5
    assert manifest["execution_enabled"] is False


def test_protected_finding_is_rejected(tmp_path: Path) -> None:
    item = next(f for f in findings() if f.status == "PROTECTED")
    with pytest.raises(ValueError, match="Only WASTE_DETECTED"):
        generate_artifact(item, template_dir=TEMPLATE_DIR, output_dir=tmp_path)


def test_review_required_finding_is_rejected(tmp_path: Path) -> None:
    item = next(f for f in findings() if f.status == "REVIEW_REQUIRED")
    with pytest.raises(ValueError, match="Only WASTE_DETECTED"):
        generate_artifact(item, template_dir=TEMPLATE_DIR, output_dir=tmp_path)


def test_unknown_resource_action_combination_is_rejected(tmp_path: Path) -> None:
    item = next(f.to_dict() for f in findings() if f.artifact_expected)
    item["resource_type"] = "public_ip"
    with pytest.raises(ValueError, match="Unsupported resource/action"):
        generate_artifact(item, template_dir=TEMPLATE_DIR, output_dir=tmp_path)


def test_generated_artifact_is_review_only(tmp_path: Path) -> None:
    item = next(f for f in findings() if f.artifact_expected)
    artifact = generate_artifact(item, template_dir=TEMPLATE_DIR, output_dir=tmp_path)
    content = Path(artifact.artifact_path).read_text(encoding="utf-8")
    lowered = content.casefold()
    assert "dry_run                  = true" in content
    assert "human_approval_required  = true" in content
    assert 'resource "' not in lowered
    assert "terraform apply" not in lowered
    assert "local-exec" not in lowered


def test_resource_id_cannot_escape_output_directory(tmp_path: Path) -> None:
    item = next(f.to_dict() for f in findings() if f.artifact_expected)
    item["resource_id"] = "../../outside resource"
    artifact = generate_artifact(item, template_dir=TEMPLATE_DIR, output_dir=tmp_path)
    path = Path(artifact.artifact_path).resolve()
    assert tmp_path.resolve() in path.parents
    assert path.parent.parent == tmp_path.resolve()
    assert ".." not in path.name
    assert ".." not in path.parent.name
