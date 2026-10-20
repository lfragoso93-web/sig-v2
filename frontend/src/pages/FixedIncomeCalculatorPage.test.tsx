import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import FixedIncomeCalculatorPage from './FixedIncomeCalculatorPage'

describe('FixedIncomeCalculatorPage', () => {
  it('shows gross return, progressive income tax, net value, and equivalence', () => {
    render(<FixedIncomeCalculatorPage />)

    expect(screen.getByText('R$ 11.200,00')).toBeTruthy()
    expect(screen.getByText('R$ 210,00')).toBeTruthy()
    expect(screen.getByText('R$ 10.990,00')).toBeTruthy()
    expect(screen.getByText(/Para igualar o valor/)).toBeTruthy()
  })

  it('derives income tax from the selected product type', () => {
    render(<FixedIncomeCalculatorPage />)
    fireEvent.change(screen.getAllByRole('combobox')[1], { target: { value: 'CDB' } })

    expect(screen.getAllByText('17,50%')).toHaveLength(2)
    fireEvent.change(screen.getAllByRole('combobox')[1], { target: { value: 'LCI' } })
    expect(screen.getByText('0,00%')).toBeTruthy()
  })

  it('keeps invalid assumptions visible and blocks the result', () => {
    render(<FixedIncomeCalculatorPage />)
    fireEvent.change(screen.getAllByRole('spinbutton')[1], { target: { value: '29' } })

    expect(screen.getByRole('alert').textContent).toMatch(/entre 30 e 36.500 dias/)
    expect(screen.getByText(/Corrija as premissas/)).toBeTruthy()
  })

  it('does not interpret an empty assumption as zero', () => {
    render(<FixedIncomeCalculatorPage />)
    fireEvent.change(screen.getAllByRole('spinbutton')[2], { target: { value: '' } })

    expect(screen.getByRole('alert').textContent).toMatch(/taxa efetiva anual/)
    expect(screen.getByText(/Corrija as premissas/)).toBeTruthy()
  })

  it('associates field guidance and announces updated comparisons accessibly', () => {
    render(<FixedIncomeCalculatorPage />)

    const principal = screen.getByRole('spinbutton', { name: 'Valor aplicado' })
    expect(principal.getAttribute('aria-describedby')).toBeTruthy()
    expect(document.getElementById(principal.getAttribute('aria-describedby')!)).toBeTruthy()
    expect(screen.getByRole('status').textContent).toContain('Comparação atualizada')
    expect(screen.getByRole('region', { name: /Tabela de comparação dos títulos/ })).toBeTruthy()
  })
})
