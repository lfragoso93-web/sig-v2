import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import CarteirasRecomendadasPage from './CarteirasRecomendadasPage'

const mockNavigate = vi.fn()
vi.mock('react-router-dom', () => ({
  useNavigate: () => mockNavigate,
}))

const mockPortfolios = [
  {
    id: 'patrimonio',
    title: 'Aumento e Preservação de Patrimônio',
    subtitle: 'Crescimento sustentável com foco em baixa volatilidade e valor real',
    strategy: 'patrimonio',
    thesis: 'Estratégia focada na acumulação constante e blindagem de patrimônio no longo prazo.',
    risk_profile: 'Moderado / Defensivo',
    expected_annual_return: 'IPCA + 6,5% a.a.',
    expected_dividend_yield: '5,5% a.a.',
    suggested_time_horizon: 'Mínimo 5 anos',
    diversification_score: 93,
    classes: [
      {
        asset_type: 'ACAO',
        label: 'Ações Nacionais',
        target_weight_pct: 40.0,
        description: 'Participação em grandes corporações.',
        assets: [
          {
            ticker: 'ITUB4',
            name: 'Itaú Unibanco PN',
            asset_type: 'ACAO',
            current_price: 35.0,
            target_weight_pct: 40.0,
            reason: 'Maior banco privado com alto ROE.',
            expected_yield_pct: 6.5,
            risk_level: 'moderate',
          },
        ],
      },
      {
        asset_type: 'FII',
        label: 'Fundos Imobiliários',
        target_weight_pct: 60.0,
        description: 'Ativos imobiliários com proventos.',
        assets: [
          {
            ticker: 'HGLG11',
            name: 'CSHG Logística FII',
            asset_type: 'FII',
            current_price: 160.0,
            target_weight_pct: 60.0,
            reason: 'Galpões logísticos padrão AAA.',
            expected_yield_pct: 8.5,
            risk_level: 'low',
          },
        ],
      },
    ],
  },
  {
    id: 'proventos',
    title: 'Renda Passiva e Fluxo de Proventos',
    subtitle: 'Maximização de fluxo de caixa mensal',
    strategy: 'proventos',
    thesis: 'Construída para gerar um fluxo mensal consistente de dividendos.',
    risk_profile: 'Moderado',
    expected_annual_return: '11,0% a.a.',
    expected_dividend_yield: '9,5% a.a.',
    suggested_time_horizon: 'Mínimo 3 anos',
    diversification_score: 91,
    classes: [
      {
        asset_type: 'FII',
        label: 'Fundos Imobiliários',
        target_weight_pct: 70.0,
        description: 'Proventos mensais.',
        assets: [
          {
            ticker: 'MXRF11',
            name: 'Maxi Renda FII',
            asset_type: 'FII',
            current_price: 10.0,
            target_weight_pct: 70.0,
            reason: 'Maior liquidez da indústria de FIIs.',
            expected_yield_pct: 11.5,
            risk_level: 'moderate',
          },
        ],
      },
    ],
  },
]

const mockSimulate = vi.fn()

vi.mock('@/hooks/useRecommendedPortfolios', () => ({
  useRecommendedPortfolios: () => ({
    data: mockPortfolios,
    isLoading: false,
    isError: false,
  }),
  useSimulateRecommendedPortfolio: () => ({
    mutate: mockSimulate,
    isPending: false,
    data: {
      strategy: 'patrimonio',
      total_amount: 5000.0,
      summary: 'Simulação para aporte de R$ 5.000,00 na estratégia.',
      classes: [
        {
          asset_type: 'ACAO',
          label: 'Ações Nacionais',
          target_weight_pct: 40.0,
          allocated_amount: 2000.0,
          assets: [
            {
              ticker: 'ITUB4',
              name: 'Itaú Unibanco PN',
              asset_type: 'ACAO',
              current_price: 35.0,
              weight_in_portfolio_pct: 40.0,
              allocated_amount: 2000.0,
              suggested_quantity: 57.14,
              reason: 'Maior banco privado.',
            },
          ],
        },
      ],
    },
  }),
}))

describe('CarteirasRecomendadasPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renderiza o cabeçalho e abas das 3 premissas estratégicas', () => {
    render(<CarteirasRecomendadasPage />)

    expect(screen.getByText('Carteiras Recomendadas')).toBeTruthy()
    expect(screen.getByRole('tab', { name: /Aumento de Patrimônio/i })).toBeTruthy()
    expect(screen.getByRole('tab', { name: /Renda Passiva/i })).toBeTruthy()
    expect(screen.getByRole('tab', { name: /Performance & Crescimento/i })).toBeTruthy()
  })

  it('exibe as métricas analíticas e a tese da estratégia selecionada', () => {
    render(<CarteirasRecomendadasPage />)

    expect(screen.getByText('Aumento e Preservação de Patrimônio')).toBeTruthy()
    expect(screen.getByText('IPCA + 6,5% a.a.')).toBeTruthy()
    expect(screen.getByText('5,5% a.a.')).toBeTruthy()
    expect(screen.getByText('93/100')).toBeTruthy()
    expect(screen.getAllByText('ITUB4')[0]).toBeTruthy()
  })

  it('permite alternar entre as premissas estratégicas', () => {
    render(<CarteirasRecomendadasPage />)

    const proventosTab = screen.getByRole('tab', { name: /Renda Passiva/i })
    fireEvent.click(proventosTab)

    expect(screen.getByText('Renda Passiva e Fluxo de Proventos')).toBeTruthy()
    expect(screen.getByText('11,0% a.a.')).toBeTruthy()
    expect(screen.getByText('9,5% a.a.')).toBeTruthy()
  })

  it('permite alternar modo customizado de pesos e ajustar percentual', () => {
    render(<CarteirasRecomendadasPage />)

    const adjustBtn = screen.getByRole('button', { name: /Ajustar Pesos/i })
    fireEvent.click(adjustBtn)

    expect(screen.getByRole('button', { name: /Modo Customizado/i })).toBeTruthy()
  })

  it('executa simulação de aporte ao preencher o valor e submeter o formulário', () => {
    render(<CarteirasRecomendadasPage />)

    const input = screen.getByPlaceholderText('Ex: 5000')
    fireEvent.change(input, { target: { value: '10000' } })

    const simulateBtn = screen.getByRole('button', { name: /^Simular$/i })
    fireEvent.click(simulateBtn)

    expect(mockSimulate).toHaveBeenCalledWith(
      expect.objectContaining({
        total_amount: 10000,
        strategy: 'patrimonio',
      }),
    )
  })

  it('redireciona para Minhas Metas ao clicar em Adotar Alocação', async () => {
    render(<CarteirasRecomendadasPage />)

    const adoptBtn = screen.getByRole('button', { name: /Adotar Alocação em Minhas Metas/i })
    fireEvent.click(adoptBtn)

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/carteira/metas')
    }, { timeout: 1500 })
  })
})
