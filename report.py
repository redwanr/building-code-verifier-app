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
    return (f'<img src="data:image/png;base64,{data}" '
            f'style="max-width:100%;border:1px solid #E7E0D0;border-radius:6px"/>')


def _e(s) -> str:
    return html_mod.escape(str(s))


def _conf_meter_html(c: float) -> str:
    """Inline confidence meter for the audit table."""
    if c <= 0.0:
        return ('<span class="missing">INPUT MISSING</span>')
    fill = "#5C7A4F" if c >= 0.80 else "#B07A22" if c >= 0.50 else "#A6342A"
    return (f'<span class="cf"><span class="track">'
            f'<i style="width:{int(c*100)}%;background:{fill}"></i>'
            f'</span>{c:.2f}</span>')


def _sev_class(sev: str) -> str:
    s = sev.lower()
    if s == "critical": return "crit"
    if s == "high":     return "high"
    if s in ("medium", "moderate"): return "med"
    return "ok"


def _regime_pill(regime: str) -> str:
    if regime.upper() == "BNBC":
        return '<span class="src-pill bnbc">BNBC</span>'
    return '<span class="src-pill rajuk">RAJUK</span>'


def _inputs_html(inputs_used) -> str:
    if isinstance(inputs_used, dict):
        s = " · ".join(f"{_e(k)}: {_e(v)}" for k, v in inputs_used.items())
        return s or '<span class="empty">none supplied</span>'
    s = _e(str(inputs_used)) if inputs_used else ""
    return s or '<span class="empty">none supplied</span>'


def _finding_html(f: "Finding") -> str:  # noqa: F821
    sc = _sev_class(f.severity)
    stmt = _e(f.reason).replace(
        "[VERIFY]", '<span class="mono" style="color:#B07A22">[VERIFY]</span>')
    right = ""
    if f.verify_flag:
        right += '<span class="verify-tag">VERIFY · threshold in flux</span> '
    if f.confidence <= 0.0:
        right += '<span class="missing">INPUT MISSING</span>'
    else:
        fill = "#5C7A4F" if f.confidence >= 0.80 else "#B07A22" if f.confidence >= 0.50 else "#A6342A"
        right += (f'<div class="conf"><span class="lab">conf</span>'
                  f'<div class="track"><i style="width:{int(f.confidence*100)}%;'
                  f'background:{fill}"></i></div>'
                  f'<span class="val">{f.confidence:.2f}</span></div>')
    fix_label = "NOTE" if f.bucket == "appears_compliant" else "SUGGESTED FIX"
    crop = _crop_img_tag(f.sheet_location)
    action_html = ""
    if f.user_action:
        note = f" — {_e(f.user_note)}" if f.user_note else ""
        action_html = (f'<p style="font-family:\'IBM Plex Mono\',monospace;'
                       f'font-size:11px;color:#5F574A;margin-top:8px">'
                       f'Reviewer: {_e(f.user_action)}{note}</p>')
    return (
        f'<div class="finding f-{sc}">'
        f'<div class="f-top"><span class="sev {sc}">{_e(f.severity).upper()}</span>'
        f'<span class="code">{_e(f.rule_id)}</span>'
        f'<div class="f-right">{right}</div></div>'
        f'<p class="f-statement">{stmt}</p>'
        f'<div class="f-src">{_regime_pill(f.regime)}'
        f'<span>{_e(f.citation)}</span></div>'
        f'<div class="f-inputs"><div class="k">INPUTS</div>'
        f'<div class="v">{_inputs_html(f.inputs_used)}</div></div>'
        f'<div class="f-fix"><div class="k">{fix_label}</div>'
        f'<div class="v">{_e(f.remediation)}</div></div>'
        f'{crop}{action_html}</div>'
    )


_BUCKET_DOTS = {
    "likely_violation":  "#A6342A",
    "needs_verification": "#B07A22",
    "appears_compliant":  "#5C7A4F",
}
_BUCKET_LABELS_HTML = {
    "likely_violation":  "Likely violation",
    "needs_verification": "Needs verification",
    "appears_compliant":  "Appears compliant",
}
_STAT_CLASS = {
    "likely_violation": "crit",
    "needs_verification": "med",
    "appears_compliant": "ok",
}
_STAT_LABEL = {
    "likely_violation": "Likely violation",
    "needs_verification": "Needs verification",
    "appears_compliant": "Appears compliant",
}


