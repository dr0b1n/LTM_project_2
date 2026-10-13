"""Allow-listed generation of review-only Terraform proposal artifacts."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

_TEMPLATE_ALLOWLIST = {
    ("compute_instance", "DOWNSIZE"): "downsize_proposal.tf.j2",
    ("storage_volume", "ARCHIVE"): "archive_proposal.tf.j2",
    ("snapshot", "ARCHIVE"): "archive_proposal.tf.j2",
}
_SAFE_NAME = re.compile(r"[^A-Za-z0-9_-]+")
_FORBIDDEN_CONTENT = (
    "terraform apply",
    "terraform destroy",
    "local-exec",
    "remote-exec",
    "access_key",
    "secret_key",
    "client_secret",
    "private_key",
)


@dataclass(frozen=True, slots=True)
class ArtifactRecord:
    """Manifest entry for one generated proposal artifact."""

    resource_id: str
    finding_id: str
    matched_policy: str
    recommended_action: str
    template_name: str
    artifact_path: str
    sha256: str
    dry_run: bool = True
    human_approval_required: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _as_record(finding: Any) -> dict[str, Any]:
    if hasattr(finding, "to_dict"):
        return finding.to_dict()
    if is_dataclass(finding) and not isinstance(finding, type):
        return asdict(finding)
    if isinstance(finding, Mapping):
        return dict(finding)
    raise TypeError("Finding must be a mapping or finding dataclass")


def _safe_filename(resource_id: str) -> str:
    cleaned = _SAFE_NAME.sub("_", resource_id).strip("._-")
    if not cleaned:
        raise ValueError("resource_id does not produce a safe filename")
    return cleaned[:100]


def _validate_eligibility(record: Mapping[str, Any]) -> str:
    required = {
        "finding_id",
        "resource_id",
        "cloud_provider",
        "resource_type",
        "matched_policy",
        "status",
        "recommended_action",
        "current_monthly_cost",
        "estimated_monthly_savings",
        "currency",
        "reason",
        "protected_resource",
        "requires_human_approval",
        "artifact_expected",
    }
    missing = required - record.keys()
    if missing:
        raise ValueError("Finding is missing fields: " + ", ".join(sorted(missing)))
    if record["status"] != "WASTE_DETECTED":
        raise ValueError("Only WASTE_DETECTED findings can generate artifacts")
    if record["protected_resource"]:
        raise ValueError("Protected resources cannot generate artifacts")
    if not record["artifact_expected"]:
        raise ValueError("Finding is not eligible for an artifact")
    if not record["requires_human_approval"]:
        raise ValueError("Artifact generation requires human approval metadata")

    key = (str(record["resource_type"]), str(record["recommended_action"]))
    template_name = _TEMPLATE_ALLOWLIST.get(key)
    if template_name is None:
        raise ValueError(f"Unsupported resource/action combination: {key}")
    return template_name


def _environment(template_dir: Path) -> Environment:
    if not template_dir.is_dir():
        raise FileNotFoundError(f"Template directory does not exist: {template_dir}")
    return Environment(
        loader=FileSystemLoader(template_dir),
        undefined=StrictUndefined,
        autoescape=select_autoescape(default_for_string=False, default=False),
        keep_trailing_newline=True,
    )


def _validate_rendered_content(content: str) -> None:
    lowered = content.casefold()
    forbidden = [token for token in _FORBIDDEN_CONTENT if token in lowered]
    if forbidden:
        raise ValueError("Generated artifact contains forbidden content: " + ", ".join(forbidden))
    if 'resource \"' in lowered or 'module \"' in lowered:
        raise ValueError("Session 5 proposal artifacts cannot declare resources or modules")
    if "dry_run                  = true" not in content:
        raise ValueError("Generated artifact is missing the dry-run declaration")
    if "human_approval_required  = true" not in content:
        raise ValueError("Generated artifact is missing the approval declaration")


def generate_artifact(
    finding: Any,
    *,
    template_dir: str | Path,
    output_dir: str | Path,
) -> ArtifactRecord:
    """Generate one deterministic proposal artifact after all safety checks."""

    record = _as_record(finding)
    template_name = _validate_eligibility(record)
    destination = Path(output_dir).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    safe_name = _safe_filename(str(record["resource_id"]))
    artifact_dir = (destination / safe_name).resolve()
    if artifact_dir.parent != destination:
        raise ValueError("Artifact path escaped the configured output directory")
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = (
        artifact_dir / f"{record['recommended_action'].lower()}_proposal.tf"
    ).resolve()
    if artifact_path.parent != artifact_dir:
        raise ValueError("Artifact path escaped the resource artifact directory")

    template = _environment(Path(template_dir)).get_template(template_name)
    render_context = {
        key: record[key]
        for key in (
            "finding_id",
            "resource_id",
            "cloud_provider",
            "resource_type",
            "matched_policy",
            "current_monthly_cost",
            "estimated_monthly_savings",
            "currency",
            "reason",
        )
    }
    content = template.render(**render_context)
    _validate_rendered_content(content)
    artifact_path.write_text(content, encoding="utf-8", newline="\n")
    checksum = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
    return ArtifactRecord(
        resource_id=str(record["resource_id"]),
        finding_id=str(record["finding_id"]),
        matched_policy=str(record["matched_policy"]),
        recommended_action=str(record["recommended_action"]),
        template_name=template_name,
        artifact_path=str(artifact_path),
        sha256=checksum,
    )


def generate_eligible_artifacts(
    findings: Iterable[Any],
    *,
    template_dir: str | Path,
    output_dir: str | Path,
) -> list[ArtifactRecord]:
    """Generate artifacts only for findings explicitly marked as eligible."""

    records = [_as_record(finding) for finding in findings]
    eligible = [record for record in records if record.get("artifact_expected") is True]
    artifacts = [
        generate_artifact(
            record,
            template_dir=template_dir,
            output_dir=output_dir,
        )
        for record in eligible
    ]
    manifest_path = Path(output_dir) / "artifact_manifest.json"
    manifest = {
        "synthetic": True,
        "dry_run": True,
        "execution_enabled": False,
        "artifact_count": len(artifacts),
        "artifacts": [artifact.to_dict() for artifact in artifacts],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return artifacts
