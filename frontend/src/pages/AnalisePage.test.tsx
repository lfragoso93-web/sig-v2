import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import AnalisePage from './AnalisePage'
import type { PortfolioConsolidatedAnalysisResponse } from '@/hooks/usePortfolioAnalysis'
import type { PortfolioAiAnalysisResponse, ContributionSimulationResponse } from '@/hooks/usePortfolioAiAnalysis'

const mockAnalysis: PortfolioConsolidatedAnalysisResponse = {
  portfolio_id: 15,
  portfolio_name: 'Carteira Principal',
  reference_date: '2026-10-21',
  total_value: 100000.0,
  overall_health_score: 85,
  max_divergence_class: 'Ações',
  classes_analyzed_count: 2,
  rebalance_priority_classes: ['Ações'],
  classes: [
    {
      asset_type: 'ACAO',
      label: 'Ações',
      health_score: 80,
      allocation: {
        current_value: 30000.0,
        current_weight_pct: 30.0,
        target_weight_pct: 40.0,
        target_value: 40000.0,
        gap_weight_pct: -10.0,
        gap_value: 10000.0,
        rebalance_action: 'buy',
        suggested_action_label: 'Aporte sugerido de R$ 10.000,00 para convergir à meta de 40.0%',
      },
      concentration: {
        asset_count: 3,
        top_asset: {
          ticker: 'PETR4',
          name: 'Petrobras',
          current_value: 15000.0,
          weight_in_class_pct: 50.0,
          weight_in_portfolio_pct: 15.0,
        },
        hhi_score: 3500.0,
        risk_level: 'warning',
        risk_label: 'Atenção',
        status_message: 'PETR4 representa 50.0% do patrimônio desta classe.',
      },
      income: {
        is_applicable: true,
        total_proventos: 1500.0,
        weighted_dy_pct: 5.0,
        top_income_asset: 'PETR4',
        status_label: 'R$ 1.500,00 recebidos',
      },
      fixed_income: {
        is_applicable: false,
        cdi_allocation_pct: null,
        ipca_allocation_pct: null,
        pre_allocation_pct: null,
        maturing_next_12m_value: null,
        maturing_next_12m_pct: null,
      },
      key_findings: ['Aporte sugerido para atingir a meta'],
    },
    {
      asset_type: 'FII',
      label: 'FIIs',
      health_score: 90,
      allocation: {
        current_value: 70000.0,
        current_weight_pct: 70.0,
        target_weight_pct: 60.0,
        target_value: 60000.0,
        gap_weight_pct: 10.0,
        gap_value: -10000.0,
        rebalance_action: 'reduce',
        suggested_action_label: 'Excesso de R$ 10.000,00 (10.0% acima da meta)',
      },
      concentration: {
        asset_count: 5,
        top_asset: {
          ticker: 'HGLG11',
          name: 'CSHG Logística',
          current_value: 20000.0,
          weight_in_class_pct: 28.5,
          weight_in_portfolio_pct: 20.0,
        },
        hhi_score: 2200.0,
        risk_level: 'balanced',
        risk_label: 'Equilibrado',
        status_message: 'Distribuição equilibrada entre os fundos.',
      },
      income: {
        is_applicable: true,
        total_proventos: 4200.0,
        weighted_dy_pct: 7.2,
        top_income_asset: 'HGLG11',
        status_label: 'R$ 4.200,00 recebidos',
      },
      fixed_income: {
        is_applicable: false,
        cdi_allocation_pct: null,
        ipca_allocation_pct: null,
        pre_allocation_pct: null,
        maturing_next_12m_value: null,
        maturing_next_12m_pct: null,
      },
      key_findings: ['Excesso de R$ 10.000,00'],
    },
  ],
  provenance: {
    valuation: 'canonical intraday valuation',
    targets: 'portfolio_class_targets',
  },
}

