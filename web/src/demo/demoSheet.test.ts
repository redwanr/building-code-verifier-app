import { describe, expect, test } from 'vitest'

import { DEMO_SHEET, demoParams } from './demoSheet'

describe('demo sheet fixture', () => {
  test('ports all 20 mock params with python values and confidences', () => {
    const params = demoParams()
    expect(params).toHaveLength(20)
    const byName = Object.fromEntries(params.map((p) => [p.param, p]))
    expect(byName['claimed_far'].value).toBe(4.2)
    expect(byName['claimed_far'].confidence).toBe(0.62) // flagged (<0.7)
    expect(byName['num_exit_stairs'].value).toBe(1)
    expect(byName['parking_count_on_plan'].value).toBe(6) // mismatch vs table 8
    expect(byName['has_fire_hydrant_standpipe'].value).toBe(false)
  })

  test('flagged params (<0.7) start unconfirmed, rest confirmed', () => {
    for (const p of demoParams()) {
      expect(p.confirmed, p.param).toBe(p.confidence >= 0.7)
    }
  })

  test('every param has a bbox inside the sheet canvas', () => {
    for (const p of demoParams()) {
      const [x0, y0, x1, y1] = p.bbox!
      expect(x0, p.param).toBeGreaterThanOrEqual(0)
      expect(y0, p.param).toBeGreaterThanOrEqual(0)
      expect(x1, p.param).toBeLessThanOrEqual(DEMO_SHEET.width)
      expect(y1, p.param).toBeLessThanOrEqual(DEMO_SHEET.height)
      expect(x1).toBeGreaterThan(x0)
      expect(y1).toBeGreaterThan(y0)
    }
  })

  test('sheet is a valid svg data url and marked synthetic', () => {
    expect(DEMO_SHEET.svg).toContain('<svg')
    expect(DEMO_SHEET.svg).toContain('SYNTHETIC DEMO')
  })
})
