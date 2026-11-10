import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import EditPortfolioModal from './EditPortfolioModal'

const mocks = vi.hoisted(() => ({
  mutateAsync: vi.fn(),
  isPending: false,
}))

vi.mock('@/hooks/usePortfolios', () => ({
  useUpdatePortfolio: () => ({
    mutateAsync: mocks.mutateAsync,
    isPending: mocks.isPending,
  }),
}))

describe('EditPortfolioModal', () => {
  const samplePortfolio = {
    id: 10,
    name: 'Carteira Atual',
    description: 'Descrição existente',
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders prefilled portfolio details via portal', () => {
    const onClose = vi.fn()
    render(<EditPortfolioModal portfolio={samplePortfolio} onClose={onClose} />)

    expect(screen.getByText('Editar carteira')).toBeDefined()
    expect(screen.getByDisplayValue('Carteira Atual')).toBeDefined()
    expect(screen.getByDisplayValue('Descrição existente')).toBeDefined()
    expect(screen.getByRole('button', { name: 'Salvar alterações' })).toBeDefined()
  })

  it('validates non-empty portfolio name', async () => {
    const onClose = vi.fn()
    render(<EditPortfolioModal portfolio={samplePortfolio} onClose={onClose} />)

    fireEvent.change(screen.getByDisplayValue('Carteira Atual'), { target: { value: '   ' } })
    fireEvent.click(screen.getByRole('button', { name: 'Salvar alterações' }))

    expect(screen.getByText('Informe um nome para a carteira.')).toBeDefined()
    expect(mocks.mutateAsync).not.toHaveBeenCalled()
  })

  it('submits updated values successfully', async () => {
    const onClose = vi.fn()
    mocks.mutateAsync.mockResolvedValueOnce({ id: 10, name: 'Carteira Atualizada' })

    render(<EditPortfolioModal portfolio={samplePortfolio} onClose={onClose} />)

    fireEvent.change(screen.getByDisplayValue('Carteira Atual'), { target: { value: 'Carteira Atualizada' } })
    fireEvent.click(screen.getByRole('button', { name: 'Salvar alterações' }))

    await waitFor(() => {
      expect(mocks.mutateAsync).toHaveBeenCalledWith({
        id: 10,
        name: 'Carteira Atualizada',
        description: 'Descrição existente',
      })
      expect(onClose).toHaveBeenCalled()
    })
  })
})
