import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { ProventoItem } from '@/services/proventosService'
import MeusProventosTable from './MeusProventosTable'

function item(overrides: Partial<ProventoItem> = {}): ProventoItem {
  return {
    id: 1,
    ticker: 'PETR4',
    asset_type: 'ACAO',
    dividend_type: 'DIVIDENDO',
    is_cash: true,
    status: 'RECEBIDO',
    record_date: '2026-01-09',
    ex_date: '2026-01-12',
    payment_date: '2026-01-30',
    approved_on: '2026-01-05',
    quantity: 10,
    value_per_unit: 1.25,
    gross_value_per_unit: null,
    factor: null,
    complete_factor: null,
    total_value: 12.5,
    net_value: 12.5,
    isin_code: null,
    asset_issued: null,
    related_to: null,
    remarks: null,
    ...overrides,
  }
}

describe('MeusProventosTable', () => {
  it('renders the empty state', () => {
    render(<MeusProventosTable data={[]} />)

    expect(screen.getByText('Sem eventos no período.')).toBeTruthy()
  })

  it('uses the canonical is_cash flag for non-monetary events', () => {
    render(
      <MeusProventosTable
        data={[item({
          dividend_type: 'BONIFICACAO',
          is_cash: false,
          factor: 0.1,
          total_value: 999,
          net_value: 999,
        })]}
      />,
    )

    expect(screen.getAllByText('Não soma').length).toBeGreaterThan(0)
    expect(screen.queryByText('R$ 999,00')).toBeNull()
  })

  it.each([
    ['PENDENTE', 'Pendente'],
    ['CANCELADO', 'Cancelado'],
  ] as const)('renders %s with its own label', (status, label) => {
    render(<MeusProventosTable data={[item({ status })]} />)

    expect(screen.getAllByText(label).length).toBeGreaterThan(0)
  })
})
