"""RAJUK Permit-Sheet Code Verifier — Streamlit MVP.

5-step wizard (PRD §5): password gate -> [Upload -> Confirm -> Findings ->
Inspect -> Export]. Session-state only; nothing persists beyond the session
(PRD §14).

UI: "drafting instrument" direction — cool neutrals + one structural-blue
accent, Space Grotesk display, IBM Plex Mono for every measured value. Sketch
aesthetic dropped. Real extraction/rules/export pipeline unchanged.
"""

import tempfile

import streamlit as st

from extraction import extract_params, CONFIDENCE_THRESHOLD
from report import DISCLAIMER, BUCKETS, BUCKET_LABELS, ExtractedParam, \
    new_report, render_html, render_markdown
from rules import evaluate_rules, load_packs, PACK_DIR

st.set_page_config(page_title="RAJUK Code Verifier", page_icon="◳",
                   layout="wide")

# --- design tokens ---
INK = "#16191D"
MUTED = "#5B6470"
BORDER = "#E2E5E9"
ACCENT = "#1F4BE0"
CRIT, WARN, OK = "#C8362B", "#B5740A", "#1E7D54"
CRIT_BG, WARN_BG, OK_BG = "#FCEDEB", "#FBF1DE", "#E7F4EC"
MONO = "'IBM Plex Mono',monospace"

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
    # ponytail: targets Streamlit's generated DOM — brittle to version bumps.
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');

    .stApp {{ background:#F5F6F7; }}
    .block-container {{
        font-family:'Space Grotesk',sans-serif; color:{INK};
        max-width:1140px; padding-top:2rem;
    }}
    h1,h2,h3 {{ font-family:'Space Grotesk',sans-serif !important;
        letter-spacing:-.02em; font-weight:600; color:{INK}; }}
    h3 {{ font-size:1.35rem; }}
    .block-container p, .block-container li, .block-container label {{
        font-family:'Space Grotesk',sans-serif; }}
    code {{ font-family:{MONO}; background:#EEF0F2; color:{INK};
        font-size:.85em; padding:1px 5px; border-radius:4px; }}

    /* buttons */
    .stButton>button {{
        font-family:'Space Grotesk',sans-serif; font-weight:500; font-size:13px;
        border-radius:8px; border:1px solid {BORDER}; background:#fff;
        color:{INK}; transition:all .12s ease; box-shadow:none;
    }}
    .stButton>button:hover {{ border-color:{ACCENT}; color:{ACCENT}; background:#fff; }}
    .stButton>button[kind="primary"] {{
        background:{ACCENT}; border-color:{ACCENT}; color:#fff; }}
    .stButton>button[kind="primary"]:hover {{
        background:#1A40C4; border-color:#1A40C4; color:#fff; }}
    .stButton>button:disabled, .stButton>button[kind="primary"]:disabled {{
        background:#C7CCD3; border-color:#C7CCD3; color:#fff; }}
    .stDownloadButton>button {{
        font-family:'Space Grotesk',sans-serif; font-weight:500;
        border-radius:8px; background:{ACCENT}; border:1px solid {ACCENT};
        color:#fff; }}
    .stDownloadButton>button:hover {{ background:#1A40C4; color:#fff; }}

    /* disclaimer = restrained amber rail, not a shouty box */
    [data-testid="stAlertContainer"], [data-testid="stAlert"] {{
        background:#FBF6EA !important; border:1px solid #ECDFBE !important;
        border-left:3px solid #C99A2E !important; border-radius:8px !important;
        color:#7A5A12 !important; }}
    [data-testid="stAlertContainer"] p {{ font-size:12px; line-height:1.45;
        color:#7A5A12 !important; }}

    /* inputs + dropzone */
    [data-testid="stTextInput"] input, [data-baseweb="input"],
    [data-testid="stNumberInput"] input {{ border-radius:8px !important; }}
    [data-testid="stFileUploaderDropzone"] {{
        background:#fff; border:1.5px dashed #C4CAD2; border-radius:10px; }}
    [data-testid="stFileUploaderDropzone"]:hover {{ border-color:{ACCENT}; }}

    /* radio row -> tidy chips spacing */
    [role="radiogroup"] {{ gap:6px; }}
    hr {{ border-color:{BORDER}; }}
    </style>
    """, unsafe_allow_html=True)


def disclaimer():
    # strip the text's leading ⚠️ — st.warning already renders one
    st.warning(DISCLAIMER.lstrip("⚠️ "))


def eyebrow(text: str):
    st.markdown(
        f"<div style='font-family:{MONO};font-size:10.5px;letter-spacing:.12em;"
        f"text-transform:uppercase;color:{MUTED};margin-bottom:1px'>{text}</div>",
        unsafe_allow_html=True)


def chip(text: str, color: str, bg: str) -> str:
    return (f"<span style='font-family:{MONO};font-size:10px;font-weight:500;"
            f"letter-spacing:.04em;text-transform:uppercase;color:{color};"
            f"background:{bg};border-radius:5px;padding:3px 8px'>{text}</span>")


def render_inline(html: str):
    # Streamlit only passes HTML through when the block starts with a
    # block-level tag — wrap bare inline spans so they don't render literally.
    st.markdown(f"<div>{html}</div>", unsafe_allow_html=True)


def conf_bar(c: float) -> str:
    color = OK if c >= 0.80 else WARN if c >= 0.60 else CRIT
    return (
        f"<div style='display:flex;align-items:center;gap:8px;font-family:{MONO};"
        f"font-size:11px;color:{MUTED}'>"
        f"<div style='flex:1;height:5px;background:#EAECEF;border-radius:3px;"
        f"overflow:hidden'><div style='width:{int(c*100)}%;height:100%;"
        f"background:{color}'></div></div>{c:.2f}</div>")


def bucket_color(bucket: str) -> str:
    return {"likely_violation": CRIT, "needs_verification": WARN,
            "appears_compliant": OK}[bucket]


def _sev_bg(color: str) -> str:
    return {CRIT: CRIT_BG, WARN: WARN_BG, OK: OK_BG}[color]


def goto(step: int):
    st.session_state.step = step
    st.rerun()


def password_gate() -> bool:
    if st.session_state.get("authed"):
        return True
    eyebrow("Restricted · licensed reviewers only")
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


def header():
    st.markdown(
        f"<div style='display:flex;align-items:baseline;gap:13px;"
        f"border-bottom:1px solid {BORDER};padding-bottom:13px;margin-bottom:4px'>"
        f"<div style='font-family:\"Space Grotesk\";font-weight:600;font-size:21px;"
        f"letter-spacing:-.02em'>RAJUK Permit-Sheet Verifier</div>"
        f"<div style='font-family:{MONO};font-size:10.5px;color:{MUTED};"
        f"text-transform:uppercase;letter-spacing:.12em'>MVP · decision-support"
        f"</div></div>", unsafe_allow_html=True)


def step_rail():
    """Measured flow rail — clickable, free navigation per design."""
    step = st.session_state.step
    eyebrow("Submission flow")
    for i, name in enumerate(STEP_NAMES):
        mark = "✓" if i < step else f"{i+1:02d}"
        if st.button(f"{mark}   {name}", key=f"rail_{i}",
                     type="primary" if i == step else "secondary",
                     use_container_width=True):
            goto(i)
    st.markdown(
        f"<div style='font-family:{MONO};font-size:9.5px;color:#9aa0a8;"
        f"line-height:1.4;margin-top:12px'>Uploads &amp; crops deleted after the "
        f"session. No permanent archive.</div>", unsafe_allow_html=True)


def step_heading(idx: int, title: str, right_html: str = ""):
    eyebrow(f"Step {idx+1:02d} / 05")
    if right_html:
        c1, c2 = st.columns([3, 2])
        c1.subheader(title)
        c2.markdown(f"<div style='text-align:right;padding-top:12px'>{right_html}"
                    f"</div>", unsafe_allow_html=True)
    else:
        st.subheader(title)


# ---------------------------------------------------------------- step 0
def step_upload(provider, api_key):
    step_heading(0, "Upload")
    packs = sorted(p.stem for p in PACK_DIR.glob("*.yaml"))
    uploaded = st.file_uploader(
        "Drop a permit-sheet PDF — raster ok (no text layer) · ≤ 2 pages",
        type=["pdf"])
    c1, c2 = st.columns(2)
    c1.text_input("Jurisdiction / rule pack",
                  value="RAJUK DAP 2025 + BNBC-2020", disabled=True)
    c2.text_input("Effective date", value="2025-09-01", disabled=True)
    st.markdown(
        f"<div style='font-family:{MONO};font-size:11px;color:{MUTED};"
        f"margin-top:2px'>Active packs · " +
        " · ".join(p for p in packs) + "</div>", unsafe_allow_html=True)
    st.markdown(
        f"<div style='font-size:12px;color:{MUTED};border-left:2px solid {BORDER};"
        f"padding:2px 0 2px 11px;margin-top:12px'>Rule pack and effective date "
        f"are stamped on every report — reproducible against a dated gazette."
        f"</div>", unsafe_allow_html=True)

    if uploaded and st.button("Extract parameters →", type="primary",
                              disabled=not api_key):
        crop_dir = tempfile.mkdtemp(prefix="crops_")
        with st.spinner(f"Rasterizing and reading the sheet with {provider}…"):
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
        st.info("Upload and extract a sheet first.")
        return

    edited = []
    flagged_unconfirmed = []
    # placeholder for the status pill (count known only after the loop)
    pill = st.empty()
    step_heading(1, "Confirm parameters")
    st.markdown(
        f"<div style='font-size:12.5px;color:{MUTED};margin:-4px 0 8px'>Checks "
        f"won't run until every flagged field is confirmed — no manufactured "
        f"confidence. Edits are kept in the audit trail.</div>",
        unsafe_allow_html=True)

    hdr = st.columns([2.4, 1, 2, 1.1])
    for col, t in zip(hdr, ["FIELD", "VALUE", "CONFIDENCE", "CONFIRM"]):
        col.markdown(f"<div style='font-family:{MONO};font-size:10px;"
                     f"letter-spacing:.08em;color:{MUTED}'>{t}</div>",
                     unsafe_allow_html=True)

    for p in params:
        flagged = p.confidence < CONFIDENCE_THRESHOLD
        cols = st.columns([2.4, 1, 2, 1.1])
        cols[0].markdown(
            f"<div style='font-family:{MONO};font-size:12.5px;padding-top:6px'>"
            f"{'🔸 ' if flagged else ''}{p.param}"
            f"<span style='color:{MUTED};font-size:10px'>  {p.unit}</span></div>",
            unsafe_allow_html=True)
        if isinstance(p.value, bool):
            new_val = cols[1].checkbox(p.param, value=p.value, key=f"v_{p.param}",
                                       label_visibility="collapsed")
        else:
            new_val = cols[1].number_input(p.param, value=float(p.value),
                                           key=f"v_{p.param}",
                                           label_visibility="collapsed")
        cols[2].markdown(f"<div style='padding-top:8px'>{conf_bar(p.confidence)}"
                         f"</div>", unsafe_allow_html=True)
        confirm = cols[3].checkbox("confirm", value=not flagged,
                                   key=f"c_{p.param}",
                                   label_visibility="collapsed")
        if p.source_crop:
            with cols[2].popover("crop"):
                st.image(p.source_crop)
        elif p.crop_fallback_note:
            cols[2].caption(f"p{p.source_page}: {p.crop_fallback_note}")
        if flagged and not confirm:
            flagged_unconfirmed.append(p.param)
        edited.append(ExtractedParam(
            param=p.param, value=new_val, unit=p.unit, confidence=p.confidence,
            source_page=p.source_page, source_crop=p.source_crop,
            crop_fallback_note=p.crop_fallback_note, confirmed=confirm,
            edited_from=p.value if new_val != p.value else None,
        ))

    if flagged_unconfirmed:
        n = len(flagged_unconfirmed)
        pill.markdown(f"<div>{chip(f'{n} field' + ('' if n == 1 else 's') + ' to confirm', WARN, WARN_BG)}</div>",
                      unsafe_allow_html=True)
    else:
        pill.markdown(f"<div>{chip('all fields confirmed', OK, OK_BG)}</div>",
                      unsafe_allow_html=True)

    st.markdown(f"<div style='font-family:{MONO};font-size:10px;letter-spacing:"
                f".08em;color:{MUTED};margin-top:14px'>REVIEWER-SUPPLIED LIMITS</div>"
                f"<div style='font-size:11.5px;color:{MUTED};margin-bottom:4px'>"
                f"Ward/LUC-specific — the sheet can't tell us these; blank = rule "
                f"reports <i>cannot evaluate</i>.</div>", unsafe_allow_html=True)
    extracted_names = {p.param for p in edited}
    for name, lbl in USER_SUPPLIED.items():
        if name in extracted_names:
            continue
        val = st.number_input(lbl, value=0.0, key=f"u_{name}")
        if val:
            edited.append(ExtractedParam(
                param=name, value=val, unit="", confidence=1.0,
                source_page=0, confirmed=True))

    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    if st.button("Run code checks →", type="primary",
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
        st.info("Run checks first.")
        return
    counts = {b: sum(1 for f in findings if f.bucket == b) for b in BUCKETS}
    labels = {"likely_violation": "likely", "needs_verification": "verify",
              "appears_compliant": "ok"}
    badges = "  ".join(
        chip(f"{counts[b]} {labels[b]}", bucket_color(b),
             _sev_bg(bucket_color(b))) for b in BUCKETS)
    step_heading(2, "Findings", right_html=badges)

    flt = st.radio("filter", FILTERS, horizontal=True,
                   label_visibility="collapsed")

    for i, f in enumerate(findings):
        if not _passes_filter(f, flt):
            continue
        color = bucket_color(f.bucket)
        verify = "  ·  VERIFY" if f.verify_flag else ""
        st.markdown(
            f"<div style='background:#fff;border:1px solid {BORDER};"
            f"border-left:3px solid {color};border-radius:10px;padding:12px 15px;"
            f"margin-top:8px;display:flex;align-items:center;gap:13px'>"
            f"<div style='flex:1'>"
            f"<div style='font-size:13px;font-weight:500;color:{INK};"
            f"line-height:1.35'>{f.reason}</div>"
            f"<div style='font-family:{MONO};font-size:10.5px;color:{MUTED};"
            f"margin-top:3px'>{f.rule_id} · {f.regime} · {f.citation}{verify}</div>"
            f"</div>"
            f"{chip(f.severity, color, _sev_bg(color))}"
            f"<span style='font-family:{MONO};font-size:11px;color:{MUTED};"
            f"min-width:30px;text-align:right'>{f.confidence:.2f}</span>"
            f"</div>", unsafe_allow_html=True)
        if st.button("Inspect →", key=f"insp_{i}"):
            st.session_state.active_finding = i
            goto(3)


# ---------------------------------------------------------------- step 3
def step_inspect():
    findings = st.session_state.get("findings")
    if not findings:
        st.info("Run checks first.")
        return
    idx = max(0, min(st.session_state.get("active_finding", 0),
                     len(findings) - 1))
    f = findings[idx]
    color = bucket_color(f.bucket)

    top = st.columns([3, 1])
    if top[0].button("‹ Back to findings"):
        goto(2)
    top[1].markdown(f"<div style='text-align:right;font-family:{MONO};"
                    f"font-size:11px;color:{MUTED};padding-top:7px'>"
                    f"{idx+1:02d} / {len(findings):02d}</div>",
                    unsafe_allow_html=True)

    left, right = st.columns([2, 1])
    with left:
        render_inline(
            chip(f.severity, color, _sev_bg(color)) + "  " +
            chip(f.regime, INK, "#EEF0F2") +
            f"  <span style='font-family:{MONO};font-size:10.5px;color:{MUTED}'>"
            f"confidence {f.confidence:.2f}</span>")
        st.markdown(
            f"<div style='font-size:19px;font-weight:600;letter-spacing:-.01em;"
            f"margin:10px 0 4px;line-height:1.25'>{f.reason}</div>",
            unsafe_allow_html=True)
        st.markdown(
            f"<div style='font-size:11px;color:{MUTED};font-family:{MONO}'>"
            f"Inputs · {f.inputs_used}</div>", unsafe_allow_html=True)
        st.markdown(
            f"<div style='font-size:12px;background:#F7F8F9;border-left:3px solid "
            f"{INK};border-radius:0 6px 6px 0;padding:9px 12px;margin-top:12px'>"
            f"<span style='font-family:{MONO};font-size:9.5px;letter-spacing:"
            f".1em;color:{MUTED}'>CLAUSE</span><br>{f.citation}</div>",
            unsafe_allow_html=True)
        st.markdown(
            f"<div style='font-size:12px;background:{OK_BG};border-left:3px solid "
            f"{OK};border-radius:0 6px 6px 0;padding:9px 12px;margin-top:8px'>"
            f"<span style='font-family:{MONO};font-size:9.5px;letter-spacing:"
            f".1em;color:{OK}'>SUGGESTED FIX</span><br>{f.remediation}</div>",
            unsafe_allow_html=True)
    with right:
        eyebrow("Sheet evidence")
        if f.sheet_location:
            st.image(f.sheet_location, caption="extracted crop")
        else:
            st.markdown(
                f"<div style='background:#fff;border:1px dashed #C4CAD2;"
                f"border-radius:8px;height:150px;display:flex;align-items:center;"
                f"justify-content:center;font-family:{MONO};font-size:10.5px;"
                f"color:{MUTED}'>no crop available</div>", unsafe_allow_html=True)

    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    act = st.columns([1, 1, 3])
    if act[0].button("Accept", type="primary"):
        f.user_action = "accept"
    if act[1].button("Dismiss"):
        f.user_action = "dismiss"
    f.user_note = act[2].text_input("Add a note for the report",
                                    value=f.user_note or "",
                                    label_visibility="collapsed",
                                    placeholder="Add a note for the report…") \
        or None
    if f.user_action:
        render_inline(chip(f"reviewer · {f.user_action}", INK, "#EEF0F2"))


# ---------------------------------------------------------------- step 4
def step_export():
    findings = st.session_state.get("findings")
    if not findings:
        st.info("Run checks first.")
        return
    step_heading(4, "Export report")
    left, right = st.columns([1, 1])
    with left:
        eyebrow("Format")
        fmt = st.radio("format", ["HTML (print → PDF)", "Markdown"],
                       label_visibility="collapsed")
        eyebrow("Include")
        st.checkbox("Risk summary (counts by severity)", value=True, disabled=True)
        st.checkbox("Full findings + accept/dismiss notes", value=True,
                    disabled=True)
        st.checkbox("Parameters used (audit trail)", value=True, disabled=True)
        include_crops = st.checkbox("Evidence crops — confidential", value=False)
        st.checkbox("Disclaimer + rule-pack version — locked on", value=True,
                    disabled=True)
    with right:
        packs = sorted(p.stem for p in PACK_DIR.glob("*.yaml"))
        report = new_report(packs, st.session_state.confirmed_params, findings)
        # ponytail: crop toggle strips crops from the HTML render (only one that
        # embeds them); MD has none.
        if not include_crops:
            for f in report.findings:
                f.sheet_location = None
        counts = {b: sum(1 for f in findings if f.bucket == b) for b in BUCKETS}
        labels = {"likely_violation": "likely", "needs_verification": "verify",
                  "appears_compliant": "ok"}
        eyebrow("Preview")
        st.markdown(
            f"<div style='background:#fff;border:1px solid {BORDER};"
            f"border-radius:10px;padding:16px'>"
            f"<div style='font-weight:600;font-size:14px'>Permit-sheet triage "
            f"report</div>"
            f"<div style='font-size:10px;background:#FBF6EA;border-left:3px solid "
            f"#C99A2E;color:#7A5A12;padding:5px 8px;border-radius:0 4px 4px 0;"
            f"margin:8px 0'>Decision-support only — not a certification.</div>"
            f"<div style='font-family:{MONO};font-size:9px;color:{MUTED}'>"
            f"{' · '.join(packs)}</div>"
            f"<div style='margin-top:8px'>" +
            "  ".join(chip(f"{counts[b]} {labels[b]}", bucket_color(b),
                           _sev_bg(bucket_color(b))) for b in BUCKETS) +
            f"</div></div>", unsafe_allow_html=True)
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        if fmt.startswith("Markdown"):
            st.download_button("Export report →", render_markdown(report),
                               file_name=f"findings_{report.submission_id[:8]}.md",
                               use_container_width=True)
        else:
            st.download_button("Export report →", render_html(report),
                               file_name=f"findings_{report.submission_id[:8]}.html",
                               use_container_width=True)


# ---------------------------------------------------------------- footer
def footer_nav():
    step = st.session_state.step
    has_params = bool(st.session_state.get("params"))
    has_findings = bool(st.session_state.get("findings"))
    st.divider()
    c1, c2, c3 = st.columns([1, 2, 1])
    if step > 0 and c1.button("‹ Back"):
        goto(step - 1)
    c2.markdown(
        f"<div style='text-align:center;font-family:{MONO};font-size:10.5px;"
        f"letter-spacing:.06em;color:{MUTED}'>STEP {step+1:02d} / 05 · "
        f"{STEP_NAMES[step].upper()}</div>", unsafe_allow_html=True)
    # Confirm + Export carry their action button in-panel; no footer Next.
    if step in (0, 2, 3):
        nxt_label = "Export →" if step == 3 else "Next →"
        disabled = (step == 0 and not has_params) or \
                   (step in (2, 3) and not has_findings)
        if c3.button(nxt_label, type="primary", disabled=disabled,
                     key=f"next_{step}"):
            goto(step + 1)


def main():
    inject_css()
    header()
    disclaimer()
    if not password_gate():
        return
    provider, api_key = provider_config()
    st.session_state.setdefault("step", 0)

    rail_col, content = st.columns([1, 3.4], gap="large")
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


main()
