import type { PropsWithChildren } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import api from '@/services/api'
import {
  parseClassReconciliation,
  parseIntradayReconciliation,
  useIntradayReconciliation,
} from './useReconciliation'

vi.mock('@/services/api', () => ({
  default: {
    get: vi.fn(),
  },
}))

const check = {
  field: 'market_value',
  expected: 100,
  observed: 100,
  difference: 0,
  tolerance: 0.01,
  is_reconciled: true,
}

const classPayload = {
  is_reconciled: true,
  is_comparable: true,
  status: 'evaluated',
  unsupported_asset_types: [],
  snapshot_date: '2026-07-18',
  checks: [check],
}

const intradayPayload = {
  portfolio_id: 46,
  valuation_mode: 'intraday',
  valuation_updated_at: '2026-07-18T15:00:00Z',
  snapshot_evaluated: false,
  money_tolerance: 0.01,
  is_reconciled: true,
  failed_fields: [],
  checks: [check],
  source_contracts: ['summary.v2', 'positions', 'asset-distribution'],
  positions_groups_count: 2,
  distribution_classes_count: 2,
}

beforeEach(() => {
  vi.clearAllMocks()
})

function createWrapper() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return function Wrapper({ children }: PropsWithChildren) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>
  }
}

describe('reconciliation contracts', () => {
  it('aceita snapshots por classe somente com estado conhecido', () => {
    expect(parseClassReconciliation(classPayload).is_comparable).toBe(true)
    expect(() => parseClassReconciliation({
      ...classPayload,
      status: 'comparacao_local',
    })).toThrow('status')
  })

  it('preserva estado não comparável sem converter null em sucesso', () => {
    const parsed = parseClassReconciliation({
      ...classPayload,
      is_reconciled: null,
      is_comparable: false,
      status: 'missing_class_snapshots',
      snapshot_date: null,
      checks: [],
    })

    expect(parsed.is_comparable).toBe(false)
    expect(parsed.is_reconciled).toBeNull()
  })

  it('exige que a reconciliação intradiária não avalie snapshot', () => {
    expect(parseIntradayReconciliation(intradayPayload).snapshot_evaluated).toBe(false)
    expect(() => parseIntradayReconciliation({
      ...intradayPayload,
      snapshot_evaluated: true,
    })).toThrow('snapshot_evaluated')
  })

  it('rejeita diferenças recalculadas ou campos extras fora do backend', () => {
    expect(() => parseIntradayReconciliation({
      ...intradayPayload,
      diferenca_frontend: 0,
    })).toThrow('diferenca_frontend')
  })

  it('consulta o endpoint intradiário canônico', async () => {
    vi.mocked(api.get).mockResolvedValue({ data: intradayPayload })

    const { result } = renderHook(() => useIntradayReconciliation(46), {
      wrapper: createWrapper(),
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(api.get).toHaveBeenCalledWith('/portfolios/46/reconciliation/intraday')
    expect(result.current.data?.source_contracts).toEqual(intradayPayload.source_contracts)
  })
})
