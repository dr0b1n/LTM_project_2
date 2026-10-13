"""Deterministic safety, policy, and savings evaluation for the FinOps demo."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from finops_demo.loaders import load_policies, load_telemetry
from finops_demo.models import (
    ComputeConditions,
    PolicyRule,
    PolicySet,
    PublicIpConditions,
    RecommendedAction,
    ResourceTelemetry,
    ResourceType,
    SnapshotConditions,
    StorageConditions,
)


@dataclass(frozen=True, slots=True)
class Finding:
    """One deterministic, review-only result."""

    finding_id: str
    resource_id: str
    cloud_provider: str
    resource_type: str
    matched_policy: str
    status: str
    recommended_action: str
    reason: str
    current_monthly_cost: float
    estimated_monthly_savings: float
    estimated_annual_savings: float
    currency: str
    protected_resource: bool
    requires_human_approval: bool
    artifact_expected: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _finding(
    resource: ResourceTelemetry,
    *,
    matched_policy: str,
    status: str,
    action: RecommendedAction,
    reason: str,
    savings: float = 0.0,
    protected: bool = False,
) -> Finding:
    monthly = round(max(savings, 0.0), 2)
    artifact_expected = status == "WASTE_DETECTED" and action in {
        RecommendedAction.DOWNSIZE,
        RecommendedAction.ARCHIVE,
    }
    return Finding(
        finding_id=f"finding-{resource.resource_id}",
        resource_id=resource.resource_id,
        cloud_provider=resource.cloud_provider.value,
        resource_type=resource.resource_type.value,
        matched_policy=matched_policy,
        status=status,
        recommended_action=action.value,
        reason=reason,
        current_monthly_cost=round(resource.current_monthly_cost, 2),
        estimated_monthly_savings=monthly,
        estimated_annual_savings=round(monthly * 12, 2),
        currency=resource.currency,
        protected_resource=protected,
        requires_human_approval=action
        in {
            RecommendedAction.DOWNSIZE,
            RecommendedAction.ARCHIVE,
            RecommendedAction.REVIEW_REQUIRED,
        },
        artifact_expected=artifact_expected,
    )


def _environment_conflicts(resource: ResourceTelemetry) -> bool:
    tagged = resource.tags.get("environment")
    return tagged is not None and tagged.casefold() != resource.environment.casefold()


def apply_safety_gates(resource: ResourceTelemetry) -> Finding | None:
    """Apply explicit safety precedence before optimization policies."""

    if resource.production_protected or resource.critical_protected or resource.legal_hold:
        return _finding(
            resource,
            matched_policy="SAFETY-001",
            status="PROTECTED",
            action=RecommendedAction.NO_ACTION,
            reason="Production, critical, or legal-hold protection takes precedence.",
            protected=True,
        )

    exempt_tag = resource.tags.get("finops_exempt", "").casefold() == "true"
    if resource.exemption_reason or exempt_tag:
        return _finding(
            resource,
            matched_policy="SAFETY-002",
            status="PROTECTED",
            action=RecommendedAction.NO_ACTION,
            reason="Explicit exemption takes precedence.",
            protected=True,
        )

    if resource.owner is None or not resource.owner.strip():
        return _finding(
            resource,
            matched_policy="SAFETY-003",
            status="REVIEW_REQUIRED",
            action=RecommendedAction.REVIEW_REQUIRED,
            reason="Owner is missing.",
        )

    if resource.environment.casefold() == "unknown" or _environment_conflicts(resource):
        reason = (
            "Environment field conflicts with tag."
            if _environment_conflicts(resource)
            else "Environment is unknown."
        )
        return _finding(
            resource,
            matched_policy="SAFETY-004",
            status="REVIEW_REQUIRED",
            action=RecommendedAction.REVIEW_REQUIRED,
            reason=reason,
        )

    return None


def _savings(resource: ResourceTelemetry) -> float:
    return round(resource.current_monthly_cost - resource.recommended_monthly_cost, 2)


def _snapshot_age_days(resource: ResourceTelemetry) -> int:
    return (resource.observation_end - resource.creation_time).days


def _evaluate_compute(resource: ResourceTelemetry, rule: PolicyRule) -> Finding:
    conditions = rule.conditions
    if not isinstance(conditions, ComputeConditions):
        raise TypeError("Compute policy has incompatible conditions")
    if resource.cpu_utilization_average is None:
        return _finding(
            resource,
            matched_policy=rule.rule_id,
            status="INSUFFICIENT_DATA",
            action=RecommendedAction.NO_ACTION,
            reason="CPU utilization is missing.",
        )
    if resource.observation_days < conditions.minimum_observation_days:
        return _finding(
            resource,
            matched_policy=rule.rule_id,
            status="INSUFFICIENT_DATA",
            action=RecommendedAction.NO_ACTION,
            reason="Observation window is below the policy minimum.",
        )
    if resource.cpu_utilization_average <= conditions.maximum_cpu_percent:
        savings = _savings(resource)
        if savings <= 0:
            return _finding(
                resource,
                matched_policy=rule.rule_id,
                status="NO_WASTE_DETECTED",
                action=RecommendedAction.NO_ACTION,
                reason="Idle threshold matches, but calculated savings are zero.",
            )
        return _finding(
            resource,
            matched_policy=rule.rule_id,
            status="WASTE_DETECTED",
            action=rule.recommended_action,
            reason="CPU and observation window meet the idle-compute policy.",
            savings=savings,
        )
    return _finding(
        resource,
        matched_policy="NONE",
        status="NO_WASTE_DETECTED",
        action=RecommendedAction.NO_ACTION,
        reason="CPU does not meet the idle threshold.",
    )


def _evaluate_storage(resource: ResourceTelemetry, rule: PolicyRule) -> Finding:
    conditions = rule.conditions
    if not isinstance(conditions, StorageConditions):
        raise TypeError("Storage policy has incompatible conditions")
    if resource.attachment_status != conditions.attachment_status:
        return _finding(
            resource,
            matched_policy="NONE",
            status="NO_WASTE_DETECTED",
            action=RecommendedAction.NO_ACTION,
            reason="Volume is attached or otherwise does not meet the policy.",
        )
    if resource.observation_days < conditions.minimum_unattached_days:
        return _finding(
            resource,
            matched_policy=rule.rule_id,
            status="INSUFFICIENT_DATA",
            action=RecommendedAction.NO_ACTION,
            reason="Unattached observation window is below the policy minimum.",
        )
    savings = _savings(resource)
    if savings <= 0:
        return _finding(
            resource,
            matched_policy=rule.rule_id,
            status="NO_WASTE_DETECTED",
            action=RecommendedAction.NO_ACTION,
            reason="Storage policy matches, but calculated savings are zero.",
        )
    return _finding(
        resource,
        matched_policy=rule.rule_id,
        status="WASTE_DETECTED",
        action=rule.recommended_action,
        reason="Volume is unattached beyond the minimum observation period.",
        savings=savings,
    )


def _evaluate_snapshot(
    resource: ResourceTelemetry,
    rule: PolicyRule,
) -> Finding:
    conditions = rule.conditions

    if not isinstance(conditions, SnapshotConditions):
        raise TypeError("Snapshot policy has incompatible conditions")

    if resource.referenced is not conditions.referenced:
        return _finding(
            resource,
            matched_policy="NONE",
            status="NO_WASTE_DETECTED",
            action=RecommendedAction.NO_ACTION,
            reason="Snapshot is referenced.",
        )

    if _snapshot_age_days(resource) < conditions.minimum_age_days:
        return _finding(
            resource,
            matched_policy=rule.rule_id,
            status="NO_WASTE_DETECTED",
            action=RecommendedAction.NO_ACTION,
            reason="Snapshot is below the policy age threshold.",
        )

    savings = _savings(resource)

    if savings <= 0:
        return _finding(
            resource,
            matched_policy=rule.rule_id,
            status="NO_WASTE_DETECTED",
            action=RecommendedAction.NO_ACTION,
            reason="Snapshot policy matches, but calculated savings are zero.",
        )

    return _finding(
        resource,
        matched_policy=rule.rule_id,
        status="WASTE_DETECTED",
        action=rule.recommended_action,
        reason="Snapshot is old and unreferenced.",
        savings=savings,
    )



def _evaluate_public_ip(resource: ResourceTelemetry, rule: PolicyRule) -> Finding:
    conditions = rule.conditions
    if not isinstance(conditions, PublicIpConditions):
        raise TypeError("Public IP policy has incompatible conditions")
    matches = (
        resource.attachment_status == conditions.attachment_status
        and resource.referenced is conditions.referenced
    )
    if not matches:
        return _finding(
            resource,
            matched_policy="NONE",
            status="NO_WASTE_DETECTED",
            action=RecommendedAction.NO_ACTION,
            reason="Public IP is associated or referenced.",
        )
    return _finding(
        resource,
        matched_policy=rule.rule_id,
        status="REVIEW_REQUIRED",
        action=RecommendedAction.REVIEW_REQUIRED,
        reason="Unassociated public IP requires human review.",
        savings=_savings(resource),
    )


def evaluate_resource(resource: ResourceTelemetry, policies: PolicySet) -> Finding:
    """Evaluate one resource deterministically with safety-first precedence."""

    safety_result = apply_safety_gates(resource)
    if safety_result is not None:
        return safety_result

    rule = next(
        (
            item
            for item in policies.rules
            if item.enabled and item.resource_type == resource.resource_type
        ),
        None,
    )
    if rule is None:
        return _finding(
            resource,
            matched_policy="NONE",
            status="NO_WASTE_DETECTED",
            action=RecommendedAction.NO_ACTION,
            reason="No enabled policy applies to this resource type.",
        )

    evaluators = {
        ResourceType.COMPUTE_INSTANCE: _evaluate_compute,
        ResourceType.STORAGE_VOLUME: _evaluate_storage,
        ResourceType.SNAPSHOT: _evaluate_snapshot,
        ResourceType.PUBLIC_IP: _evaluate_public_ip,
    }
    return evaluators[resource.resource_type](resource, rule)


def analyze_files(
    telemetry_path: str | Path,
    policy_path: str | Path,
) -> list[Finding]:
    """Load validated inputs and return deterministic findings in input order."""

    dataset = load_telemetry(telemetry_path)
    policies = load_policies(policy_path)
    return [evaluate_resource(resource, policies) for resource in dataset.records]
