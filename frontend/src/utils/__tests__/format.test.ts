import { describe, it, expect } from 'vitest'
import { formatDate, formatDateShort, formatBRL, fmtMoney, formatPercent } from '../format'

describe('format utils - Date formatting without timezone shifts', () => {
  it('formats ISO date strings as DD/MM/YYYY exactly without timezone shift', () => {
    expect(formatDate('2026-11-04')).toBe('04/11/2026')
    expect(formatDate('2026-01-01')).toBe('01/01/2026')
    expect(formatDate('2026-12-31')).toBe('31/12/2026')
  })

  it('formats ISO datetime strings preserving date part', () => {
    expect(formatDate('2026-11-04T00:00:00.000Z')).toBe('04/11/2026')
    expect(formatDate('2026-11-04T23:59:59.000Z')).toBe('04/11/2026')
  })

  it('handles empty or null values gracefully', () => {
    expect(formatDate('')).toBe('-')
    expect(formatDateShort('')).toBe('-')
  })

  it('formats short month/year safely', () => {
    const formatted = formatDateShort('2026-11-04')
    expect(formatted.toLowerCase()).toContain('nov')
    expect(formatted).toContain('26')
  })

  it('formats money and percent correctly', () => {
    expect(fmtMoney(123.45, 'BRL')).toBe(formatBRL(123.45))
    expect(fmtMoney(50, 'USD')).toContain('50.00')
    expect(formatPercent(12.5)).toContain('12,50')
  })
})