const mockAiData: PortfolioAiAnalysisResponse = {
  portfolio_id: 15,
  portfolio_name: 'Carteira Principal',
  reference_date: '2026-10-21',
  overall_health_score: 85,
  posture_label: 'Equilibrada com foco em proventos',
  posture_summary: 'A carteira alinha geração de fluxo recorrente com potencial de valorização.',
  executive_summary: 'Carteira com patrimônio de R$ 100.000,00 e bom score de governança.',
  key_strengths: [
    'Diversificação em 2 classes de ativos com proventos ativos.',
    'Concentração controlada em FIIs.',
  ],
  attention_points: [
    'Concentração moderada de PETR4 na classe Ações.',
  ],
  rebalancing_strategy: 'Priorizar novos aportes na classe Ações para fechar o gap de 10%.',
  contribution_scenarios: [
    {
      amount: 5000.0,
      description: 'Aporte de R$ 5.000,00',
      priority_class: 'Ações',
      estimated_gap_reduction: 'Reduz o déficit de Ações em 50%',
    },
  ],
  metadata: {
    provider: 'sgi-audit-explainer-v1',
    model: 'deterministic-rule-engine',
    is_mock_or_deterministic: true,
    execution_time_ms: 12.5,
    disclaimer: 'Análise gerada por IA baseada estritamente nas métricas determinísticas.',
  },
}

const mockSimulationData: ContributionSimulationResponse = {
  portfolio_id: 15,
  contribution_amount: 5000.0,
  strategy: 'proventos',
  current_total_value: 100000.0,
  projected_total_value: 105000.0,
  suggested_allocations: [
    {
      asset_type: 'ACAO',
      label: 'Ações',
      current_value: 30000.0,
      current_weight_pct: 30.0,
      target_weight_pct: 40.0,
      allocated_amount: 5000.0,
      projected_value: 35000.0,
      projected_weight_pct: 33.3,
      action_explanation: 'Recebe R$ 5.000,00 para aproximar da meta.',
    },
  ],
  suggested_assets: [
    {
      ticker: 'BBAS3',
      name: 'Banco do Brasil ON',
      asset_type: 'ACAO',
      current_quantity: 100,
      current_price: 28.0,
      current_value: 2800.0,
      suggested_amount: 5000.0,
      suggested_quantity: 178.5714,
      reason: 'Foco em Proventos: histórico consistente de dividendos.',
    },
  ],
  overall_impact_summary: 'Aporte prioriza Ações e foco em proventos.',
  metadata: {
    provider: 'sgi-audit-explainer-v1',
    model: 'deterministic-rule-engine',
    is_mock_or_deterministic: true,
    execution_time_ms: 10.0,
    disclaimer: 'Deterministic simulation.',
  },
}

const mockMutateSimulate = vi.fn()

vi.mock('@/store/appStore', () => ({
  useAppStore: (selector?: (state: any) => any) => {
    const state = {
      selectedPortfolioId: 15,
      setSelectedPortfolioId: vi.fn(),
    }
    return selector ? selector(state) : state
  },
}))

vi.mock('@/hooks/usePortfolios', () => ({
  usePortfolios: () => ({
    data: [{ id: 15, name: 'Carteira Principal' }],
    isLoading: false,
  }),
}))

let currentAnalysisData: PortfolioConsolidatedAnalysisResponse | null = mockAnalysis
let currentSimulationData: ContributionSimulationResponse | null = null

vi.mock('@/hooks/usePortfolioAnalysis', async () => {
  const actual = await vi.importActual<object>('@/hooks/usePortfolioAnalysis')
  return {
    ...actual,
    usePortfolioAnalysis: () => ({
      data: currentAnalysisData,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    }),
  }
})

