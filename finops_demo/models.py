"""Pydantic models for synthetic FinOps telemetry and policy inputs."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CloudProvider(StrEnum):
    AWS = "AWS"
    AZURE = "Azure"


class ResourceType(StrEnum):
    COMPUTE_INSTANCE = "compute_instance"
    STORAGE_VOLUME = "storage_volume"
    SNAPSHOT = "snapshot"
    PUBLIC_IP = "public_ip"


class RecommendedAction(StrEnum):
    DOWNSIZE = "DOWNSIZE"
    ARCHIVE = "ARCHIVE"
    NO_ACTION = "NO_ACTION"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


class FindingStatus(StrEnum):
    WASTE_DETECTED = "WASTE_DETECTED"
    NO_WASTE_DETECTED = "NO_WASTE_DETECTED"
    PROTECTED = "PROTECTED"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


NonBlankString = Annotated[str, Field(min_length=1)]
NonNegativeMoney = Annotated[float, Field(ge=0)]
Percentage = Annotated[float, Field(ge=0, le=100)]


class ResourceTelemetry(BaseModel):
    """One normalized synthetic cloud-resource telemetry record."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    resource_id: NonBlankString
    cloud_provider: CloudProvider
    account_or_subscription_id: NonBlankString
    resource_type: ResourceType
    resource_name: NonBlankString
    region: NonBlankString
    owner: str | None = None
    environment: NonBlankString
    tags: dict[str, str] = Field(default_factory=dict)
    creation_time: datetime
    observation_start: datetime
    observation_end: datetime
    lifecycle_state: NonBlankString
    attachment_status: str | None = None
    referenced: bool | None = None
    cpu_utilization_average: Percentage | None = None
    current_monthly_cost: NonNegativeMoney
    recommended_monthly_cost: NonNegativeMoney
    currency: NonBlankString
    production_protected: bool = False
    critical_protected: bool = False
    legal_hold: bool = False
    exemption_reason: str | None = None

    @model_validator(mode="after")
    def validate_record_consistency(self) -> ResourceTelemetry:
        datetimes = {
            "creation_time": self.creation_time,
            "observation_start": self.observation_start,
            "observation_end": self.observation_end,
        }
        naive = [name for name, value in datetimes.items() if value.tzinfo is None]
        if naive:
            raise ValueError(
                "Timezone information is required for: " + ", ".join(naive)
            )
        if self.observation_end < self.observation_start:
            raise ValueError("observation_end cannot precede observation_start")
        if self.creation_time > self.observation_end:
            raise ValueError("creation_time cannot be after observation_end")
        if self.recommended_monthly_cost > self.current_monthly_cost:
            raise ValueError(
                "recommended_monthly_cost cannot exceed current_monthly_cost"
            )
        if self.owner == "":
            self.owner = None
        if self.exemption_reason == "":
            self.exemption_reason = None
        return self

    @property
    def observation_days(self) -> int:
        """Return complete elapsed days in the observation window."""

        return (self.observation_end - self.observation_start).days


class TelemetryDataset(BaseModel):
    """Top-level wrapper for the synthetic telemetry JSON file."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    dataset_name: NonBlankString
    synthetic: Literal[True]
    record_count: Annotated[int, Field(ge=1)]
    records: Annotated[list[ResourceTelemetry], Field(min_length=1)]

    @model_validator(mode="after")
    def validate_dataset_consistency(self) -> TelemetryDataset:
        if self.record_count != len(self.records):
            raise ValueError(
                "record_count does not match the number of telemetry records"
            )
        ids = [record.resource_id for record in self.records]
        duplicates = sorted({item for item in ids if ids.count(item) > 1})
        if duplicates:
            raise ValueError(
                "Duplicate resource_id values: " + ", ".join(duplicates)
            )
        return self


class ComputeConditions(BaseModel):
    model_config = ConfigDict(extra="forbid")
    maximum_cpu_percent: Percentage
    minimum_observation_days: Annotated[int, Field(ge=1)]


class StorageConditions(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    attachment_status: NonBlankString
    minimum_unattached_days: Annotated[int, Field(ge=1)]


class SnapshotConditions(BaseModel):
    model_config = ConfigDict(extra="forbid")
    minimum_age_days: Annotated[int, Field(ge=1)]
    referenced: bool


class PublicIpConditions(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    attachment_status: NonBlankString
    referenced: bool


PolicyConditions = (
    ComputeConditions | StorageConditions | SnapshotConditions | PublicIpConditions
)


class PolicyRule(BaseModel):
    """Validated optimization policy definition."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    rule_id: NonBlankString
    name: NonBlankString
    resource_type: ResourceType
    enabled: bool
    conditions: PolicyConditions
    recommended_action: RecommendedAction
    severity: Literal["low", "medium", "high", "critical"]
    requires_human_approval: bool
    savings_method: NonBlankString

    @model_validator(mode="after")
    def conditions_must_match_resource_type(self) -> PolicyRule:
        expected = {
            ResourceType.COMPUTE_INSTANCE: ComputeConditions,
            ResourceType.STORAGE_VOLUME: StorageConditions,
            ResourceType.SNAPSHOT: SnapshotConditions,
            ResourceType.PUBLIC_IP: PublicIpConditions,
        }
        if not isinstance(self.conditions, expected[self.resource_type]):
            raise TypeError(
                f"conditions do not match resource_type {self.resource_type.value}"
            )
        return self


class SafetyGate(BaseModel):
    """Descriptive safety gate; its expression is never executed dynamically."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    gate_id: NonBlankString
    name: NonBlankString
    when: NonBlankString
    outcome: Literal["PROTECTED", "REVIEW_REQUIRED"]
    recommended_action: Literal["NO_ACTION", "REVIEW_REQUIRED"]

    @model_validator(mode="after")
    def validate_outcome_action_pair(self) -> SafetyGate:
        expected_action = {
            "PROTECTED": "NO_ACTION",
            "REVIEW_REQUIRED": "REVIEW_REQUIRED",
        }[self.outcome]
        if self.recommended_action != expected_action:
            raise ValueError(
                f"{self.outcome} must use recommended_action {expected_action}"
            )
        return self


class PolicySet(BaseModel):
    """Top-level wrapper for the policy YAML file."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    policy_version: NonBlankString
    dataset_note: NonBlankString
    protected_environments: Annotated[list[NonBlankString], Field(min_length=1)]
    safety_gates: Annotated[list[SafetyGate], Field(min_length=1)]
    rules: Annotated[list[PolicyRule], Field(min_length=1)]

    @model_validator(mode="after")
    def validate_unique_identifiers(self) -> PolicySet:
        rule_ids = [rule.rule_id for rule in self.rules]
        gate_ids = [gate.gate_id for gate in self.safety_gates]
        duplicate_rules = sorted({item for item in rule_ids if rule_ids.count(item) > 1})
        duplicate_gates = sorted({item for item in gate_ids if gate_ids.count(item) > 1})
        if duplicate_rules:
            raise ValueError("Duplicate rule_id values: " + ", ".join(duplicate_rules))
        if duplicate_gates:
            raise ValueError("Duplicate gate_id values: " + ", ".join(duplicate_gates))
        return self
