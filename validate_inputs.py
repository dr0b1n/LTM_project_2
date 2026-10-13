"""Validate the Session 2 telemetry and policy inputs."""

from collections import Counter
from pathlib import Path

from finops_demo.loaders import InputLoadError, load_policies, load_telemetry

PROJECT_ROOT = Path(__file__).resolve().parent
TELEMETRY_PATH = PROJECT_ROOT / "synthetic_data" / "resources.json"
POLICY_PATH = PROJECT_ROOT / "policies" / "finops_rules.yaml"


def main() -> int:
    try:
        dataset = load_telemetry(TELEMETRY_PATH)
        policies = load_policies(POLICY_PATH)
    except InputLoadError as exc:
        print("Input validation: FAILED")
        print(exc)
        return 1

    providers = Counter(record.cloud_provider.value for record in dataset.records)
    resource_types = Counter(record.resource_type.value for record in dataset.records)

    print(f"Dataset: {dataset.dataset_name}")
    print(f"Validated resources: {len(dataset.records)}")
    print("Providers: " + ", ".join(f"{key}={value}" for key, value in sorted(providers.items())))
    print(
        "Resource types: "
        + ", ".join(f"{key}={value}" for key, value in sorted(resource_types.items()))
    )
    print(f"Validated optimization policies: {len(policies.rules)}")
    print(f"Validated safety gates: {len(policies.safety_gates)}")
    print("Input validation: PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
