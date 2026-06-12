# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
.venv/bin/pytest tests/ -q              # full suite (rule engine, report, extraction, UI smoke, G+9 acceptance)
.venv/bin/pytest tests/test_rules.py -q # single file
.venv/bin/streamlit run app.py          # run app locally (needs .streamlit/secrets.toml — see secrets.toml.example)
.venv/bin/python eval_providers.py both # Claude vs Gemini extraction accuracy (needs fixtures/*.pdf + *.truth.yaml + API keys)
```

System dep: `poppler` (brew) for pdf2image.

## Code map

- `report.py` — PRD §11 dataclasses (ExtractedParam/Finding/Report) — the single internal data contract — plus MD/HTML render.
- `rules.py` — YAML pack loader + simpleeval interpreter. Rules cap at "needs_verification" when `verify_flag: true`; missing/unconfirmed input → "cannot evaluate" (FR-9).
- `rule_packs/*.yaml` — the rules. Edit values here, never in code. `logic` must be a single-line simpleeval expression (multi-line YAML folds break ast.parse).
- `extraction.py` — pdf2image → provider-switched vision call (Claude `claude-opus-4-8` default, Gemini via `GEMINI_MODEL`). Confidence < 0.7 → unconfirmed.
- `app.py` — Streamlit flow: password gate → upload → confirmation gate → findings → export.

## Project status

**MVP implemented; awaiting real permit-sheet fixtures for the provider A/B eval.** No application code exists yet. The repo contains the planning docs for a RAJUK Permit-Sheet Code Verifier MVP: upload a Dhaka building-approval drawing (flattened raster PDF), extract planning/life-safety parameters via OCR + vision-LLM, run data-driven code checks, present triaged findings for a qualified architect/engineer to review.

Read these before any work:
- `docs/PRD.md` — full product spec (FRs, schemas, pipeline, eval plan)
- `docs/rule-catalog.md` — 9 seed rules + schema; the 6-rule MVP subset is at the bottom
- `docs/CONTEXT.md` — original brief with the non-negotiable domain facts
- `docs/open-questions.md` — unresolved founder questions (rule values, LLM provider, labeled set)

## Non-negotiable domain constraints

These come from `docs/CONTEXT.md` and override convenience:

1. **Jurisdiction split is structural.** Planning rules (FAR, MGC, setbacks, parking) come from RAJUK DAP/Bidhimala packs; life-safety rules (egress, exits, fire, room sizes) come from BNBC-2020 packs. A rule belongs to exactly one source; every finding cites its regime. Never check a planning value against BNBC or vice versa.
2. **Rule values are data, never code.** Thresholds are in flux (DAP 2025 revision, draft Building Rules 2025). Rule packs are versioned data files keyed `{jurisdiction, effective_date}` (e.g. `bnbc-2020@2020-01-01`), maintained by a domain expert. Adding/changing a rule or threshold must require no code change (FR-10). Rule logic uses a small declarative vocabulary (`gt`, `lt`, `eq`, `param_present`, `compare`, `consistency`, `if/then`) evaluated by a tiny interpreter.
3. **Input is a flattened raster PDF — no text layer.** Extraction is rasterize → region detection → OCR + vision-LLM, never PDF text parsing. Tier 1 = table/text reads (MVP); Tier 2 = geometry measurement (deferred — geometry-dependent checks emit "needs verification", never guesses).
4. **Safety-critical posture.** Decision-support only, never certification. False negatives (missed violations) are the worst failure mode — optimize for recall on life-safety items. The human-confirmation gate on low-confidence extracted fields (default threshold 0.7) is mandatory before checks run. A rule with a missing/unconfirmed input emits "cannot evaluate", never a silent pass (FR-9). The non-certification disclaimer appears on every screen and export. "Appears compliant" — never "is compliant".

## Planned architecture (PRD §10, Option A — chosen)

Python monolith (Streamlit or Gradio) on a free tier (Streamlit Community Cloud / HF Spaces):
- `pdf2image` rasterize → Tesseract OCR + Claude vision call (server-side; API key never in browser/repo) → params schema → confirmation gate → rule interpreter → findings UI → PDF/Markdown export.
- Rule packs live as JSON/YAML files in the repo.
- Findings always land in exactly three buckets: Likely violation / Needs verification / Appears compliant.
- Data schemas for extracted param, rule, finding, and report are in PRD §11 — use them as written.

## Scope guardrails

Out of MVP (PRD §2, don't build): geometry/CAD measurement off pixels, structural/seismic review, multi-sheet sets, occupancies beyond residential A-3, accounts/RBAC/billing, automatic rule scraping. Bias narrow: ship the 6 trusted table-readable checks (EGRESS-001, FIRE-002 presence-only, FAR-003, MGC-004, PARKING-006, LIFT-009) over a wide set.

Uploads and crops get a short TTL — no permanent drawing archive in MVP. Drawings are confidential; pages sent to the vision-LLM provider must be on a no-training tier and disclosed to users.

When citing a code threshold you are not certain of, mark it `[VERIFY]` — never invent BNBC/RAJUK values.
