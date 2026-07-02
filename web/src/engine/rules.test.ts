/**
 * Parity suite ported from tests/test_rules.py — the TS engine must produce
 * the same buckets as the Python engine for identical inputs (PRD §7, FR-9).
 */
import { readFileSync, readdirSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, test } from 'vitest'

import { evaluateRules, parsePack, type ExtractedParam, type Rule } from './rules'

const PACK_DIR = join(dirname(fileURLToPath(import.meta.url)), '../../../rule_packs')

function loadPacks(): Rule[] {
  return readdirSync(PACK_DIR)
    .filter((f) => f.endsWith('.yaml'))
    .sort()
    .flatMap((f) => parsePack(readFileSync(join(PACK_DIR, f), 'utf8')))
}

function param(name: string, value: unknown, confirmed = true, confidence = 0.95): ExtractedParam {
  return {
    param: name, value, unit: '', confidence,
    sourcePage: 1, sourceCrop: null, confirmed,
  }
}

function makeRule(overrides: Partial<Rule> = {}): Rule {
  return {
    id: 'TEST-001',
    source: 'BNBC-2020',
    title: 'Test rule',
    parameters: ['a'],
    logic: 'a > 5',
    severity: 'High',
    confidenceBasis: 'test',
    citation: 'BNBC-2020 test clause',
    remediation: 'fix it',
    verifyFlag: false,
    ...overrides,
  }
}

describe('pack loading', () => {
  test('returns rules from yaml', () => {
    const rules = loadPacks()
    const ids = new Set(rules.map((r) => r.id))
    expect(ids).toContain('BNBC-EGRESS-001')
    expect(ids).toContain('RAJUK-PARKING-006-RATIO')
    const egress = rules.find((r) => r.id === 'BNBC-EGRESS-001')!
    expect(egress.source).toBe('BNBC-2020')
    expect(egress.severity).toBe('Critical')
    expect(egress.verifyFlag).toBe(true)
  })

  test('rules belong to exactly one source', () => {
    for (const rule of loadPacks()) {
      expect(['BNBC-2020', 'RAJUK-DAP/Bidhimala']).toContain(rule.source)
    }
  })
})

describe('evaluation buckets', () => {
  test('passing rule appears compliant', () => {
    const findings = evaluateRules([makeRule()], [param('a', 10)])
    expect(findings[0].bucket).toBe('appears_compliant')
  })

  test('failing rule likely violation', () => {
    const findings = evaluateRules([makeRule()], [param('a', 3)])
    expect(findings[0].bucket).toBe('likely_violation')
  })

  test('failing verify_flag rule caps at needs_verification', () => {
    const findings = evaluateRules([makeRule({ verifyFlag: true })], [param('a', 3)])
    expect(findings[0].bucket).toBe('needs_verification')
  })

  test('passing verify_flag rule still appears compliant', () => {
    const findings = evaluateRules([makeRule({ verifyFlag: true })], [param('a', 10)])
    expect(findings[0].bucket).toBe('appears_compliant')
  })
})

describe('FR-9: never silently pass', () => {
  test('missing required param cannot evaluate', () => {
    const findings = evaluateRules([makeRule()], [])
    const f = findings[0]
    expect(f.bucket).toBe('needs_verification')
    expect(f.reason.toLowerCase()).toContain('cannot evaluate')
    expect(f.reason).toContain('a')
  })

  test('unconfirmed param treated as missing', () => {
    const findings = evaluateRules([makeRule()], [param('a', 10, false)])
    expect(findings[0].bucket).toBe('needs_verification')
    expect(findings[0].reason.toLowerCase()).toContain('cannot evaluate')
  })
})

describe('helpers in the eval namespace', () => {
  test('param_present helper', () => {
    const rule = makeRule({ parameters: ['a'], logic: "param_present('a')" })
    const findings = evaluateRules([rule], [param('a', true)])
    expect(findings[0].bucket).toBe('appears_compliant')
  })

  test('consistency within tolerance', () => {
    const rule = makeRule({ parameters: ['x', 'y'], logic: 'consistency([x, y])' })
    const findings = evaluateRules([rule], [param('x', 100.0), param('y', 102.0)])
    expect(findings[0].bucket).toBe('appears_compliant')
  })

  test('consistency flags mismatch', () => {
    const rule = makeRule({ parameters: ['x', 'y'], logic: 'consistency([x, y])' })
    const findings = evaluateRules([rule], [param('x', 100.0), param('y', 130.0)])
    expect(findings[0].bucket).toBe('likely_violation')
  })
})

describe('real seed rules against G+9-shaped params', () => {
  const G9 = [
    param('num_storeys', 10),
    param('building_height_m', 30.0),
    param('num_exit_stairs', 1),
  ]

  test('egress rule flags single stair highrise', () => {
    const rules = loadPacks().filter((r) => r.id === 'BNBC-EGRESS-001')
    const f = evaluateRules(rules, G9)[0]
    expect(f.bucket).toBe('needs_verification') // verify_flag cap
    expect(f.severity).toBe('Critical')
    expect(f.regime).toBe('BNBC')
  })

  test('egress rule passes with two stairs', () => {
    const rules = loadPacks().filter((r) => r.id === 'BNBC-EGRESS-001')
    const params = [...G9.slice(0, 2), param('num_exit_stairs', 2)]
    expect(evaluateRules(rules, params)[0].bucket).toBe('appears_compliant')
  })

  test('parking consistency rule flags mismatch', () => {
    const rules = loadPacks().filter((r) => r.id === 'RAJUK-PARKING-006-CONSISTENCY')
    expect(rules.length).toBeGreaterThan(0)
    const params = [param('parking_provided_table', 20), param('parking_count_on_plan', 14)]
    expect(evaluateRules(rules, params)[0].bucket).not.toBe('appears_compliant')
  })

  test('FAR limit rule cannot evaluate without permissible', () => {
    const rules = loadPacks().filter((r) => r.id === 'RAJUK-FAR-003-LIMIT')
    expect(rules.length).toBeGreaterThan(0)
    const f = evaluateRules(rules, [param('claimed_far', 4.2)])[0]
    expect(f.bucket).toBe('needs_verification')
    expect(f.reason.toLowerCase()).toContain('cannot evaluate')
  })

  test('every pack rule evaluates without throwing when all inputs supplied', () => {
    // transpiler must handle every logic expression actually in the packs
    for (const rule of loadPacks()) {
      const params = rule.parameters.map((p) => param(p, 1))
      expect(() => evaluateRules([rule], params), rule.id).not.toThrow()
    }
  })

  test('FIRE-002 presence logic matches python semantics', () => {
    const rules = loadPacks().filter((r) => r.id === 'BNBC-FIRE-002')
    // high-rise without fire params present -> not compliant
    const f = evaluateRules(rules, [param('building_height_m', 30)])[0]
    expect(f.bucket).not.toBe('appears_compliant')
    // low-rise -> True branch -> compliant
    const g = evaluateRules(rules, [param('building_height_m', 10)])[0]
    expect(g.bucket).toBe('appears_compliant')
  })
})

describe('finding record completeness (FR-8)', () => {
  test('records inputs and citation', () => {
    const f = evaluateRules([makeRule()], [param('a', 3)])[0]
    expect(f.ruleId).toBe('TEST-001')
    expect(f.citation).toBe('BNBC-2020 test clause')
    expect(f.regime).toBe('BNBC')
    expect(f.inputsUsed).toEqual({ a: 3 })
    expect(f.remediation).toBe('fix it')
    expect(f.confidence).toBeGreaterThanOrEqual(0)
    expect(f.confidence).toBeLessThanOrEqual(1)
  })
})
