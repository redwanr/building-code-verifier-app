# PRD — RAJUK Permit-Sheet Code Verifier (MVP)

**Status:** Draft v0.1 · **Owner:** Founder + PM · **Date:** 2026-06-12
**One-line:** Upload a RAJUK building-approval drawing; get a triaged list of likely building-code violations for a qualified architect/engineer to review.

---

## 0. Assumptions (read first)

These are stated explicitly so they can be corrected. None block this draft.

- **A1.** The MVP audience is a small internal team + a few friendly firms in Dhaka, not the public. "Test the water," not certify.
- **A2.** Input is one flattened raster PDF "permit sheet" per building (no multi-sheet sets in MVP). Typically exported from Photoshop/CAD-to-image — **no text layer**.
- **A3.** Residential apartment occupancy (BNBC Group A-3 / typical G+ buildings) is the only occupancy class in MVP. Mixed-use, commercial, industrial → out.
- **A4.** A human expert (architect/engineer) reviews every output. The tool never gates or approves anything.
- **A5.** Rule *values* (FAR tables, setback schedules, parking ratios) are in flux for 2025–2026 and will be entered/maintained by a human domain expert as versioned data, not by us guessing them.
- **A6.** Free-tier hosting + a paid vision-LLM API key (small volume) is acceptable cost for MVP. We are not optimizing $ yet, but must stay inside free compute/storage tiers.
- **A7.** English-language sheets dominate; Bangla labels appear in tables and must be tolerated by OCR but are not the primary target for MVP accuracy.
- **A8.** "Finding" quality bar: high recall on life-safety items (egress, exits, fire) is more important than precision. Missing a real violation (false negative) is the worst outcome.

---

## 1. Problem & context

Dhaka is one of the densest cities on earth and sits in an active seismic zone (BNBC Seismic Zone 2, coefficient ~0.20). Plan-review quality is therefore a genuine public-safety issue, not paperwork. A flawed egress or fire-protection scheme in a G+9 apartment block is a mass-casualty risk; an inflated FAR is both a legal and a structural-load problem.

Today, plan review is manual, slow, and inconsistent. Reviewers eyeball a single dense permit sheet — floor plans, elevations, sections, and area/FAR/MGC/setback/parking tables — and must hold both **planning rules** (RAJUK) and **life-safety rules** (BNBC) in their head at once. Mistakes slip through.

**Validated manually:** On a real G+9 residential sheet, the concept correctly flagged (1) a single-staircase egress problem, (2) missing high-rise fire provisions, (3) a questionable FAR figure, and (4) an inconsistent parking count. That is the proof the triage idea works. This MVP automates that first pass so a qualified reviewer spends their time *verifying* findings instead of *hunting* for them.

**Why now:** RAJUK's DAP 2022–2035 was revised in 2025 (FAR/heights raised, now ward/density-block specific) and a draft "Dhaka Metropolitan Building Construction Rules 2025" aligned to BNBC-2020 is awaiting gazette. Reviewers are operating against moving targets — a tool that keeps rule values as maintained, dated data is more useful now than ever.

---

## 2. Goals & Non-goals

### Goals (MVP)
- **G1.** Ingest one raster permit-sheet PDF and extract a defined set of planning + life-safety parameters with per-field confidence and an audit crop.
- **G2.** Run a small, high-confidence set of code checks against versioned rule data and produce triaged findings.
- **G3.** Present findings as genuinely actionable: severity, plain-language reason, the specific clause, the sheet location, a suggested fix, and a confidence level.
- **G4.** Make every finding human-verifiable and export a shareable report.
- **G5.** Ship on a free tier and demo to a small team.

