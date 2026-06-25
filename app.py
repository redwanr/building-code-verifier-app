"""RAJUK Permit-Sheet Code Verifier — Streamlit MVP.

5-step wizard (PRD §5): password gate → Upload → Confirm → Findings →
Inspect → Export. Session-state only; nothing persists beyond the session.

UI: warm-professional instrument-grade direction — IBM Plex family, clay
accent, horizontal stepper, rich HTML finding cards.
"""

import hashlib
import html as html_mod
import tempfile

import streamlit as st

from extraction import extract_params, mock_params, CONFIDENCE_THRESHOLD
from report import DISCLAIMER, BUCKETS, ExtractedParam, \
    new_report, render_html, render_markdown
from rules import evaluate_rules, load_packs, PACK_DIR

st.set_page_config(page_title="RAJUK Verifier", page_icon="◳", layout="wide")

# --- design tokens (from design handoff README) ---
INK       = "#211C15"
INK2      = "#5F574A"
INK3      = "#938977"
LINE      = "#E7E0D0"
LINE2     = "#F0EADC"
BSTRONG   = "#DcD3C0"
CANVAS    = "#F6F1E7"
SURFACE   = "#FFFFFF"
SOFT      = "#FBF8F1"
CLAY      = "#B65C30"
CLAY_DK   = "#9E4B27"
CLAY_SOFT = "#F4E5D9"
CRIT,     CRIT_BG  = "#A6342A", "#F7E6E2"
HIGH,     HIGH_BG  = "#C0662C", "#F7E9DC"
MED,      MED_BG   = "#B07A22", "#F7EDD8"
MED_DK    = "#8A5F18"
OK,       OK_BG    = "#5C7A4F", "#E8EEE1"
MONO  = "'IBM Plex Mono',monospace"
SANS  = "'IBM Plex Sans',system-ui,sans-serif"
SERIF = "'IBM Plex Serif',Georgia,serif"

STEP_NAMES = ["Upload", "Confirm", "Findings", "Inspect", "Export"]

DISCLAIMER_FULL = (
    "Decision-support only — not a certification. This tool gives a "
    "first-pass, automated triage of possible code issues for review by a "
    "qualified, licensed architect/engineer. It does not approve, certify, or "
    "guarantee compliance with RAJUK rules or BNBC. Extracted values and "
    "findings may be wrong. A qualified professional must independently "
    "verify everything. No legal reliance."
)

# Reviewer-supplied values the sheet can't tell us.
USER_SUPPLIED = {
    "permissible_far": "Permissible FAR (from DAP ward/LUC)",
    "allowable_mgc_pct": "Allowable MGC %",
    "required_front_setback_m": "Required front setback (m)",
    "required_rear_setback_m": "Required rear setback (m)",
    "required_side_setback_m": "Required side setback (m)",
    "parking_required": "Required parking count",
    "min_stair_width_m": "Min exit-stair width (m, BNBC)",
    "min_room_area_m2": "Min habitable room area (m², BNBC)",
    "min_room_width_m": "Min habitable room width (m, BNBC)",
}


# ---------------------------------------------------------------- CSS
def inject_css():
    # ponytail: targets Streamlit's generated DOM — brittle to version bumps.
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Serif:wght@500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

:root {
  --ink:#211C15; --ink2:#5F574A; --ink3:#938977;
  --line:#E7E0D0; --line2:#F0EADC; --bstrong:#DcD3C0;
  --canvas:#F6F1E7; --surface:#FFFFFF; --soft:#FBF8F1;
  --clay:#B65C30; --clay-dk:#9E4B27; --clay-soft:#F4E5D9;
  --crit:#A6342A; --crit-bg:#F7E6E2;
  --high:#C0662C; --high-bg:#F7E9DC;
  --med:#B07A22; --med-bg:#F7EDD8; --med-dk:#8A5F18;
  --ok:#5C7A4F; --ok-bg:#E8EEE1;
  --shadow:0 1px 2px rgba(33,28,21,.04), 0 10px 30px -14px rgba(33,28,21,.16);
}
[data-testid="stHeader"] { display:none; }
.stApp { background:var(--canvas); }
.block-container {
  font-family:'IBM Plex Sans',system-ui,sans-serif;
  color:var(--ink); max-width:1180px;
  padding-top:2rem; padding-bottom:4rem;
}
h1,h2,h3 {
  font-family:'IBM Plex Serif',Georgia,serif !important;
  font-weight:600; color:var(--ink); letter-spacing:-.01em;
}

