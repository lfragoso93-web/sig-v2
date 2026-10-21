import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import ErrorBoundary from './ErrorBoundary'

function ProblemChild({ shouldThrow }: { shouldThrow: boolean }) {
  if (shouldThrow) {
    throw new Error('Falha simulada no componente filho')
  }
  return <div>Filho renderizado com sucesso</div>
}

describe('ErrorBoundary', () => {
  it('renderiza os filhos normalmente quando não há erros', () => {
    render(
      <ErrorBoundary>
        <ProblemChild shouldThrow={false} />
      </ErrorBoundary>,
    )

    expect(screen.getByText('Filho renderizado com sucesso')).toBeDefined()
  })

  it('captura exceções e exibe o fallback amigável ao invés de crashar a página', () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {})

    render(
      <ErrorBoundary>
        <ProblemChild shouldThrow={true} />
      </ErrorBoundary>,
    )

    expect(screen.getByTestId('error-boundary-fallback')).toBeDefined()
    expect(screen.getByText('Algo deu errado ao carregar este conteúdo')).toBeDefined()
    expect(screen.getByText('Recarregar página')).toBeDefined()

    spy.mockRestore()
  })
})