### Non-goals (explicitly OUT of MVP)
- **N1.** Any structural or seismic-design review (loads, member sizing, drift). Future track.
- **N2.** Geometry/CAD reconstruction from drawings (measuring setbacks/areas off pixels). MVP reads *tabular* values; geometry checks are roadmap.
- **N3.** Multi-sheet drawing sets, multiple buildings per submission.
- **N4.** Occupancies beyond residential apartment (A-3).
- **N5.** Legal certification, e-submission to RAJUK, or any "approval" semantics.
- **N6.** Automatic rule scraping/interpretation of gazettes. Rules are human-entered.
- **N7.** Multi-user accounts, RBAC, billing. Single shared internal instance is fine.

---

## 3. Target users & jobs-to-be-done

| User | Job-to-be-done | What they need from the tool |
|---|---|---|
| **Architect (firm)** | "Before I submit, catch the violations a RAJUK reviewer will reject me for." | Fast, trustworthy triage with exact clause + fix hint. |
| **Draftsperson** | "Did I transcribe the area/FAR/parking tables consistently?" | Internal-consistency checks; flag mismatches between tables and stated totals. |
| **Small-firm owner** | "Is this submission going to bounce and cost me weeks?" | A one-page risk summary, severity-sorted. |
| **RAJUK liaison / reviewer** | "Where do I focus my manual review time?" | A prioritized checklist with sheet locations to inspect. |

Primary JTBD for MVP: **"Give me a triaged first-pass review of this sheet so I know where to look."**

---

## 4. MVP scope — in vs out

**IN**
- Single raster PDF upload (≤ N pages, typically 1–2).
- Vision-LLM + OCR extraction of: building height/storeys, occupancy (assumed A-3), claimed FAR, claimed MGC/ground coverage, plot area, number of stairs/exits, stair width (if tabulated), parking count (required vs provided), unit count/sizes, lift count — **wherever these appear as text/table values**.
- A starter rule pack (see `rule-catalog.md`) of ~9 checks, split into "table-readable" (realistic) and "geometry-dependent" (deferred).
- Triaged findings UI + exportable PDF/Markdown report.
- Human confirmation step on low-confidence extracted fields **before** checks run.

**OUT** — see Non-goals. Notably: no pixel-measured setback/area verification, no seismic, no multi-occupancy, no rule auto-update.

**Bias:** Narrow + high-confidence. Better to ship 5 checks the team trusts than 20 they don't.

---

## 5. Core user flow

```
1. Upload permit-sheet PDF
2. System rasterizes → detects regions/tables → OCR + vision-LLM → extracted params (each w/ confidence + source crop)
3. Human review screen: confirm/correct low-confidence fields  ← gate
4. Run checks (rule pack for jurisdiction + effective date)
5. Triaged findings: Likely violation / Needs verification / Appears compliant
6. Reviewer inspects each (clause, sheet location crop, suggested fix), marks accept/dismiss
7. Export report (PDF/MD)
```

The **gate at step 3** is non-negotiable: checks must not run on unconfirmed low-confidence inputs, or we manufacture false confidence.

---

## 6. Functional requirements (numbered, testable)

**Ingestion**
- **FR-1.** System accepts a PDF upload up to a configured size limit; rejects non-PDF with a clear error.
- **FR-2.** System rasterizes each PDF page to image(s) at a configurable DPI (default 200+).
- **FR-3.** For each extracted parameter, system stores: value, unit, confidence (0–1), source page, and a bounding-box crop image.
- **FR-4.** System flags any field with confidence below a configurable threshold (default 0.7) as "needs human confirmation."

**Human-in-the-loop**
- **FR-5.** Before running checks, system presents all extracted params; user can edit any value and must confirm flagged fields.
- **FR-6.** User edits are recorded (original value, edited value) for the audit trail.

**Rule engine**
- **FR-7.** Checks run against a selected rule pack identified by `{jurisdiction, effective_date}`; the active pack is displayed to the user.
- **FR-8.** Each finding records: rule id, source doc, severity, confidence, citation text, remediation hint, and the input values used.
- **FR-9.** A rule may declare required inputs; if a required input is missing/unconfirmed, the rule emits a "cannot evaluate — input missing" finding rather than passing or failing silently.
- **FR-10.** Adding/editing a rule or a threshold value requires **no code change** — only editing rule-pack data.

