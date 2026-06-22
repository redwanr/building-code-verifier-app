"""RAJUK Permit-Sheet Code Verifier — Streamlit MVP.

5-step wizard (PRD §5): password gate -> [Upload -> Confirm -> Findings ->
Inspect -> Export]. Session-state only; nothing persists beyond the session
(PRD §14). UI restyled per design_handoff_rajuk_verifier — sketch aesthetic
applied via injected CSS; the real extraction/rules/export pipeline is unchanged.
"""

import tempfile

import streamlit as st

from extraction import extract_params, CONFIDENCE_THRESHOLD
from report import DISCLAIMER, BUCKETS, BUCKET_LABELS, ExtractedParam, \
    new_report, render_html, render_markdown
from rules import evaluate_rules, load_packs, PACK_DIR

st.set_page_config(page_title="RAJUK Code Verifier (MVP)", page_icon="📐",
                   layout="wide")

# --- design tokens (from handoff README) ---
INK = "#2b2b2b"
CRIT, WARN, OK = "#c0392b", "#c8920f", "#2e7d4f"
CRIT_BG, WARN_BG, OK_BG = "#f8e3df", "#faf0d6", "#dff0e4"
MUTED = "#8a8678"

STEP_NAMES = ["Upload", "Confirm", "Findings", "Inspect", "Export"]

# Reviewer-supplied values the sheet can't tell us (DAP ward/LUC-specific).
USER_SUPPLIED = {
    "permissible_far": "Permissible FAR (from DAP ward/LUC — enter if known)",
    "allowable_mgc_pct": "Allowable MGC % (from Bidhimala bracket)",
    "required_front_setback_m": "Required front setback (m)",
    "required_rear_setback_m": "Required rear setback (m)",
    "required_side_setback_m": "Required side setback (m)",
    "parking_required": "Required parking count (from ratio for unit mix)",
    "min_stair_width_m": "Minimum exit-stair width (m, BNBC)",
    "min_room_area_m2": "Minimum habitable room area (m², BNBC)",
    "min_room_width_m": "Minimum habitable room width (m, BNBC)",
}


