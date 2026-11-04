import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import ScheduledJobsPanel from './ScheduledJobsPanel'
import api from '@/services/api'

vi.mock('@/services/api', () => ({ default: { get: vi.fn(), post: vi.fn() } }))

function renderPanel() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <ScheduledJobsPanel />
    </QueryClientProvider>,
  )
}

describe('ScheduledJobsPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows failed jobs and next-run details', async () => {
    vi.mocked(api.get).mockResolvedValue({
      data: {
        timezone: 'America/Sao_Paulo',
        status_retention_days: 90,
        status_store_available: true,
        jobs: [{
          id: 'sync_asset_dividends_morning',
          name: 'Coleta global de proventos',
          enabled: true,
          next_run_at: '2026-11-03T08:00:00-03:00',
          last_status: 'failed',
          last_started_at: '2026-11-02T08:00:00-03:00',
          last_finished_at: '2026-11-02T08:00:03-03:00',
          duration_ms: '3000',
          last_error_type: 'ProviderError',
        }],
      },
    })

    renderPanel()

    expect(await screen.findByText(/há tarefa agendada com falha/i)).toBeDefined()
    expect(screen.getByText(/Falhou \(ProviderError\)/)).toBeDefined()
    expect(screen.getByText('3000 ms')).toBeDefined()
  })

  it('shows manual execution and history controls for enabled jobs', async () => {
    vi.mocked(api.get).mockResolvedValue({
      data: {
        timezone: 'America/Sao_Paulo', status_retention_days: 90, status_store_available: true,
        jobs: [{
          id: 'refresh_asset_fundamentals_daily', name: 'Fundamentos', enabled: true,
          next_run_at: null, last_status: 'never_run', last_started_at: null,
          last_finished_at: null, duration_ms: null, last_error_type: null,
          lease_ttl_seconds: null, trigger_source: null,
        }],
      },
    })
    renderPanel()
    expect(await screen.findByRole('button', { name: 'Executar Fundamentos agora' })).toBeDefined()
    expect(screen.getByRole('button', { name: 'Ver histórico de Fundamentos' })).toBeDefined()
  })

  it('warns when Redis status history is unavailable', async () => {
    vi.mocked(api.get).mockResolvedValue({
      data: {
        timezone: 'America/Sao_Paulo',
        status_retention_days: 90,
        status_store_available: false,
        jobs: [],
      },
    })

    renderPanel()

    expect(await screen.findByText(/redis está indisponível/i)).toBeDefined()
  })
})
