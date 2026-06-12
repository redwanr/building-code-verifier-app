
PRODUCT CONTEXT
We are scoping an MVP web app for architecture/construction firms in Dhaka that ingests a RAJUK
building-approval drawing (a single dense PDF "permit sheet": floor plans, elevations, sections,
and data tables for area/FAR/MGC/setback/parking) and returns an actionable, triaged list of
likely building-code violations. The concept was validated manually: on a real G+9 residential
sheet we correctly flagged a single-staircase egress problem, missing high-rise fire provisions,
a questionable FAR figure, and an inconsistent parking count. Demand exists because Dhaka is
extremely dense and sits in an active seismic zone, so plan-review quality is a real safety issue.
Goal of THIS MVP: "test the water" — minimal, user-friendly, hosted on a free tier, shown to a
small team. Not a production/certified tool.

NON-NEGOTIABLE DOMAIN FACTS (encode these; do not contradict them)
1. Jurisdiction split: planning numbers (FAR, MGC/ground coverage, setbacks, parking) are governed
   by RAJUK's Dhaka Imarat Nirman Bidhimala / Detailed Area Plan (DAP), NOT BNBC directly. BNBC-2020
   governs life-safety: means of egress, number of exits, fire protection (Parts 3 & 4), room sizes,
   heights. The PRD must keep these two rule sources distinct.
2. The rules are IN FLUX (2025–2026): DAP 2022–2035 was revised in 2025 (FAR/heights raised, now
   ward/density-block specific), with draft "Dhaka Metropolitan Building Construction Rules 2025"
   aligned to BNBC-2020 and gazette pending. THEREFORE rule values (FAR tables, setback schedules,
   parking ratios) MUST be data-driven, versioned, and human-maintained with effective dates — never
   hardcoded in app logic. Treat the rule engine as a config/data layer, not code.
3. The input drawing is typically a FLATTENED RASTER PDF (e.g., exported from Photoshop) with NO text
   layer. So extraction needs OCR/vision, not PDF text parsing. The hardest technical risk is reliably
   reading the data tables and key dimensions/geometry off a dense sheet.
4. This is SAFETY-CRITICAL. The product is a triage/decision-support assistant for a qualified
   architect/engineer — it is NOT a certifier and gives no legal guarantee. Human-in-the-loop is
   mandatory. Every finding must carry a severity, a confidence level, the specific code provision it
   references, and a clear "needs human verification" path. False negatives (missed violations) are the
   highest-cost failure mode and must be treated as such throughout the PRD.

DELIVERABLES (create these files)
- docs/PRD.md            — the main document
- docs/rule-catalog.md   — seed catalog of checks (schema + the starter rules below, expanded)
- docs/open-questions.md — assumptions made + clarifying questions for the founder

PRD.md REQUIRED SECTIONS
1.  Problem & context (incl. why Dhaka density + seismic zone raises the stakes)
2.  Goals and explicit Non-goals (MVP)
3.  Target users & jobs-to-be-done (architects, draftspersons, small firm owners, RAJUK liaison)
4.  MVP scope: clearly in vs out. Bias toward a NARROW, high-confidence slice.
5.  Core user flow (upload sheet -> extract params -> run checks -> review triaged findings -> export)
6.  Functional requirements (numbered, testable)
7.  Compliance rule engine design: data-driven, versioned rule packs keyed to jurisdiction + effective
    date; each rule = id, source, parameter(s) needed, logic, severity, confidence, citation, remediation
    hint. Explain how new/changed rules are added without code changes.
8.  Drawing ingestion & data-extraction approach: realistic pipeline for raster PDFs (rasterize ->
    region/table detection -> OCR + vision LLM -> structured params with per-field confidence + the
    source crop for human audit). Define a minimal "extracted parameters" schema. Be honest about
    extraction accuracy limits and where human confirmation is required before checks run.
