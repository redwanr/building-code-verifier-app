"""Acceptance test: the validated G+9 sheet's four known findings.

Rule-engine half runs on ground-truth params (the post-confirmation state).
The extraction half — reading these values off the real PDF — is exercised
by eval_providers.py against fixtures/ once the sheet is added.

The four manual-validation findings (PRD §1):
  1. single-staircase egress problem
  2. missing high-rise fire provisions
  3. questionable FAR figure
  4. inconsistent parking count
"""

from report import ExtractedParam
from rules import evaluate_rules, load_packs


def p(name, value):
    return ExtractedParam(param=name, value=value, unit="", confidence=0.9,
                          source_page=1, confirmed=True)


# Ground truth for the G+9 sheet (confirmed-state params). FAR figure on the
# sheet (4.2) does not reconcile with floor-area math (~5.0); parking table
# says 20 but plan shows 14; one stair; no high-rise fire provisions noted.
G9_CONFIRMED = [
    p("num_storeys", 10),
    p("building_height_m", 30.0),
    p("num_exit_stairs", 1),
    p("num_lifts", 1),
    p("claimed_far", 4.2),
    p("total_floor_area_m2", 2500.0),
    p("plot_area_m2", 500.0),
    p("parking_provided_table", 20),
    p("parking_count_on_plan", 14),
]


def flagged(findings):
    return {f.rule_id for f in findings
            if f.bucket in ("likely_violation", "needs_verification")}


def test_g9_reproduces_all_four_manual_findings():
    findings = evaluate_rules(load_packs(), G9_CONFIRMED)
    bad = flagged(findings)
    assert "BNBC-EGRESS-001" in bad            # 1. single staircase
    assert "BNBC-FIRE-002" in bad              # 2. missing fire provisions
    assert "RAJUK-FAR-003-CONSISTENCY" in bad  # 3. questionable FAR
    assert "RAJUK-PARKING-006-CONSISTENCY" in bad  # 4. parking mismatch


def test_g9_hard_violations_not_hidden_behind_verify():
    """Consistency checks have no in-flux threshold -> full-strength bucket."""
    findings = evaluate_rules(load_packs(), G9_CONFIRMED)
    by_id = {f.rule_id: f for f in findings}
    assert by_id["RAJUK-FAR-003-CONSISTENCY"].bucket == "likely_violation"
    assert by_id["RAJUK-PARKING-006-CONSISTENCY"].bucket == "likely_violation"


def test_g9_no_silent_passes_for_missing_inputs():
    """Rules whose inputs aren't on the sheet must say 'cannot evaluate'."""
    findings = evaluate_rules(load_packs(), G9_CONFIRMED)
    by_id = {f.rule_id: f for f in findings}
    assert "cannot evaluate" in by_id["RAJUK-SETBACK-005"].reason.lower()
    assert by_id["RAJUK-SETBACK-005"].bucket == "needs_verification"
