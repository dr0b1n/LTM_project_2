"""Streamlit review interface for the synthetic FinOps demonstration."""

import json
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from finops_demo.loaders import InputLoadError, load_policies, load_telemetry
from finops_demo.policy_engine import analyze_files
from finops_demo.remediation_compiler import generate_eligible_artifacts
from finops_demo.reporting import (
    aggregate_savings,
    build_report,
    calculate_portfolio_summary,
    findings_to_csv,
    prioritize_findings,
    report_to_json,
)

PROJECT_ROOT = Path(__file__).resolve().parent
TELEMETRY_PATH = PROJECT_ROOT / "synthetic_data" / "resources.json"
POLICY_PATH = PROJECT_ROOT / "policies" / "finops_rules.yaml"
TEMPLATE_DIR = PROJECT_ROOT / "templates" / "terraform"
TERRAFORM_OUTPUT_DIR = PROJECT_ROOT / "output" / "terraform"
TERRAFORM_VALIDATION_PATH = (
    PROJECT_ROOT
    / "output"
    / "reports"
    / "terraform_validation_results.json"
)

@st.cache_data
def load_input_readiness() -> dict[str, str | int | bool]:
    """Validate inputs for display in the review interface."""

    try:
        dataset = load_telemetry(TELEMETRY_PATH)
        policies = load_policies(POLICY_PATH)
    except InputLoadError as exc:
        return {
            "valid": False,
            "message": str(exc),
            "resources": 0,
            "policies": 0,
            "safety_gates": 0,
        }

    return {
        "valid": True,
        "message": "Telemetry and policy inputs passed validation.",
        "resources": len(dataset.records),
        "policies": len(policies.rules),
        "safety_gates": len(policies.safety_gates),
    }


@st.cache_data
def load_engine_findings() -> list[dict[str, Any]]:
    """Run the deterministic engine and return dashboard-ready findings."""

    findings = analyze_files(TELEMETRY_PATH, POLICY_PATH)
    return [finding.to_dict() for finding in findings]


@st.cache_data
def load_portfolio_metadata() -> tuple[str, str]:
    """Return the validated dataset name and policy version."""

    dataset = load_telemetry(TELEMETRY_PATH)
    policies = load_policies(POLICY_PATH)
    return dataset.dataset_name, policies.policy_version


st.set_page_config(
    page_title="Cloud FinOps Remediation Agent",
    page_icon="☁️",
    layout="wide",
)

st.title("Autonomous Cloud FinOps Remediation Agent")
st.caption("Validated synthetic inputs with deterministic policy findings")
st.info(
    "This is a synthetic, deterministic, non-production demonstration. "
    "The application validates local telemetry and policies, applies explicit "
    "Python safety and optimization rules, and produces review-only findings. "
    "No cloud resources are accessed or modified."
)

st.subheader("Input readiness")
input_readiness = load_input_readiness()

if input_readiness["valid"]:
    st.success(str(input_readiness["message"]))
    readiness_columns = st.columns(3)
    readiness_columns[0].metric(
        "Validated telemetry records",
        input_readiness["resources"],
    )
    readiness_columns[1].metric(
        "Optimization policies",
        input_readiness["policies"],
    )
    readiness_columns[2].metric(
        "Safety gates",
        input_readiness["safety_gates"],
    )
else:
    st.error("Input validation failed.")
    st.code(str(input_readiness["message"]))
    st.stop()

try:
    all_findings = load_engine_findings()
    dataset_name, policy_version = load_portfolio_metadata()
except (InputLoadError, KeyError, TypeError, ValueError) as exc:
    st.error("The deterministic policy analysis failed.")
    st.code(str(exc))
    st.stop()

if not all_findings:
    st.warning("The deterministic engine returned no findings.")
    st.stop()

all_findings_frame = pd.DataFrame(all_findings)
required_finding_columns = {
    "resource_id",
    "cloud_provider",
    "resource_type",
    "matched_policy",
    "status",
    "recommended_action",
    "current_monthly_cost",
    "estimated_monthly_savings",
    "estimated_annual_savings",
    "currency",
    "protected_resource",
    "requires_human_approval",
    "artifact_expected",
    "reason",
}
missing_columns = required_finding_columns - set(all_findings_frame.columns)

if missing_columns:
    st.error("The policy engine returned an incomplete findings schema.")
    st.code(", ".join(sorted(missing_columns)))
    st.stop()

try:
    portfolio_report = build_report(
        all_findings,
        dataset_name=dataset_name,
        policy_version=policy_version,
    )
    portfolio_summary = portfolio_report["summary"]
