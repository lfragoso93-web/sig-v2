import { describe, expect, it } from 'vitest'
import { formatValue } from './AssetComparisonPage'

describe('AssetComparisonPage value formatting', () => {
  it('preserves precision for low-priced assets', () => {
    expect(formatValue(0.00000001)).toBe('0,00000001')
    expect(formatValue(0.0000000001)).toBe('0,0000000001')
  })

  it('keeps fundamental values readable with significant digit formatting', () => {
    expect(formatValue(1.234567891)).toBe('1,2345679')
  })
})
