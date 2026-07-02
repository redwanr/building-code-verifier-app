# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
.venv/bin/pytest tests/ -q              # full suite (rule engine, report, extraction, UI smoke, G+9 acceptance)
.venv/bin/pytest tests/test_rules.py -q # single file
.venv/bin/streamlit run app.py          # run app locally (needs .streamlit/secrets.toml — see secrets.toml.example)
.venv/bin/python eval_providers.py both # Claude vs Gemini extraction accuracy (needs fixtures/*.pdf + *.truth.yaml + API keys)
.venv/bin/python e2e_run.py "<sheet>.pdf" gemini  # headless e2e: extract→rules→findings; dumps raw JSON + crops to e2e_out/ (gitignored)
```

System dep: `poppler` (brew) for pdf2image. Cloud installs it via `packages.txt`.

## Dev workflow — main = production (deployed to Streamlit Community Cloud)

The app is LIVE for partner testing; Streamlit auto-redeploys from `main` on every
push (~1-2 min, via deploy webhook). So **`main` is production — never merge half-done
work.** Follow this loop for every change:

1. **Branch** off main (never commit straight to main).
2. **Edit** code or `rule_packs/*.yaml`.
3. **Test:** `.venv/bin/pytest tests/ -q` — must be green before merge.
4. **Preview live behavior locally** when UI/extraction/rules changed:
   `.venv/bin/streamlit run app.py` (localhost:8501) — catch breakage before testers do.
5. **Commit → PR → merge to main** (squash/merge via `gh`). Merge = auto-deploy.
6. **Rollback** a bad deploy: `git revert <commit>` → push to main → Streamlit redeploys good state.

Secrets (APP_PASSWORD, GEMINI_API_KEY) live ONLY in the cloud Secrets panel + local
`.streamlit/secrets.toml` (gitignored) — never commit them. Confidential drawings/
fixtures/test PDFs stay gitignored. Rotate the API key + keep a billing cap since the
URL is shared.

## Code map

- `report.py` — PRD §11 dataclasses (ExtractedParam/Finding/Report) — the single internal data contract — plus MD/HTML render.
- `rules.py` — YAML pack loader + simpleeval interpreter. Rules cap at "needs_verification" when `verify_flag: true`; missing/unconfirmed input → "cannot evaluate" (FR-9).
- `rule_packs/*.yaml` — the rules. Edit values here, never in code. `logic` must be a single-line simpleeval expression (multi-line YAML folds break ast.parse).
- `extraction.py` — pdf2image → provider-switched vision call (Claude `claude-opus-4-8` default, Gemini via `GEMINI_MODEL`). Confidence < 0.7 → unconfirmed.
- `app.py` — Streamlit flow: password gate → upload → confirmation gate → findings → export.

## SPA v3 (branch `spa-v3`, 2026-07-01) — drawing-first rebuild off Streamlit

Full product revamp on this branch, replacing the Streamlit UI (which stays
live on main until founder-approved cutover). Static React SPA (GitHub Pages)
+ Cloudflare Worker key-holding proxy. Decision log: `~/.claude/plans/shiny-percolating-barto.md`.

- `web/` — Vite+React+TS. Drawing-first workspace: pdf.js renders the sheet
  in-browser, extracted values are crosshair pins (bbox), review panel with
  live rule re-eval on every confirm (FR-9 keeps unconfirmed → cannot
  evaluate). Drafting-room-dark design, IBM Plex + clay. Demo mode uses a
  synthetic SVG G+9 sheet (`web/src/demo/demoSheet.ts`).
- `web/src/engine/rules.ts` — TS port of rules.py; same YAML packs (synced to
  `web/public/rule_packs` at build); parity tests from test_rules.py.
- `worker/` — ~110-line authenticated forwarder (password + provider keys).
  Deploy guide in `worker/README.md`; local dev via `.dev.vars` (gitignored).
- Commands: `cd web && npm test` (vitest, 29) · `npm run dev` (demo) ·
  `VITE_WORKER_URL=http://localhost:8787 npm run dev` + `cd worker && npx
  wrangler dev` (live extraction, e2e-verified against the Uttara fixture).
- Cutover checklist: deploy worker (needs Cloudflare login), set
  `VITE_WORKER_URL` repo Actions variable, enable Pages (build_type
  workflow), merge, founder demo, then retire Streamlit.

## Project status & next steps (as of 2026-06-17)

**MVP implemented and DEPLOYED LIVE to Streamlit Community Cloud for partner testing (2026-06-17).** Tests green, repo at https://github.com/redwanr/building-code-verifier-app (private). Full decision log in `~/.claude/plans/cozy-churning-orbit.md` (grill-me interview: Streamlit monolith, vision-LLM-only extraction, Claude Opus 4.8 default + Gemini option, simpleeval YAML rules, provisional [VERIFY] thresholds capped at needs-verification, user-supplied permissible FAR/MGC at gate, session-only persistence, MD/HTML export, shared-password gate). Sidebar provider defaults to **gemini** (cloud secrets only carry a Gemini key). Gemini `gemini-3.5-flash` VERIFIED working e2e against the real firm sheet `tests/Uttara15C1 _ architectural.pdf` (gitignored). Done since 06-12: ✅ secrets, ✅ Gemini model verified, ✅ deploy. Partner explainer: `docs/How-The-MVP-Works.docx`.

Next steps, in order:
1. **Fixtures + accuracy** — add validation sheets as `fixtures/<name>.pdf` + `<name>.truth.yaml`; run `eval_providers.py` to measure field accuracy (target ≥0.80 Tier-1, PRD §12). No truth file exists for the Uttara sheet yet.
2. **Provider A/B** — `.venv/bin/python eval_providers.py both`; revisit production default (currently gemini by necessity, not measured accuracy).
3. **Live extraction tuning** — iterate `EXTRACTION_PROMPT` in `extraction.py`; note observed run-to-run non-determinism on the same sheet (recall-critical — consider multi-pass reconcile).
4. **Rule thresholds** — 9 of 11 rules carry `verify_flag` (provisional [VERIFY]); domain expert must confirm 2025/2026 values to unlock hard red/green beyond the 2 consistency rules.

Open items from `docs/open-questions.md` still unanswered: rule-pack value owner (Q4), go-bar confirmation (Q5). Product: a RAJUK Permit-Sheet Code Verifier MVP — upload a Dhaka building-approval drawing (flattened raster PDF), extract planning/life-safety parameters via vision-LLM (no OCR engine — vision-only), run data-driven code checks, present triaged findings for a qualified architect/engineer to review.

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
