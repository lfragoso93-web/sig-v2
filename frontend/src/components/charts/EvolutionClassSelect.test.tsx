import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import EvolutionClassSelect from './EvolutionClassSelect'

const availability = [
  {
    asset_type: 'TESOURO_DIRETO',
    available: false,
    engine_supported: false,
    data_available: false,
    latest_snapshot_date: null,
    status: 'dedicated_history_not_available',
    reason: 'Motor dedicado indisponível.',
  },
  {
    asset_type: 'ACAO',
    available: true,
    engine_supported: true,
    data_available: true,
    latest_snapshot_date: '2026-07-18',
    status: 'available',
    reason: null,
  },
]

describe('EvolutionClassSelect', () => {
  it('lista somente as classes informadas pelo backend com rótulos canônicos', () => {
    render(
      <EvolutionClassSelect
        value="all"
        availability={availability}
        isLoading={false}
        onChange={vi.fn()}
      />,
    )

    expect(screen.getByRole('option', { name: 'Todas as classes' })).toBeTruthy()
    expect(screen.getByRole('option', { name: 'Ações' })).toBeTruthy()
    expect(screen.getByRole('option', { name: 'Tesouro Direto' })).toBeTruthy()
    expect(screen.queryByRole('option', { name: 'FIIs' })).toBeNull()
  })

  it('emite a classe canônica selecionada', () => {
    const onChange = vi.fn()
    render(
      <EvolutionClassSelect
        value="all"
        availability={availability}
        isLoading={false}
        onChange={onChange}
      />,
    )

    fireEvent.change(screen.getByLabelText('Classe do histórico'), {
      target: { value: 'ACAO' },
    })
    expect(onChange).toHaveBeenCalledWith('ACAO')
  })
})
