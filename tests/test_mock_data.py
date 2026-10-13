"""Focused tests for the deterministic Session 1 mock findings."""

from finops_demo.mock_data import calculate_summary, get_mock_findings


def test_mock_findings_have_expected_summary() -> None:
    findings = get_mock_findings()
    summary = calculate_summary(findings)

    assert summary == {
        "total_resources": 8,
        "waste_detected": 3,
        "protected_resources": 2,
        "review_required": 1,
        "estimated_monthly_savings": 72.45,
    }


def test_protected_findings_receive_no_action() -> None:
    protected_findings = [
        finding for finding in get_mock_findings() if finding["protected"]
    ]

    assert protected_findings
    assert all(
        finding["recommended_action"] == "NO_ACTION" for finding in protected_findings
    )
    assert all(
        finding["estimated_monthly_savings"] == 0.00 for finding in protected_findings
    )


def test_get_mock_findings_returns_independent_records() -> None:
    first_result = get_mock_findings()
    first_result[0]["status"] = "CHANGED_BY_TEST"

    second_result = get_mock_findings()

    assert second_result[0]["status"] == "WASTE_DETECTED"
