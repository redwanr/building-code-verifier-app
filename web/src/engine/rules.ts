/**
 * Rule engine — TS port of rules.py with identical semantics (PRD §7).
 *
 * Rules are data, not code (FR-10): the YAML packs are shared byte-for-byte
 * with the Python engine. `logic` strings are written in the packs'
 * Python-ish grammar; a tiny transpile step maps them to JS before eval.
 *
 * FR-9: a rule with a missing/unconfirmed required input emits a
 * "cannot evaluate" finding — never a silent pass.
 * verify_flag rules cap at needs_verification.
 */
import { load as parseYaml } from 'js-yaml'

export interface ExtractedParam {
  param: string
  value: unknown
  unit: string
  confidence: number
  sourcePage: number
  sourceCrop: string | null // data-URL crop image
  cropFallbackNote?: string | null
  bbox?: [number, number, number, number] | null // page-pixel coords
  confirmed: boolean
  editedFrom?: unknown
}

export interface Rule {
  id: string
  source: string
  title: string
  parameters: string[]
  logic: string
  severity: string
  confidenceBasis: string
  citation: string
  remediation: string
  verifyFlag: boolean
}

export type Bucket = 'likely_violation' | 'needs_verification' | 'appears_compliant'

export interface Finding {
  ruleId: string
  bucket: Bucket
  severity: string
  confidence: number
  reason: string
  citation: string
  regime: 'BNBC' | 'RAJUK'
  inputsUsed: Record<string, unknown>
  sheetLocation: string | null
  remediation: string
  verifyFlag: boolean
  userAction?: 'accept' | 'dismiss' | null
  userNote?: string | null
}

const REGIME: Record<string, 'BNBC' | 'RAJUK'> = {
  'BNBC-2020': 'BNBC',
  'RAJUK-DAP/Bidhimala': 'RAJUK',
}

interface PackYaml {
  source: string
  rules: Array<{
    id: string
    title: string
    parameters: string[]
    logic: string
    severity: string
    confidence_basis: string
    citation: string
    remediation: string
    verify_flag?: boolean
  }>
}

export function parsePack(yamlText: string): Rule[] {
  const pack = parseYaml(yamlText) as PackYaml
  return pack.rules.map((row) => ({
    id: row.id,
    source: pack.source,
    title: row.title,
    parameters: row.parameters,
    logic: row.logic,
    severity: row.severity,
    confidenceBasis: row.confidence_basis,
    citation: row.citation,
    remediation: row.remediation,
    verifyFlag: row.verify_flag ?? false,
  }))
}

/**
 * Python-ish → JS. Handles exactly the grammar the packs use:
 * one-level `X if C else Y`, `and/or/not`, `True/False`, list literals
 * (same syntax), and helper calls. Packs are repo-controlled data — same
 * trust level as code.
 */
export function transpileLogic(logic: string): string {
  let js = logic
    .replace(/\bTrue\b/g, 'true')
    .replace(/\bFalse\b/g, 'false')
    .replace(/\bnot\s+/g, '!')
    .replace(/\band\b/g, '&&')
    .replace(/\bor\b/g, '||')
  // single conditional expression: X if C else Y  →  (C) ? (X) : (Y)
  const cond = js.match(/^(.*?)\s+if\s+(.*?)\s+else\s+(.*)$/)
  if (cond) js = `(${cond[2]}) ? (${cond[1]}) : (${cond[3]})`
  return js
}

function consistency(values: unknown[], tolerance = 0.05): boolean {
  const nums = values.map(Number)
  const lo = Math.min(...nums)
  const hi = Math.max(...nums)
  return hi === 0 || (hi - lo) / Math.max(Math.abs(hi), 1e-9) <= tolerance
}

function evalLogic(logic: string, names: Record<string, unknown>): boolean {
  const scope = {
    ...names,
    param_present: (n: string) => n in names && Boolean(names[n]),
    consistency,
  }
  // non-strict Function body so `with` is allowed; packs are trusted repo data
  const fn = new Function('scope', `with (scope) { return (${transpileLogic(logic)}) }`)
  return Boolean(fn(scope))
}

export function evaluateRules(rules: Rule[], params: ExtractedParam[]): Finding[] {
  const confirmed: Record<string, unknown> = {}
  const crops: Record<string, string | null> = {}
  for (const p of params) {
    if (p.confirmed) {
      confirmed[p.param] = p.value
      if (p.sourceCrop) crops[p.param] = p.sourceCrop
    }
  }

  return rules.map((rule) => {
    const regime = REGIME[rule.source]
    const missing = rule.parameters.filter((n) => !(n in confirmed))
    const crop = rule.parameters.map((n) => crops[n]).find(Boolean) ?? null

    if (missing.length) {
      return {
        ruleId: rule.id,
        bucket: 'needs_verification' as const,
        severity: rule.severity,
        confidence: 0.0,
        reason: `Cannot evaluate — input missing or unconfirmed: ${missing.join(', ')}.`,
        citation: rule.citation,
        regime,
        inputsUsed: Object.fromEntries(
          rule.parameters.filter((n) => n in confirmed).map((n) => [n, confirmed[n]]),
        ),
        sheetLocation: crop,
        remediation: rule.remediation,
        verifyFlag: rule.verifyFlag,
      }
    }

    const passed = evalLogic(rule.logic, confirmed)
    const inputsUsed = Object.fromEntries(rule.parameters.map((n) => [n, confirmed[n]]))

    let bucket: Bucket
    let reason: string
    if (passed) {
      bucket = 'appears_compliant'
      reason = `${rule.title}: appears compliant on confirmed inputs (not a certification).`
    } else {
      bucket = rule.verifyFlag ? 'needs_verification' : 'likely_violation'
      reason = `${rule.title}: check failed on confirmed inputs.`
      if (rule.verifyFlag) {
        reason +=
          ' Threshold is [VERIFY] (2025/2026 rules in flux) — expert must confirm the value before relying on this.'
      }
    }

    const confidences = params
      .filter((p) => p.confirmed && rule.parameters.includes(p.param))
      .map((p) => p.confidence)

    return {
      ruleId: rule.id,
      bucket,
      severity: rule.severity,
      confidence: confidences.length ? Math.min(...confidences) : 1.0,
      reason,
      citation: rule.citation,
      regime,
      inputsUsed,
      sheetLocation: crop,
      remediation: rule.remediation,
      verifyFlag: rule.verifyFlag,
    }
  })
}
