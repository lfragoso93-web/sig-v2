import type { ComponentProps } from 'react'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import EvolutionQueryState from './EvolutionQueryState'

function renderState(overrides: Partial<ComponentProps<typeof EvolutionQueryState>> = {}) {
  const props: ComponentProps<typeof EvolutionQueryState> = {
    isLoading: false,
    isError: false,
    isEmpty: false,
    onRetry: vi.fn(),
    children: <div>gráfico canônico</div>,
    ...overrides,
  }
  render(<EvolutionQueryState {...props} />)
  return props
}

describe('EvolutionQueryState', () => {
  it('prioriza loading sem apresentar ausência de dados', () => {
    renderState({ isLoading: true, isEmpty: true })

    expect(screen.getByLabelText('Carregando evolução patrimonial')).toBeTruthy()
    expect(screen.queryByText('Nenhum snapshot para o período selecionado.')).toBeNull()
  })

  it('apresenta erro com nova tentativa', () => {
    const props = renderState({ isError: true })

    fireEvent.click(screen.getByRole('button', { name: 'Tentar novamente' }))
    expect(props.onRetry).toHaveBeenCalledOnce()
  })

  it('distingue vazio de sucesso', () => {
    const { rerender } = render(
      <EvolutionQueryState isLoading={false} isError={false} isEmpty onRetry={vi.fn()}>
        <div>gráfico canônico</div>
      </EvolutionQueryState>,
    )

    expect(screen.getByText('Nenhum snapshot para o período selecionado.')).toBeTruthy()

    rerender(
      <EvolutionQueryState isLoading={false} isError={false} isEmpty={false} onRetry={vi.fn()}>
        <div>gráfico canônico</div>
      </EvolutionQueryState>,
    )
    expect(screen.getByText('gráfico canônico')).toBeTruthy()
  })
})
