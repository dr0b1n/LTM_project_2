"""Generate allow-listed review-only Terraform proposal artifacts."""

from __future__ import annotations

from pathlib import Path

from finops_demo.loaders import InputLoadError
from finops_demo.policy_engine import analyze_files
from finops_demo.remediation_compiler import generate_eligible_artifacts

PROJECT_ROOT = Path(__file__).resolve().parent
TELEMETRY_PATH = PROJECT_ROOT / "synthetic_data" / "resources.json"
POLICY_PATH = PROJECT_ROOT / "policies" / "finops_rules.yaml"
TEMPLATE_DIR = PROJECT_ROOT / "templates" / "terraform"
OUTPUT_DIR = PROJECT_ROOT / "output" / "terraform"


def main() -> int:
    try:
        findings = analyze_files(TELEMETRY_PATH, POLICY_PATH)
        artifacts = generate_eligible_artifacts(
            findings,
            template_dir=TEMPLATE_DIR,
            output_dir=OUTPUT_DIR,
        )
    except (InputLoadError, KeyError, OSError, TypeError, ValueError) as exc:
        print("Artifact generation: FAILED")
        print(exc)
        return 1

    print(f"Eligible findings: {sum(f.artifact_expected for f in findings)}")
    print(f"Artifacts generated: {len(artifacts)}")
    for artifact in artifacts:
        print(f"- {artifact.resource_id}: {artifact.artifact_path}")
    print(f"Manifest: {OUTPUT_DIR / 'artifact_manifest.json'}")
    print("Execution enabled: False")
    print("Artifact generation: PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
