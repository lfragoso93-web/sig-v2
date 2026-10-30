import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import MetasPage from './MetasPage'
import type { Goal } from '@/hooks/useGoals'
import type { ClassTargetRow } from '@/hooks/useClassTargets'

let mockSelectedPortfolioId: number | null = 10

vi.mock('@/store/appStore', () => ({
  useAppStore: (selector: any) =>
    selector({
      selectedPortfolioId: mockSelectedPortfolioId,
    }),
}))

const mockGoals: Goal[] = [
  {
    id: 1,
    portfolio_id: 10,
    goal_type: 'PATRIMONIO',
    name: 'Meta R$ 1 Milhão',
    target_value: 1000000.0,
    current_value: 500000.0,
    base_value: 100000.0,
    monthly_contribution: 5000.0,
    target_date: '2030-12-31',
    description: 'Meta de longo prazo',
    created_at: '2026-01-01T00:00:00Z',
    progress_pct: 50.0,
    is_completed: false,
    months_to_goal: 100,
    projected_date: '2035-04-01T00:00:00Z',
  },
  {
    id: 2,
    portfolio_id: 10,
    goal_type: 'PROVENTOS',
    name: 'Renda R$ 5k/mês',
    target_value: 5000.0,
    current_value: 5000.0,
    base_value: 1000.0,
    monthly_contribution: null,
    target_date: null,
    description: 'Concluído',
    created_at: '2026-01-01T00:00:00Z',
    progress_pct: 100.0,
    is_completed: true,
    months_to_goal: 0,
    projected_date: null,
  },
]

const mockClassTargets: ClassTargetRow[] = [
  {
    asset_type: 'ACAO',
    label: 'Ações',
    target_pct: 40.0,
    current_pct: 35.0,
    delta_pct: -5.0,
    color: '#3B82F6',
  },
  {
    asset_type: 'FII',
    label: 'Fundos Imobiliários',
    target_pct: 30.0,
    current_pct: 30.0,
    delta_pct: 0.0,
    color: '#10B981',
  },
]

vi.mock('@/hooks/useGoals', () => ({
  useGoals: () => ({
    data: mockGoals,
    isLoading: false,
    isError: false,
  }),
  useCreateGoal: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
  useUpdateGoal: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
  useDeleteGoal: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
}))

vi.mock('@/hooks/useClassTargets', () => ({
  useClassTargets: () => ({
    data: mockClassTargets,
    isLoading: false,
  }),
}))

function renderComponent() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <MetasPage />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('MetasPage', () => {
  it('renders goals and class allocation targets section', () => {
    mockSelectedPortfolioId = 10
    renderComponent()

    expect(screen.getByText('Nova meta')).toBeDefined()
    expect(screen.getByText('Metas ativas')).toBeDefined()

    // Class allocation targets section
    expect(
      screen.getByText('Alocação Alvo por Classe de Ativo')
    ).toBeDefined()
    expect(screen.getByText('Ações')).toBeDefined()
    expect(screen.getByText('Fundos Imobiliários')).toBeDefined()

    // Link to AnalisePage
    const analiseLink = screen.getByRole('link', {
      name: /Análise & Rebalanceamento/i,
    })
    expect(analiseLink).toBeDefined()
    expect(analiseLink.getAttribute('href')).toBe('/carteira/analise')

    // Goals cards
    expect(screen.getByText('Meta R$ 1 Milhão')).toBeDefined()
    expect(screen.getByText('Renda R$ 5k/mês')).toBeDefined()
    expect(screen.getByText('Em andamento (1)')).toBeDefined()
    expect(screen.getByText('Concluídas (1)')).toBeDefined()
  })

  it('renders empty state when no portfolio is selected', () => {
    mockSelectedPortfolioId = null
    renderComponent()

    expect(screen.getByText('Nenhuma carteira selecionada')).toBeDefined()
  })
})
