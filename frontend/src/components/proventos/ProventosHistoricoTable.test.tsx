import { act, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { ProventosHistoricoMes } from '@/services/proventosService'
import ProventosHistoricoTable from './ProventosHistoricoTable'

const history: ProventosHistoricoMes[] = [{
  year: 2026,
  months: [null, null, 153.1, null, null, null, null, null, null, null, null, null],
  total: 153.1,
  media: 153.1,
  month_details: [{
    month: 3,
    total: 153.1,
    by_asset_class: [
      { asset_type: 'FII', label: 'FIIs', value: 90.8 },
      { asset_type: 'ETF_NACIONAL', label: 'ETFs nacionais', value: 38.65 },
      { asset_type: 'ACAO', label: 'Ações', value: 23.65 },
    ],
  }],
}]

afterEach(() => {
  vi.useRealTimers()
})

describe('ProventosHistoricoTable', () => {
  it('renders a clear empty state', () => {
    render(<ProventosHistoricoTable data={[]} />)

    expect(screen.getByText('Sem dados')).toBeTruthy()
    expect(screen.queryByRole('dialog')).toBeNull()
  })

  it('opens on hover, keeps the portal open under the pointer and renders the composition', () => {
    vi.useFakeTimers()
    render(<ProventosHistoricoTable data={history} />)

    const button = screen.getByRole('button', { name: 'Detalhar Mar de 2026' })
    fireEvent.mouseEnter(button)

    const dialog = screen.getByRole('dialog', { name: 'Proventos de março de 2026' })
    expect(screen.getByText('FIIs')).toBeTruthy()
    expect(screen.getByText('ETFs nacionais')).toBeTruthy()
    expect(screen.getByText('Ações')).toBeTruthy()
    expect(dialog.textContent?.replace(/\s/g, ' ')).toContain('R$ 153,10')

    fireEvent.mouseLeave(button)
    fireEvent.mouseEnter(dialog)
    act(() => vi.advanceTimersByTime(150))
    expect(screen.getByRole('dialog')).toBeTruthy()

    fireEvent.mouseLeave(dialog)
    act(() => vi.advanceTimersByTime(150))
    expect(screen.queryByRole('dialog')).toBeNull()
  })

  it('supports keyboard focus and Escape, returning focus to the cell', () => {
    render(<ProventosHistoricoTable data={history} />)
    const button = screen.getByRole('button', { name: 'Detalhar Mar de 2026' })

    fireEvent.focus(button)
    expect(screen.getByRole('dialog')).toBeTruthy()
    expect(button.getAttribute('aria-expanded')).toBe('true')

    fireEvent.keyDown(document, { key: 'Escape' })
    expect(screen.queryByRole('dialog')).toBeNull()
    expect(document.activeElement).toBe(button)
  })

  it('opens by click/touch and closes on an outside pointer event', () => {
    render(<ProventosHistoricoTable data={history} />)
    const button = screen.getByRole('button', { name: 'Detalhar Mar de 2026' })

    fireEvent.click(button)
    expect(screen.getByRole('dialog')).toBeTruthy()
    fireEvent.pointerDown(document.body)
    expect(screen.queryByRole('dialog')).toBeNull()
  })

  it('clamps the portal inside the viewport near the bottom-right edge', () => {
    Object.defineProperty(window, 'innerWidth', { configurable: true, value: 320 })
    Object.defineProperty(window, 'innerHeight', { configurable: true, value: 200 })
    Object.defineProperty(HTMLElement.prototype, 'offsetHeight', {
      configurable: true,
      get() { return this.getAttribute('role') === 'dialog' ? 150 : 0 },
    })
    render(<ProventosHistoricoTable data={history} />)
    const button = screen.getByRole('button', { name: 'Detalhar Mar de 2026' })
    vi.spyOn(button, 'getBoundingClientRect').mockReturnValue({
      bottom: 190,
      height: 20,
      left: 300,
      right: 320,
      top: 170,
      width: 20,
      x: 300,
      y: 170,
      toJSON: () => ({}),
    })

    fireEvent.mouseEnter(button)
    const dialog = screen.getByRole('dialog')
    expect(parseFloat(dialog.style.left)).toBeGreaterThanOrEqual(8)
    expect(parseFloat(dialog.style.left) + 288).toBeLessThanOrEqual(312)
    expect(parseFloat(dialog.style.top)).toBeGreaterThanOrEqual(8)
    expect(parseFloat(dialog.style.top) + 150).toBeLessThanOrEqual(192)
  })
})
