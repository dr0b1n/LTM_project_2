"""Deterministic mock findings for the Session 1 review interface.

These records are synthetic. They do not represent real cloud resources,
accounts, subscriptions, costs, or policy-engine output.
"""

from typing import Final, TypedDict


class MockFinding(TypedDict):
    """Shape of one mock FinOps finding displayed by the dashboard."""

    resource_id: str
    cloud: str
    resource_type: str
    matched_policy: str
    status: str
    recommended_action: str
    estimated_monthly_savings: float
    protected: bool
    reason: str


MOCK_FINDINGS: Final[list[MockFinding]] = [
    {
        "resource_id": "aws-demo-ec2-001",
        "cloud": "AWS",
        "resource_type": "compute_instance",
        "matched_policy": "FINOPS-COMPUTE-001",
        "status": "WASTE_DETECTED",
        "recommended_action": "DOWNSIZE",
        "estimated_monthly_savings": 42.50,
        "protected": False,
        "reason": (
            "Synthetic development instance has average CPU utilization below "
            "the mock threshold for the required observation period."
        ),
    },
    {
        "resource_id": "aws-prod-ec2-002",
        "cloud": "AWS",
        "resource_type": "compute_instance",
        "matched_policy": "SAFETY-PROTECTION-001",
        "status": "PROTECTED",
        "recommended_action": "NO_ACTION",
        "estimated_monthly_savings": 0.00,
        "protected": True,
        "reason": (
            "Production-tagged resource is protected even though its synthetic "
            "utilization is low."
        ),
    },
    {
        "resource_id": "azure-demo-disk-001",
        "cloud": "Azure",
        "resource_type": "storage_volume",
        "matched_policy": "FINOPS-STORAGE-001",
        "status": "WASTE_DETECTED",
        "recommended_action": "ARCHIVE",
        "estimated_monthly_savings": 18.75,
        "protected": False,
        "reason": (
            "Synthetic development disk has been unattached longer than the "
            "mock minimum period."
        ),
    },
    {
        "resource_id": "aws-demo-volume-003",
        "cloud": "AWS",
        "resource_type": "storage_volume",
        "matched_policy": "FINOPS-STORAGE-001",
        "status": "INSUFFICIENT_DATA",
        "recommended_action": "NO_ACTION",
        "estimated_monthly_savings": 0.00,
        "protected": False,
        "reason": (
            "The volume was detached recently and has not completed the mock "
            "minimum observation period."
        ),
    },
    {
        "resource_id": "aws-demo-snapshot-001",
        "cloud": "AWS",
        "resource_type": "snapshot",
        "matched_policy": "FINOPS-SNAPSHOT-001",
        "status": "WASTE_DETECTED",
        "recommended_action": "ARCHIVE",
        "estimated_monthly_savings": 11.20,
        "protected": False,
        "reason": (
            "Synthetic snapshot is older than the mock age threshold and is "
            "not referenced by a recovery process."
        ),
    },
    {
        "resource_id": "azure-demo-vm-004",
        "cloud": "Azure",
        "resource_type": "compute_instance",
        "matched_policy": "FINOPS-GOVERNANCE-001",
        "status": "REVIEW_REQUIRED",
        "recommended_action": "REVIEW_REQUIRED",
        "estimated_monthly_savings": 0.00,
        "protected": False,
        "reason": (
            "The synthetic resource has no owner, so an optimization action "
            "cannot be recommended automatically."
        ),
    },
    {
        "resource_id": "aws-test-ec2-005",
        "cloud": "AWS",
        "resource_type": "compute_instance",
        "matched_policy": "SAFETY-EXEMPTION-001",
        "status": "PROTECTED",
        "recommended_action": "NO_ACTION",
        "estimated_monthly_savings": 0.00,
        "protected": True,
        "reason": ("The synthetic resource contains an explicit FinOps exemption tag."),
    },
    {
        "resource_id": "azure-dev-vm-006",
        "cloud": "Azure",
        "resource_type": "compute_instance",
        "matched_policy": "NONE",
        "status": "NO_WASTE_DETECTED",
        "recommended_action": "NO_ACTION",
        "estimated_monthly_savings": 0.00,
        "protected": False,
        "reason": ("The synthetic utilization does not meet any mock waste condition."),
    },
]


def get_mock_findings() -> list[MockFinding]:
    """Return independent copies so callers cannot modify the source data."""

    return [finding.copy() for finding in MOCK_FINDINGS]


def calculate_summary(
    findings: list[MockFinding],
) -> dict[str, int | float]:
    """Calculate the summary values displayed by the dashboard."""

    return {
        "total_resources": len(findings),
        "waste_detected": sum(
            finding["status"] == "WASTE_DETECTED" for finding in findings
        ),
        "protected_resources": sum(finding["protected"] for finding in findings),
        "review_required": sum(
            finding["status"] == "REVIEW_REQUIRED" for finding in findings
        ),
        "estimated_monthly_savings": round(
            sum(finding["estimated_monthly_savings"] for finding in findings),
            2,
        ),
    }
