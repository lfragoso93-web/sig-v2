import { describe, it, expect } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import KpiCard from '../KpiCard'
import { TWR_HELP_DESCRIPTION, TWR_HELP_TITLE } from '../TwrHelpPopover'

describe('KpiCard', () => {
  it('renders label and value', () => {
    render(
      <KpiCard
        label="Total Investido"
        value="R$ 100.000"
      />,
    )

    expect(screen.getByText('Total Investido')).toBeTruthy()
    expect(screen.getByText('R$ 100.000')).toBeTruthy()
  })

  it('renders change percentage when provided', () => {
    render(
      <KpiCard
        label="Rentabilidade"
        value="R$ 120.000"
        change={5.5}
      />,
    )

    expect(screen.getByText((content) => content.replace(/\s/g, '') === '+5,50%')).toBeTruthy()
  })

  it('renders subValue and subLabel when provided', () => {
    render(
      <KpiCard
        label="Patrimônio"
        value="R$ 150.000"
        subValue="R$ 50.000"
        subLabel="Ganho capital"
      />,
    )

    expect(screen.getByText('R$ 50.000')).toBeTruthy()
    expect(screen.getByText('Ganho capital')).toBeTruthy()
  })

  it('handles null change gracefully', () => {
    const { container } = render(
      <KpiCard
        label="Teste"
        value="R$ 100"
        change={null}
      />,
    )

    expect(container.firstChild).toBeTruthy()
  })

  it('displays negative change with minus sign', () => {
    render(
      <KpiCard
        label="Perdas"
        value="R$ 90.000"
        change={-3.25}
      />,
    )

    expect(screen.getByText('-3,25%')).toBeTruthy()
  })

  it('automatically shows contextual TWR help for TWR labels and opens on hover/click/focus', () => {
    render(
      <KpiCard
        label="TWR em 12 meses"
        value="+14,20%"
      />,
    )

    const helpTrigger = screen.getByRole('button', { name: 'Ajuda sobre TWR' })
    expect(helpTrigger).toBeTruthy()

    fireEvent.mouseEnter(helpTrigger)
    expect(screen.getByRole('tooltip')).toBeTruthy()
    expect(screen.getByText(TWR_HELP_TITLE)).toBeTruthy()
    expect(screen.getByText(TWR_HELP_DESCRIPTION)).toBeTruthy()

    fireEvent.keyDown(document, { key: 'Escape' })
    expect(screen.queryByRole('tooltip')).toBeNull()

    fireEvent.click(helpTrigger)
    expect(screen.getByRole('tooltip')).toBeTruthy()
  })
})
