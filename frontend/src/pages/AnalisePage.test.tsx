import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import AnalisePage from './AnalisePage'
import type { PortfolioConsolidatedAnalysisResponse } from '@/hooks/usePortfolioAnalysis'

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
        hhi_score: 1800.0,
        risk_level: 'low',
        risk_label: 'Baixo',
        status_message: 'Classe bem distribuída entre 5 ativos.',
      },
      income: {
        is_applicable: true,
        total_proventos: 4500.0,
        weighted_dy_pct: 6.4,
        top_income_asset: 'HGLG11',
        status_label: 'R$ 4.500,00 recebidos',
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

vi.mock('@/store/appStore', () => ({
  useAppStore: () => ({
    selectedPortfolioId: 15,
  }),
}))

vi.mock('@/hooks/usePortfolioAnalysis', async () => {
  const actual = await vi.importActual<object>('@/hooks/usePortfolioAnalysis')
  return {
    ...actual,
    usePortfolioAnalysis: () => ({
      data: mockAnalysis,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    }),
  }
})

describe('AnalisePage determinismo e diagnósticos por classe (Issue #360)', () => {
  it('renders overall health score and rebalance metrics', () => {
    render(
      <MemoryRouter>
        <AnalisePage />
      </MemoryRouter>,
    )

    expect(screen.getByText('Análise de Carteira')).toBeDefined()
    expect(screen.getByText('85/100')).toBeDefined()
    expect(screen.getByText('Carteira Principal · Diagnóstico determinístico por classe de ativos e rebalanceamento')).toBeDefined()
    expect(screen.getByText('Oportunidades de Rebalanceamento Identificadas')).toBeDefined()
  })

  it('renders class breakdown cards with actions and findings', () => {
    render(
      <MemoryRouter>
        <AnalisePage />
      </MemoryRouter>,
    )

    expect(screen.getAllByText('Ações').length).toBeGreaterThan(0)
    expect(screen.getAllByText('FIIs').length).toBeGreaterThan(0)
    expect(screen.getByText('Aporte sugerido de R$ 10.000,00 para convergir à meta de 40.0%')).toBeDefined()
    expect(screen.getByText('Excesso de R$ 10.000,00 (10.0% acima da meta)')).toBeDefined()
    expect(screen.getByText(/Proveniência Canônica dos Dados:/i)).toBeDefined()
  })
})