**Output**
- **FR-11.** Findings are grouped into exactly three buckets: *Likely violation*, *Needs verification*, *Appears compliant*.
- **FR-12.** Each finding shows plain-language reason, exact clause/citation, sheet location (linked crop), suggested fix, severity, confidence.
- **FR-13.** User can mark each finding accept/dismiss with an optional note.
- **FR-14.** System exports a report (PDF and/or Markdown) including the active rule-pack version, disclaimers, all findings, and the params used.

**Safety**
- **FR-15.** Every screen and every export displays the non-certification disclaimer (see §13).
- **FR-16.** Confidence and "needs human verification" status are visible on every finding; nothing is presented as definitive approval.

---

## 7. Compliance rule engine design

**Principle:** The rule engine is a **data/config layer, not code.** Rule values change with gazettes; code does not.

**Rule pack = a versioned data file** (JSON/YAML) keyed by `{jurisdiction, effective_date}`. Example: `rajuk-dap-2025@2025-09-01`, `bnbc-2020@2020-01-01`. The app loads the appropriate pack(s); a building submission is evaluated against the pack effective on its submission date (or the latest, user-selectable).

**Each rule record** (schema in §11 and `rule-catalog.md`):
- `id` — stable identifier.
- `source` — `BNBC-2020` (life-safety) **or** `RAJUK-DAP/Bidhimala` (planning). These two sources are kept distinct; a rule belongs to exactly one.
- `parameters` — the extracted params it needs.
- `logic` — a small declarative expression (threshold/compare/consistency), evaluated by a tiny interpreter, not bespoke per-rule code.
- `severity` — Critical / High / Medium / Low.
- `confidence_basis` — how confident we are in the *rule itself* (separate from extraction confidence).
- `citation` — clause text/number.
- `remediation` — plain-language fix hint.
- `verify_flag` — `[VERIFY]` true when the threshold depends on in-flux 2025/2026 rules.

**Adding a rule without code changes:** A domain expert adds a row to the rule-pack file with a `logic` expression drawn from a fixed, documented vocabulary (e.g. `gt`, `lt`, `eq`, `param_present`, `compare(a,b)`, `consistency([...])`). The interpreter supports that vocabulary; new *values* and new *combinations* need no deploy. Only a brand-new *operator* would need code — and the starter vocabulary is chosen to avoid that for the seed rules.

**Jurisdiction split is structural, not cosmetic:** planning checks (FAR/MGC/setback/parking) read from RAJUK packs; life-safety checks (egress/exits/fire/room sizes) read from BNBC packs. A finding always cites which regime it came from. This prevents the classic error of "checking FAR against BNBC."

---

## 8. Drawing ingestion & data-extraction approach

**Reality:** Input is a flattened raster with no text layer. There is no shortcut via PDF text parsing. This is the **highest technical risk** in the product.

**Pipeline:**
```
PDF → rasterize (pdf→image, ~200–300 DPI)
    → region detection (find table blocks, title block, drawing areas)
    → for table/text regions: OCR (Tesseract/cloud OCR) + vision-LLM read
    → vision-LLM structures values into the params schema, each with:
         value, confidence, source page, bounding-box crop
    → low-confidence fields routed to human-confirmation gate (FR-4/FR-5)
    → only confirmed params feed the rule engine
```

**Two extraction tiers, by difficulty:**
- **Tier 1 — table/text reads (MVP target):** FAR, MGC, plot area, parking provided/required, unit counts, storey count, stair count, lift count, tabulated stair width. These appear as printed values in the data tables. Realistic to extract with OCR + vision-LLM.
- **Tier 2 — geometry reads (NOT MVP):** measuring actual setbacks, actual areas, actual stair widths off the plan geometry when not tabulated. Requires reliable scale + line detection. Deferred to roadmap; flagged "needs human verification" if a check would need it.

