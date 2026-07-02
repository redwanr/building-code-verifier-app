# RAJUK Verifier — v3 SPA

Drawing-first review workspace. Static React app (GitHub Pages) + a tiny
Cloudflare Worker proxy (`../worker`) that holds the LLM keys.

- pdf.js rasterizes the permit sheet **in the browser**; page images go only
  to the vision model via the worker (no-training API tier).
- The rule engine runs client-side (`src/engine/rules.ts`) over the **same
  YAML packs** as the Python engine (`../rule_packs`, synced into
  `public/rule_packs` at build). FR-9/FR-10 semantics are covered by a
  parity test suite ported from `tests/test_rules.py`.
- Demo mode needs no worker, no key, no upload: a synthetic G+9 sheet
  (`src/demo/demoSheet.ts` — real fixtures are confidential).

```bash
npm install
npm run dev     # http://localhost:5173/building-code-verifier-app/ (demo mode)
VITE_WORKER_URL=http://localhost:8787 npm run dev   # with local worker → live extraction
npm test        # vitest: engine parity, extraction parse, report render, demo fixture
npm run build   # tsc + vite → dist/
```

Deploys to GitHub Pages from `.github/workflows/pages.yml` on push to main.
Set the `VITE_WORKER_URL` Actions **variable** to the deployed worker URL so
live extraction works on Pages (without it the app is demo-only).