except (KeyError, TypeError, ValueError) as exc:
    st.error("Portfolio reporting failed.")
    st.code(str(exc))
    st.stop()

st.success(
    "The findings below were calculated from validated synthetic telemetry "
    "and YAML policies using deterministic Python rules."
)

with st.sidebar:
    st.header("Finding filters")
    cloud_options = sorted(all_findings_frame["cloud_provider"].unique().tolist())
    resource_type_options = sorted(
        all_findings_frame["resource_type"].unique().tolist()
    )
    status_options = sorted(all_findings_frame["status"].unique().tolist())
    action_options = sorted(
        all_findings_frame["recommended_action"].unique().tolist()
    )

    selected_clouds = st.multiselect(
        "Cloud provider",
        options=cloud_options,
        default=cloud_options,
    )
    selected_resource_types = st.multiselect(
        "Resource type",
        options=resource_type_options,
        default=resource_type_options,
    )
    selected_statuses = st.multiselect(
        "Finding status",
        options=status_options,
        default=status_options,
    )
    selected_actions = st.multiselect(
        "Recommended action",
        options=action_options,
        default=action_options,
    )
    protected_filter = st.selectbox(
        "Protection state",
        options=["All resources", "Protected only", "Not protected"],
    )

filtered_frame = all_findings_frame[
    all_findings_frame["cloud_provider"].isin(selected_clouds)
    & all_findings_frame["resource_type"].isin(selected_resource_types)
    & all_findings_frame["status"].isin(selected_statuses)
    & all_findings_frame["recommended_action"].isin(selected_actions)
].copy()

if protected_filter == "Protected only":
    filtered_frame = filtered_frame[filtered_frame["protected_resource"]]
elif protected_filter == "Not protected":
    filtered_frame = filtered_frame[~filtered_frame["protected_resource"]]

filtered_records = filtered_frame.to_dict(orient="records")
filtered_summary = calculate_portfolio_summary(filtered_records)

st.subheader("Portfolio overview")
portfolio_columns = st.columns(4)
portfolio_columns[0].metric(
    "Current monthly cost",
    f"${portfolio_summary['current_monthly_cost']:,.2f}",
    help="Total synthetic current monthly cost across all resources.",
)
portfolio_columns[1].metric(
    "Confirmed monthly savings",
    f"${portfolio_summary['confirmed_monthly_savings']:,.2f}",
    help="Includes WASTE_DETECTED findings only.",
)
portfolio_columns[2].metric(
    "Confirmed annual savings",
    f"${portfolio_summary['confirmed_annual_savings']:,.2f}",
    help="Confirmed illustrative monthly savings multiplied by 12.",
)
portfolio_columns[3].metric(
    "Savings percentage",
    f"{portfolio_summary['savings_percentage']:.2f}%",
    help="Confirmed monthly savings divided by current monthly cost.",
)

opportunity_columns = st.columns(4)
opportunity_columns[0].metric(
    "Actionable findings",
    portfolio_summary["actionable_findings"],
)
opportunity_columns[1].metric(
    "Review required",
    portfolio_summary["review_required_findings"],
)
opportunity_columns[2].metric(
    "Protected resources",
    portfolio_summary["protected_resources"],
)
opportunity_columns[3].metric(
    "Potential savings pending review",
    f"${portfolio_summary['review_required_monthly_savings']:,.2f}",
    help=(
        "Potential savings associated with REVIEW_REQUIRED findings. "
        "This value is excluded from confirmed savings."
    ),
)

st.subheader("Filtered review summary")
filtered_columns = st.columns(5)
filtered_columns[0].metric("Resources shown", filtered_summary["resource_count"])
filtered_columns[1].metric(
    "Actionable findings",
    filtered_summary["actionable_findings"],
)
filtered_columns[2].metric(
    "Protected",
    filtered_summary["protected_resources"],
)
filtered_columns[3].metric(
    "Review required",
    filtered_summary["review_required_findings"],
)
filtered_columns[4].metric(
    "Confirmed monthly savings",
    f"${filtered_summary['confirmed_monthly_savings']:,.2f}",
)

st.subheader("Prioritized recommendations")
prioritized = prioritize_findings(filtered_records)

if not prioritized:
    st.info("No waste-detected recommendations match the selected filters.")
