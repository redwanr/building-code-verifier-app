"""Rule engine: YAML pack loader + simpleeval interpreter (PRD §7).

Rules are data, not code (FR-10). A domain expert edits the YAML packs;
this module only knows how to evaluate `logic` expressions.

FR-9: a rule with a missing/unconfirmed required input emits a
"cannot evaluate" finding — never a silent pass.
Grill-me decision: verify_flag rules cap at needs_verification.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml
from simpleeval import EvalWithCompoundTypes

from report import ExtractedParam, Finding

PACK_DIR = Path(__file__).resolve().parent / "rule_packs"

_REGIME = {"BNBC-2020": "BNBC", "RAJUK-DAP/Bidhimala": "RAJUK"}


@dataclass
class Rule:
    id: str
    source: str
    title: str
    parameters: list
    logic: str
    severity: str
    confidence_basis: str
    citation: str
    remediation: str
    verify_flag: bool = False


def load_packs(pack_dir: Path = PACK_DIR) -> list[Rule]:
    rules = []
    for path in sorted(pack_dir.glob("*.yaml")):
        pack = yaml.safe_load(path.read_text())
        for row in pack["rules"]:
            rules.append(Rule(source=pack["source"], **row))
    return rules


def _consistency(values, tolerance=0.05):
    """True when all values agree within relative tolerance."""
    nums = [float(v) for v in values]
    lo, hi = min(nums), max(nums)
    return hi == 0 or (hi - lo) / max(abs(hi), 1e-9) <= tolerance


def evaluate_rules(rules: list[Rule], params: list[ExtractedParam]) -> list[Finding]:
    confirmed = {p.param: p.value for p in params if p.confirmed}
    crops = {p.param: p.source_crop for p in params if p.confirmed}

    findings = []
    for rule in rules:
        missing = [name for name in rule.parameters if name not in confirmed]
        regime = _REGIME[rule.source]
        crop = next((crops[n] for n in rule.parameters if crops.get(n)), None)

        if missing:
            findings.append(Finding(
                rule_id=rule.id, bucket="needs_verification",
                severity=rule.severity, confidence=0.0,
                reason=(f"Cannot evaluate — input missing or unconfirmed: "
                        f"{', '.join(missing)}."),
                citation=rule.citation, regime=regime,
                inputs_used={k: confirmed[k] for k in rule.parameters
                             if k in confirmed},
                sheet_location=crop, remediation=rule.remediation,
                verify_flag=rule.verify_flag,
            ))
            continue

        names = dict(confirmed)
        evaluator = EvalWithCompoundTypes(
            names=names,
            functions={
                "param_present": lambda n, _c=confirmed: n in _c and bool(_c[n]),
                "consistency": _consistency,
            },
        )
        passed = bool(evaluator.eval(rule.logic))
        inputs_used = {k: confirmed[k] for k in rule.parameters}

        if passed:
            bucket, reason = "appears_compliant", (
                f"{rule.title}: appears compliant on confirmed inputs "
                f"(not a certification)."
            )
        else:
            bucket = "needs_verification" if rule.verify_flag else "likely_violation"
            reason = f"{rule.title}: check failed on confirmed inputs."
            if rule.verify_flag:
                reason += (" Threshold is [VERIFY] (2025/2026 rules in flux) — "
                           "expert must confirm the value before relying on this.")

        findings.append(Finding(
            rule_id=rule.id, bucket=bucket, severity=rule.severity,
            confidence=min((p.confidence for p in params
                            if p.confirmed and p.param in rule.parameters),
                           default=1.0),
            reason=reason, citation=rule.citation, regime=regime,
            inputs_used=inputs_used, sheet_location=crop,
            remediation=rule.remediation, verify_flag=rule.verify_flag,
        ))
    return findings
