"""Rule engine tests — written before implementation (TDD).

Semantics under test (PRD §7, FR-9, grill-me decisions):
- Rules load from YAML packs keyed {jurisdiction}@{effective_date}.
- logic is a simpleeval expression over confirmed params + helpers.
- Missing/unconfirmed required input -> "cannot evaluate" finding (FR-9),
  never a silent pass.
- verify_flag rules cap at needs_verification, never likely_violation.
- Buckets: likely_violation / needs_verification / appears_compliant.
"""

import pytest

from report import ExtractedParam
from rules import evaluate_rules, load_packs, Rule


def param(name, value, confirmed=True, confidence=0.95):
    return ExtractedParam(
        param=name, value=value, unit="", confidence=confidence,
        source_page=1, source_crop=None, confirmed=confirmed,
    )


def make_rule(**overrides):
    base = dict(
        id="TEST-001",
        source="BNBC-2020",
        title="Test rule",
        parameters=["a"],
        logic="a > 5",
        severity="High",
        confidence_basis="test",
        citation="BNBC-2020 test clause",
        remediation="fix it",
        verify_flag=False,
    )
    base.update(overrides)
    return Rule(**base)


# --- pack loading ---

def test_load_packs_returns_rules_from_yaml():
    rules = load_packs()
    ids = {r.id for r in rules}
    assert "BNBC-EGRESS-001" in ids
    assert "RAJUK-PARKING-006-RATIO" in ids
    egress = next(r for r in rules if r.id == "BNBC-EGRESS-001")
    assert egress.source == "BNBC-2020"
    assert egress.severity == "Critical"
    assert egress.verify_flag is True


def test_rules_belong_to_exactly_one_source():
    for rule in load_packs():
        assert rule.source in ("BNBC-2020", "RAJUK-DAP/Bidhimala")


# --- evaluation buckets ---

def test_passing_rule_appears_compliant():
    findings = evaluate_rules([make_rule()], [param("a", 10)])
    assert findings[0].bucket == "appears_compliant"


def test_failing_rule_likely_violation():
    findings = evaluate_rules([make_rule()], [param("a", 3)])
    assert findings[0].bucket == "likely_violation"


def test_failing_verify_flag_rule_caps_at_needs_verification():
    rule = make_rule(verify_flag=True)
    findings = evaluate_rules([rule], [param("a", 3)])
    assert findings[0].bucket == "needs_verification"


def test_passing_verify_flag_rule_still_appears_compliant():
    rule = make_rule(verify_flag=True)
    findings = evaluate_rules([rule], [param("a", 10)])
    assert findings[0].bucket == "appears_compliant"


# --- FR-9: never silently pass ---

def test_missing_required_param_cannot_evaluate():
    findings = evaluate_rules([make_rule()], [])
    f = findings[0]
    assert f.bucket == "needs_verification"
    assert "cannot evaluate" in f.reason.lower()
    assert "a" in f.reason


def test_unconfirmed_param_treated_as_missing():
    findings = evaluate_rules([make_rule()], [param("a", 10, confirmed=False)])
    assert findings[0].bucket == "needs_verification"
    assert "cannot evaluate" in findings[0].reason.lower()


# --- helpers in the eval namespace ---

def test_param_present_helper():
    rule = make_rule(parameters=["a"], logic="param_present('a')")
    findings = evaluate_rules([rule], [param("a", True)])
    assert findings[0].bucket == "appears_compliant"


def test_consistency_helper_within_tolerance():
    rule = make_rule(parameters=["x", "y"], logic="consistency([x, y])")
    findings = evaluate_rules([rule], [param("x", 100.0), param("y", 102.0)])
    assert findings[0].bucket == "appears_compliant"


def test_consistency_helper_flags_mismatch():
    rule = make_rule(parameters=["x", "y"], logic="consistency([x, y])")
    findings = evaluate_rules([rule], [param("x", 100.0), param("y", 130.0)])
    assert findings[0].bucket == "likely_violation"


# --- real seed rules against G+9-shaped params ---

G9_PARAMS = [
    param("num_storeys", 10),
    param("building_height_m", 30.0),
    param("num_exit_stairs", 1),
]


def test_egress_rule_flags_single_stair_highrise():
    rules = [r for r in load_packs() if r.id == "BNBC-EGRESS-001"]
    findings = evaluate_rules(rules, G9_PARAMS)
    f = findings[0]
    # verify_flag rule -> capped at needs_verification, but flagged not passing
    assert f.bucket == "needs_verification"
    assert f.severity == "Critical"
    assert f.regime == "BNBC"


def test_egress_rule_passes_with_two_stairs():
    rules = [r for r in load_packs() if r.id == "BNBC-EGRESS-001"]
    params = G9_PARAMS[:2] + [param("num_exit_stairs", 2)]
    findings = evaluate_rules(rules, params)
    assert findings[0].bucket == "appears_compliant"


def test_parking_consistency_rule_flags_mismatch():
    rules = [r for r in load_packs() if r.id == "RAJUK-PARKING-006-CONSISTENCY"]
    assert rules, "parking consistency rule must exist as its own data row"
    params = [param("parking_provided_table", 20), param("parking_count_on_plan", 14)]
    findings = evaluate_rules(rules, params)
    assert findings[0].bucket != "appears_compliant"


def test_far_limit_rule_cannot_evaluate_without_permissible():
    rules = [r for r in load_packs() if r.id == "RAJUK-FAR-003-LIMIT"]
    assert rules
    findings = evaluate_rules(rules, [param("claimed_far", 4.2)])
    assert findings[0].bucket == "needs_verification"
    assert "cannot evaluate" in findings[0].reason.lower()


# --- finding record completeness (FR-8) ---

def test_finding_records_inputs_and_citation():
    findings = evaluate_rules([make_rule()], [param("a", 3)])
    f = findings[0]
    assert f.rule_id == "TEST-001"
    assert f.citation == "BNBC-2020 test clause"
    assert f.regime == "BNBC"
    assert f.inputs_used == {"a": 3}
    assert f.remediation == "fix it"
    assert 0.0 <= f.confidence <= 1.0