else:
    priority_frame = pd.DataFrame(prioritized).rename(
        columns={
            "priority": "Priority",
            "resource_id": "Resource ID",
            "cloud_provider": "Cloud",
            "resource_type": "Resource Type",
            "matched_policy": "Policy",
            "recommended_action": "Recommended Action",
            "estimated_monthly_savings": "Monthly Savings",
            "estimated_annual_savings": "Annual Savings",
            "requires_human_approval": "Approval Required",
            "reason": "Reason",
        }
    )
    priority_columns = [
        "Priority",
        "Resource ID",
        "Cloud",
        "Resource Type",
        "Policy",
        "Recommended Action",
        "Monthly Savings",
        "Annual Savings",
        "Approval Required",
        "Reason",
    ]
    st.dataframe(
        priority_frame[priority_columns],
        width="stretch",
        hide_index=True,
        column_config={
            "Monthly Savings": st.column_config.NumberColumn(
                "Monthly Savings",
                format="$%.2f",
            ),
            "Annual Savings": st.column_config.NumberColumn(
                "Annual Savings",
                format="$%.2f",
            ),
            "Approval Required": st.column_config.CheckboxColumn(
                "Approval Required",
            ),
        },
    )

st.subheader("Confirmed savings breakdown")
cloud_savings = pd.DataFrame(aggregate_savings(filtered_records, "cloud_provider"))
resource_savings = pd.DataFrame(
    aggregate_savings(filtered_records, "resource_type")
)
action_savings = pd.DataFrame(
    aggregate_savings(filtered_records, "recommended_action")
)
chart_columns = st.columns(3)

with chart_columns[0]:
    st.markdown("#### By cloud")
    if cloud_savings.empty:
        st.info("No confirmed savings.")
    else:
        st.bar_chart(cloud_savings, x="cloud_provider", y="monthly_savings")

with chart_columns[1]:
    st.markdown("#### By resource type")
    if resource_savings.empty:
        st.info("No confirmed savings.")
    else:
        st.bar_chart(resource_savings, x="resource_type", y="monthly_savings")

with chart_columns[2]:
    st.markdown("#### By action")
    if action_savings.empty:
        st.info("No confirmed savings.")
    else:
        st.bar_chart(action_savings, x="recommended_action", y="monthly_savings")

st.subheader("Deterministic policy findings")
if filtered_frame.empty:
    st.warning("No findings match all the selected filters.")
else:
    display_frame = filtered_frame.rename(
        columns={
            "resource_id": "Resource ID",
            "cloud_provider": "Cloud",
            "resource_type": "Resource Type",
            "matched_policy": "Matched Policy",
            "status": "Status",
            "recommended_action": "Recommended Action",
            "current_monthly_cost": "Current Monthly Cost",
            "estimated_monthly_savings": "Monthly Savings",
            "estimated_annual_savings": "Annual Savings",
            "protected_resource": "Protected",
            "requires_human_approval": "Approval Required",
            "artifact_expected": "Artifact Expected",
            "reason": "Reason",
        }
    )
    display_columns = [
        "Resource ID",
        "Cloud",
        "Resource Type",
        "Matched Policy",
        "Status",
        "Recommended Action",
        "Current Monthly Cost",
        "Monthly Savings",
        "Annual Savings",
        "Protected",
        "Approval Required",
        "Artifact Expected",
        "Reason",
    ]
    st.dataframe(
        display_frame[display_columns],
        width="stretch",
        hide_index=True,
        column_config={
            "Current Monthly Cost": st.column_config.NumberColumn(
                "Current Monthly Cost",
                format="$%.2f",
            ),
            "Monthly Savings": st.column_config.NumberColumn(
                "Monthly Savings",
                format="$%.2f",
            ),
            "Annual Savings": st.column_config.NumberColumn(
                "Annual Savings",
                format="$%.2f",
            ),
            "Protected": st.column_config.CheckboxColumn("Protected"),
            "Approval Required": st.column_config.CheckboxColumn(
                "Approval Required"
            ),
            "Artifact Expected": st.column_config.CheckboxColumn(
                "Artifact Expected"
            ),
        },
    )
    st.caption(
        f"Showing {len(filtered_frame)} of "
        f"{len(all_findings_frame)} deterministic findings."
    )

st.subheader("Finding status distribution")
status_counts = (
    filtered_frame["status"]
    .value_counts()
    .rename_axis("Status")
    .reset_index(name="Resources")
)
if status_counts.empty:
    st.info("No status distribution is available for the selected filters.")
else:
    st.bar_chart(status_counts, x="Status", y="Resources")

