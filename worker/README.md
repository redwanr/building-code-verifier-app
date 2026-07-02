# rajuk-verifier-proxy

The only server piece of the v3 SPA: a Cloudflare Worker that holds the LLM
API keys and gates every call behind the shared reviewer password. It is a
dumb authenticated forwarder — the SPA builds the full provider request body,
so prompt/schema iteration never needs a worker deploy.

## Endpoints

- `GET /health` — liveness, no auth
- `POST /auth` — 200 if `Authorization: Bearer <password>` matches
- `POST /extract` — `{provider: 'gemini'|'claude', model, body}` → forwarded
  to the provider with the key attached; response returned verbatim

## Deploy (one-time)

```bash
cd worker
npm install
npx wrangler login                      # opens browser, needs a Cloudflare account
npx wrangler secret put APP_PASSWORD    # the shared reviewer password
npx wrangler secret put GEMINI_API_KEY
npx wrangler secret put ANTHROPIC_API_KEY   # optional — Claude provider
npm run deploy                          # prints https://rajuk-verifier-proxy.<acct>.workers.dev
```

Then set that URL as `VITE_WORKER_URL` for the SPA build (GitHub repo →
Settings → Secrets and variables → Actions → **Variables** → `VITE_WORKER_URL`)
and add the Pages origin to `ORIGINS` in `src/index.ts` if it differs from
`https://redwanr.github.io`.

## Local dev

```bash
# .dev.vars (gitignored): APP_PASSWORD=..., GEMINI_API_KEY=...
npx wrangler dev --port 8787 --local
# then: cd ../web && VITE_WORKER_URL=http://localhost:8787 npm run dev
```