def render_html(report: "Report") -> str:  # noqa: F821
    """Production-grade findings report — ported from export-report.html design handoff."""
    e = _e
    summary = report.summary

    # summary stat cards
    stat_html = "".join(
        f'<div class="stat {_STAT_CLASS[b]}">'
        f'<div class="n">{summary[b]}</div>'
        f'<div class="l"><i></i>{_STAT_LABEL[b]}</div></div>'
        for b in BUCKETS)

    # finding groups
    groups_html = ""
    for bucket in BUCKETS:
        in_bucket = [f for f in report.findings if f.bucket == bucket]
        dot = _BUCKET_DOTS[bucket]
        label = _BUCKET_LABELS_HTML[bucket]
        ct = len(in_bucket)
        findings_html = "".join(_finding_html(f) for f in in_bucket) if in_bucket else (
            f'<div class="empty-group">'
            f'<div class="big">None flagged as {label.lower()}.</div>'
            f'<div class="small">No check resolved to this outcome on the supplied inputs. '
            f'Review the other groups before relying on this.</div></div>')
        groups_html += (
            f'<div class="group">'
            f'<div class="group-head">'
            f'<span class="dot" style="background:{dot}"></span>'
            f'<h2>{label}</h2>'
            f'<span class="ct">{ct} finding{"s" if ct != 1 else ""}</span>'
            f'</div>{findings_html}</div>')

    # audit table rows
    audit_rows = ""
    for p in report.params:
        edited = e(str(p.edited_from)) if p.edited_from is not None else '<span class="dash">—</span>'
        confirmed = ('<span class="yes"><i>✓</i>yes</span>'
                     if p.confirmed else '<span class="dash">no</span>')
        audit_rows += (
            f'<tr><td>{e(p.param)}</td>'
            f'<td class="num">{e(str(p.value))}</td>'
            f'<td class="unit">{e(p.unit)}</td>'
            f'<td>{_conf_meter_html(p.confidence)}</td>'
            f'<td>{confirmed}</td>'
            f'<td>{edited}</td></tr>')

    # pack pills
    pack_pills = "".join(
        f'<span class="pack"><i></i>{e(pk)}</span>'
        for pk in report.rule_packs)

    created = report.created_at[:16].replace("T", " ") + " UTC"

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>RAJUK Verifier — Findings Report</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Serif:wght@500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  :root{{
    --ink:#211C15; --ink2:#5F574A; --ink3:#938977; --line:#E7E0D0; --line2:#F0EADC;
    --paper:#FFFFFF; --cream:#F6F1E7; --soft:#FBF8F1;
    --clay:#B65C30; --clay-dk:#9E4B27; --clay-soft:#F4E5D9;
    --crit:#A6342A; --crit-bg:#F7E6E2;
    --high:#C0662C; --high-bg:#F7E9DC;
    --med:#B07A22; --med-bg:#F7EDD8;
    --ok:#5C7A4F; --ok-bg:#E8EEE1;
  }}
  *{{box-sizing:border-box;}}
  html{{-webkit-print-color-adjust:exact; print-color-adjust:exact;}}
  body{{margin:0; background:#EDE7DA; color:var(--ink);
    font-family:'IBM Plex Sans',system-ui,sans-serif; font-size:14px; line-height:1.55;
    -webkit-font-smoothing:antialiased;}}
  .sheet{{max-width:880px; margin:28px auto; background:var(--paper);
    border:1px solid var(--line); border-radius:6px; overflow:hidden;}}
  .mono{{font-family:'IBM Plex Mono',monospace;}}
  .head{{background:var(--cream); padding:34px 44px 28px; border-bottom:1px solid var(--line);}}
  .brand{{display:flex; align-items:center; gap:14px;}}
  .mark{{position:relative; width:42px; height:42px; border-radius:11px;
    background:var(--clay); flex:none; box-shadow:0 3px 8px rgba(182,92,48,.32);}}
  .mark::before{{content:""; position:absolute; left:11px; top:9px; width:14px;
    height:18px; border:2px solid rgba(255,255,255,.55); border-radius:3px;}}
  .mark::after{{content:""; position:absolute; left:16px; top:14px; width:14px;
    height:18px; border:2px solid #fff; border-radius:3px; background:var(--clay);}}
  .brand-name{{font:600 18px/1.1 'IBM Plex Serif',serif;}}
  .brand-sub{{font:400 11.5px/1.3 'IBM Plex Mono',monospace; color:var(--ink3); margin-top:3px;}}
  .report-title{{font:600 30px/1.15 'IBM Plex Serif',serif; margin:22px 0 4px;}}
  .report-kicker{{font:600 11px/1 'IBM Plex Mono',monospace; letter-spacing:.14em;
    text-transform:uppercase; color:var(--clay-dk);}}
  .meta{{display:flex; flex-wrap:wrap; gap:22px 40px; margin-top:18px;}}
  .meta-item .k{{font:600 10px/1 'IBM Plex Mono',monospace; letter-spacing:.1em;
    text-transform:uppercase; color:var(--ink3); margin-bottom:5px;}}
  .meta-item .v{{font:500 13px/1.4 'IBM Plex Mono',monospace; color:var(--ink);}}
  .packs{{display:flex; gap:8px; margin-top:4px;}}
  .pack{{display:inline-flex; align-items:center; gap:7px; background:#fff;
    border:1px solid var(--line); border-radius:999px; padding:5px 12px;
    font:500 11.5px 'IBM Plex Mono',monospace; color:var(--ink2);}}
  .pack i{{width:7px; height:7px; border-radius:999px; background:var(--ok); display:inline-block;}}
  .body{{padding:32px 44px 12px;}}
  .notice{{display:flex; gap:13px; align-items:flex-start; background:var(--med-bg);
    border:1px solid #EAD9AE; border-left:3px solid var(--med); border-radius:8px;
    padding:13px 16px; margin-bottom:30px;}}
  .notice .ic{{width:20px; height:20px; border-radius:999px; background:var(--med);
    color:#fff; display:flex; align-items:center; justify-content:center;
    font:700 12px 'IBM Plex Sans'; flex:none; margin-top:1px;}}
  .notice .tx{{font:400 12.5px/1.55 'IBM Plex Sans'; color:#6E4F18;}}
  .notice .tx b{{font-weight:600; color:#5A3F10;}}
  .sec-label{{font:600 11px/1 'IBM Plex Mono',monospace; letter-spacing:.14em;
    text-transform:uppercase; color:var(--ink3); margin:0 0 14px;}}
  .summary{{display:grid; grid-template-columns:repeat(3,1fr); gap:14px; margin-bottom:34px;}}
  .stat{{border:1px solid var(--line); border-radius:12px; padding:18px 20px; background:var(--soft);}}
  .stat .n{{font:600 34px/1 'IBM Plex Serif',serif;}}
  .stat .l{{display:flex; align-items:center; gap:8px; margin-top:10px;
    font:600 12px 'IBM Plex Sans'; letter-spacing:.02em;}}
  .stat .l i{{width:9px; height:9px; border-radius:999px; display:inline-block;}}
  .stat.crit{{background:var(--crit-bg); border-color:#EBC9C2;}}
  .stat.crit .n,.stat.crit .l{{color:var(--crit);}} .stat.crit i{{background:var(--crit);}}
  .stat.med{{background:var(--med-bg); border-color:#EAD9AE;}}
  .stat.med .n,.stat.med .l{{color:#8A5F18;}} .stat.med i{{background:var(--med);}}
  .stat.ok{{background:var(--ok-bg); border-color:#CFE0C6;}}
  .stat.ok .n,.stat.ok .l{{color:var(--ok);}} .stat.ok i{{background:var(--ok);}}
  .group{{margin-bottom:30px;}}
  .group-head{{display:flex; align-items:center; gap:11px; margin:0 0 16px;
    padding-bottom:11px; border-bottom:1px solid var(--line);}}
  .group-head .dot{{width:10px; height:10px; border-radius:999px;}}
  .group-head h2{{font:600 17px/1 'IBM Plex Serif',serif; margin:0;}}
  .group-head .ct{{font:600 12px 'IBM Plex Mono',monospace; color:var(--ink3); margin-left:auto;}}
  .finding{{border:1px solid var(--line); border-radius:12px; padding:18px 20px;
    margin-bottom:12px; background:#fff; break-inside:avoid;}}
  .finding.f-crit{{border-left:3px solid var(--crit);}}
  .finding.f-high{{border-left:3px solid var(--high);}}
  .finding.f-med{{border-left:3px solid var(--med);}}
  .finding.f-ok{{border-left:3px solid var(--ok);}}
  .f-top{{display:flex; align-items:center; gap:10px; margin-bottom:11px;}}
  .sev{{font:600 10.5px 'IBM Plex Sans'; letter-spacing:.05em; padding:3px 10px; border-radius:999px;}}
  .sev.crit{{color:var(--crit); background:var(--crit-bg);}}
  .sev.high{{color:var(--high); background:var(--high-bg);}}
  .sev.med{{color:#8A5F18; background:var(--med-bg);}}
  .sev.ok{{color:var(--ok); background:var(--ok-bg);}}
  .code{{font:500 12px 'IBM Plex Mono',monospace; color:var(--ink2);}}
  .f-right{{margin-left:auto; display:flex; align-items:center; gap:9px;}}
  .conf{{display:flex; align-items:center; gap:8px;}}
  .conf .lab{{font:400 10px 'IBM Plex Mono',monospace; color:var(--ink3); letter-spacing:.06em;}}
  .track{{width:60px; height:7px; border-radius:999px; background:#ECE6D9; overflow:hidden;}}
  .track > i{{display:block; height:100%; border-radius:999px;}}
  .conf .val{{font:600 12.5px 'IBM Plex Mono',monospace; color:var(--ink);}}
  .missing{{font:600 10px 'IBM Plex Mono',monospace; letter-spacing:.06em; color:var(--ink3);
    background:var(--line2); border:1px solid var(--line); padding:3px 9px; border-radius:999px;}}
  .verify-tag{{font:600 10px 'IBM Plex Sans'; letter-spacing:.04em; color:var(--med);
    border:1px solid #E3CF96; padding:3px 9px; border-radius:999px;}}
  .f-statement{{font:500 14.5px/1.5 'IBM Plex Sans'; color:var(--ink); margin:0 0 12px;}}
  .f-src{{font:400 12px/1.4 'IBM Plex Sans'; color:var(--ink2); margin:0 0 11px;
    display:flex; gap:8px; align-items:baseline;}}
  .src-pill{{font:600 10px 'IBM Plex Mono',monospace; letter-spacing:.06em;
    padding:2px 8px; border-radius:5px; flex:none;}}
  .src-pill.bnbc{{color:#4A5A2E; background:#EDF0E2;}}
  .src-pill.rajuk{{color:var(--clay-dk); background:var(--clay-soft);}}
  .f-inputs{{background:var(--soft); border:1px solid var(--line); border-radius:9px;
    padding:9px 13px; margin-bottom:11px;}}
  .f-inputs .k{{font:600 9.5px 'IBM Plex Mono',monospace; letter-spacing:.1em;
    color:var(--ink3); margin-bottom:5px;}}
  .f-inputs .v{{font:500 12.5px/1.65 'IBM Plex Mono',monospace; color:var(--ink); word-break:break-word;}}
  .f-inputs .v .empty{{color:var(--ink3);}}
  .f-fix{{border:1px solid #CFE0C6; border-left:3px solid var(--ok); background:#F2F6EE;
    border-radius:9px; padding:10px 14px;}}
  .f-fix .k{{font:600 9.5px 'IBM Plex Mono',monospace; letter-spacing:.1em; color:var(--ok); margin-bottom:5px;}}
  .f-fix .v{{font:500 13px/1.5 'IBM Plex Sans'; color:#2F4A28;}}
  .empty-group{{border:1px dashed var(--line); border-radius:12px; padding:22px;
    text-align:center; background:var(--soft);}}
  .empty-group .big{{font:600 15px 'IBM Plex Serif',serif; color:var(--ok);}}
  .empty-group .small{{font:400 12.5px 'IBM Plex Sans'; color:var(--ink2); margin-top:4px;}}
  .audit{{width:100%; border-collapse:separate; border-spacing:0;
    border:1px solid var(--line); border-radius:12px; overflow:hidden;}}
  .audit th{{font:600 9.5px 'IBM Plex Mono',monospace; letter-spacing:.1em; text-transform:uppercase;
    color:var(--ink3); text-align:left; padding:11px 16px; background:#F1EBDD; border-bottom:1px solid var(--line);}}
  .audit td{{font:500 13px 'IBM Plex Mono',monospace; color:var(--ink); padding:10px 16px;
    border-bottom:1px solid var(--line2);}}
  .audit tr:last-child td{{border-bottom:none;}}
  .audit tr:nth-child(even) td{{background:var(--soft);}}
  .audit .num{{color:var(--ink);}}
  .audit .unit{{color:var(--ink3); font-size:12px;}}
  .audit .cf{{display:inline-flex; align-items:center; gap:8px;}}
  .audit .cf .track{{width:46px;}}
  .yes{{display:inline-flex; align-items:center; gap:6px; font:600 11px 'IBM Plex Sans'; color:var(--ok);}}
  .yes i{{width:14px; height:14px; border-radius:5px; background:var(--ok); color:#fff;
    display:inline-flex; align-items:center; justify-content:center; font-size:9px;}}
  .dash{{color:var(--ink3);}}
  .foot{{margin:32px 44px 0; padding:20px 0 34px; border-top:1px solid var(--line);}}
  .foot .notice{{margin-bottom:16px;}}
  .foot .stamp{{display:flex; flex-wrap:wrap; gap:6px 18px;
    font:400 11px 'IBM Plex Mono',monospace; color:var(--ink3);}}
  .foot .stamp b{{color:var(--ink2); font-weight:600;}}
  @page{{size:A4; margin:14mm;}}
  @media print{{
    body{{background:#fff;}}
    .sheet{{margin:0; max-width:none; border:none; border-radius:0;}}
    .head{{padding:0 0 24px;}}
    .body{{padding:24px 0 0;}}
    .foot{{margin:28px 0 0;}}
    .finding,.stat,.group{{break-inside:avoid;}}
  }}
</style>
</head>
<body>
<div class="sheet">
  <header class="head">
    <div class="brand">
      <div class="mark"></div>
      <div>
        <div class="brand-name">RAJUK Verifier</div>
        <div class="brand-sub">Permit-sheet triage · decision support</div>
      </div>
    </div>
    <div class="report-kicker">Findings report</div>
    <div class="report-title">Permit-sheet code verification</div>
    <div class="meta">
      <div class="meta-item">
        <div class="k">Submission</div>
        <div class="v">{e(report.submission_id)}</div>
      </div>
      <div class="meta-item">
        <div class="k">Generated</div>
        <div class="v">{e(created)}</div>
      </div>
      <div class="meta-item">
        <div class="k">Active rule packs</div>
        <div class="packs">{pack_pills}</div>
      </div>
    </div>
  </header>
  <div class="body">
    <div class="notice">
      <div class="ic">!</div>
      <div class="tx"><b>Decision-support only — not a certification.</b> This is a
        first-pass automated triage of possible code issues for review by a qualified,
        licensed architect/engineer. It does not approve, certify, or guarantee
        compliance with RAJUK rules or BNBC. Extracted values and findings may be wrong
        — a qualified professional must independently verify everything. No legal
        reliance.</div>
    </div>
    <div class="sec-label">Risk summary</div>
    <div class="summary">{stat_html}</div>
    {groups_html}
    <div class="group">
      <div class="sec-label">Extracted parameters — audit trail</div>
      <table class="audit">
        <thead>
          <tr><th>Parameter</th><th>Value</th><th>Unit</th><th>Confidence</th>
              <th>Confirmed</th><th>Edited from</th></tr>
        </thead>
        <tbody>{audit_rows}</tbody>
      </table>
    </div>
  </div>
  <div class="foot">
    <div class="notice">
      <div class="ic">!</div>
      <div class="tx"><b>Decision-support only — not a certification.</b>
        A qualified, licensed professional must independently verify every value and
        finding. No legal reliance.</div>
    </div>
    <div class="stamp">
      <span><b>Rule packs</b> · {e(" · ".join(report.rule_packs))}</span>
      <span><b>Submission</b> · {e(report.submission_id[:8])}</span>
      <span><b>Generated</b> · {e(created)}</span>
    </div>
  </div>
</div>
</body>
</html>"""
