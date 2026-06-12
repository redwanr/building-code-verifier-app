"""Report rendering tests — written before implementation (TDD)."""

from report import (
    DISCLAIMER, ExtractedParam, Finding, Report,
    render_markdown, render_html,
)


def sample_report():
    params = [ExtractedParam(
        param="claimed_far", value=4.2, unit="ratio", confidence=0.62,
        source_page=1, source_crop=None, confirmed=True, edited_from=3.9,
    )]
    findings = [Finding(
        rule_id="BNBC-EGRESS-001", bucket="needs_verification",
        severity="Critical", confidence=0.74,
        reason="10 storeys with 1 stair; high-rise needs >=2 exits.",
        citation="BNBC-2020 Part 3", regime="BNBC",
        inputs_used={"num_storeys": 10, "num_exit_stairs": 1},
        sheet_location=None,
        remediation="Add a second fire-separated exit stair.",
        verify_flag=True,
    )]
    return Report(
        submission_id="test-uuid",
        rule_packs=["bnbc-2020@2020-01-01", "rajuk-dap-2025@2025-09-01"],
        params=params, findings=findings,
    )


def test_markdown_contains_disclaimer_and_packs():
    md = render_markdown(sample_report())
    assert DISCLAIMER in md
    assert "bnbc-2020@2020-01-01" in md
    assert "BNBC-EGRESS-001" in md
    assert "[VERIFY]" in md  # verify-flagged threshold surfaced


def test_markdown_summary_counts():
    md = render_markdown(sample_report())
    assert "needs_verification: 1" in md or "Needs verification: 1" in md


def test_markdown_records_user_edit():
    md = render_markdown(sample_report())
    assert "3.9" in md  # edited_from in audit trail (FR-6)


def test_html_contains_disclaimer():
    html = render_html(sample_report())
    assert "Decision-support only" in html
    assert "<html" in html.lower()


def test_report_summary_property():
    r = sample_report()
    assert r.summary == {
        "likely_violation": 0, "needs_verification": 1, "appears_compliant": 0,
    }