def inject_css():
    # ponytail: targets Streamlit's generated DOM — restyle, not pixel-perfect.
    # Brittle to Streamlit version bumps; keep selectors broad.
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Caveat:wght@500;700&family=Kalam:wght@300;400;700&display=swap');
    .stApp { background:#efece4; }
    .block-container { font-family:'Kalam',cursive; color:#2b2b2b; max-width:1180px; }
    h1,h2,h3,.dc-display { font-family:'Caveat',cursive !important; font-weight:700; }
    /* primary CTAs: organic asymmetric radius */
    .stButton > button {
        font-family:'Kalam',cursive; font-weight:700;
        border-radius:10px 8px 12px 8px; border:2px solid #2b2b2b;
    }
    .stButton > button[kind="primary"] { background:#2b2b2b; color:#fff; }
    .stButton > button[kind="primary"]:disabled { background:#bdbab0; border-color:#bdbab0; }
    /* disclaimer banner — st.warning restyled to dashed amber */
    [data-testid="stAlertContainer"] {
        background:#faf0d6 !important; border:none !important;
        border-bottom:2px dashed #c8920f !important; border-radius:8px;
        color:#7a5a08 !important; font-size:12px;
    }
    /* cards / containers with borders */
    [data-testid="stVerticalBlockBorderWrapper"] {
        border-radius:12px !important;
    }
    </style>
    """, unsafe_allow_html=True)


def disclaimer():
    st.warning(DISCLAIMER)


def conf_bar(c: float) -> str:
    color = OK if c >= 0.80 else WARN if c >= 0.60 else CRIT
    bg = OK_BG if c >= 0.80 else WARN_BG if c >= 0.60 else CRIT_BG
    return (
        f'<div style="display:flex;align-items:center;gap:6px;font-size:12px">'
        f'<div style="flex:1;height:7px;background:{bg};border-radius:4px;overflow:hidden">'
        f'<div style="width:{int(c*100)}%;height:100%;background:{color}"></div></div>'
        f'{c:.2f}</div>'
    )


def bucket_color(bucket: str) -> str:
    return {"likely_violation": CRIT, "needs_verification": WARN,
            "appears_compliant": OK}[bucket]


def goto(step: int):
    st.session_state.step = step
    st.rerun()


def password_gate() -> bool:
    if st.session_state.get("authed"):
        return True
    pw = st.text_input("Access password", type="password")
    if pw and pw == st.secrets.get("APP_PASSWORD", ""):
        st.session_state.authed = True
        st.rerun()
    elif pw:
        st.error("Wrong password.")
    return False


def provider_config():
    # gemini first = default: cloud deploy only has a Gemini key in secrets.
    provider = st.sidebar.selectbox("Extraction provider", ["gemini", "claude"])
    key_name = "ANTHROPIC_API_KEY" if provider == "claude" else "GEMINI_API_KEY"
    api_key = st.secrets.get(key_name, "")
    if not api_key:
        st.sidebar.error(f"{key_name} missing from secrets.")
    st.sidebar.caption(
        "Privacy: uploaded pages are sent to the selected LLM provider for "
        "extraction (no-training API tier). Files are kept only for this "
        "session — no permanent archive."
    )
    return provider, api_key


def step_rail():
    """Clickable left rail — free navigation per design (no gate)."""
    step = st.session_state.step
    st.markdown("<div style='font-size:10.5px;color:#9a978b;text-transform:"
                "uppercase;letter-spacing:.06em;margin-bottom:6px'>Submission "
                "flow</div>", unsafe_allow_html=True)
    for i, name in enumerate(STEP_NAMES):
        mark = "✓" if i < step else "▶" if i == step else str(i + 1)
        if st.button(f"{mark}  {name}", key=f"rail_{i}",
                     type="primary" if i == step else "secondary",
                     use_container_width=True):
            goto(i)
    st.markdown("<div style='font-size:10px;color:#9a978b;line-height:1.3;"
                "margin-top:10px'>Uploads &amp; crops deleted after the "
                "session — no permanent archive.</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------- step 0
def step_upload(provider, api_key):
    st.subheader("1 · Upload")
    packs = sorted(p.stem for p in PACK_DIR.glob("*.yaml"))
    uploaded = st.file_uploader(
        "Drop permit-sheet PDF here  ·  raster ok (no text layer) · ≤ 2 pages",
        type=["pdf"])
    c1, c2 = st.columns(2)
    c1.text_input("Jurisdiction / rule pack",
                  value="RAJUK DAP 2025 + BNBC-2020", disabled=True)
    c2.text_input("Effective date", value="2025-09-01", disabled=True)
    st.caption("Active rule packs: " + ", ".join(f"`{p}`" for p in packs))
    st.markdown(
        "<div style='font-family:Caveat,cursive;font-size:15px;color:#7a5a08;"
        "background:#faf0d6;border-radius:8px;padding:8px 10px;margin-top:8px'>"
        "Rule pack &amp; date are recorded on every report — reproducible "
        "against a dated gazette.</div>", unsafe_allow_html=True)

    if uploaded and st.button("Extract parameters →", type="primary",
                              disabled=not api_key):
        crop_dir = tempfile.mkdtemp(prefix="crops_")
        with st.spinner(f"Rasterizing + reading sheet with {provider}…"):
            try:
                st.session_state.params = extract_params(
                    uploaded.read(), provider, api_key, crop_dir)
                st.session_state.findings = None
                goto(1)
            except Exception as e:  # surface provider errors plainly
                st.error(f"Extraction failed: {e}")


# ---------------------------------------------------------------- step 1
def step_confirm():
    """FR-5 gate: user edits/confirms before checks run. Non-negotiable."""
    params = st.session_state.get("params")
    if not params:
        st.info("Upload and extract a sheet first (step 1).")
        return

    flagged_unconfirmed = []  # filled while rendering
    st.subheader("2 · Confirm extracted parameters")
    st.caption("Checks won't run until every flagged field (🟡) is confirmed — "
               "no manufactured confidence. Every edit is stored in the audit "
               "trail.")
    hdr = st.columns([2.2, 1, 2, 1.2])
    for col, t in zip(hdr, ["Field", "Value", "Confidence", "Confirm"]):
        col.markdown(f"**{t}**")

    edited = []
    for p in params:
        flagged = p.confidence < CONFIDENCE_THRESHOLD
        cols = st.columns([2.2, 1, 2, 1.2])
        label = f"{'🟡 ' if flagged else ''}{p.param}"
        cols[0].markdown(f"`{p.param}` {'🟡' if flagged else ''}<br>"
                         f"<span style='font-size:10px;color:{MUTED}'>{p.unit}</span>",
                         unsafe_allow_html=True)
        if isinstance(p.value, bool):
            new_val = cols[1].checkbox(p.param, value=p.value, key=f"v_{p.param}",
                                       label_visibility="collapsed")
        else:
            new_val = cols[1].number_input(p.param, value=float(p.value),
                                           key=f"v_{p.param}",
                                           label_visibility="collapsed")
        cols[2].markdown(conf_bar(p.confidence), unsafe_allow_html=True)
        confirm = cols[3].checkbox("confirm", value=not flagged,
                                   key=f"c_{p.param}",
                                   label_visibility="collapsed")
        if p.source_crop:
            with cols[2].popover("📍 crop"):
                st.image(p.source_crop)
        elif p.crop_fallback_note:
            cols[2].caption(f"📍 p{p.source_page}: {p.crop_fallback_note}")
        if flagged and not confirm:
            flagged_unconfirmed.append(p.param)
        edited.append(ExtractedParam(
            param=p.param, value=new_val, unit=p.unit, confidence=p.confidence,
            source_page=p.source_page, source_crop=p.source_crop,
            crop_fallback_note=p.crop_fallback_note, confirmed=confirm,
            edited_from=p.value if new_val != p.value else None,
        ))

    st.markdown("**Reviewer-supplied limits** (ward/LUC-specific — the sheet "
                "can't tell us these; blank = rule reports *cannot evaluate*)")
    extracted_names = {p.param for p in edited}
    for name, lbl in USER_SUPPLIED.items():
        if name in extracted_names:
            continue
        val = st.number_input(lbl, value=0.0, key=f"u_{name}")
        if val:
            edited.append(ExtractedParam(
                param=name, value=val, unit="", confidence=1.0,
                source_page=0, confirmed=True))

    if flagged_unconfirmed:
        st.markdown(
            f"<span style='font-size:11px;font-weight:700;color:#7a5a08;"
            f"background:#faf0d6;border-radius:7px;padding:4px 9px'>"
            f"{len(flagged_unconfirmed)} field"
            f"{'' if len(flagged_unconfirmed)==1 else 's'} need confirmation"
            f"</span>", unsafe_allow_html=True)
    else:
        st.markdown("<span style='font-size:11px;font-weight:700;color:#2e7d4f;"
                    "background:#dff0e4;border-radius:7px;padding:4px 9px'>"
                    "All fields confirmed ✓</span>", unsafe_allow_html=True)

    if st.button("Run checks →", type="primary",
                 disabled=bool(flagged_unconfirmed)):
        st.session_state.confirmed_params = edited
        st.session_state.findings = evaluate_rules(load_packs(), edited)
        goto(2)


# ---------------------------------------------------------------- step 2
FILTERS = ["All", "Likely violation", "Needs verification", "BNBC", "RAJUK"]


def _passes_filter(f, flt):
    if flt == "All":
        return True
    if flt == "Likely violation":
        return f.bucket == "likely_violation"
    if flt == "Needs verification":
        return f.bucket == "needs_verification"
    return f.regime == flt  # BNBC / RAJUK


def step_findings():
    findings = st.session_state.get("findings")
    if not findings:
        st.info("Run checks first (step 2).")
        return
    st.subheader("3 · Triaged findings")
    counts = {b: sum(1 for f in findings if f.bucket == b) for b in BUCKETS}
    badges = "".join(
        f"<span style='font-size:11px;font-weight:700;color:{bucket_color(b)};"
        f"background:{ {CRIT:CRIT_BG,WARN:WARN_BG,OK:OK_BG}[bucket_color(b)] };"
        f"border-radius:7px;padding:3px 8px;margin-right:6px'>"
        f"{counts[b]} {BUCKET_LABELS[b].split(' ',1)[1]}</span>"
        for b in BUCKETS)
    st.markdown(badges, unsafe_allow_html=True)

    flt = st.radio("filter", FILTERS, horizontal=True,
                   label_visibility="collapsed")

    for i, f in enumerate(findings):
        if not _passes_filter(f, flt):
            continue
        color = bucket_color(f.bucket)
        verify = " · [VERIFY]" if f.verify_flag else ""
        st.markdown(
            f"<div style='border:2px solid #2b2b2b;border-left:5px solid {color};"
            f"border-radius:11px;padding:11px 14px;margin-top:8px'>"
            f"<div style='display:flex;align-items:center;gap:9px'>"
            f"<div style='width:11px;height:11px;border-radius:50%;background:{color}'></div>"
            f"<div style='flex:1'><b style='font-size:13px'>{f.rule_id} — {f.severity}{verify}</b>"
            f"<br><span style='font-size:10.5px;color:{MUTED}'>{f.regime} · {f.citation}</span></div>"
            f"<span style='font-size:10px;color:{MUTED}'>{f.confidence:.2f}</span></div>"
            f"</div>", unsafe_allow_html=True)
        if st.button("Inspect ›", key=f"insp_{i}"):
            st.session_state.active_finding = i
            goto(3)


# ---------------------------------------------------------------- step 3
def step_inspect():
    findings = st.session_state.get("findings")
    if not findings:
        st.info("Run checks first (step 2).")
        return
    idx = st.session_state.get("active_finding", 0)
    idx = max(0, min(idx, len(findings) - 1))
    f = findings[idx]
    color = bucket_color(f.bucket)

    top = st.columns([3, 1])
    if top[0].button("‹ back to findings"):
        goto(2)
    top[1].markdown(f"<div style='text-align:right;font-size:11px;font-weight:700'>"
                    f"Finding {idx+1} of {len(findings)}</div>",
                    unsafe_allow_html=True)

    left, right = st.columns([2, 1])
    with left:
        st.markdown(
            f"<span style='font-size:10.5px;font-weight:700;color:{color};"
            f"background:{ {CRIT:CRIT_BG,WARN:WARN_BG,OK:OK_BG}[color] };"
            f"border-radius:6px;padding:3px 8px'>{f.severity}</span> "
            f"<span style='font-size:10.5px;font-weight:700;background:#ece9df;"
            f"border-radius:6px;padding:3px 8px'>{f.regime}</span> "
            f"<span style='font-size:10.5px;color:{MUTED}'>confidence "
            f"{f.confidence:.2f}</span>", unsafe_allow_html=True)
        st.markdown(f"<div class='dc-display' style='font-size:24px;font-weight:700;"
                    f"margin:8px 0'>{f.rule_id}</div>", unsafe_allow_html=True)
        st.write(f.reason)
        st.markdown(
            f"<div style='font-size:11.5px;background:#f4f2eb;border-left:3px "
            f"solid #2b2b2b;padding:8px 11px'><b>Clause</b><br>{f.citation}</div>",
            unsafe_allow_html=True)
        st.markdown(
            f"<div style='font-size:11.5px;background:#eef6f0;border-left:3px "
            f"solid #2e7d4f;padding:8px 11px;margin-top:8px'><b>Suggested fix</b>"
            f"<br>{f.remediation}</div>", unsafe_allow_html=True)
        st.caption(f"Inputs used: `{f.inputs_used}`")
    with right:
        st.markdown(f"<div style='font-size:11px;color:#6b6859'>Sheet location · "
                    f"page</div>", unsafe_allow_html=True)
        if f.sheet_location:
            st.image(f.sheet_location, caption="evidence crop")
        else:
            st.markdown("<div style='background:repeating-linear-gradient(45deg,"
                        "#eeece4,#eeece4 8px,#e1ded2 8px,#e1ded2 16px);border:2px "
                        "solid #2b2b2b;border-radius:6px;height:140px;display:flex;"
                        "align-items:center;justify-content:center'><span "
                        "style='font-family:monospace;font-size:10px;background:#fff;"
                        "padding:3px 6px;border-radius:3px'>no crop</span></div>",
                        unsafe_allow_html=True)

    act = st.columns([1, 1, 3])
    if act[0].button("Accept finding", type="primary"):
        f.user_action = "accept"
    if act[1].button("Dismiss"):
        f.user_action = "dismiss"
    f.user_note = act[2].text_input("add a note for the report…",
                                    value=f.user_note or "",
                                    label_visibility="collapsed") or None
    if f.user_action:
        st.caption(f"Reviewer action: **{f.user_action}**")


# ---------------------------------------------------------------- step 4
def step_export():
    findings = st.session_state.get("findings")
    if not findings:
        st.info("Run checks first (step 2).")
        return
    st.subheader("5 · Build & export report")
    left, right = st.columns([1, 1])
    with left:
        st.markdown("**Format**")
        fmt = st.radio("format", ["PDF (print HTML)", "Markdown"],
                       label_visibility="collapsed")
        st.markdown("**Include**")
        st.checkbox("Risk summary (counts by severity)", value=True, disabled=True)
        st.checkbox("Full findings list + accept/dismiss notes", value=True,
                    disabled=True)
        st.checkbox("Parameters used", value=True, disabled=True)
        include_crops = st.checkbox("Evidence crops (confidential)", value=False)
        st.checkbox("Disclaimer + rule-pack version (🔒 locked on)", value=True,
                    disabled=True)
    with right:
        packs = sorted(p.stem for p in PACK_DIR.glob("*.yaml"))
        report = new_report(packs, st.session_state.confirmed_params, findings)
        # ponytail: crop toggle only strips crops from HTML export (the only
        # render that embeds them); MD has none. Strip in-place on a shallow copy.
        if not include_crops:
            for f in report.findings:
                f.sheet_location = None
        st.markdown("**Preview**")
        st.markdown(
            f"<div style='background:#e7e4db;border-radius:6px;padding:12px'>"
            f"<div style='background:#fff;border:1px solid #c4c0b3;padding:10px'>"
            f"<div class='dc-display' style='font-size:15px;font-weight:700'>"
            f"Permit-sheet triage report</div>"
            f"<div style='font-size:8.5px;color:#6b6859'>"
            f"{' · '.join(packs)}</div></div></div>", unsafe_allow_html=True)
        if fmt.startswith("Markdown"):
            st.download_button("Export report →", render_markdown(report),
                               type="primary",
                               file_name=f"findings_{report.submission_id[:8]}.md")
        else:
            st.download_button("Export report →", render_html(report),
                               type="primary",
                               file_name=f"findings_{report.submission_id[:8]}.html")


# ---------------------------------------------------------------- footer
def footer_nav():
    step = st.session_state.step
    has_params = bool(st.session_state.get("params"))
    has_findings = bool(st.session_state.get("findings"))
    st.divider()
    c1, c2, c3 = st.columns([1, 2, 1])
    if step > 0 and c1.button("‹ Back"):
        goto(step - 1)
    c2.markdown(f"<div style='text-align:center;font-size:11.5px;color:#6b6859'>"
                f"Step {step+1} of 5 · {STEP_NAMES[step]}</div>",
                unsafe_allow_html=True)
    # Confirm + Export carry their action button in-panel; no footer Next.
    if step in (0, 2, 3):
        nxt_label = "Export →" if step == 3 else "Next →"
        # gate Upload->Confirm on extraction; Findings/Inspect need findings.
        disabled = (step == 0 and not has_params) or \
                   (step in (2, 3) and not has_findings)
        if c3.button(nxt_label, type="primary", disabled=disabled,
                     key=f"next_{step}"):
            goto(step + 1)


def main():
    inject_css()
    st.markdown("<h1>📐 RAJUK Permit-Sheet Verifier — MVP</h1>",
                unsafe_allow_html=True)
    disclaimer()
    if not password_gate():
        return
    provider, api_key = provider_config()
    st.session_state.setdefault("step", 0)

    rail_col, content = st.columns([1, 4])
    with rail_col:
        step_rail()
    with content:
        step = st.session_state.step
        if step == 0:
            step_upload(provider, api_key)
        elif step == 1:
            step_confirm()
        elif step == 2:
            step_findings()
        elif step == 3:
            step_inspect()
        elif step == 4:
            step_export()
        footer_nav()
    disclaimer()


main()
