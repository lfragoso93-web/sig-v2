import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import CorporateEventReviewPanel from './CorporateEventReviewPanel'
import { corporateEventReviewService } from '@/services/corporateEventReviewService'

vi.mock('@/services/corporateEventReviewService', () => ({
  corporateEventReviewService: {
    list: vi.fn(),
    evidence: vi.fn(),
    projectionPlan: vi.fn(),
    review: vi.fn(),
  },
}))

const event = {
  id: 41,
  asset_id: 7,
  ticker: 'PETR4',
  event_type: 'DESDOBRAMENTO',
  effective_date: '2026-07-01',
  quantity_factor: '2.000000000000',
  source_provider: 'brapi',
  source_event_id: 'brapi-41',
  reconciliation_status: 'CONFLICT',
  status: 'DISCOVERED',
  is_canonical: false,
  requires_review: true,
  review_reason: 'fontes divergem para o mesmo evento',
  reviewed_at: null,
  reviewed_by_user_id: null,
  review_note: null,
}

function renderPanel() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={client}>
      <CorporateEventReviewPanel />
    </QueryClientProvider>,
  )
}

describe('CorporateEventReviewPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(corporateEventReviewService.list).mockResolvedValue({
      items: [event],
      total: 1,
      page: 1,
      page_size: 20,
    })
    vi.mocked(corporateEventReviewService.review).mockResolvedValue({
      ...event,
      status: 'VALIDATED',
      reconciliation_status: 'MANUALLY_VALIDATED',
      is_canonical: true,
      requires_review: false,
      reviewed_at: '2026-07-31T12:00:00Z',
      reviewed_by_user_id: 1,
      review_note: 'Conferido em documento oficial.',
    })
    vi.mocked(corporateEventReviewService.evidence).mockResolvedValue({
      selected_event_id: 41,
      reconciliation_group_hash: 'group-41',
      economic_effect: 'DESTINATION_ASSET_EXCHANGE',
      terms_complete: true,
      automatic_application_supported: false,
      missing_terms: [],
      destination_resolution_status: 'RESOLVED',
      destination_asset_id: 8,
      destination_ticker: 'NEW3',
      destination_candidate_ids: [],
      evidences: [
        { ...event, record_date: null, ex_date: null, payment_date: null, cash_component: null, subscription_price: null, destination_cost_allocation: null, quantity_step: null, fractional_settlement_price: null, cash_treatment: null, currency: 'BRL', isin_code: null, destination_isin_code: null, raw_metadata: { factor: 2 } },
        { ...event, id: 42, source_provider: 'yahoo', source_event_id: 'yahoo-42', quantity_factor: '3.000000000000', record_date: null, ex_date: null, payment_date: null, cash_component: null, subscription_price: null, destination_cost_allocation: null, quantity_step: null, fractional_settlement_price: null, cash_treatment: null, currency: 'BRL', isin_code: null, destination_isin_code: null, raw_metadata: { factor: 3 } },
      ],
      comparisons: [
        { field: 'event_type', values: { '41': 'DESDOBRAMENTO', '42': 'DESDOBRAMENTO' }, divergent: false },
        { field: 'quantity_factor', values: { '41': '2.000000000000', '42': '3.000000000000' }, divergent: true },
      ],
    })
    vi.mocked(corporateEventReviewService.projectionPlan).mockResolvedValue({
      event_id: 41,
      source_asset_id: 7,
      destination_asset_id: 8,
      source_quantity_before: '100',
      source_quantity_after: '0',
      destination_quantity_delta: '50',
      destination_fractional_quantity: '0',
      total_cost_before: '2500',
      allocated_source_cost: '0',
      allocated_destination_cost: '2500',
      cash_component_total: '0',
      cash_treatment: null,
      executable: true,
      blocking_reasons: [],
    })
  })

  it('requires a justification and confirms conflict approval', async () => {
    renderPanel()

    expect(await screen.findByText('PETR4')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /aprovar/i }))

    await screen.findByRole('dialog', { name: /aprovar PETR4/i })
    expect(screen.getByText(/concorrentes do mesmo grupo/i)).toBeTruthy()
    const confirm = screen.getByRole('button', {
      name: /confirmar aprovação/i,
    }) as HTMLButtonElement
    expect(confirm.disabled).toBe(true)

    fireEvent.change(screen.getByLabelText('Justificativa da revisão'), {
      target: { value: 'Conferido em documento oficial.' },
    })
    expect(confirm.disabled).toBe(false)
    fireEvent.click(confirm)

    await waitFor(() => {
      expect(corporateEventReviewService.review).toHaveBeenCalledWith(
        41,
        'APPROVE',
        'Conferido em documento oficial.',
      )
    })
    expect(await screen.findByText(/revisado com sucesso/i)).toBeTruthy()
  })

  it('compares provider evidence and exposes raw payloads', async () => {
    renderPanel()
    expect(await screen.findByText('PETR4')).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: /evidências/i }))

    expect(await screen.findByRole('dialog', { name: /evidências de PETR4/i })).toBeTruthy()
    expect(await screen.findByText('Fator de quantidade')).toBeTruthy()
    expect(screen.getByText('divergente')).toBeTruthy()
    expect(screen.getByText(/Payload bruto · yahoo/i)).toBeTruthy()
    expect(corporateEventReviewService.evidence).toHaveBeenCalledWith(41)
  })

  it('simulates an exchange without submitting an execution', async () => {
    renderPanel()
    expect(await screen.findByText('PETR4')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /evidências/i }))
    expect(await screen.findByText('Simulador econômico')).toBeTruthy()

    fireEvent.change(screen.getByLabelText('Quantidade na origem'), { target: { value: '100' } })
    fireEvent.change(screen.getByLabelText('Custo total atual'), { target: { value: '2500' } })
    fireEvent.click(screen.getByRole('button', { name: /simular projeção/i }))

    expect(await screen.findByText('Quantidade recebida')).toBeTruthy()
    expect(screen.getByText('Completo')).toBeTruthy()
    expect(corporateEventReviewService.projectionPlan).toHaveBeenCalledWith(41, '100', '2500')
    expect(corporateEventReviewService.review).not.toHaveBeenCalled()
  })
})