vi.mock('@/hooks/usePortfolioAiAnalysis', async () => {
  const actual = await vi.importActual<object>('@/hooks/usePortfolioAiAnalysis')
  return {
    ...actual,
    usePortfolioAiAnalysis: () => ({
      data: mockAiData,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    }),
    useSimulateContribution: () => ({
      mutate: mockMutateSimulate,
      data: currentSimulationData,
      isPending: false,
    }),
    useAskPortfolioAi: () => ({
      mutate: vi.fn(),
      data: null,
      isPending: false,
    }),
  }
})

function renderWithProviders() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <AnalisePage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('AnalisePage determinismo e inteligência artificial (Issues #360 e #361)', () => {
  it('renders overall health score and AI executive summary tab', () => {
    currentAnalysisData = mockAnalysis
    currentSimulationData = null
    renderWithProviders()

    expect(screen.getByText(/Análise de Carteira/i)).toBeDefined()
    expect(screen.getByText('85/100')).toBeDefined()
    expect(screen.getByText(/Diagnóstico determinístico por classe/i)).toBeDefined()
    expect(screen.getByText('Síntese Executiva & Postura Estratégica')).toBeDefined()
    expect(screen.getByText('Equilibrada com foco em proventos')).toBeDefined()
    expect(screen.getByText('Pontos Fortes Observados')).toBeDefined()
    expect(screen.getByText('Simulador Inteligente de Próximo Aporte')).toBeDefined()
    expect(screen.getByText('Acúmulo de Patrimônio')).toBeDefined()
    expect(screen.getByText('Proventos & Renda')).toBeDefined()
    expect(screen.getByText('Performance & Crescimento')).toBeDefined()
  })

  it('renders class breakdown cards when switching to classes tab', () => {
    currentAnalysisData = mockAnalysis
    currentSimulationData = null
    renderWithProviders()

    const classesTabBtn = screen.getByRole('button', { name: /Detalhamento por Classes/i })
    fireEvent.click(classesTabBtn)

    expect(screen.getAllByText('Ações').length).toBeGreaterThan(0)
    expect(screen.getAllByText('FIIs').length).toBeGreaterThan(0)
    expect(screen.getByText('Aporte sugerido de R$ 10.000,00 para convergir à meta de 40.0%')).toBeDefined()
    expect(screen.getByText('Excesso de R$ 10.000,00 (10.0% acima da meta)')).toBeDefined()
    expect(screen.getByText(/Proveniência Canônica dos Dados:/i)).toBeDefined()
  })

  it('allows selecting strategy and triggers simulation with strategy payload (Item 6)', () => {
    currentAnalysisData = mockAnalysis
    currentSimulationData = null
    mockMutateSimulate.mockClear()
    renderWithProviders()

    const proventosBtn = screen.getByText('Proventos & Renda')
    fireEvent.click(proventosBtn)

    expect(mockMutateSimulate).toHaveBeenCalledWith({
      amount: 5000,
      strategy: 'proventos',
    })
  })

  it('renders recommended assets table when simulation returns suggested_assets (Item 6)', () => {
    currentAnalysisData = mockAnalysis
    currentSimulationData = mockSimulationData
    renderWithProviders()

    expect(screen.getByText(/Ativos Recomendados para Aporte/i)).toBeDefined()
    expect(screen.getByText('BBAS3')).toBeDefined()
    expect(screen.getByText('Banco do Brasil ON')).toBeDefined()
    expect(screen.getByText('Foco em Proventos: histórico consistente de dividendos.')).toBeDefined()
    expect(screen.getAllByText(/\+\s*R\$\s*5\.000,00/).length).toBeGreaterThan(0)
  })

  it('renders empty state banner with CTA to distribution settings when classes is empty (Item 7)', () => {
    currentAnalysisData = {
      ...mockAnalysis,
      classes: [],
      classes_analyzed_count: 0,
    }
    currentSimulationData = null
    renderWithProviders()

    expect(screen.getByText(/Sua carteira ainda não possui metas de distribuição cadastradas/i)).toBeDefined()
    expect(screen.getByText('Definir Metas')).toBeDefined()
  })
})
