import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import BootstrapPanel, { type BootstrapStatusResponse } from './BootstrapPanel'
import api from '@/services/api'

vi.mock('@/services/api', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}))

const mockStatusResponse: BootstrapStatusResponse = {
  state: 'ready',
  schema_version: 'system-bootstrap.v4',
  started_at: '2026-10-21T10:00:00Z',
  finished_at: '2026-10-21T10:05:00Z',
  failed_stage: null,
  detail: 'bootstrap parcial concluído; certificação operacional pendente',
  certified_for_real_data: false,
  bootstrap_complete: true,
  ready_for_real_data: false,
  launch_reserved: false,
  commit_sha: '1111111111111111111111111111111111111111',
  current_stage: null,
  stages: [
    {
      id: 'b3_baseline',
      name: 'Catálogo e Histórico Base B3',
      description: 'Ingestão COTAHIST B3 e criação do catálogo base de ativos',
      dependencies: [],
      provider_dependent: false,
      destructive: false,
      status: 'success',
      detail: 'ok=True catalog_created=10 prices_inserted=500',
      last_run_at: '2026-10-21T10:01:00Z',
      error: null,
    },
    {
      id: 'asset_catalog',
      name: 'Enriquecimento BRAPI e Cripto',
      description: 'Enriquecimento de ações/FIIs via BRAPI e suporte Cripto',
      dependencies: ['b3_baseline'],
      provider_dependent: true,
      destructive: false,
      status: 'idle',
      detail: null,
      last_run_at: null,
      error: null,
    },
    {
      id: 'treasury_history',
      name: 'Histórico Oficial do Tesouro',
      description: 'Reconstrução oficial de PU e taxas dos títulos públicos',
      dependencies: ['treasury_catalog'],
      provider_dependent: true,
      destructive: true,
      status: 'idle',
      detail: null,
      last_run_at: null,
      error: null,
    },
  ],
}

describe('BootstrapPanel (Issue #253)', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    })
    vi.clearAllMocks()
    vi.mocked(api.get).mockResolvedValue({ data: mockStatusResponse })
  })

  function renderComponent() {
    return render(
      <QueryClientProvider client={queryClient}>
        <BootstrapPanel />
      </QueryClientProvider>
    )
  }

  it('renders global bootstrap status card and stages', async () => {
    renderComponent()

    expect(await screen.findByText('Sistema Pronto')).toBeDefined()
    expect(screen.getByText('Status Global:')).toBeDefined()
    expect(screen.getByText('Certificação Real Pendente')).toBeDefined()
    expect(screen.getByText('Catálogo e Histórico Base B3')).toBeDefined()
    expect(screen.getByText('Enriquecimento BRAPI e Cripto')).toBeDefined()
    expect(screen.getByText('Histórico Oficial do Tesouro')).toBeDefined()
    expect(screen.getByText('Concluído')).toBeDefined()
  })

  it('opens confirmation modal and triggers full bootstrap', async () => {
    vi.mocked(api.post).mockResolvedValue({
      data: {
        status: 'accepted',
        detail: 'bootstrap global reservado para execucao',
      },
    })

    renderComponent()

    expect(await screen.findByText('Executar Bootstrap Completo')).toBeDefined()
    fireEvent.click(screen.getByText('Executar Bootstrap Completo'))

    expect(await screen.findByText('Confirmar Bootstrap Completo')).toBeDefined()
    const input = screen.getByPlaceholderText('Ex: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa')
    fireEvent.change(input, { target: { value: '1111111111111111111111111111111111111111' } })

    fireEvent.click(screen.getByText('Confirmar e Iniciar'))

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith('/admin/bootstrap', {
        commit_sha: '1111111111111111111111111111111111111111',
        stages: undefined,
      })
    })

    expect(await screen.findByText('bootstrap global reservado para execucao')).toBeDefined()
  })

  it('opens stage modal and triggers selective bootstrap', async () => {
    vi.mocked(api.post).mockResolvedValue({
      data: {
        status: 'accepted',
        detail: 'bootstrap seletivo (1 etapas) reservado para execucao',
      },
    })

    renderComponent()

    expect(await screen.findByText('Catálogo e Histórico Base B3')).toBeDefined()
    const stageButtons = screen.getAllByRole('button', { name: /Executar Etapa/i })
    fireEvent.click(stageButtons[1]) // asset_catalog

    expect(await screen.findByText(/Executar Etapa: Enriquecimento BRAPI e Cripto/)).toBeDefined()
    expect(screen.getByText(/Atenção às dependências:/)).toBeDefined()

    const input = screen.getByPlaceholderText('Ex: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa')
    fireEvent.change(input, { target: { value: '1111111111111111111111111111111111111111' } })

    fireEvent.click(screen.getByText('Confirmar Execução'))

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith('/admin/bootstrap', {
        commit_sha: '1111111111111111111111111111111111111111',
        stages: ['asset_catalog'],
      })
    })
  })

  it('toggles detail view for a stage with execution details', async () => {
    renderComponent()

    expect(await screen.findByText('Detalhes')).toBeDefined()
    fireEvent.click(screen.getByText('Detalhes'))

    expect(screen.getByText(/catalog_created=10/)).toBeDefined()
  })
})
