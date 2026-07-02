/** Parse-layer parity with tests/test_extraction.py (deterministic parts). */
import { describe, expect, test } from 'vitest'

import { bestPerParam, CONFIDENCE_THRESHOLD, paramsFromResponse, validBbox } from './extract'

const SAMPLE = {
  params: [
    {
      param: 'claimed_far', value: 4.2, unit: 'ratio', confidence: 0.62,
      bbox: [100, 200, 300, 250], location_note: 'area table',
    },
    {
      param: 'num_storeys', value: 10, unit: 'count', confidence: 0.95,
      bbox: null, location_note: 'title block, building description',
    },
  ],
}

describe('paramsFromResponse', () => {
  test('confidence gate: below threshold unconfirmed, above pre-confirmed', () => {
    const params = paramsFromResponse(SAMPLE, 1, 1000, 800)
    const byName = Object.fromEntries(params.map((p) => [p.param, p]))
    expect(byName.claimed_far.value).toBe(4.2)
    expect(byName.claimed_far.confirmed).toBe(false)
    expect(byName.num_storeys.confirmed).toBe(true)
    expect(CONFIDENCE_THRESHOLD).toBe(0.7)
  })

  test('valid bbox kept, missing bbox falls back to location note', () => {
    const params = paramsFromResponse(SAMPLE, 1, 1000, 800)
    const byName = Object.fromEntries(params.map((p) => [p.param, p]))
    expect(byName.claimed_far.bbox).toEqual([100, 200, 300, 250])
    expect(byName.num_storeys.bbox).toBeNull()
    expect(byName.num_storeys.cropFallbackNote).toContain('title block')
  })

  test('garbage bbox rejected, never crashes', () => {
    expect(validBbox([5000, 5000, 6000, 6000], 1000, 800)).toBeNull()
    expect(validBbox([300, 200, 100, 250], 1000, 800)).toBeNull() // inverted
    expect(validBbox(['a', 0, 1, 1], 1000, 800)).toBeNull()
    expect(validBbox(null, 1000, 800)).toBeNull()
    expect(validBbox([100, 200, 300, 250], 1000, 800)).toEqual([100, 200, 300, 250])
  })

  test('bestPerParam keeps highest-confidence duplicate across pages', () => {
    const a = paramsFromResponse(SAMPLE, 1, 1000, 800)
    const b = paramsFromResponse(
      { params: [{ param: 'claimed_far', value: 4.5, unit: 'ratio', confidence: 0.9, bbox: null, location_note: 'p2' }] },
      2, 1000, 800,
    )
    const best = bestPerParam([...a, ...b])
    const far = best.find((p) => p.param === 'claimed_far')!
    expect(far.value).toBe(4.5)
    expect(far.sourcePage).toBe(2)
    expect(best.filter((p) => p.param === 'claimed_far')).toHaveLength(1)
  })
})
