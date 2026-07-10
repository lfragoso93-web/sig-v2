import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import PositionTable from '../PositionTable'

const group = {
  label: 'Acoes',
  count: 1,
  total_value: 920,
  total_invested: 1000,
  rentabilidade_pct: -8,
  positions: [
    {
      id: 1,
      ticker: 'TEST3',
      asset_type: 'ACAO',
      asset_label: 'Teste SA',
      quantity: 10,
      average_price: 100,
      current_price: 92,
      current_value: 920,
      invested_value: 1000,
      variation_value: -80,
      variation_percent: -8,
      allocation_pct: 100,
      logo_url: null,
    },
  ],
}

describe('PositionTable action menu', () => {
  beforeEach(() => {
    Object.defineProperty(window, 'matchMedia', {
      configurable: true,
      value: vi.fn().mockImplementation(query => ({
        matches: true,
        media: query,
        onchange: null,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        addListener: vi.fn(),
        removeListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    })
  })

  it('renders the menu in a portal, flips inside the viewport, and closes with Escape', () => {
    render(
      <MemoryRouter>
        <PositionTable groups={[group]} portfolioId={1} />
      </MemoryRouter>,
    )

    Object.defineProperty(window, 'innerHeight', { configurable: true, value: 140 })

    const trigger = screen.getByLabelText(/Op/)
    trigger.getBoundingClientRect = () => ({
      width: 28,
      height: 28,
      top: 112,
      bottom: 140,
      left: 260,
      right: 288,
      x: 260,
      y: 112,
      toJSON: () => ({}),
    })

    fireEvent.click(trigger)

    const menu = screen.getByRole('menu')
    expect(menu.parentElement).toBe(document.body)
    expect(Number((menu as HTMLElement).style.top.replace('px', ''))).toBeLessThan(112)
    expect(screen.getByText(/Adicionar/)).toBeTruthy()

    fireEvent.keyDown(document, { key: 'Escape' })

    expect(screen.queryByRole('menu')).toBeNull()
  })
})