st.subheader("Download review report")
json_report = report_to_json(portfolio_report)
csv_report = findings_to_csv(all_findings)
download_columns = st.columns(2)
download_columns[0].download_button(
    label="Download JSON report",
    data=json_report,
    file_name="finops_review_report.json",
    mime="application/json",
)
download_columns[1].download_button(
    label="Download findings CSV",
    data=csv_report,
    file_name="finops_review_report.csv",
    mime="text/csv",
)

st.subheader("Review-only Terraform proposals")

st.info(
    "Artifact generation is explicit and allow-listed. Generated Terraform "
    "files contain proposal metadata only, declare no cloud resources, and "
    "cannot apply changes."
)

eligible_count = sum(
    finding.get("artifact_expected") is True
    for finding in all_findings
)

st.metric("Eligible findings", eligible_count)

if st.button(
    "Generate review-only Terraform proposals",
    type="primary",
):
    try:
        generated_artifacts = generate_eligible_artifacts(
            all_findings,
            template_dir=TEMPLATE_DIR,
            output_dir=TERRAFORM_OUTPUT_DIR,
        )
    except (KeyError, OSError, TypeError, ValueError) as exc:
        st.error("Terraform proposal generation failed.")
        st.code(str(exc))
    else:
        st.session_state["generated_artifacts"] = [
            artifact.to_dict()
            for artifact in generated_artifacts
        ]
        st.success(
            f"Generated {len(generated_artifacts)} "
            "review-only proposals."
        )

artifact_rows = st.session_state.get(
    "generated_artifacts",
    [],
)

if artifact_rows:
    artifact_frame = pd.DataFrame(artifact_rows).rename(
        columns={
            "resource_id": "Resource ID",
            "matched_policy": "Policy",
            "recommended_action": "Action",
            "template_name": "Template",
            "artifact_path": "Artifact Path",
            "sha256": "SHA-256",
            "dry_run": "Dry Run",
            "human_approval_required": "Approval Required",
        }
    )

    artifact_columns = [
        "Resource ID",
        "Policy",
        "Action",
        "Template",
        "Artifact Path",
        "SHA-256",
        "Dry Run",
        "Approval Required",
    ]

    st.dataframe(
        artifact_frame[artifact_columns],
        width="stretch",
        hide_index=True,
    )

    manifest_path = (
        TERRAFORM_OUTPUT_DIR / "artifact_manifest.json"
    )

    if manifest_path.is_file():
        st.download_button(
            label="Download artifact manifest",
            data=manifest_path.read_text(
                encoding="utf-8"
            ),
            file_name="artifact_manifest.json",
            mime="application/json",
        )

st.subheader("Terraform validation results")