/* sidebar */
[data-testid="stSidebar"] { background:#EEE7D8; border-right:1px solid var(--line); }
[data-testid="stSidebar"] label {
  font-family:'IBM Plex Mono',monospace !important;
  font-size:11px !important; letter-spacing:.1em !important;
  text-transform:uppercase; color:var(--ink3) !important;
}

/* inputs */
[data-baseweb="input"], [data-baseweb="base-input"] {
  border-radius:10px !important; background:var(--soft) !important;
  border-color:var(--bstrong) !important;
}
[data-baseweb="input"]:focus-within {
  border-color:var(--clay) !important;
  box-shadow:0 0 0 3px var(--clay-soft) !important;
}
[data-baseweb="select"] > div {
  border-radius:10px !important; background:var(--surface) !important;
  border-color:var(--bstrong) !important;
}
[data-testid="stNumberInput"] input {
  font-family:'IBM Plex Mono',monospace !important; font-size:13px !important;
}
input[type="checkbox"] { accent-color:var(--clay) !important; }

/* file uploader */
[data-testid="stFileUploaderDropzone"] {
  background:var(--soft); border:1.5px dashed #CFC6B2;
  border-radius:12px; padding:30px 22px;
  transition:border-color .14s, background .14s;
}
[data-testid="stFileUploaderDropzone"]:hover {
  border-color:var(--clay); background:#FDF9F6;
}

/* buttons — ink fill default; clay for type="primary"; white/border secondary */
.stButton > button {
  font-family:'IBM Plex Sans',system-ui,sans-serif !important;
  font-weight:600 !important; font-size:14px !important;
  border-radius:10px !important; padding:10px 22px !important;
  background:var(--ink) !important; color:#fff !important;
  border:1px solid var(--ink) !important;
  transition:opacity .12s, transform .12s;
}
.stButton > button:hover { opacity:.82; transform:translateY(-1px); }
.stButton > button[kind="secondary"] {
  background:var(--surface) !important; color:var(--ink) !important;
  border:1px solid var(--bstrong) !important;
}
.stButton > button[kind="secondary"]:hover { border-color:var(--ink) !important; }
.stButton > button:disabled {
  background:#D8CFBD !important; border-color:#D8CFBD !important;
  color:#fff !important; opacity:1 !important; transform:none !important;
}
.stButton > button[kind="primary"] {
  background:var(--clay) !important; border-color:var(--clay) !important;
  color:#fff !important;
  box-shadow:0 6px 16px -6px rgba(182,92,48,.5) !important;
}
.stButton > button[kind="primary"]:hover {
  background:var(--clay-dk) !important; border-color:var(--clay-dk) !important;
}
.stDownloadButton > button {
  font-family:'IBM Plex Sans',system-ui,sans-serif !important;
  font-weight:600 !important; font-size:14px !important;
  border-radius:10px !important; padding:10px 22px !important;
  background:var(--clay) !important; color:#fff !important;
  border:1px solid var(--clay) !important;
  box-shadow:0 6px 16px -6px rgba(182,92,48,.5) !important;
  width:100%;
}
.stDownloadButton > button:hover {
  background:var(--clay-dk) !important; border-color:var(--clay-dk) !important;
  transform:translateY(-1px);
}

/* radio + toggle */
[role="radiogroup"] { gap:6px; }
[data-testid="stToggle"] label {
  font-family:'IBM Plex Sans',system-ui,sans-serif !important;
  font-weight:500 !important;
}

/* expander (disclaimer full notice) */
[data-testid="stExpander"] details { border:none !important; background:transparent !important; }
[data-testid="stExpander"] summary {
  font-family:'IBM Plex Sans',system-ui,sans-serif !important;
  font-size:12px !important; font-weight:600 !important;
  color:var(--clay-dk) !important; padding:0 !important;
}

hr { border-color:var(--line); }

@media (max-width:820px) {
  .block-container { padding-left:1rem; padding-right:1rem; padding-top:1.2rem; }
}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------- helpers
def _e(s) -> str:
    return html_mod.escape(str(s))


def goto(step: int):
    st.session_state.step = step
    st.rerun()


def _auth_token() -> str:
    pw = st.secrets.get("APP_PASSWORD", "")
    return hashlib.sha256(f"rajuk-gate::{pw}".encode()).hexdigest()[:24]


def render_inline(html: str):
    """Wrap bare inline HTML so Streamlit passes it through."""
    st.markdown(f"<div>{html}</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------- design atoms
def _sev_colors(sev: str) -> tuple[str, str]:
    s = sev.lower()
    if s == "critical":                  return CRIT,   CRIT_BG
    if s == "high":                      return HIGH,   HIGH_BG
    if s in ("medium", "moderate"):      return MED_DK, MED_BG
    if s in ("low", "ok", "pass"):       return OK,     OK_BG
    return INK2, LINE2


def sev_chip(sev: str) -> str:
    tc, bg = _sev_colors(sev)
    return (
        f"<span style='font-family:{SANS};font-size:10.5px;font-weight:600;"
        f"letter-spacing:.05em;text-transform:uppercase;padding:3px 10px;"
        f"border-radius:999px;color:{tc};background:{bg}'>{_e(sev)}</span>"
    )


def regime_pill(regime: str) -> str:
    if regime.upper() == "BNBC":
        return (f"<span style='font-family:{MONO};font-size:10px;font-weight:600;"
                f"letter-spacing:.06em;text-transform:uppercase;padding:2px 8px;"
                f"border-radius:5px;color:#4A5A2E;background:#EDF0E2'>BNBC</span>")
    return (f"<span style='font-family:{MONO};font-size:10px;font-weight:600;"
            f"letter-spacing:.06em;text-transform:uppercase;padding:2px 8px;"
            f"border-radius:5px;color:{CLAY_DK};background:{CLAY_SOFT}'>RAJUK</span>")


def conf_meter(c: float, compact: bool = False) -> str:
    """Inline confidence track + value. c=0.0 → INPUT MISSING pill."""
    if c <= 0.0:
        return (f"<span style='font-family:{MONO};font-size:10px;font-weight:600;"
                f"letter-spacing:.06em;color:{INK3};background:{LINE2};"
                f"border:1px solid {LINE};padding:3px 9px;border-radius:999px'>"
                f"INPUT MISSING</span>")
    fill = OK if c >= 0.80 else MED if c >= 0.50 else CRIT
    w = f"{int(c * 100)}%"
    track_w = "46px" if compact else "60px"
    return (
        f"<span style='display:inline-flex;align-items:center;gap:8px'>"
        f"<span style='font-family:{MONO};font-size:10px;color:{INK3};"
        f"letter-spacing:.06em'>conf</span>"
        f"<span style='width:{track_w};height:7px;border-radius:999px;"
        f"background:#ECE6D9;display:inline-block;overflow:hidden'>"
        f"<span style='display:block;height:100%;width:{w};background:{fill};"
        f"border-radius:999px'></span></span>"
        f"<span style='font-family:{MONO};font-size:12.5px;font-weight:600;"
        f"color:{INK}'>{c:.2f}</span></span>"
    )


def verify_tag_html() -> str:
    return (f"<span style='font-family:{SANS};font-size:10px;font-weight:600;"
            f"letter-spacing:.04em;color:{MED};border:1px solid #E3CF96;"
            f"padding:3px 9px;border-radius:999px'>VERIFY · threshold in flux</span>")


def bucket_dot_color(bucket: str) -> str:
    return {
        "likely_violation":  CRIT,
        "needs_verification": MED,
        "appears_compliant":  OK,
    }.get(bucket, INK2)


# ---------------------------------------------------------------- chrome blocks
def header():
    packs = sorted(p.stem for p in PACK_DIR.glob("*.yaml"))
    pack_chips = "".join(
        f"<span style='display:inline-flex;align-items:center;gap:7px;"
        f"background:{SURFACE};border:1px solid {LINE};border-radius:999px;"
        f"padding:4px 11px;font-family:{MONO};font-size:11.5px;color:{INK2}'>"
        f"<i style='width:7px;height:7px;border-radius:999px;"
        f"background:{OK};display:inline-block'></i>{_e(p)}</span>"
        for p in packs
    )
    st.markdown(
        f"<div style='display:flex;align-items:center;gap:14px;"
        f"padding-bottom:18px;margin-bottom:4px;border-bottom:1px solid {LINE}'>"
        # app mark: clay tile + two offset white-outlined rectangles
        f"<div style='position:relative;width:42px;height:42px;"
        f"border-radius:11px;background:{CLAY};flex:none;"
        f"box-shadow:0 3px 8px rgba(182,92,48,.32)'>"
        f"<div style='position:absolute;left:11px;top:9px;width:14px;height:18px;"
        f"border:2px solid rgba(255,255,255,.55);border-radius:3px'></div>"
        f"<div style='position:absolute;left:16px;top:14px;width:14px;height:18px;"
        f"border:2px solid #fff;border-radius:3px;background:{CLAY}'></div>"
        f"</div>"
        f"<div>"
        f"<div style='font-family:{SERIF};font-weight:600;font-size:19px;"
        f"line-height:1.1'>RAJUK Verifier</div>"
        f"<div style='font-family:{MONO};font-size:11.5px;color:{INK3};"
        f"margin-top:3px'>Permit-sheet triage · decision support</div>"
        f"</div>"
        f"<div style='margin-left:auto;display:flex;gap:8px;flex-wrap:wrap;"
        f"justify-content:flex-end'>{pack_chips}</div>"
        f"</div>",
        unsafe_allow_html=True)


def disclaimer_strip():
    st.markdown(
        f"<div style='display:flex;gap:11px;align-items:flex-start;"
        f"background:{MED_BG};border:1px solid #EAD9AE;"
        f"border-left:3px solid {MED};border-radius:8px;"
        f"padding:9px 14px;margin-bottom:18px'>"
        f"<div style='width:20px;height:20px;border-radius:999px;"
        f"background:{MED};color:#fff;display:flex;align-items:center;"
        f"justify-content:center;font-family:{SANS};font-weight:700;"
        f"font-size:12px;flex:none;margin-top:1px'>!</div>"
        f"<div style='font-family:{SANS};font-size:12.5px;line-height:1.55;"
        f"color:#7A5616'><b>Decision-support only — not a certification.</b> "
        f"A licensed professional must verify every value.</div>"
        f"</div>",
        unsafe_allow_html=True)
    with st.expander("Read full notice ▸"):
        st.markdown(
            f"<div style='font-family:{SANS};font-size:12.5px;line-height:1.6;"
            f"color:{INK2}'>{_e(DISCLAIMER_FULL)}</div>",
            unsafe_allow_html=True)


def stepper():
    step = st.session_state.step
    nodes = []
    for i, name in enumerate(STEP_NAMES):
        if i < step:
            circle = (
                f"<div style='width:28px;height:28px;border-radius:999px;"
                f"background:{INK};display:flex;align-items:center;"
                f"justify-content:center;flex:none'>"
                f"<span style='color:#fff;font-family:{MONO};font-size:12px;"
                f"font-weight:600'>✓</span></div>")
            label_style = f"font-family:{SANS};font-size:11px;color:{INK2}"
        elif i == step:
            circle = (
                f"<div style='width:28px;height:28px;border-radius:999px;"
                f"background:{CLAY};display:flex;align-items:center;"
                f"justify-content:center;flex:none;"
                f"box-shadow:0 0 0 4px {CLAY_SOFT}'>"
                f"<span style='color:#fff;font-family:{MONO};font-size:12px;"
                f"font-weight:600'>{i+1}</span></div>")
            label_style = (f"font-family:{SANS};font-size:11px;"
                           f"font-weight:600;color:{CLAY}")
        else:
            circle = (
                f"<div style='width:28px;height:28px;border-radius:999px;"
                f"background:{SURFACE};border:1.5px solid {BSTRONG};"
                f"display:flex;align-items:center;justify-content:center;flex:none'>"
                f"<span style='color:{INK3};font-family:{MONO};font-size:12px;"
                f"font-weight:600'>{i+1}</span></div>")
            label_style = f"font-family:{SANS};font-size:11px;color:{INK3}"

        connector = ""
        if i > 0:
            if i <= step:
                bg = INK
            elif i == step + 1:
                bg = f"linear-gradient(90deg,{INK},{CLAY})"
            else:
                bg = LINE
            connector = (
                f"<div style='flex:1;height:2px;min-width:16px;margin:0 4px;"
                f"background:{bg}'></div>")

        nodes.append(
            f"{connector}"
            f"<div style='display:flex;flex-direction:column;"
            f"align-items:center;gap:6px'>"
            f"{circle}"
            f"<span style='{label_style}'>{name}</span></div>")

    st.markdown(
        f"<div style='display:flex;align-items:center;"
        f"padding:16px 0 24px'>{''.join(nodes)}</div>",
        unsafe_allow_html=True)


def screen_title(idx: int, title: str, subtitle: str = ""):
    st.markdown(
        f"<div style='font-family:{MONO};font-size:11px;font-weight:600;"
        f"letter-spacing:.14em;text-transform:uppercase;color:{CLAY_DK};"
        f"margin-bottom:6px'>step {idx+1:02d} / 05</div>",
        unsafe_allow_html=True)
    if subtitle:
        c1, c2 = st.columns([3, 2])
        c1.markdown(
            f"<div style='font-family:{SERIF};font-size:28px;font-weight:600;"
            f"line-height:1.15;color:{INK}'>{_e(title)}</div>",
            unsafe_allow_html=True)
        c2.markdown(
            f"<div style='text-align:right;padding-top:10px'>{subtitle}</div>",
            unsafe_allow_html=True)
    else:
        st.markdown(
            f"<div style='font-family:{SERIF};font-size:28px;font-weight:600;"
            f"line-height:1.15;color:{INK};margin-bottom:20px'>{_e(title)}</div>",
            unsafe_allow_html=True)


# ---------------------------------------------------------------- auth
def password_gate() -> bool:
    if st.session_state.get("authed"):
        return True
    if st.secrets.get("APP_PASSWORD", "") and \
            st.query_params.get("k") == _auth_token():
        st.session_state.authed = True
        return True
    st.markdown(
        f"<div style='font-family:{MONO};font-size:10.5px;letter-spacing:.12em;"
        f"text-transform:uppercase;color:{INK3};margin-bottom:4px'>"
        f"Restricted · licensed reviewers only</div>",
        unsafe_allow_html=True)
    pw = st.text_input("Access password", type="password")
    if pw and pw == st.secrets.get("APP_PASSWORD", ""):
        st.session_state.authed = True
        st.query_params["k"] = _auth_token()
        st.rerun()
    elif pw:
        st.error("Wrong password.")
    return False


# ---------------------------------------------------------------- sidebar
def provider_config():
    st.sidebar.markdown(
        f"<div style='font-family:{MONO};font-size:10.5px;letter-spacing:.1em;"
        f"text-transform:uppercase;color:{INK3};margin-bottom:6px'>"
        f"Extraction provider</div>",
        unsafe_allow_html=True)
    provider = st.sidebar.selectbox("Extraction provider", ["gemini", "claude"],
                                    label_visibility="collapsed")
    key_name = "ANTHROPIC_API_KEY" if provider == "claude" else "GEMINI_API_KEY"
    api_key = st.secrets.get(key_name, "")
    if not api_key:
        st.sidebar.error(f"{key_name} missing from secrets.")
    st.sidebar.markdown(
        f"<div style='font-family:{SANS};font-size:12px;color:{INK3};"
        f"line-height:1.5;margin-top:10px'>"
        f"Pages sent to the selected LLM provider (no-training API tier). "
        f"Files kept only for this session — no permanent archive.</div>",
        unsafe_allow_html=True)
    return provider, api_key


# ---------------------------------------------------------------- step 0 — Upload
def step_upload(provider, api_key):
    screen_title(0, "Upload permit sheet")

    mock = st.toggle(
        "Demo mode — skip the API, load sample data (no file, no credits)",
        key="demo_mode")
    if mock:
        st.markdown(
            f"<div style='font-family:{SANS};font-size:12.5px;color:{CLAY_DK};"
            f"background:{CLAY_SOFT};border-radius:9px;padding:9px 14px;"
            f"margin-bottom:8px'>Demo mode is on. <b>{_e(provider)}</b> is "
            f"bypassed — click <b>Load demo parameters →</b> below.</div>",
            unsafe_allow_html=True)

    uploaded = st.file_uploader(
        "Drop a permit-sheet PDF here, or browse",
        type=["pdf"], disabled=mock,
        help="Raster PDF, no text layer required · ≤ 2 pages · 200 MB max")

    c1, c2 = st.columns(2)
    c1.text_input("Jurisdiction / rule pack",
                  value="RAJUK DAP 2025 + BNBC-2020", disabled=True)
    c2.text_input("Effective date", value="2025-09-01", disabled=True)

    packs = sorted(p.stem for p in PACK_DIR.glob("*.yaml"))
    st.markdown(
        f"<div style='font-family:{SANS};font-size:12px;color:{INK3};"
        f"margin-top:6px'>Rule pack &amp; effective date are stamped on every "
        f"report — reproducible against a dated gazette.</div>",
        unsafe_allow_html=True)
    st.markdown(
        f"<div style='font-family:{MONO};font-size:11px;color:{INK3};"
        f"margin-top:3px'>Active packs · " + " · ".join(packs) + "</div>",
        unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    btn_label = "Load demo parameters →" if mock else "Extract parameters →"
    if st.button(btn_label, type="primary",
                 disabled=not (mock or (uploaded and api_key))):
        if mock:
            st.session_state.params = mock_params()
            st.session_state.findings = None
            goto(1)
        crop_dir = tempfile.mkdtemp(prefix="crops_")
        with st.spinner(f"Rasterising and reading the sheet with {provider}…"):
            try:
                st.session_state.params = extract_params(
                    uploaded.read(), provider, api_key, crop_dir)
                st.session_state.findings = None
                goto(1)
            except Exception as e:
                st.error(f"Extraction failed: {e}")


# ---------------------------------------------------------------- step 1 — Confirm
def step_confirm():
    params = st.session_state.get("params")
    if not params:
        st.info("Upload and extract a sheet first.")
        return

    edited = []
    flagged_unconfirmed = []
    pill_slot = st.empty()

    screen_title(1, "Confirm parameters")
    st.markdown(
        f"<div style='font-family:{SANS};font-size:13px;color:{INK2};"
        f"margin-bottom:16px'>Checks won't run until every flagged field is "
        f"confirmed — no manufactured confidence. Edits are kept in the audit "
        f"trail.</div>", unsafe_allow_html=True)

    # table header row
    hcols = st.columns([2.4, 1.1, 2.2, 1.1])
    for col, label in zip(hcols, ["FIELD", "VALUE", "CONFIDENCE", "CONFIRM"]):
        col.markdown(
            f"<div style='font-family:{MONO};font-size:10px;letter-spacing:.10em;"
            f"text-transform:uppercase;color:{INK3};padding-bottom:4px;"
            f"border-bottom:1px solid {LINE}'>{label}</div>",
            unsafe_allow_html=True)

    for p in params:
        flagged = p.confidence < CONFIDENCE_THRESHOLD
        row_style = (
            f"background:{MED_BG};border-left:3px solid {MED};"
            f"border-radius:6px;padding:4px 8px;" if flagged else "")
        cols = st.columns([2.4, 1.1, 2.2, 1.1])

        tag = (
            f"<span style='font-family:{MONO};font-size:9px;font-weight:600;"
            f"letter-spacing:.08em;text-transform:uppercase;color:{MED};"
            f"margin-left:6px'>NEEDS REVIEW</span>" if flagged else "")
        cols[0].markdown(
            f"<div style='{row_style}font-family:{MONO};font-size:12.5px;"
            f"padding-top:7px'>{_e(p.param)}"
            f"<span style='color:{INK3};font-size:10px'> {_e(p.unit)}</span>"
            f"{tag}</div>",
            unsafe_allow_html=True)

        if isinstance(p.value, bool):
            new_val = cols[1].checkbox(p.param, value=p.value, key=f"v_{p.param}",
                                       label_visibility="collapsed")
        else:
            new_val = cols[1].number_input(p.param, value=float(p.value),
                                           key=f"v_{p.param}",
                                           label_visibility="collapsed")

        cols[2].markdown(
            f"<div style='padding-top:9px'>{conf_meter(p.confidence)}</div>",
            unsafe_allow_html=True)
        if p.source_crop:
            with cols[2].popover("crop"):
                st.image(p.source_crop)
        elif p.crop_fallback_note:
            cols[2].caption(f"p{p.source_page}: {p.crop_fallback_note}")

        confirmed = cols[3].checkbox("confirm", value=not flagged,
                                     key=f"c_{p.param}",
                                     label_visibility="collapsed")
        if flagged and not confirmed:
            flagged_unconfirmed.append(p.param)
        edited.append(ExtractedParam(
            param=p.param, value=new_val, unit=p.unit, confidence=p.confidence,
            source_page=p.source_page, source_crop=p.source_crop,
            crop_fallback_note=p.crop_fallback_note, confirmed=confirmed,
            edited_from=p.value if new_val != p.value else None,
        ))

    if flagged_unconfirmed:
        n = len(flagged_unconfirmed)
        pill_slot.markdown(
            f"<div style='margin-bottom:12px'>"
            f"<span style='font-family:{MONO};font-size:11px;font-weight:600;"
            f"letter-spacing:.04em;color:{CLAY_DK};background:{CLAY_SOFT};"
            f"border-radius:999px;padding:4px 12px'>"
            f"{n} field{'s' if n != 1 else ''} to confirm</span></div>",
            unsafe_allow_html=True)
    else:
        pill_slot.markdown(
            f"<div style='margin-bottom:12px'>"
            f"<span style='font-family:{MONO};font-size:11px;font-weight:600;"
            f"letter-spacing:.04em;color:{OK};background:{OK_BG};"
            f"border-radius:999px;padding:4px 12px'>"
            f"all fields confirmed</span></div>",
            unsafe_allow_html=True)

    # reviewer-supplied limits section
    st.markdown(
        f"<div style='margin-top:20px;font-family:{MONO};font-size:10px;"
        f"letter-spacing:.10em;text-transform:uppercase;color:{INK3}'>"
        f"Reviewer-supplied limits</div>"
        f"<div style='font-family:{SANS};font-size:12px;color:{INK3};"
        f"margin-bottom:8px'>Ward/LUC-specific — the sheet can't tell us these; "
        f"blank = rule reports <i>cannot evaluate</i>.</div>",
        unsafe_allow_html=True)
    extracted_names = {p.param for p in edited}
    for name, lbl in USER_SUPPLIED.items():
        if name in extracted_names:
            continue
        val = st.number_input(lbl, value=0.0, key=f"u_{name}")
        if val:
            edited.append(ExtractedParam(
                param=name, value=val, unit="", confidence=1.0,
                source_page=0, confirmed=True))

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    if st.button("Run code checks →", type="primary",
                 disabled=bool(flagged_unconfirmed)):
        st.session_state.confirmed_params = edited
        st.session_state.findings = evaluate_rules(load_packs(), edited)
        goto(2)


# ---------------------------------------------------------------- step 2 — Findings
def _inputs_str(inputs_used) -> str:
    if isinstance(inputs_used, dict):
        return " · ".join(f"{_e(k)}: {_e(v)}" for k, v in inputs_used.items()) \
            or "none supplied"
    return _e(str(inputs_used)) if inputs_used else "none supplied"


def _finding_card_html(f) -> str:
    """Full finding card anatomy per spec."""
    lbc = bucket_dot_color(f.bucket)

    right_el = ""
    if f.verify_flag:
        right_el += verify_tag_html() + "&nbsp; "
    right_el += conf_meter(f.confidence)

    stmt = _e(f.reason).replace(
        "[VERIFY]",
        f"<span style='font-family:{MONO};color:{MED}'>[VERIFY]</span>")

    inp_str = _inputs_str(f.inputs_used)
    inp_color = INK if inp_str != "none supplied" else INK3
    fix_label = "NOTE" if f.bucket == "appears_compliant" else "SUGGESTED FIX"

    return (
        f"<div style='border:1px solid {LINE};border-left:3px solid {lbc};"
        f"border-radius:12px;padding:18px 20px;margin-bottom:12px;"
        f"background:{SURFACE};box-shadow:0 1px 2px rgba(33,28,21,.04)'>"
        # top row
        f"<div style='display:flex;align-items:center;gap:10px;"
        f"margin-bottom:11px;flex-wrap:wrap'>"
        f"{sev_chip(f.severity)}"
        f"<span style='font-family:{MONO};font-size:12px;font-weight:500;"
        f"color:{INK2}'>{_e(f.rule_id)}</span>"
        f"<div style='margin-left:auto;display:flex;align-items:center;"
        f"gap:9px;flex-wrap:wrap'>{right_el}</div></div>"
        # statement
        f"<p style='font-family:{SANS};font-size:14.5px;font-weight:500;"
        f"line-height:1.5;color:{INK};margin:0 0 12px'>{stmt}</p>"
        # source
        f"<div style='display:flex;gap:8px;align-items:baseline;"
        f"font-family:{SANS};font-size:12px;color:{INK2};margin-bottom:11px'>"
        f"{regime_pill(f.regime)}"
        f"<span>{_e(f.citation)}</span></div>"
        # inputs box
        f"<div style='background:{SOFT};border:1px solid {LINE};"
        f"border-radius:9px;padding:9px 13px;margin-bottom:11px'>"
        f"<div style='font-family:{MONO};font-size:9.5px;font-weight:600;"
        f"letter-spacing:.10em;text-transform:uppercase;color:{INK3};"
        f"margin-bottom:5px'>INPUTS</div>"
        f"<div style='font-family:{MONO};font-size:12.5px;line-height:1.65;"
        f"color:{inp_color}'>{inp_str}</div></div>"
        # fix / note
        f"<div style='border:1px solid #CFE0C6;border-left:3px solid {OK};"
        f"background:#F2F6EE;border-radius:9px;padding:10px 14px'>"
        f"<div style='font-family:{MONO};font-size:9.5px;font-weight:600;"
        f"letter-spacing:.10em;text-transform:uppercase;color:{OK};"
        f"margin-bottom:5px'>{fix_label}</div>"
        f"<div style='font-family:{SANS};font-size:13px;line-height:1.5;"
        f"color:#2F4A28'>{_e(f.remediation)}</div></div>"
        f"</div>"
    )


_SEV_ORDER = {"critical": 0, "high": 1, "medium": 2, "moderate": 2, "low": 3}
_BUCKET_LABELS = {
    "likely_violation":  "Likely violation",
    "needs_verification": "Needs verification",
    "appears_compliant":  "Appears compliant",
}


def step_findings():
    findings = st.session_state.get("findings")
    if not findings:
        st.info("Run checks first.")
        return

    counts = {b: sum(1 for f in findings if f.bucket == b) for b in BUCKETS}
    short = {"likely_violation": "fail", "needs_verification": "verify",
             "appears_compliant": "ok"}
    bg = {"likely_violation": CRIT_BG, "needs_verification": MED_BG,
          "appears_compliant": OK_BG}
    pills_html = " ".join(
        f"<span style='font-family:{MONO};font-size:12px;font-weight:600;"
        f"letter-spacing:.04em;color:{bucket_dot_color(b)};"
        f"background:{bg[b]};border-radius:999px;padding:4px 12px'>"
        f"{counts[b]} {short[b]}</span>"
        for b in BUCKETS)

    screen_title(2, "Findings",
                 subtitle=f"<div style='display:flex;gap:8px;flex-wrap:wrap;"
                           f"padding-top:4px'>{pills_html}</div>")

    # filter in sidebar
    st.sidebar.markdown(
        f"<div style='font-family:{MONO};font-size:10.5px;letter-spacing:.1em;"
        f"text-transform:uppercase;color:{INK3};margin-top:16px;margin-bottom:6px'>"
        f"Filter</div>", unsafe_allow_html=True)
    flt = st.sidebar.radio(
        "Filter", ["All", "Likely violation", "Needs verification", "BNBC", "RAJUK"],
        label_visibility="collapsed")

    def passes(f):
        if flt == "All":               return True
        if flt == "Likely violation":  return f.bucket == "likely_violation"
        if flt == "Needs verification": return f.bucket == "needs_verification"
        return f.regime == flt

    for bucket in BUCKETS:
        visible = [f for f in findings if f.bucket == bucket and passes(f)]
        all_in_bucket = [f for f in findings if f.bucket == bucket]
        if not all_in_bucket:
            continue

        dot = bucket_dot_color(bucket)
        st.markdown(
            f"<div style='display:flex;align-items:center;gap:11px;"
            f"border-bottom:1px solid {LINE};padding-bottom:11px;margin:20px 0 16px'>"
            f"<span style='width:10px;height:10px;border-radius:999px;"
            f"background:{dot};flex:none;display:inline-block'></span>"
            f"<span style='font-family:{SERIF};font-size:17px;font-weight:600'>"
            f"{_BUCKET_LABELS[bucket]}</span>"
            f"<span style='font-family:{MONO};font-size:12px;color:{INK3};"
            f"margin-left:auto'>{len(all_in_bucket)} finding"
            f"{'s' if len(all_in_bucket) != 1 else ''}</span></div>",
            unsafe_allow_html=True)

        if not visible:
            st.markdown(
                f"<div style='border:1px dashed {LINE};border-radius:12px;"
                f"padding:18px;text-align:center;background:{SOFT};"
                f"font-family:{SANS};font-size:13px;color:{INK3};"
                f"margin-bottom:12px'>No findings match the current filter.</div>",
                unsafe_allow_html=True)
            continue

        sorted_visible = sorted(visible, key=lambda x: _SEV_ORDER.get(x.severity.lower(), 9))
        for i, f in enumerate(findings):
            if f not in sorted_visible:
                continue
            st.markdown(_finding_card_html(f), unsafe_allow_html=True)
            if st.button("Inspect →", key=f"insp_{i}", type="secondary"):
                st.session_state.active_finding = i
                goto(3)


# ---------------------------------------------------------------- step 3 — Inspect
def step_inspect():
    findings = st.session_state.get("findings")
    if not findings:
        st.info("Run checks first.")
        return
    idx = max(0, min(st.session_state.get("active_finding", 0), len(findings) - 1))
    f = findings[idx]

    top = st.columns([3, 2])
    if top[0].button("‹ Back to findings", type="secondary"):
        goto(2)
    top[1].markdown(
        f"<div style='text-align:right;font-family:{MONO};font-size:11px;"
        f"color:{INK3};padding-top:9px'>"
        f"finding {idx+1:02d} / {len(findings):02d}</div>",
        unsafe_allow_html=True)

    left, right = st.columns([3, 2])
    with left:
        render_inline(
            sev_chip(f.severity) + "&nbsp;&nbsp;" +
            regime_pill(f.regime) + "&nbsp;&nbsp;" +
            conf_meter(f.confidence, compact=True))

        stmt = _e(f.reason).replace(
            "[VERIFY]",
            f"<span style='font-family:{MONO};color:{MED}'>[VERIFY]</span>")
        st.markdown(
            f"<div style='font-family:{SERIF};font-size:22px;font-weight:600;"
            f"line-height:1.25;color:{INK};margin:12px 0 14px'>{stmt}</div>",
            unsafe_allow_html=True)

        inp_str = _inputs_str(f.inputs_used)
        st.markdown(
            f"<div style='background:{SOFT};border:1px solid {LINE};"
            f"border-radius:9px;padding:9px 13px;margin-bottom:11px'>"
            f"<div style='font-family:{MONO};font-size:9.5px;font-weight:600;"
            f"letter-spacing:.10em;text-transform:uppercase;color:{INK3};"
            f"margin-bottom:5px'>INPUTS</div>"
            f"<div style='font-family:{MONO};font-size:12.5px;color:{INK}'>"
            f"{inp_str}</div></div>",
            unsafe_allow_html=True)

        st.markdown(
            f"<div style='background:#F7F8F9;border-left:3px solid {INK};"
            f"border-radius:0 9px 9px 0;padding:10px 14px;margin-bottom:8px'>"
            f"<div style='font-family:{MONO};font-size:9.5px;font-weight:600;"
            f"letter-spacing:.10em;text-transform:uppercase;color:{INK3};"
            f"margin-bottom:5px'>CLAUSE</div>"
            f"<div style='font-family:{SANS};font-size:13px;color:{INK2}'>"
            f"{_e(f.citation)}</div></div>",
            unsafe_allow_html=True)

        fix_label = "NOTE" if f.bucket == "appears_compliant" else "SUGGESTED FIX"
        st.markdown(
            f"<div style='border:1px solid #CFE0C6;border-left:3px solid {OK};"
            f"background:#F2F6EE;border-radius:9px;padding:10px 14px;"
            f"margin-bottom:16px'>"
            f"<div style='font-family:{MONO};font-size:9.5px;font-weight:600;"
            f"letter-spacing:.10em;text-transform:uppercase;color:{OK};"
            f"margin-bottom:5px'>{fix_label}</div>"
            f"<div style='font-family:{SANS};font-size:13px;line-height:1.5;"
            f"color:#2F4A28'>{_e(f.remediation)}</div></div>",
            unsafe_allow_html=True)

        act = st.columns([1, 1, 3])
        if act[0].button("Accept", type="primary"):
            f.user_action = "accept"
        if act[1].button("Dismiss", type="secondary"):
            f.user_action = "dismiss"
        f.user_note = act[2].text_input(
            "note", value=f.user_note or "",
            label_visibility="collapsed",
            placeholder="Add a note for the report…") or None
        if f.user_action:
            render_inline(
                f"<span style='font-family:{MONO};font-size:11px;font-weight:600;"
                f"letter-spacing:.04em;color:{INK2};background:{LINE2};"
                f"border-radius:999px;padding:3px 10px'>"
                f"reviewer · {_e(f.user_action)}</span>")

    with right:
        st.markdown(
            f"<div style='font-family:{MONO};font-size:10.5px;font-weight:600;"
            f"letter-spacing:.10em;text-transform:uppercase;color:{INK3};"
            f"margin-bottom:10px'>Sheet evidence</div>",
            unsafe_allow_html=True)
        if f.sheet_location:
            st.image(f.sheet_location, caption="extracted crop")
            st.caption("Crops are confidential and excluded from the report "
                       "unless explicitly included at export.")
        else:
            st.markdown(
                f"<div style='background:repeating-linear-gradient(45deg,"
                f"{SOFT} 0,{SOFT} 4px,{LINE2} 4px,{LINE2} 8px);"
                f"border:1px solid {LINE};border-radius:10px;height:180px;"
                f"display:flex;align-items:center;justify-content:center;"
                f"flex-direction:column;gap:6px'>"
                f"<div style='font-family:{MONO};font-size:11px;color:{INK3}'>"
                f"no crop available</div>"
                f"<div style='font-family:{MONO};font-size:10px;color:{INK3}'>"
                f"evidence region · page 1</div></div>",
                unsafe_allow_html=True)

    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    prev_c, _, next_c = st.columns([1, 4, 1])
    if idx > 0 and prev_c.button("‹ Prev", type="secondary", key="prev_f"):
        st.session_state.active_finding = idx - 1
        st.rerun()
    if idx < len(findings) - 1 and next_c.button("Next ›", type="secondary", key="next_f"):
        st.session_state.active_finding = idx + 1
        st.rerun()


# ---------------------------------------------------------------- step 4 — Export
def step_export():
    findings = st.session_state.get("findings")
    if not findings:
        st.info("Run checks first.")
        return
    screen_title(4, "Export report")

    left, right = st.columns([1, 1])
    with left:
        st.markdown(
            f"<div style='font-family:{MONO};font-size:10.5px;font-weight:600;"
            f"letter-spacing:.10em;text-transform:uppercase;color:{INK3};"
            f"margin-bottom:8px'>Format</div>",
            unsafe_allow_html=True)
        fmt = st.radio("format", ["HTML (print → PDF)", "Markdown"],
                       label_visibility="collapsed")
        st.markdown(
            f"<div style='font-family:{MONO};font-size:10.5px;font-weight:600;"
            f"letter-spacing:.10em;text-transform:uppercase;color:{INK3};"
            f"margin-top:16px;margin-bottom:8px'>Include</div>",
            unsafe_allow_html=True)
        st.checkbox("Risk summary (counts by severity)", value=True, disabled=True)
        st.checkbox("Full findings + accept/dismiss notes", value=True, disabled=True)
        st.checkbox("Parameters used (audit trail)", value=True, disabled=True)
        include_crops = st.checkbox("Evidence crops — confidential", value=False)
        st.markdown(
            f"<div style='font-family:{MONO};font-size:11px;color:{CRIT};"
            f"margin-left:22px;margin-top:-4px'>confidential</div>",
            unsafe_allow_html=True)
        st.checkbox("Disclaimer + rule-pack version", value=True, disabled=True)

    with right:
        packs = sorted(p.stem for p in PACK_DIR.glob("*.yaml"))
        report = new_report(packs, st.session_state.confirmed_params, findings)
        if not include_crops:
            for f in report.findings:
                f.sheet_location = None
        counts = {b: sum(1 for f in findings if f.bucket == b) for b in BUCKETS}
        short = {"likely_violation": "likely", "needs_verification": "verify",
                 "appears_compliant": "ok"}
        bg = {"likely_violation": CRIT_BG, "needs_verification": MED_BG,
              "appears_compliant": OK_BG}

        st.markdown(
            f"<div style='font-family:{MONO};font-size:10.5px;font-weight:600;"
            f"letter-spacing:.10em;text-transform:uppercase;color:{INK3};"
            f"margin-bottom:10px'>Preview</div>",
            unsafe_allow_html=True)
        pills_html = " ".join(
            f"<span style='font-family:{MONO};font-size:11px;font-weight:600;"
            f"letter-spacing:.04em;color:{bucket_dot_color(b)};background:{bg[b]};"
            f"border-radius:999px;padding:3px 10px'>{counts[b]} {short[b]}</span>"
            for b in BUCKETS)
        st.markdown(
            f"<div style='background:{SURFACE};border:1px solid {LINE};"
            f"border-radius:12px;padding:20px 22px;"
            f"box-shadow:0 1px 2px rgba(33,28,21,.04)'>"
            f"<div style='font-family:{SERIF};font-size:16px;font-weight:600;"
            f"margin-bottom:8px'>Permit-sheet code verification</div>"
            f"<div style='display:flex;gap:11px;align-items:center;"
            f"background:{MED_BG};border:1px solid #EAD9AE;"
            f"border-left:3px solid {MED};border-radius:6px;"
            f"padding:7px 11px;margin-bottom:12px'>"
            f"<span style='color:{MED};font-weight:700;font-size:12px'>!</span>"
            f"<span style='font-family:{SANS};font-size:11.5px;color:#7A5616'>"
            f"Decision-support only — not a certification.</span></div>"
            f"<div style='font-family:{MONO};font-size:10px;color:{INK3};"
            f"margin-bottom:10px'>{' · '.join(packs)}</div>"
            f"<div style='display:flex;gap:8px;flex-wrap:wrap'>{pills_html}</div>"
            f"</div>",
            unsafe_allow_html=True)

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        if fmt.startswith("Markdown"):
            st.download_button(
                "Export report →", render_markdown(report),
                file_name=f"findings_{report.submission_id[:8]}.md",
                use_container_width=True)
        else:
            st.download_button(
                "Export report →", render_html(report),
                file_name=f"findings_{report.submission_id[:8]}.html",
                use_container_width=True)


# ---------------------------------------------------------------- footer nav
def footer_nav():
    step = st.session_state.step
    has_params = bool(st.session_state.get("params"))
    has_findings = bool(st.session_state.get("findings"))
    st.markdown(
        f"<hr style='margin:24px 0 16px;border-color:{LINE}'>",
        unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    if step > 0 and c1.button("‹ Back", type="secondary", key=f"back_{step}"):
        goto(step - 1)
    c2.markdown(
        f"<div style='text-align:center;font-family:{MONO};font-size:10.5px;"
        f"letter-spacing:.06em;color:{INK3};padding-top:12px'>"
        f"STEP {step+1:02d} / 05 · {STEP_NAMES[step].upper()}</div>",
        unsafe_allow_html=True)
    # Confirm + Export carry their own action button; no footer Next there
    if step in (0, 2, 3):
        nxt_label = "Export →" if step == 3 else "Next →"
        disabled = (step == 0 and not has_params) or \
                   (step in (2, 3) and not has_findings)
        if c3.button(nxt_label, type="secondary", key=f"next_{step}",
                     disabled=disabled):
            goto(step + 1)


# ---------------------------------------------------------------- main
def main():
    inject_css()
    header()
    disclaimer_strip()
    if not password_gate():
        return
    provider, api_key = provider_config()
    st.session_state.setdefault("step", 0)
    stepper()

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
