# Handoff: RAJUK Permit-Sheet Verifier — Full Submission Flow

## Overview

This is the complete UI design for the **RAJUK Permit-Sheet Verifier** — a decision-support tool that lets architects and engineers upload a building permit PDF, auto-extracts key parameters via AI, cross-checks them against RAJUK DAP 2025 + BNBC-2020 rules, and generates a triage report.

The tool is **decision-support only** — not a certification instrument. Every screen reinforces this with a persistent disclaimer banner.

---

## About the Design Files

The `.dc.html` file in this folder is an **interactive HTML prototype** — it shows the intended look, layout, copy, and interactions but is **not production code**. Your task is to **recreate these screens in the existing web app's codebase** using its established framework, component library, and routing patterns. Do not ship the HTML directly.

---

## Fidelity

**High-fidelity.** The prototype uses final copy, exact colors, real spacing values, and working interactions (step navigation, field confirmation toggling, finding drill-down). Recreate the UI pixel-closely using your codebase's design system; where your existing components differ slightly in shape, prefer the existing component over inventing new ones.

---

## Screens / Views

The flow is a **5-step linear wizard** with a persistent left-side step rail. All steps live within a single browser-chrome wrapper (fake URL bar + traffic-light dots).

### Global Shell

- **Background:** `#efece4` (warm off-white)  
- **Card:** `background:#fff`, `border: 2px solid #2b2b2b`, `border-radius: 16px`, `box-shadow: 5px 6px 0 rgba(43,43,43,.12)`  
- **Browser chrome bar:** `background: #f4f2eb`, `border-bottom: 2px solid #2b2b2b`; three 10×10px circle dots (outlined, no fill); URL pill `background:#e6e3da`, `border-radius:8px`, `font-size:10px`, `color:#8a8678`  
- **Disclaimer banner** (toggleable via a `showDisclaimer` prop/flag):  
  `background:#faf0d6`, `border-bottom: 2px dashed #c8920f`, `font-size:11px`, `color:#7a5a08`  
  Text: *"⚠ Decision-support only — not a certification. This tool triages possible code issues for review by a licensed architect/engineer. It does not approve or certify anything."*

### Left Step Rail

- **Width:** 178px, `background:#f4f2eb`, `border-right: 2px solid #2b2b2b`  
- **Label above list:** `"Submission flow"`, `font-size:10.5px`, `color:#9a978b`, `text-transform:uppercase`, `letter-spacing:.06em`  
- **Each step row:** `padding: 7px 9px`, `border-radius:8px`, `font-size:12.5px`  
  - **Active step:** `font-weight:700`, `background:#fff`, `border: 2px solid #2b2b2b`  
  - **Completed step:** `font-weight:400`, `color:#2b2b2b`  
  - **Future step:** `color:#9a978b`  
- **Step circle (22×22px, border-radius:50%):**  
  - Active: `background:#2b2b2b`, `color:#fff`, shows step number  
  - Completed: `background:#2e7d4f` (green), `color:#fff`, shows `✓`  
  - Future: `background:#fff`, `border: 2px solid #b8b5a8`, `color:#9a978b`, shows step number  
- **Footer note** (bottom of rail): `font-size:10px`, `color:#9a978b`  
  Text: *"Uploads & crops deleted after the session — no permanent archive."*

### Footer Navigation Bar

- `background:#f4f2eb`, `border-top: 2px solid #2b2b2b`, `padding: 12px 22px`  
- **Back button** (hidden on step 1): `border: 2px solid #2b2b2b`, `background:#fff`, `border-radius: 10px 8px 12px 8px`, `font-size:13px`  
- **Step label** (center): `"Step N of 5 · [Name]"`, `font-size:11.5px`, `color:#6b6859`  
- **Primary CTA** (right): `background:#2b2b2b`, `color:#fff`, `border-radius: 10px 8px 12px 8px`, `font-size:13px`  
  - Steps 1, 3: `"Next →"`  
  - Step 2 (Confirm): replaced by `"Run checks →"` — **disabled** (`background:#bdbab0`, `cursor:not-allowed`) until all flagged fields are confirmed  
  - Step 4 (Inspect): `"Export →"`  
  - Step 5 (Export): no CTA, replaced by the Export button inside the panel  