9.  Findings/output UX: how results are presented to be genuinely ACTIONABLE — grouped by severity
    (Likely violation / Needs verification / Appears compliant), each with plain-language reason, the
    code clause, the relevant sheet location, and a suggested fix. Include exportable report.
10. Architecture & stack options for a free-tier MVP (give 2–3 concrete options with tradeoffs, e.g.
    a lightweight Python app vs a JS front + serverless; note where the vision/LLM call sits, and
    cost/limits). Recommend one for the MVP and justify briefly.
11. Data model / schemas (extracted params, rule, finding, report).
12. Accuracy, evaluation & validation plan: build a small labeled set of real sheets with known
    issues; define recall (esp. on seeded true violations), precision, extraction field accuracy, and
    a manual-review protocol. State target numbers for an MVP "go" decision.
13. Safety, disclaimers, liability, human-in-the-loop: required UI disclaimers, scope-of-use language,
    and how confidence/uncertainty is surfaced so no one treats output as approval.
14. Privacy & security: drawings are proprietary/sensitive — retention, where files/LLM calls go,
    what a free host implies, opt-out of training, etc.
15. Success metrics for the "test the water" demo (qualitative team feedback + quantitative on the
    validation set + time-to-result).
16. Risks & mitigations (extraction errors on varied drawing styles, rule staleness, false neg/pos,
    over-trust, liability, vendor/free-tier limits, data leakage).
17. Roadmap beyond MVP (deeper geometry/CAD parsing, more occupancy types, multi-sheet sets, and a
    clearly-future structural/seismic-review track — explicitly OUT of MVP, with reasoning).
18. Open questions & assumptions (mirror docs/open-questions.md).

SEED RULES for docs/rule-catalog.md (define a clean schema first, then encode these as starter rows,
each with source doc, parameter inputs, check logic, default severity, confidence, citation,
remediation, and a [VERIFY] flag on any threshold that depends on the in-flux 2025/2026 rules):
- Minimum two means of egress / second fire-separated stair for high-rise (>6 storeys or >20 m). [BNBC-2020 Part 3/4]
- High-rise A-3 fire provisions for buildings >20 m: fire alarm + fixed hydrant in fire-stair landings/lift lobby; fire-rated stair enclosure; fire-fighting lift. [BNBC-2020 Part 4]
- FAR reconciliation: compare FAR claimed on sheet vs the permissible value, and force a check against the plot's LUC / current DAP ward area-FAR (do NOT assume the legacy katha/road-width table). [RAJUK DAP / Bidhimala — VERIFY]
- MGC / ground coverage vs allowable for plot bracket. [RAJUK]
- Setbacks (front/rear/side) vs schedule for plot size + building height. [RAJUK — VERIFY against Building Rules 2025]
- Parking count sanity vs required ratio for unit size/count; flag internal inconsistencies. [RAJUK — VERIFY]
- Minimum habitable room area/width, kitchen, toilet. [BNBC-2020 Part 3]
- Minimum exit stair width for apartments. [BNBC-2020 Part 3]
- Lift provision / fire lift for height. [BNBC-2020]
For each rule note required-input availability: which need a clean table read vs which need geometry
(harder) — and recommend which subset is realistic for the MVP.

PROCESS & STYLE
- Begin PRD.md with an "Assumptions" block (state them explicitly) and put up to ~6 high-leverage
  clarifying questions in open-questions.md — but still produce a COMPLETE first draft now; do not
  block on answers.
- Where you cite a code number/threshold you are not certain of, mark it [VERIFY] rather than inventing
  it. Distinguish "verified principle" from "exact value TBD."
- Use analogies sparingly where a concept is unfamiliar, but keep the doc tight and skimmable.
- Keep the MVP genuinely minimal and shippable on a free tier. Resist scope creep; push ambitious
  ideas to the roadmap.
- No application code in this session. When the PRD and rule catalog are written, stop and summarize
  the key decisions and the top 3 open questions for me to answer before we move to build.