if TERRAFORM_VALIDATION_PATH.is_file():
    try:
        validation_rows = json.loads(
            TERRAFORM_VALIDATION_PATH.read_text(
                encoding="utf-8-sig",
            )
        )
    except (json.JSONDecodeError, OSError) as exc:
        st.error("Unable to read Terraform validation results.")
        st.code(str(exc))
    else:
        if not isinstance(validation_rows, list):
            st.error(
                "Terraform validation results must contain a JSON list."
            )
        else:
            validation_frame = pd.DataFrame(validation_rows)

            required_validation_columns = {
                "ResourceDirectory",
                "TerraformFmt",
                "TerraformInit",
                "TerraformValidate",
                "TFLint",
                "DryRunPresent",
                "ApprovalRequiredPresent",
                "UnsafeContentFound",
                "PostFormatSha256",
                "OverallPassed",
            }

            missing_validation_columns = (
                required_validation_columns
                - set(validation_frame.columns)
            )

            if missing_validation_columns:
                st.error(
                    "The Terraform validation evidence has an "
                    "incomplete schema."
                )
                st.code(
                    ", ".join(
                        sorted(missing_validation_columns)
                    )
                )
            elif validation_frame.empty:
                st.info(
                    "No Terraform validation results are available."
                )
            else:
                boolean_columns = [
                    "TerraformFmt",
                    "TerraformInit",
                    "TerraformValidate",
                    "TFLint",
                    "OverallPassed",
                ]

                for column in boolean_columns:
                    validation_frame[column] = (
                        validation_frame[column]
                        .astype(str)
                        .str.casefold()
                        .map(
                            {
                                "true": True,
                                "false": False,
                            }
                        )
                        .fillna(False)
                    )

                passed_count = int(
                    validation_frame["OverallPassed"].sum()
                )
                failure_count = (
                    len(validation_frame) - passed_count
                )

                validation_columns = st.columns(3)

                validation_columns[0].metric(
                    "Proposal directories",
                    len(validation_frame),
                )
                validation_columns[1].metric(
                    "Fully validated",
                    passed_count,
                )
                validation_columns[2].metric(
                    "Validation failures",
                    failure_count,
                )

                display_validation_frame = (
                    validation_frame.rename(
                        columns={
                            "ResourceDirectory": (
                                "Resource Directory"
                            ),
                            "TerraformFmt": "Terraform Format",
                            "TerraformInit": "Terraform Init",
                            "TerraformValidate": (
                                "Terraform Validate"
                            ),
                            "TFLint": "TFLint",
                            "DryRunPresent": "Dry Run Present",
                            "ApprovalRequiredPresent": "Approval Required",
                            "UnsafeContentFound": "Unsafe Content Found",
                            "PostFormatSha256": "Validated SHA-256",
                            "OverallPassed": "Overall Passed",
                        }
                    )
                )

                validation_display_columns = [
                    "Resource Directory",
                    "Terraform Format",
                    "Terraform Init",
                    "Terraform Validate",
                    "TFLint",
                    "Dry Run Present",
                    "Approval Required",
                    "Unsafe Content Found",
                    "Validated SHA-256",
                    "Overall Passed",
                ]

                st.dataframe(
                    display_validation_frame[
                    validation_display_columns
                    ],
                    width="stretch",
                    hide_index=True,
                    column_config={
                        "Terraform Format": (
                            st.column_config.CheckboxColumn(
                                "Terraform Format"
                            )
                        ),
                        "Terraform Init": (
                            st.column_config.CheckboxColumn(
                                "Terraform Init"
                            )
                        ),
                        "Terraform Validate": (
                            st.column_config.CheckboxColumn(
                                "Terraform Validate"
                            )
                        ),
                        "TFLint": (
                            st.column_config.CheckboxColumn(
                                "TFLint"
                            )
                        ),
                        "Dry Run Present": st.column_config.CheckboxColumn(
                            "Dry Run Present"
                        ),
                        "Approval Required": st.column_config.CheckboxColumn(
                            "Approval Required"
                        ),
                        "Unsafe Content Found": st.column_config.CheckboxColumn(
                            "Unsafe Content Found"
                        ),
                        "Overall Passed": (
                            st.column_config.CheckboxColumn(
                                "Overall Passed"
                            )
                        ),
                    },
                )

                if passed_count == len(validation_frame):
                    st.success(
                        "All review-only Terraform proposals "
                        "passed formatting, structural "
                        "validation, and linting."
                    )
                else:
                    st.warning(
                        "One or more Terraform proposals did "
                        "not pass all validation checks."
                    )
else:
    st.info(
        "Terraform validation evidence has not been "
        "generated yet."
    )

st.subheader("Safety boundary")
st.markdown(
    """
- Safety gates run before optimization policies.
- Production, critical, legal-hold, and exempt resources receive `NO_ACTION`.
- Missing ownership and ambiguous environments result in `REVIEW_REQUIRED`.
- Resources with insufficient observation history do not receive an action.
- Confirmed savings include only `WASTE_DETECTED` findings.
- Potential savings pending review remain separate from confirmed savings.
- Every material recommendation requires human approval.
- YAML safety expressions are descriptive and are never dynamically executed.
- Terraform proposals contain metadata only and declare no cloud resources.
- Terraform apply is never executed by this application.
- No AWS or Azure API calls are performed.
- All costs and savings are synthetic and illustrative.
"""
)

with st.expander("How the deterministic workflow works"):
    st.markdown(
        """
1. Load and validate synthetic telemetry.
2. Load and validate versioned YAML policies.
3. Apply explicit Python safety gates.
4. Evaluate the policy matching each resource type.
5. Calculate illustrative monthly and annual savings.
6. Separate confirmed savings from opportunities pending review.
7. Prioritize waste findings by monthly savings.
8. Display and export structured findings for human review.

The language model does not choose policies, actions, or savings values.
"""
    )

with st.expander("Current project scope"):
    st.markdown(
        """
### Implemented

- Synthetic AWS-style and Azure-style telemetry
- Pydantic input validation
- YAML policy validation
- Deterministic safety and policy evaluation
- Transparent portfolio and savings reporting
- Prioritized recommendations
- JSON and CSV reports
- Ground-truth regression testing
- Streamlit review interface

### Planned for later sessions

- Allow-listed Jinja2 Terraform templates
- Plan-only Terraform artifact generation
- Terraform formatting and validation
- Final documentation and demonstration rehearsal

Automatic remediation and `terraform apply` remain outside the project scope.
"""
    )
