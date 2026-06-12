"""Data contracts (PRD §11) + report rendering.

These objects are the single internal data contract: every screen reads/writes
them, exports serialize them. Production later = same objects, DB sink.
"""

from __future__ import annotations

import base64
import html as html_mod
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DISCLAIMER = (
    "⚠️ Decision-support only — not a certification. This tool gives a "
    "first-pass, automated triage of possible code issues for review by a "
    "qualified, licensed architect/engineer. It does not approve, certify, or "
    "guarantee compliance with RAJUK rules or BNBC. Extracted values and "
    "findings may be wrong. A qualified professional must independently "
    "verify everything. No legal reliance."
)

BUCKETS = ("likely_violation", "needs_verification", "appears_compliant")

BUCKET_LABELS = {
    "likely_violation": "🔴 Likely violation",
    "needs_verification": "🟡 Needs verification",
    "appears_compliant": "🟢 Appears compliant",
}


@dataclass
class ExtractedParam:
    param: str
    value: Any
    unit: str
    confidence: float
    source_page: int
    source_crop: str | None = None  # path to crop image
    crop_fallback_note: str | None = None  # text location when bbox unusable
    confirmed: bool = False
    edited_from: Any = None


@dataclass
class Finding:
    rule_id: str
    bucket: str
    severity: str
    confidence: float
    reason: str
    citation: str
    regime: str  # "BNBC" or "RAJUK"
    inputs_used: dict
    sheet_location: str | None
    remediation: str
    verify_flag: bool = False
    user_action: str | None = None  # accept / dismiss
    user_note: str | None = None


@dataclass
class Report:
    submission_id: str
    rule_packs: list[str]
    params: list[ExtractedParam]
    findings: list[Finding]
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    disclaimer_version: str = "v1"

    @property
    def summary(self) -> dict[str, int]:
        return {b: sum(1 for f in self.findings if f.bucket == b) for b in BUCKETS}

    def to_dict(self) -> dict:
        d = asdict(self)
        d["summary"] = self.summary
        return d


def new_report(rule_packs, params, findings) -> Report:
    return Report(
        submission_id=str(uuid.uuid4()),
        rule_packs=list(rule_packs), params=list(params), findings=list(findings),
    )


def _finding_md(f: Finding) -> str:
    verify = " `[VERIFY]`" if f.verify_flag else ""
    action = f" — reviewer: {f.user_action}" if f.user_action else ""
    note = f" ({f.user_note})" if f.user_note else ""
    return (
        f"### {f.rule_id}{verify} — {f.severity} (confidence {f.confidence:.2f})\n\n"
        f"{f.reason}\n\n"
        f"- **Regime:** {f.regime} · **Citation:** {f.citation}\n"
        f"- **Inputs used:** {f.inputs_used}\n"
        f"- **Suggested fix:** {f.remediation}{action}{note}\n"
    )


def _params_md(params: list[ExtractedParam]) -> str:
    lines = ["| Param | Value | Unit | Confidence | Confirmed | Edited from |",
             "|---|---|---|---|---|---|"]
    for p in params:
        lines.append(
            f"| {p.param} | {p.value} | {p.unit} | {p.confidence:.2f} "
            f"| {'yes' if p.confirmed else 'no'} "
            f"| {p.edited_from if p.edited_from is not None else '—'} |"
        )
    return "\n".join(lines)


def render_markdown(report: Report) -> str:
    parts = [
        "# Permit-Sheet Code Verifier — Findings Report",
        f"> {DISCLAIMER}",
        f"**Submission:** {report.submission_id} · **Created:** {report.created_at}",
        "**Active rule packs:** " + ", ".join(f"`{p}`" for p in report.rule_packs),
        "## Summary",
        "\n".join(f"- {BUCKET_LABELS[b]}: {n}" for b, n in report.summary.items()),
    ]
    for bucket in BUCKETS:
        in_bucket = [f for f in report.findings if f.bucket == bucket]
        if in_bucket:
            parts.append(f"## {BUCKET_LABELS[bucket]}")
            parts.extend(_finding_md(f) for f in in_bucket)
    parts += ["## Extracted parameters (audit trail)", _params_md(report.params),
              f"> {DISCLAIMER}"]
    return "\n\n".join(parts)


