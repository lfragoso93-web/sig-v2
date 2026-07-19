import { fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { PositionGroup } from '@/hooks/usePortfolio'
import PositionTable, { investedValueOf } from './PositionTable'

vi.mock('@/components/ui/AssetLogo', () => ({
  default: () => <span aria-hidden="true" />,
}))

vi.mock('@/components/portfolio/AssetDetailDrawer', () => ({
  default: () => null,
}))

vi.mock('@/hooks/useClassTargets', () => ({
  useUpsertClassTarget: () => ({ mutate: vi.fn(), isPending: false }),
}))

vi.mock('@/store/appStore', () => ({
  useAppStore: (selector: (state: { openTransactionModal: () => void }) => unknown) =>
    selector({ openTransactionModal: vi.fn() }),
}))

function buildGroup(positionCount: number): PositionGroup {
  return {
    label: 'Ações',
    count: positionCount,
    total_value: positionCount * 110,
    total_invested: positionCount * 100,
    daily_variation_pct: 0.5,
    positions: Array.from({ length: positionCount }, (_, index) => ({
      id: index + 1,
      ticker: `TEST${index + 1}`,
      asset_type: 'ACAO',
      asset_label: `Ação ${index + 1}`,
      quantity: 1,
      average_price: 100,
      current_price: 110,
      current_value: 110,
      invested_value: 100,
      variation_value: 10,
      variation_percent: 10,
      allocation_pct: 100 / positionCount,
    })),
  }
}

function mockButtonPosition(button: HTMLButtonElement, top: number): void {
  vi.spyOn(button, 'getBoundingClientRect').mockReturnValue({
    x: 1000,
    y: top,
    top,
    right: 1028,
    bottom: top + 28,
    left: 1000,
    width: 28,
    height: 28,
    toJSON: () => ({}),
  } as DOMRect)
}

describe('PositionTable', () => {
  beforeEach(() => {
    Object.defineProperty(window, 'innerWidth', { configurable: true, value: 1280 })
    Object.defineProperty(window, 'innerHeight', { configurable: true, value: 800 })
    Object.defineProperty(window, 'matchMedia', {
      configurable: true,
      value: vi.fn().mockImplementation((query: string) => ({
        matches: true,
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    })
  })

  it.each([
    ['poucas linhas', 1, 100],
    ['muitas linhas', 20, 740],
  ])('renderiza o dropdown fora da tabela com %s', (_, positionCount, top) => {
    render(
      <MemoryRouter>
        <PositionTable groups={[buildGroup(positionCount)]} portfolioId={46} />
      </MemoryRouter>,
    )

    const menuButtons = screen.getAllByRole('button', { name: 'Opções' })
    const targetButton = menuButtons.at(-1) as HTMLButtonElement
    mockButtonPosition(targetButton, top)

    fireEvent.click(targetButton)

    const menu = screen.getByRole('menu')
    expect(menu.parentElement).toBe(document.body)
    expect(menu.style.position).toBe('fixed')
    expect(within(menu).getAllByRole('menuitem')).toHaveLength(3)
  })

  it('explicita custo, resultado de capital e variação diária', () => {
    render(
      <MemoryRouter>
        <PositionTable groups={[buildGroup(1)]} portfolioId={46} />
      </MemoryRouter>,
    )

    expect(screen.getByText('Custo Atual')).toBeTruthy()
    expect(screen.getByText('Resultado de Capital')).toBeTruthy()
    expect(screen.getByText('Variação diária')).toBeTruthy()
  })

  it('identifica valores indisponíveis quando o ativo não tem cotação', () => {
    const group = buildGroup(1)
    group.positions[0].current_price = null
    group.positions[0].current_value = null
    group.positions[0].variation_value = null
    group.positions[0].variation_percent = null

    render(
      <MemoryRouter>
        <PositionTable groups={[group]} portfolioId={46} />
      </MemoryRouter>,
    )

    expect(screen.getAllByText('Sem cotação')).toHaveLength(3)
  })

  it('usa o total investido canônico do grupo sem recompor as posições', () => {
    const group = buildGroup(1)
    group.total_invested = 1_234.56

    render(
      <MemoryRouter>
        <PositionTable groups={[group]} portfolioId={46} />
      </MemoryRouter>,
    )

    const groupHeader = screen.getByText('Ações').closest('button')
    expect(groupHeader).not.toBeNull()
    expect(within(groupHeader as HTMLElement).getByText(/1\.234,56/)).toBeTruthy()
  })

  it('preserva custo canônico zero sem recompor quantidade por preço médio', () => {
    const position = buildGroup(1).positions[0]
    position.invested_value = 0
    position.quantity = 10
    position.average_price = 123.45

    expect(investedValueOf(position)).toBe(0)
  })

  it('ignora rentabilidade simples legada mesmo se o payload vier poluído', () => {
    const pollutedGroup = {
      ...buildGroup(1),
      rentabilidade_pct: 99,
    } as PositionGroup

    render(
      <MemoryRouter>
        <PositionTable groups={[pollutedGroup]} portfolioId={46} />
      </MemoryRouter>,
    )

    expect(screen.queryByText('Rentab. total')).toBeNull()
  })
})
