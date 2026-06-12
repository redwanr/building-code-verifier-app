# Architecture — MVP (as built, 2026-06)

Single Streamlit monolith on a free tier. No database — the PRD §11 report
object is the data contract; session ends, data gone. Renders on GitHub
(Mermaid).

```mermaid
flowchart TB
    subgraph user["Reviewer (shared password)"]
        U[Browser]
    end

    subgraph app["Streamlit monolith — app.py (Community Cloud free tier)"]
        GATE[Password gate<br/>st.secrets APP_PASSWORD]
        UP[1 · Upload permit-sheet PDF]
        RAST[Rasterize<br/>pdf2image @ 200 DPI]
        EXT[extraction.py<br/>one vision call per page<br/>structured JSON: value, confidence, bbox]
        CROP[Best-effort bbox crops<br/>fallback: page + location note]
        CONF{2 · Human confirmation gate FR-5<br/>confidence &lt; 0.7 ⇒ must confirm<br/>+ reviewer-supplied permissible<br/>FAR / MGC / setbacks / parking}
        ENG[rules.py<br/>simpleeval interpreter]
        FIND[3 · Triaged findings<br/>🔴 likely violation · 🟡 needs verification · 🟢 appears compliant<br/>VERIFY-flagged rules cap at 🟡]
        EXP[4 · Export<br/>Markdown + HTML → browser print PDF]
        SS[(st.session_state + temp dir<br/>session-only, no archive)]
    end

    subgraph packs["Rule packs — data, not code (FR-10)"]
        BNBC[bnbc-2020@2020-01-01.yaml<br/>life-safety: egress, fire, rooms, lifts]
        RAJUK[rajuk-dap-2025@2025-09-01.yaml<br/>planning: FAR, MGC, setbacks, parking]
    end

    subgraph llm["Vision LLM (server-side key, no-training tier)"]
        CLAUDE[Claude Opus 4.8<br/>default]
        GEMINI[Gemini<br/>EXTRACTION_PROVIDER switch]
    end

    U --> GATE --> UP --> RAST --> EXT
    EXT -->|page PNG + prompt| CLAUDE
    EXT -.->|alternative| GEMINI
    CLAUDE -->|params JSON| EXT
    EXT --> CROP --> CONF
    CONF -->|confirmed params only| ENG
    BNBC --> ENG
    RAJUK --> ENG
    ENG --> FIND --> EXP --> U
    SS -.-> CONF
    SS -.-> FIND
```

Key invariants:

- **Checks never run on unconfirmed low-confidence inputs** (FR-5 gate).
- **Missing/unconfirmed required input ⇒ "cannot evaluate"** finding, never a
  silent pass (FR-9).
- **Jurisdiction split is structural**: each rule belongs to exactly one pack
  (BNBC vs RAJUK); every finding cites its regime.
- **Non-certification disclaimer** on every screen and every export.
- Pages leave our control only for the LLM extraction call — disclosed in UI.
