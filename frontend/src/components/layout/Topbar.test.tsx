import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import Topbar from './Topbar'
import { useAppStore } from '@/store/appStore'

const mocks = vi.hoisted(() => ({
  usePortfolios: vi.fn(),
  useDeletePortfolio: vi.fn(),
}))

vi.mock('@/hooks/usePortfolios', () => ({
  usePortfolios: mocks.usePortfolios,
  useDeletePortfolio: mocks.useDeletePortfolio,
}))

vi.mock('./UserMenu', () => ({
  default: () => <div data-testid="user-menu" />,
}))

vi.mock('@/components/ui/LogoSGI', () => ({
  default: () => <div data-testid="logo-sgi" />,
}))

describe('Topbar PortfolioSelector persistence', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    useAppStore.setState({
      selectedPortfolioId: null,
      theme: 'dark',
      sidebarCollapsed: false,
    })
    mocks.useDeletePortfolio.mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    })
  })

  it('mantém selectedPortfolioId ativo quando o id existe na lista', () => {
    useAppStore.setState({ selectedPortfolioId: 2 })
    mocks.usePortfolios.mockReturnValue({
      data: [
        { id: 1, name: 'Carteira Principal' },
        { id: 2, name: 'Carteira Secundária' },
      ],
      isLoading: false,
    })

    render(<Topbar />)

    expect(useAppStore.getState().selectedPortfolioId).toBe(2)
    expect(screen.getByText('Carteira Secundária')).toBeDefined()
  })

  it('faz fallback para portfolios[0].id quando selectedPortfolioId não está definido', () => {
    useAppStore.setState({ selectedPortfolioId: null })
    mocks.usePortfolios.mockReturnValue({
      data: [
        { id: 10, name: 'Carteira Única' },
      ],
      isLoading: false,
    })

    render(<Topbar />)

    expect(useAppStore.getState().selectedPortfolioId).toBe(10)
    expect(screen.getByText('Carteira Única')).toBeDefined()
  })

  it('aceita coerção entre string e número sem resetar para portfolios[0]', () => {
    // Caso de id serializado ou vindo de query string
    useAppStore.setState({ selectedPortfolioId: 15 })
    mocks.usePortfolios.mockReturnValue({
      data: [
        { id: 1, name: 'Carteira 1' },
        { id: 15, name: 'Carteira 15' },
      ],
      isLoading: false,
    })

    render(<Topbar />)

    expect(useAppStore.getState().selectedPortfolioId).toBe(15)
    expect(screen.getByText('Carteira 15')).toBeDefined()
  })
})
