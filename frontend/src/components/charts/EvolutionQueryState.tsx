import type { ReactNode } from 'react'

interface EvolutionQueryStateProps {
  isLoading: boolean
  isError: boolean
  isEmpty: boolean
  onRetry: () => void
  children: ReactNode
}

export default function EvolutionQueryState({
  isLoading,
  isError,
  isEmpty,
  onRetry,
  children,
}: EvolutionQueryStateProps) {
  if (isLoading) {
    return <div className="h-64 skeleton rounded" aria-label="Carregando evolução patrimonial" />
  }

  if (isError) {
    return (
      <div
        className="h-64 flex flex-col items-center justify-center gap-3 text-sm text-center"
        style={{ color: 'var(--color-error)' }}
        role="alert"
      >
        <span>Não foi possível carregar a evolução patrimonial.</span>
        <button type="button" className="btn-secondary" onClick={onRetry}>
          Tentar novamente
        </button>
      </div>
    )
  }

  if (isEmpty) {
    return (
      <div
        className="h-64 flex items-center justify-center text-sm text-center"
        style={{ color: 'var(--color-text-muted)' }}
      >
        Nenhum snapshot para o período selecionado.
      </div>
    )
  }

  return children
}