def _crop_img_tag(path: str | None) -> str:
    if not path or not Path(path).exists():
        return ""
    data = base64.b64encode(Path(path).read_bytes()).decode()
    return f'<img src="data:image/png;base64,{data}" style="max-width:100%;border:1px solid #ccc"/>'


_SEVERITY_COLOR = {"Critical": "#c0392b", "High": "#e67e22",
                   "Medium": "#f1c40f", "Low": "#7f8c8d"}


def render_html(report: Report) -> str:
    def badge(text, color):
        return (f'<span style="background:{color};color:#fff;border-radius:4px;'
                f'padding:2px 8px;font-size:12px">{text}</span>')

    rows = []
    for bucket in BUCKETS:
        in_bucket = [f for f in report.findings if f.bucket == bucket]
        if not in_bucket:
            continue
        rows.append(f"<h2>{html_mod.escape(BUCKET_LABELS[bucket])}</h2>")
        for f in in_bucket:
            badges = badge(f.severity, _SEVERITY_COLOR.get(f.severity, "#555"))
            badges += " " + badge(f"confidence {f.confidence:.2f}", "#2980b9")
            if f.verify_flag:
                badges += " " + badge("VERIFY — threshold in flux", "#8e44ad")
            rows.append(
                '<div style="border:1px solid #ddd;border-radius:8px;'
                'padding:12px;margin:10px 0">'
                f"<h3>{html_mod.escape(f.rule_id)}</h3>{badges}"
                f"<p>{html_mod.escape(f.reason)}</p>"
                f"<p><b>{html_mod.escape(f.regime)}</b> · "
                f"{html_mod.escape(f.citation)}</p>"
                f"<p>Inputs: <code>{html_mod.escape(str(f.inputs_used))}</code></p>"
                f"<p>Suggested fix: {html_mod.escape(f.remediation)}</p>"
                f"{_crop_img_tag(f.sheet_location)}"
                + (f"<p>Reviewer: {html_mod.escape(f.user_action)}"
                   + (f" — {html_mod.escape(f.user_note)}" if f.user_note else "")
                   + "</p>" if f.user_action else "")
                + "</div>"
            )

    summary = " · ".join(
        f"{BUCKET_LABELS[b]}: {n}" for b, n in report.summary.items()
    )
    disclaimer_box = (
        '<div style="background:#fff3cd;border:1px solid #ffc107;'
        f'border-radius:8px;padding:12px;margin:12px 0">{html_mod.escape(DISCLAIMER)}</div>'
    )
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Code Verifier Report</title></head>
<body style="font-family:Georgia,serif;max-width:860px;margin:auto;padding:24px">
<h1>Permit-Sheet Code Verifier — Findings Report</h1>
{disclaimer_box}
<p><b>Submission:</b> {html_mod.escape(report.submission_id)} ·
<b>Created:</b> {html_mod.escape(report.created_at)}</p>
<p><b>Active rule packs:</b> {html_mod.escape(', '.join(report.rule_packs))}</p>
<p>{summary}</p>
{''.join(rows)}
<h2>Extracted parameters (audit trail)</h2>
<table border="1" cellpadding="6" style="border-collapse:collapse">
<tr><th>Param</th><th>Value</th><th>Unit</th><th>Confidence</th><th>Confirmed</th><th>Edited from</th></tr>
{''.join(f'<tr><td>{html_mod.escape(p.param)}</td><td>{html_mod.escape(str(p.value))}</td><td>{html_mod.escape(p.unit)}</td><td>{p.confidence:.2f}</td><td>{"yes" if p.confirmed else "no"}</td><td>{html_mod.escape(str(p.edited_from)) if p.edited_from is not None else "—"}</td></tr>' for p in report.params)}
</table>
{disclaimer_box}
</body></html>"""