---

### Step 1 · Upload

**Purpose:** User drops or browses for a permit PDF, selects jurisdiction rule pack and effective date.

**Layout:** Two-column flex row.

**Left column (flex: 1.2):**
- Large drop zone: `border: 2px dashed #2b2b2b`, `border-radius: 170px 16px 190px 16px / 16px 190px 16px 170px` (organic pill shape), `background:#faf9f4`  
  - Upload icon `⬆` at 36px  
  - Heading: `"Drop permit-sheet PDF here"` — Caveat font, 24px bold  
  - `"or browse files"` button: `border: 2px solid #2b2b2b`, `background:#fff`, `border-radius: 9px 7px 11px 7px`, `font-size:13px`  
  - Constraint copy: `"PDF · raster ok (no text layer) · ≤ 2 pages · ≤ 25 MB"`, `font-size:11px`, `color:#8a8678`  
- Two-column field row below the drop zone:  
  - **Jurisdiction / rule pack** — read-only select-style display, value: `"RAJUK DAP 2025 + BNBC-2020"`, with `▾`  
  - **Effective date** — read-only select-style display, value: `"2025-09-01"`, with `▾`  
  - Both: `border: 2px solid #2b2b2b`, `border-radius: 9px`, `padding: 9px 11px`, `font-size:12px`

**Right column (280px):**
- `"Recent submissions"` label  
- Two recent-submission rows: flex row with PDF thumbnail placeholder (38×50px striped), filename + date, status badge  
  - Badge colors: `color:#c0392b; background:#f8e3df` for "1 critical", `color:#2e7d4f; background:#dff0e4` for "clear"  
- Annotation callout at bottom: Caveat font 15px, `color:#7a5a08`, `background:#faf0d6`, `border-radius:8px`  
  Text: *"Rule pack & date are recorded on every report — reproducible against a dated gazette."*

---

### Step 2 · Confirm Extracted Parameters

**Purpose:** User reviews AI-extracted values, manually confirms any flagged low-confidence fields before checks can run.

**Key UX rule:** The "Run checks" button stays disabled until **all flagged fields** (marked ⚑) are confirmed.

**Status pill** (top right, updates dynamically):
- Unconfirmed: `"N fields need confirmation"`, `color:#7a5a08`, `background:#faf0d6`  
- All confirmed: `"All fields confirmed ✓"`, `color:#2e7d4f`, `background:#dff0e4`

**Sub-heading:** `"Checks won't run until every flagged field is confirmed — no manufactured confidence."`  
`font-size:11.5px`, `color:#6b6859`

**Parameter table** (`border: 2px solid #2b2b2b`, `border-radius:11px`, `overflow:hidden`):

| Column | Width | Notes |
|---|---|---|
| Field | flex:1.6 | Field name; flagged rows show `⚑` suffix |
| Value | 70px | Bold for auto-confirmed; editable input style for flagged |
| Confidence | 120px | Bar + decimal. Green bar for ≥0.80, amber for 0.60–0.79, red for <0.60 |
| Crop | 54px | 30×20px striped thumbnail placeholder |
| Confirm | 90px | `"auto ✓"` in green for high-confidence; clickable checkbox for flagged |

**Rows (6 total):**

| Field | Value | Confidence | State |
|---|---|---|---|
| `num_storeys` | 10 | 0.95 | Auto-confirmed |
| `claimed_far` ⚑ | 4.2 | 0.62 | Amber; needs user confirmation. Row `background:#fdf8ec` |
| `claimed_mgc` | 58% | 0.88 | Auto-confirmed |
| `num_exit_stairs` ⚑ | 1 | 0.55 | Red; needs user confirmation. Row `background:#fdf2ef` |
| `parking_provided / required` | 8 / 12 | 0.90 | Auto-confirmed |
| `unit_count` | 36 | 0.84 | Auto-confirmed |

