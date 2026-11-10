import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import CreatePortfolioModal from './CreatePortfolioModal'
import { useAppStore } from '@/store/appStore'

const mocks = vi.hoisted(() => ({
  mutateAsync: vi.fn(),
  isPending: false,
}))

vi.mock('@/hooks/usePortfolios', () => ({
  useCreatePortfolio: () => ({
    mutateAsync: mocks.mutateAsync,
    isPending: mocks.isPending,
  }),
}))

describe('CreatePortfolioModal', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAppStore.setState({ selectedPortfolioId: null })
  })

  it('renders modal with correct title and fields into document.body via portal', () => {
    const onClose = vi.fn()
    render(<CreatePortfolioModal onClose={onClose} />)

    expect(screen.getByText('Nova Carteira')).toBeDefined()
    expect(screen.getByPlaceholderText('Ex: Carteira Principal')).toBeDefined()
    expect(screen.getByPlaceholderText('Ex: Ações, FIIs e renda fixa')).toBeDefined()
    expect(screen.getByRole('button', { name: 'Criar carteira' })).toBeDefined()
  })

  it('shows error if submitted without a name', async () => {
    const onClose = vi.fn()
    render(<CreatePortfolioModal onClose={onClose} />)

    fireEvent.click(screen.getByRole('button', { name: 'Criar carteira' }))

    expect(screen.getByText('Informe um nome para a carteira.')).toBeDefined()
    expect(mocks.mutateAsync).not.toHaveBeenCalled()
    expect(onClose).not.toHaveBeenCalled()
  })

  it('successfully creates portfolio and updates selected portfolio', async () => {
    const onClose = vi.fn()
    mocks.mutateAsync.mockResolvedValueOnce({ id: 42, name: 'Nova Carteira Teste' })

    render(<CreatePortfolioModal onClose={onClose} />)

    fireEvent.change(screen.getByPlaceholderText('Ex: Carteira Principal'), {
      target: { value: 'Nova Carteira Teste' },
    })
    fireEvent.change(screen.getByPlaceholderText('Ex: Ações, FIIs e renda fixa'), {
      target: { value: 'Descrição de teste' },
    })

    fireEvent.click(screen.getByRole('button', { name: 'Criar carteira' }))

    await waitFor(() => {
      expect(mocks.mutateAsync).toHaveBeenCalledWith({
        name: 'Nova Carteira Teste',
        description: 'Descrição de teste',
      })
      expect(useAppStore.getState().selectedPortfolioId).toBe(42)
      expect(onClose).toHaveBeenCalled()
    })
  })

  it('closes on clicking the close button or cancel button', () => {
    const onClose = vi.fn()
    render(<CreatePortfolioModal onClose={onClose} />)

    fireEvent.click(screen.getByLabelText('Fechar'))
    expect(onClose).toHaveBeenCalledTimes(1)

    fireEvent.click(screen.getByRole('button', { name: 'Cancelar' }))
    expect(onClose).toHaveBeenCalledTimes(2)
  })
})