**Honesty on accuracy:** Vision extraction on dense, varied, hand-styled sheets will be imperfect. Therefore:
- Every field carries confidence + an audit crop so a human can verify in one glance.
- Checks never run on unconfirmed low-confidence fields.
- We measure extraction field accuracy on a labeled set (§12) and surface it.

**Minimal extracted-params schema:** see §11.

---

## 9. Findings / output UX

**Three buckets, always:**
- 🔴 **Likely violation** — rule failed on confirmed inputs at high confidence. Sorted by severity.
- 🟡 **Needs verification** — rule indeterminate: input low-confidence, geometry-dependent, or threshold `[VERIFY]`.
- 🟢 **Appears compliant** — rule passed on confirmed inputs (still "appears," never "is").

**Each finding card shows:**
- Plain-language reason ("Building is 10 storeys / ~30 m but only one stair is shown. High-rise requires ≥2 fire-separated exits.")
- Exact clause/citation + which regime (BNBC vs RAJUK).
- Sheet location — clickable crop of where the relevant value/element is.
- Suggested fix (remediation hint).
- Severity + confidence badges.
- Accept / Dismiss + note.

**Export:** one-page risk summary (counts by severity) + full findings list + params used + active rule-pack version + disclaimers. PDF and Markdown.

Design intent: a reviewer should be able to act on the report **without re-reading the whole sheet** — every finding points to its evidence.

---

## 10. Architecture & stack options (free-tier MVP)

The vision/LLM call is the cost+risk center in all options. It sits server-side (never expose the API key to the browser).

**Option A — Python monolith (Streamlit/Gradio) + vision-LLM API.** *Recommended for MVP.*
- One Python app: upload widget, `pdf2image` rasterize, OCR (Tesseract) + Claude vision call, rule interpreter, findings UI, report export.
- Host: Streamlit Community Cloud / Hugging Face Spaces free tier.
- **+** Fastest to build; one language; great for a demo; rule packs are just files in repo.
- **−** Free tiers sleep/limit compute; not multi-user-robust; rasterizing big PDFs may strain memory.

**Option B — JS front (Next.js on Vercel) + serverless functions + vision-LLM.**
- Browser upload → serverless function rasterizes + calls vision-LLM + runs rules → returns JSON → React findings UI.
- **+** Nicer UX; Vercel free tier solid for the front; scales later.
- **−** Serverless function time/memory limits hurt PDF rasterization + OCR; more moving parts; two languages.

**Option C — Python API (FastAPI) + thin static/JS front, on a free PaaS (Render/Fly free).**
- **+** Clean separation, real API for later; Python keeps the CV/OCR stack.
- **−** More infra than A for no MVP benefit; free PaaS cold starts.

**Recommendation: Option A.** It is the laziest path that fully demos the product: shortest build, one stack, rule packs as files, server-side LLM call. Migrate to B/C only when multi-user or UX polish justifies it. *(ponytail: monolith now, split when a real constraint appears.)*

---

## 11. Data model / schemas

**Extracted parameter**
```json
{
  "param": "claimed_far",
  "value": 4.2,
  "unit": "ratio",
  "confidence": 0.62,
  "source_page": 1,
  "source_crop": "crops/far_p1.png",
  "confirmed": false,
  "edited_from": null
}
```

**Rule**
```json
{
  "id": "BNBC-EGRESS-002",
  "source": "BNBC-2020",
  "title": "Second fire-separated stair for high-rise",
  "parameters": ["building_height_m", "num_storeys", "num_exit_stairs"],
  "logic": "if (building_height_m > 20 OR num_storeys > 6) then num_exit_stairs >= 2",
  "severity": "Critical",
  "confidence_basis": "Verified principle (BNBC Part 3/4); exact trigger value [VERIFY]",
  "citation": "BNBC-2020 Part 3 & 4 — means of egress / number of exits",
  "remediation": "Add a second, fire-separated exit stair.",
  "verify_flag": true
}
```