**Confirm checkbox** (flagged rows):
- Unchecked: `border: 2px solid #c0392b`, `background:#fff`  
- Checked: `border: 2px solid #2e7d4f`, `background:#2e7d4f`, shows `✓` in white  
- 24×24px, `border-radius:6px`

**Footer note:** `"Every edit (original → corrected) is stored in the audit trail."`, `font-size:10.5px`, `color:#8a8678`

---

### Step 3 · Triaged Findings

**Purpose:** Displays all code-check results sorted by severity. User can filter and drill in.

**Badge row** (top right): `"2 likely"` (red), `"3 verify"` (amber), `"3 ok"` (green) — pill badges

**Filter chips** (horizontal scrollable row):
- Active chip: `background:#2b2b2b`, `color:#fff`, `border-radius:20px`, `padding:5px 13px`  
- Inactive chip: `border: 2px solid #2b2b2b`, `border-radius:20px`, `padding:4px 12px`  
- Options: `All 6` (active), `Critical`, `BNBC`, `RAJUK`, `Needs verification`

**Findings list** (`border: 2px solid #2b2b2b`, `border-radius:11px`, `overflow:hidden`):  
Each row: flex, `padding: 12px 15px`, `border-left: 5px solid [severity color]`, clickable (→ Inspect view)

| # | Title | Sub-label | Left border + dot | Badge |
|---|---|---|---|---|
| 1 | Single stair on G+9 — needs 2nd fire-separated exit | BNBC-2020 Part 3/4 · means of egress | `#c0392b` (red) | `CRITICAL` |
| 2 | Claimed FAR 4.2 exceeds ward density cap | RAJUK DAP 2025 · ward / density block | `#c0392b` (red) | `HIGH` |
| 3 | High-rise fire provisions not found | BNBC · input missing → cannot evaluate | `#c8920f` (amber) | `VERIFY` |
| 4 | Parking provided 8 vs required 12 | RAJUK · low-confidence input | `#c8920f` (amber) | `VERIFY` |
| 5 | Ground coverage 58% within MGC | RAJUK | `#2e7d4f` (green) | `OK` |
| 6 | Lift count meets minimum | BNBC | `#2e7d4f` (green) | `OK` |

Rows 1–2 (red) also show a confidence decimal (`.74`, `.81`) in `color:#8a8678` and a `›` chevron.

---

### Step 4 · Inspect Finding (Detail View)

**Purpose:** Deep-dive into a single finding — clause reference, suggested fix, evidence crop.

**Accessed from:** Clicking any row in the Findings list.  
**Back link** (top left): `"‹ back to findings"`, `font-size:12px`, `color:#6b6859`  
**Pagination label** (top right): `"Finding 1 of 6"`, `font-size:11px`

**Two-column layout** inside a `border: 2px solid #2b2b2b`, `border-radius:12px` card:

**Left panel (flex:1.05, `border-right: 2px dashed #cbc8bb`):**
- Badges row: `CRITICAL` (red pill) + `BNBC` (neutral pill) + `"confidence 0.74"` in grey  
- Title: Caveat font 24px bold, `"Single stair on a G+9 / ~30 m block"`  
- Body text (13px, `line-height:1.45`): explanation paragraph  
- Clause block: `background:#f4f2eb`, `border-left: 3px solid #2b2b2b`, `padding: 8px 11px`  
  Label: **Clause** + clause citation text  
- Suggested fix block: `background:#eef6f0`, `border-left: 3px solid #2e7d4f`  
  Label: **Suggested fix** + action text  
- Inputs used line: `font-size:10.5px`, `color:#8a8678`

