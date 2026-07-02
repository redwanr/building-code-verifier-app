import { describe, expect, test } from 'vitest'

import type { ExtractedParam, Finding } from './rules'
import { newReport, renderHtml, renderMarkdown } from './report'

const param: ExtractedParam = {
  param: 'claimed_far', value: 4.2, unit: 'ratio', confidence: 0.62,
  sourcePage: 1, sourceCrop: null, confirmed: true, editedFrom: 4.5,
}
const finding: Finding = {
  ruleId: 'RAJUK-FAR-003-LIMIT', bucket: 'likely_violation', severity: 'High',
  confidence: 0.62, reason: 'FAR exceeds permissible.', citation: 'DAP 2025',
  regime: 'RAJUK', inputsUsed: { claimed_far: 4.2 }, sheetLocation: null,
  remediation: 'Reduce built area.', verifyFlag: false,
  userAction: 'accept', userNote: 'checked with ward office',
}

describe('report rendering', () => {
  const report = newReport(['bnbc-2020@2020-01-01'], [param], [finding])

  test('markdown carries disclaimer top and bottom, findings, audit table', () => {
    const md = renderMarkdown(report)
    expect(md.startsWith('# Permit-Sheet Code Verifier')).toBe(true)
    expect(md.match(/Decision-support only/g)!.length).toBeGreaterThanOrEqual(2)
    expect(md).toContain('RAJUK-FAR-003-LIMIT')
    expect(md).toContain('reviewer: accept')
    expect(md).toContain('| claimed_far | 4.2 |')
  })

  test('html report escapes content and keeps the non-certification notice', () => {
    const evil = newReport(['p'], [param], [{ ...finding, reason: '<script>alert(1)</script>' }])
    const html = renderHtml(evil)
    expect(html).not.toContain('<script>alert(1)')
    expect(html).toContain('&lt;script&gt;')
    expect(html).toContain('Decision-support only — not a certification.')
    expect(html).toContain('claimed_far')
  })

  test('summary counts by bucket', () => {
    expect(report.summary.likely_violation).toBe(1)
    expect(report.summary.appears_compliant).toBe(0)
  })
})
