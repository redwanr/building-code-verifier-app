/**
 * RAJUK Verifier proxy — the only server piece.
 *
 * Holds the LLM API keys (never in the browser/repo) and gates every call
 * behind the shared reviewer password. Deliberately a dumb forwarder: the
 * SPA builds the full provider request body (prompt, images, schema), so
 * extraction iteration never needs a worker deploy.
 *
 * Not an open proxy: only the two fixed provider endpoints below, only
 * allowlisted model prefixes, only with the password.
 */

export interface Env {
  APP_PASSWORD: string
  GEMINI_API_KEY?: string
  ANTHROPIC_API_KEY?: string
}

const ORIGINS = [
  'https://redwanr.github.io',
  'http://localhost:5173',
  'http://127.0.0.1:5173',
]

function cors(req: Request): Record<string, string> {
  const origin = req.headers.get('Origin') ?? ''
  return {
    'Access-Control-Allow-Origin': ORIGINS.includes(origin) ? origin : ORIGINS[0],
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Authorization, Content-Type',
    'Access-Control-Max-Age': '86400',
  }
}

function json(req: Request, status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json', ...cors(req) },
  })
}

function authed(req: Request, env: Env): boolean {
  const header = req.headers.get('Authorization') ?? ''
  const pw = header.replace(/^Bearer\s+/i, '')
  return Boolean(env.APP_PASSWORD) && pw === env.APP_PASSWORD
}

export default {
  async fetch(req: Request, env: Env): Promise<Response> {
    const url = new URL(req.url)

    if (req.method === 'OPTIONS') return new Response(null, { status: 204, headers: cors(req) })
    if (url.pathname === '/health') return json(req, 200, { ok: true })

    if (!authed(req, env)) return json(req, 401, { error: 'wrong or missing password' })

    if (url.pathname === '/auth' && req.method === 'POST') {
      return json(req, 200, { ok: true })
    }

    if (url.pathname === '/extract' && req.method === 'POST') {
      let payload: { provider?: string; model?: string; body?: unknown }
      try {
        payload = await req.json()
      } catch {
        return json(req, 400, { error: 'invalid JSON' })
      }
      const { provider, model, body } = payload
      if (!model || typeof body !== 'object' || body === null) {
        return json(req, 400, { error: 'need model + body' })
      }

      let upstream: Request
      if (provider === 'gemini' && model.startsWith('gemini-')) {
        if (!env.GEMINI_API_KEY) return json(req, 503, { error: 'GEMINI_API_KEY not configured' })
        upstream = new Request(
          `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent`,
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'x-goog-api-key': env.GEMINI_API_KEY },
            body: JSON.stringify(body),
          },
        )
      } else if (provider === 'claude' && model.startsWith('claude-')) {
        if (!env.ANTHROPIC_API_KEY) return json(req, 503, { error: 'ANTHROPIC_API_KEY not configured' })
        upstream = new Request('https://api.anthropic.com/v1/messages', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'x-api-key': env.ANTHROPIC_API_KEY,
            'anthropic-version': '2023-06-01',
          },
          body: JSON.stringify({ ...body, model }),
        })
      } else {
        return json(req, 400, { error: 'unknown provider/model' })
      }

      const res = await fetch(upstream)
      const text = await res.text()
      return new Response(text, {
        status: res.status,
        headers: { 'Content-Type': 'application/json', ...cors(req) },
      })
    }

    return json(req, 404, { error: 'not found' })
  },
}
