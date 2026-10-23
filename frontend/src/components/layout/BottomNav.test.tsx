import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import BottomNav from './BottomNav'

const openTransactionModal = vi.fn()

vi.mock('@/store/appStore', () => ({
  useAppStore: () => ({
    openTransactionModal,
  }),
}))

describe('BottomNav mobile navigation (#351)', () => {
  it('includes Rentabilidade alongside Resumo, Patrimônio, Transações, Proventos and keeps the central FAB', () => {
    render(
      <MemoryRouter initialEntries={['/carteira/rentabilidade']}>
        <BottomNav />
      </MemoryRouter>,
    )

    expect(screen.getByRole('link', { name: 'Resumo' })).toBeTruthy()
    expect(screen.getByRole('link', { name: 'Patrimônio' })).toBeTruthy()
    const rentabilidadeLink = screen.getByRole('link', { name: 'Rentabilidade' })
    expect(rentabilidadeLink).toBeTruthy()
    expect(rentabilidadeLink.getAttribute('aria-current')).toBe('page')
    expect(screen.getByRole('link', { name: 'Transações' })).toBeTruthy()
    expect(screen.getByRole('link', { name: 'Proventos' })).toBeTruthy()

    const fab = screen.getByRole('button', { name: 'Novo Lançamento' })
    expect(fab).toBeTruthy()
    fireEvent.click(fab)
    expect(openTransactionModal).toHaveBeenCalledTimes(1)
  })
})
