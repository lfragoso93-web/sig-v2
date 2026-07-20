import { describe, expect, it } from 'vitest'

import type {
  ClassReconciliation,
  IntradayReconciliation,
} from '@/hooks/useReconciliation'
import {
  presentClassReconciliation,
  presentIntradayReconciliation,
} from './PortfolioReconciliationPanel'

const check = {
  field: 'market_value',
  expected: 100,
  observed: 99,
  difference: -1,
  tolerance: 0.01,
  is_reconciled: false,
}

describe('PortfolioReconciliationPanel presentations', () => {
  it('declara sucesso de classe somente quando o backend marcou comparável e reconciliado', () => {
    const result = presentClassReconciliation({
      is_reconciled: true,
      is_comparable: true,
      status: 'evaluated',
      unsupported_asset_types: [],
      snapshot_date: '2026-07-18',
      checks: [{ ...check, observed: 100, difference: 0, is_reconciled: true }],
    })

    expect(result.tone).toBe('success')
    expect(result.title).toBe('Fechamento reconciliado')
  })

  it('mantém ausência de snapshots na apresentação neutra', () => {
    const result = presentClassReconciliation({
      is_reconciled: null,
      is_comparable: false,
      status: 'missing_class_snapshots',
      unsupported_asset_types: [],
      snapshot_date: null,
      checks: [],
    })

    expect(result.tone).toBe('neutral')
    expect(result.title).toBe('Comparação ainda indisponível')
    expect(result.failedFields).toEqual([])
  })

  it('usa exclusivamente os checks falhos entregues pelo backend de classes', () => {
    const data: ClassReconciliation = {
      is_reconciled: false,
      is_comparable: true,
      status: 'evaluated',
      unsupported_asset_types: [],
      snapshot_date: '2026-07-18',
      checks: [
        check,
        { ...check, field: 'cost_basis', is_reconciled: true },
      ],
    }

    expect(presentClassReconciliation(data).failedFields).toEqual(['market_value'])
  })

  it('preserva os campos divergentes do contrato intradiário sem recalcular valores', () => {
    const data: IntradayReconciliation = {
      portfolio_id: 46,
      valuation_mode: 'intraday',
      valuation_updated_at: '2026-07-18T15:00:00Z',
      snapshot_evaluated: false,
      money_tolerance: 0.01,
      is_reconciled: false,
      failed_fields: ['positions.total_patrimonio'],
      checks: [check],
      source_contracts: ['summary.v2', 'positions', 'asset-distribution'],
      positions_groups_count: 2,
      distribution_classes_count: 2,
    }

    const result = presentIntradayReconciliation(data)
    expect(result.tone).toBe('error')
    expect(result.failedFields).toEqual(['positions.total_patrimonio'])
  })
})
