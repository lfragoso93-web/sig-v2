import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import ProviderConfigPanel, { type ProviderConfig } from './ProviderConfigPanel'
import api from '@/services/api'

vi.mock('@/services/api', () => ({
  default: {
    get: vi.fn(),
    put: vi.fn(),
    post: vi.fn(),
  },
}))

const mockProviders: ProviderConfig[] = [
  {
    provider_id: 'b3_cotahist',
    display_name: 'B3 / COTAHIST Oficial',
    description: 'Autoridade primária oficial para cotações históricas.',
    capabilities: ['quotes_historical', 'corporate_events'],
    is_enabled: true,
    priority: 1,
    base_url: null,
    effective_base_url: null,
    timeout_seconds: 60,
    rate_limit_per_minute: null,
    custom_headers: null,
    status: 'OK',
    last_health_check_at: '2026-10-21T12:00:00Z',
    last_error_message: null,
    requires_auth: false,
    has_api_key_configured: false,
    api_key_masked: null,
    is_official_authority: true,
    is_customized: false,
    doc_url: 'https://www.b3.com.br',
  },
  {
    provider_id: 'brapi',
    display_name: 'BRAPI',
    description: 'Cotações em tempo real e proventos.',
    capabilities: ['quotes_intraday', 'dividends'],
    is_enabled: true,
    priority: 5,
    base_url: 'https://brapi.dev',
    effective_base_url: 'https://brapi.dev',
    timeout_seconds: 15,
    rate_limit_per_minute: 300,
    custom_headers: null,
    status: 'OK',
    last_health_check_at: '2026-10-21T12:05:00Z',
    last_error_message: null,
    requires_auth: true,
    has_api_key_configured: true,
    api_key_masked: 'br_****7f',
    is_official_authority: false,
    is_customized: true,
    doc_url: 'https://brapi.dev/docs',
  },
]

function renderWithProviders() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <ProviderConfigPanel />
    </QueryClientProvider>
  )
}

describe('ProviderConfigPanel (Issue #127)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.get).mockResolvedValue({ data: mockProviders })
  })

  it('renders provider list with status, capabilities and masked keys', async () => {
    renderWithProviders()

    expect(await screen.findByText('B3 / COTAHIST Oficial')).toBeDefined()
    expect(screen.getByText('BRAPI')).toBeDefined()
    expect(screen.getByText('Autoridade Oficial')).toBeDefined()
    expect(screen.getByText('Personalizado')).toBeDefined()
    expect(screen.getByText('br_****7f')).toBeDefined()
    expect(screen.getAllByText('OK').length).toBeGreaterThan(0)
    expect(screen.getByText('Cotações Intradiárias')).toBeDefined()
  })

  it('opens configuration modal when clicking Configurar', async () => {
    renderWithProviders()

    await screen.findByText('BRAPI')
    const configButtons = screen.getAllByRole('button', { name: /Configurar/i })
    fireEvent.click(configButtons[1]) // click on BRAPI

    expect(await screen.findByText('Configurar BRAPI')).toBeDefined()
    expect(screen.getByText('Salvar Alterações')).toBeDefined()
    expect(screen.getByPlaceholderText('br_****7f')).toBeDefined()
  })

  it('executes connection probe test when clicking Testar Conexão', async () => {
    vi.mocked(api.post).mockResolvedValue({
      data: {
        provider_id: 'b3_cotahist',
        success: true,
        status: 'OK',
        latency_ms: 45.2,
        message: 'Parser COTAHIST e catálogo oficial B3 operacionais.',
        tested_at: '2026-10-21T13:00:00Z',
      },
    })

    renderWithProviders()

    await screen.findByText('B3 / COTAHIST Oficial')
    const testButtons = screen.getAllByRole('button', { name: /Testar Conexão/i })
    fireEvent.click(testButtons[0])

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith('/admin/providers/b3_cotahist/test')
    })
    expect(await screen.findByText('Parser COTAHIST e catálogo oficial B3 operacionais.')).toBeDefined()
  })
})
