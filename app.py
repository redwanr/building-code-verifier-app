"""RAJUK Permit-Sheet Code Verifier — Streamlit MVP.

Flow (PRD §5): password gate -> upload -> extract -> human confirmation gate
-> run checks -> triaged findings -> export. Session-state only; nothing
persists beyond the session (PRD §14).
"""

import tempfile

import streamlit as st

from extraction import extract_params, CONFIDENCE_THRESHOLD
from report import DISCLAIMER, BUCKETS, BUCKET_LABELS, ExtractedParam, \
    new_report, render_html, render_markdown
from rules import evaluate_rules, load_packs, PACK_DIR

st.set_page_config(page_title="RAJUK Code Verifier (MVP)", page_icon="📐",
                   layout="wide")

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


def disclaimer():
    st.warning(DISCLAIMER)


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


def step_upload(provider, api_key):
    uploaded = st.file_uploader("Upload permit-sheet PDF", type=["pdf"])
    if uploaded and st.button("Extract parameters", type="primary",
                              disabled=not api_key):
        crop_dir = tempfile.mkdtemp(prefix="crops_")
        with st.spinner(f"Rasterizing + reading sheet with {provider}…"):
            try:
                st.session_state.params = extract_params(
                    uploaded.read(), provider, api_key, crop_dir)
                st.session_state.findings = None
                st.rerun()
            except Exception as e:  # surface provider errors plainly
                st.error(f"Extraction failed: {e}")


def step_confirm():
    """FR-5 gate: user edits/confirms before checks run. Non-negotiable."""
    st.subheader("2 · Confirm extracted parameters")
    st.caption(f"Fields below {CONFIDENCE_THRESHOLD:.0%} confidence are "
               "flagged and MUST be confirmed before checks run. Edit "
               "anything that's wrong — edits are recorded for the audit trail.")
    params = st.session_state.params
    edited = []
    for p in params:
        flagged = p.confidence < CONFIDENCE_THRESHOLD
        cols = st.columns([2, 2, 1, 1, 2])
        label = f"{'🟡 ' if flagged else ''}{p.param} ({p.unit})"
        if isinstance(p.value, bool):
            new_val = cols[0].checkbox(label, value=p.value, key=f"v_{p.param}")
        else:
            new_val = cols[0].number_input(label, value=float(p.value),
                                           key=f"v_{p.param}")
        cols[1].metric("confidence", f"{p.confidence:.2f}")
        confirm = cols[2].checkbox("confirm", value=not flagged,
                                   key=f"c_{p.param}")
        if p.source_crop:
            with cols[4].popover("📍 view crop"):
                st.image(p.source_crop)
        elif p.crop_fallback_note:
            cols[4].caption(f"📍 page {p.source_page}: {p.crop_fallback_note}")
        edited.append(ExtractedParam(
            param=p.param, value=new_val, unit=p.unit, confidence=p.confidence,
            source_page=p.source_page, source_crop=p.source_crop,
            crop_fallback_note=p.crop_fallback_note, confirmed=confirm,
            edited_from=p.value if new_val != p.value else None,
        ))

    st.markdown("**Reviewer-supplied limits** (ward/LUC-specific — the sheet "
                "can't tell us these; blank = rule reports *cannot evaluate*)")
    extracted_names = {p.param for p in edited}
    for name, label in USER_SUPPLIED.items():
        if name in extracted_names:
            continue
        val = st.number_input(label, value=0.0, key=f"u_{name}")
        if val:
            edited.append(ExtractedParam(
                param=name, value=val, unit="", confidence=1.0,
                source_page=0, confirmed=True,
            ))

    unconfirmed_flagged = [p.param for p in edited
                           if p.confidence < CONFIDENCE_THRESHOLD
                           and not p.confirmed]
    if st.button("Run code checks", type="primary"):
        st.session_state.confirmed_params = edited
        st.session_state.findings = evaluate_rules(load_packs(), edited)
        st.rerun()
    if unconfirmed_flagged:
        st.info("Unconfirmed low-confidence fields will be treated as missing "
                f"(rules emit 'cannot evaluate'): {', '.join(unconfirmed_flagged)}")


def step_findings():
    st.subheader("3 · Triaged findings")
    findings = st.session_state.findings
    counts = {b: sum(1 for f in findings if f.bucket == b) for b in BUCKETS}
    cols = st.columns(3)
    for col, b in zip(cols, BUCKETS):
        col.metric(BUCKET_LABELS[b], counts[b])

    for i, f in enumerate(findings):
        with st.expander(f"{BUCKET_LABELS[f.bucket]} · {f.rule_id} · "
                         f"{f.severity}" + (" · [VERIFY]" if f.verify_flag else "")):
            st.write(f.reason)
            st.caption(f"**{f.regime}** · {f.citation}")
            st.caption(f"Inputs: `{f.inputs_used}` · confidence {f.confidence:.2f}")
            st.write(f"**Suggested fix:** {f.remediation}")
            if f.sheet_location:
                st.image(f.sheet_location, caption="Sheet location")
            f.user_action = st.radio(
                "Reviewer action", [None, "accept", "dismiss"],
                horizontal=True, key=f"act_{i}",
                format_func=lambda x: x or "—")
            f.user_note = st.text_input("Note", key=f"note_{i}") or None

    packs = sorted(p.stem for p in PACK_DIR.glob("*.yaml"))
    report = new_report(packs, st.session_state.confirmed_params, findings)
    st.download_button("⬇️ Export Markdown", render_markdown(report),
                       file_name=f"findings_{report.submission_id[:8]}.md")
    st.download_button("⬇️ Export HTML (print → PDF)", render_html(report),
                       file_name=f"findings_{report.submission_id[:8]}.html")


def main():
    st.title("📐 RAJUK Permit-Sheet Code Verifier — MVP")
    disclaimer()
    if not password_gate():
        return
    provider, api_key = provider_config()
    packs = sorted(p.stem for p in PACK_DIR.glob("*.yaml"))
    st.caption("Active rule packs: " + ", ".join(f"`{p}`" for p in packs))

    st.subheader("1 · Upload")
    step_upload(provider, api_key)
    if st.session_state.get("params"):
        step_confirm()
    if st.session_state.get("findings"):
        step_findings()
    disclaimer()


main()