**Finding**
```json
{
  "rule_id": "BNBC-EGRESS-002",
  "bucket": "likely_violation",
  "severity": "Critical",
  "confidence": 0.74,
  "reason": "10 storeys / ~30 m with 1 stair; high-rise needs >=2 fire-separated exits.",
  "citation": "BNBC-2020 Part 3/4",
  "regime": "BNBC",
  "inputs_used": {"num_storeys": 10, "num_exit_stairs": 1},
  "sheet_location": "crops/stairs_p1.png",
  "remediation": "Add a second fire-separated exit stair.",
  "user_action": null
}
```

**Report**
```json
{
  "submission_id": "uuid",
  "created_at": "2026-06-12T...",
  "rule_packs": ["bnbc-2020@2020-01-01", "rajuk-dap-2025@2025-09-01"],
  "params": [ /* extracted params */ ],
  "findings": [ /* findings */ ],
  "summary": {"critical": 1, "high": 1, "medium": 2, "needs_verification": 3},
  "disclaimer_version": "v1"
}
```

---

## 12. Accuracy, evaluation & validation plan

**Build a small labeled set:** 10–20 real permit sheets (including the validated G+9), each annotated by an expert with (a) ground-truth param values and (b) known true violations ("seeded truths"). Include at least a few sheets with **known** egress/fire/FAR/parking problems.

**Metrics:**
- **Recall on seeded true violations** — *the headline metric.* False negatives are the worst failure mode. Target **≥ 0.90 recall on life-safety findings** for a "go."
- **Precision on findings** — secondary. Target **≥ 0.60** (a noisy-but-safe triage is acceptable; reviewer dismisses false positives quickly).
- **Extraction field accuracy** — % of params read correctly vs ground truth, per field. Target **≥ 0.80 on Tier-1 table fields** post-human-confirmation should approach 1.0; pre-confirmation raw accuracy is what we report.
- **Time-to-result** — upload → triaged findings. Target **< 5 min** including the human-confirmation step.

**Manual-review protocol:** Two experts independently label each sheet; disagreements reconciled. Every model finding is adjudicated true/false. Extraction fields scored exact-match (numbers) / tolerant-match (units, rounding).

**"Go" decision for the test-the-water demo:** life-safety recall ≥ 0.90 on the labeled set, no Critical false negative on any seeded sheet, time-to-result < 5 min, and qualitative "would use again" from ≥ 3 of the demo team.

---

## 13. Safety, disclaimers, liability, human-in-the-loop

**Scope-of-use language (shown on every screen + every export):**
> ⚠️ **Decision-support only — not a certification.** This tool gives a first-pass, automated triage of *possible* code issues for review by a qualified, licensed architect/engineer. It does not approve, certify, or guarantee compliance with RAJUK rules or BNBC. Extracted values and findings may be wrong. A qualified professional must independently verify everything. No legal reliance.

**Human-in-the-loop mechanics:**
- Mandatory confirmation gate on low-confidence inputs before checks run (FR-5).
- Every finding carries confidence + "needs human verification" path (FR-16).
- "Appears compliant" is worded to never imply approval.
- Reports record which rule-pack version and which (possibly `[VERIFY]`) thresholds were used.

**Liability posture (MVP):** internal/friendly-user only, behind the disclaimer; no claims of accuracy; no certification. Revisit with legal counsel before any external launch.

---

## 14. Privacy & security

Drawings are proprietary and commercially sensitive. Treat as confidential.