**Right panel (240px, `background:#faf9f4`):**
- `"Sheet location · page 1"`, `font-size:11px`, `color:#6b6859`  
- Evidence crop placeholder: striped div with `"stair-plan crop"` monospace label  
- `"Open full sheet"` secondary button

**Action row (below card):**
- `"Accept finding"` — primary dark button  
- `"Dismiss"` — secondary outlined button  
- Free-text note input (flex:1): `border: 2px solid #cbc8bb`, placeholder `"add a note for the report…"`, `font-size:11.5px`, `color:#8a8678`

---

### Step 5 · Export Report

**Purpose:** Configure and download a triage report as PDF or Markdown.

**Two-column layout** (`border-right: 2px dashed #cbc8bb` divides them):

**Left column (configuration):**
- `"Format"` label → two chips: `PDF ✓` (active, dark fill) and `Markdown` (outlined)  
- `"Include"` section — 5 checklist items:
  | Item | Default |
  |---|---|
  | Risk summary (counts by severity) | ✓ checked |
  | Full findings list + accept/dismiss notes | ✓ checked |
  | Parameters used | ✓ checked |
  | Evidence crops *(confidential)* | ☐ unchecked |
  | Disclaimer + rule-pack version | 🔒 locked on (greyed, always included) |
- Checkbox style: 17×17px, `border-radius:4px`, active = `background:#2b2b2b`, `color:#fff`; locked = `background:#bdbab0`

**Right column (300px — preview + export CTA):**
- Mini PDF preview card (white card with shadow inside a `#e7e4db` container)  
  Contains: report title, disclaimer banner, rule-pack version string, severity count badges, first finding row, and three grey shimmer lines  
- `"Export report →"` CTA button — primary dark, full-width, `font-size:14px`

---

## Interactions & Behavior

### Step Navigation
- **Rail clicks:** Clicking any step in the left rail jumps directly to that step (no gate — free navigation in the prototype).
- **Next / Back buttons:** Sequential step-by-step navigation.
- **"Run checks →"** (Step 2 footer): **Disabled** until both `claimed_far` and `num_exit_stairs` checkboxes are confirmed. On enable → navigates to Step 3.
- **Finding row click** (Step 3): Navigates to Step 4 (Inspect).
- **"‹ back to findings"** (Step 4): Returns to Step 3.
- **"Export →"** (Step 4 footer): Navigates to Step 5.

### Confirmation Checkboxes (Step 2)
- Toggle on click; state tracked per field.  
- Status pill and "Run checks" button reactivity driven by whether **both** flagged fields are confirmed.  
- In production: also track original vs. corrected value in audit trail.

### Disclaimer Banner
- Controlled by a `showDisclaimer` boolean (exposed as a configurable prop/setting).  
- Shown by default.

### Animations / Transitions
None specified in the prototype. Recommend subtle fade or slide-in when switching steps (~150ms ease).

---

## State Management

| Variable | Type | Description |
|---|---|---|
| `step` | `0–4` | Current wizard step |
| `confFar` | `boolean` | Whether `claimed_far` has been manually confirmed |
| `confStairs` | `boolean` | Whether `num_exit_stairs` has been manually confirmed |
| `showDisclaimer` | `boolean` | Whether the disclaimer banner is shown (default: `true`) |

In production, additional state will be needed for:
- Uploaded PDF (file reference, upload progress)
- Extracted parameters (array of `{ field, value, confidence, confirmed, originalValue }`)
- Findings list (from API response)
- Active finding index (for Inspect view)
- Selected export format and included sections
- Accept/dismiss state per finding, plus notes

---

## Design Tokens

### Colors

