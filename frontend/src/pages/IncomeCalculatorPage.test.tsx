import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import IncomeCalculatorPage from './IncomeCalculatorPage'

describe('IncomeCalculatorPage', () => {
  it('associates field guidance and announces the projection accessibly', () => {
    render(<IncomeCalculatorPage />)

    const initialContribution = screen.getByRole('spinbutton', { name: 'Aporte inicial' })
    expect(initialContribution.getAttribute('aria-describedby')).toBeTruthy()
    expect(document.getElementById(initialContribution.getAttribute('aria-describedby')!)).toBeTruthy()
    expect(screen.getByRole('status').textContent).toContain('Projeção atualizada')
    expect(screen.getByRole('region', { name: /Tabela de evolução anual/ })).toBeTruthy()
  })
})