- **Where files go:** uploaded to the app host; **pages/crops are sent to the vision-LLM provider** for extraction. This must be disclosed to users — their drawing leaves our control for the LLM call.
- **Provider training opt-out:** use an API/tier that does **not** train on submitted data; verify and document this (Anthropic API does not train on API inputs by default — confirm current terms).
- **Retention:** default to **delete uploads + crops after the session / a short TTL**; do not build a permanent drawing archive in MVP. (ponytail: no storage we don't need.)
- **Free-host implication:** free tiers offer weak isolation/SLAs and may log requests; acceptable for friendly-team MVP, **not** for third-party confidential work without consent. Disclose.
- **Secrets:** LLM API key server-side only, never in the browser/repo; use host secret store.
- **Access:** single shared instance behind a shared password / allowlist for the demo; no public uploads.

---

## 15. Success metrics ("test the water" demo)

- **Qualitative:** ≥ 3 of the demo team say "I would use this on a real submission." Specific feedback on which findings were useful vs noise.
- **Quantitative (validation set):** life-safety recall ≥ 0.90; precision ≥ 0.60; Tier-1 extraction accuracy ≥ 0.80.
- **Time-to-result:** < 5 min end-to-end.
- **Reproduced the manual win:** correctly re-flags all four issues from the original G+9 validation sheet.

---

## 16. Risks & mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| **Extraction errors** on varied/hand-styled sheets | Wrong params → wrong findings | Per-field confidence + audit crops + mandatory confirmation gate; measure field accuracy. |
| **False negatives** (missed violation) | Highest cost — safety | Optimize for recall; "needs verification" defaults; never silently pass a rule with missing input (FR-9). |
| **False positives** | Reviewer distrust/noise | Severity sort, easy dismiss, precision target; keep MVP rule set small + high-confidence. |
| **Rule staleness** (2025/2026 flux) | Checking against wrong values | Versioned dated rule packs; `[VERIFY]` flags; human-maintained; show active pack on every report. |
| **Over-trust / automation bias** | User treats output as approval | Disclaimers everywhere; "appears compliant" wording; confidence on every finding. |
| **Liability** | Legal exposure | Internal-only MVP, disclaimer, no certification claims; counsel before external launch. |
| **Free-tier limits** (sleep, memory, rate caps) | Demo flakiness | Keep PDFs small; cache; have a paid fallback ready for the live demo. |
| **Data leakage** to LLM provider | Confidential drawing exposure | No-training tier, short retention, disclose to users, server-side key. |
| **Geometry checks tempting scope creep** | Blows MVP timeline | Hard line: Tier-2 geometry is roadmap; geometry-dependent checks emit "needs verification." |

---

## 17. Roadmap beyond MVP

- **R1. Tier-2 geometry/CAD parsing** — measure setbacks, areas, stair widths off plan geometry (needs reliable scale + line/vector detection). Enables the deferred planning/egress geometry checks.
- **R2. More occupancies** — commercial, mixed-use, institutional (new rule packs + new params).
- **R3. Multi-sheet sets** — cross-reference plans/sections/schedules across sheets.
- **R4. Rule-pack tooling** — an editor + change-log UI for the domain expert; diff between gazette versions.
- **R5. Structural / seismic-review track** *(explicitly OUT of MVP)* — load paths, member checks, drift, seismic detailing. This is a different discipline with far higher correctness stakes and liability; it must not be conflated with plan-review triage. Separate product track, separate validation, separate expert sign-off. Reasoning: getting egress/planning triage right and trusted is hard enough; structural review is a multiplied safety + liability surface that a "test the water" MVP cannot responsibly carry.

---

## 18. Open questions & assumptions

Full list in `open-questions.md`. Top 3 to unblock build:

1. **Which exact rule-pack values can we get a domain expert to commit to now** (even as `[VERIFY]` placeholders), given the 2025/2026 flux?
2. **Vision-LLM provider + no-training tier** confirmed acceptable for confidential drawings?
3. **Is Tier-1 (table-only) extraction enough** to reproduce the validated G+9 win, or does any of those 4 findings actually need geometry?