| Token | Hex | Usage |
|---|---|---|
| `ink` | `#2b2b2b` | Primary text, borders, active elements |
| `surface` | `#efece4` | Page background |
| `surface-raised` | `#f4f2eb` | Rail, footer nav, browser chrome |
| `surface-card` | `#fff` | Main content card |
| `surface-warm` | `#faf9f4` | Inspect right panel, drop zone |
| `muted` | `#8a8678` | Tertiary text, placeholders |
| `muted-medium` | `#6b6859` | Secondary text, field labels |
| `muted-border` | `#cbc8bb` | Dashed dividers, table row separators |
| `critical` | `#c0392b` | Critical finding, flagged field (red) |
| `critical-bg` | `#f8e3df` | Critical badge background |
| `warning` | `#c8920f` | Amber / verify severity |
| `warning-bg` | `#faf0d6` | Amber badge background, disclaimer banner |
| `ok` | `#2e7d4f` | OK / green severity, confirmed checkmark |
| `ok-bg` | `#dff0e4` | OK badge background, confirmed highlight |
| `step-completed` | `#2e7d4f` | Completed step circle fill |

### Typography

| Role | Family | Size | Weight |
|---|---|---|---|
| Display headings | Caveat (Google Font) | 23–30px | 700 |
| Finding title (Inspect) | Caveat | 24px | 700 |
| Body / UI | Kalam (Google Font) | 12–13.5px | 400/700 |
| Small labels | Kalam | 10–11.5px | 400 |
| Confidence / metadata | Kalam | 10–10.5px | 400 |

> In production: replace Caveat/Kalam with whatever handwriting/sketch font the existing app uses, or substitute your system UI font if the app uses a non-sketch aesthetic.

### Spacing & Radius

| Token | Value |
|---|---|
| Section padding | `20px 22px` |
| Rail padding | `16px 12px` |
| Footer nav padding | `12px 22px` |
| Card border-radius | `16px` (outer), `11–12px` (inner panels) |
| Button border-radius | `10px 8px 12px 8px` (organic asymmetric) |
| Badge border-radius | `7px` |
| Checkbox | `6px` |

### Shadows

| Usage | Value |
|---|---|
| Main card | `5px 6px 0 rgba(43,43,43,.12)` |

---

## Assets

| Asset | Source | Notes |
|---|---|---|
| PDF thumbnail placeholder | CSS `repeating-linear-gradient(45deg, #eeece4 6px, #e1ded2 12px)` | Recreate in-code; no image file needed |
| Evidence crop placeholder | Same striped gradient, `"stair-plan crop"` label | Replace with actual sheet crop from PDF parser |
| Upload icon | Unicode `⬆` | Replace with icon from your icon library |
| Disclaimer icon | Unicode `⚠` | Replace with icon from your icon library |

No external image files are referenced. All placeholders are pure CSS.

---

## Files in This Bundle

| File | Purpose |
|---|---|
| `RAJUK Verifier Flow.dc.html` | Interactive high-fidelity prototype — **design reference only** |
| `README.md` | This handoff document |

To view the prototype, open `RAJUK Verifier Flow.dc.html` in a browser alongside `support.js` (from the parent project), or open it directly in the design tool. Use it as a live reference while implementing — step through the flow with the Next button and confirm-checkbox interactions to see all states.

---

## Implementation Notes for Claude Code

1. **The prototype is a design reference**, not a code base to port. Implement in your existing framework (React, Next.js, etc.) using your established patterns.
2. The **5-step wizard** can be implemented as a simple `currentStep` state variable (0–4) controlling which step panel renders.
3. The **"Run checks" gate** is the most important UX logic: keep the CTA disabled until all low-confidence fields (`confidence < ~0.75`) are manually confirmed.
4. **Disclaimer banner** should be permanently on in production — the prototype has a toggle for design review purposes only.
5. The **step rail** should be fully clickable in the UI (not gated), so users can jump back to review earlier steps.
6. In production, the "Inspect" view (Step 4) should be reachable from any finding row, with its own finding index state.
7. All evidence crops and PDF thumbnails come from your PDF parsing/rendering pipeline — replace the CSS stripe placeholders.
