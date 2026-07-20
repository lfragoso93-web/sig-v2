import { CheckCircle2, CircleDashed, RefreshCw, TriangleAlert } from 'lucide-react'

import {
  useClassReconciliation,
  useIntradayReconciliation,
  type ClassReconciliation,
  type IntradayReconciliation,
} from '@/hooks/useReconciliation'
import { assetTypeLabel } from '@/utils/assetTypes'
import { formatReferenceDate } from '@/utils/portfolioSummary'

type Tone = 'success' | 'warning' | 'error' | 'neutral'

interface ReconciliationPresentation {
  title: string
  description: string
  tone: Tone
  failedFields: string[]
}

const TONE_COLOR: Record<Tone, string> = {
  success: 'var(--color-success)',
  warning: 'var(--color-warning)',
  error: 'var(--color-error)',
  neutral: 'var(--color-text-muted)',
}

export function presentClassReconciliation(
  data: ClassReconciliation,
): ReconciliationPresentation {
  if (!data.is_comparable) {
    const descriptions = {
      not_comparable_unsupported_classes: data.unsupported_asset_types.length
        ? `Classes ainda sem snapshot canônico: ${data.unsupported_asset_types.map(assetTypeLabel).join(', ')}.`
        : 'Existem classes ainda sem suporte ao snapshot canônico.',
      missing_portfolio_snapshot: 'Ainda não existe snapshot consolidado para estabelecer a data de referência.',
      missing_class_snapshots: 'Faltam snapshots de classe na mesma data do fechamento consolidado.',
    }
    return {
      title: 'Comparação ainda indisponível',
      description: descriptions[data.status as keyof typeof descriptions]
        ?? 'As bases temporais ainda não são comparáveis.',
      tone: 'neutral',
      failedFields: [],
    }
  }

  const failedFields = data.checks
    .filter(check => !check.is_reconciled)
    .map(check => check.field)

  return data.is_reconciled
    ? {
        title: 'Fechamento reconciliado',
        description: 'O snapshot consolidado coincide com a soma das classes na mesma data.',
        tone: 'success',
        failedFields: [],
      }
    : {
        title: 'Divergência no fechamento',
        description: 'O backend encontrou diferenças entre o consolidado e as classes.',
        tone: 'error',
        failedFields,
      }
}

export function presentIntradayReconciliation(
  data: IntradayReconciliation,
): ReconciliationPresentation {
  return data.is_reconciled
    ? {
        title: 'Valuation atual reconciliado',
        description: 'Resumo, posições e distribuição por classe usam a mesma referência intradiária.',
        tone: 'success',
        failedFields: [],
      }
    : {
        title: 'Divergência no valuation atual',
        description: 'O backend encontrou diferenças entre consumidores da mesma referência intradiária.',
        tone: 'error',
        failedFields: data.failed_fields,
      }
}

function StatusIcon({ tone }: { tone: Tone }) {
  if (tone === 'success') return <CheckCircle2 size={18} aria-hidden="true" />
  if (tone === 'error' || tone === 'warning') return <TriangleAlert size={18} aria-hidden="true" />
  return <CircleDashed size={18} aria-hidden="true" />
}

function ReconciliationCard({
  label,
  presentation,
  reference,
  detail,
}: {
  label: string
  presentation: ReconciliationPresentation
  reference: string
  detail: string
}) {
  const color = TONE_COLOR[presentation.tone]
  return (
    <div
      className="rounded-xl p-4"
      style={{
        border: '1px solid var(--color-divider)',
        background: 'var(--color-surface-offset)',
      }}
    >
      <div className="flex items-start gap-3">
        <span className="mt-0.5" style={{ color }}>
          <StatusIcon tone={presentation.tone} />
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-xs font-semibold" style={{ color: 'var(--color-text-muted)' }}>{label}</p>
          <p className="text-sm font-semibold mt-1" style={{ color }}>{presentation.title}</p>
          <p className="text-xs mt-1" style={{ color: 'var(--color-text-faint)' }}>
            {presentation.description}
          </p>
          <div className="flex flex-wrap gap-x-4 gap-y-1 mt-3 text-xs" style={{ color: 'var(--color-text-muted)' }}>
            <span>{reference}</span>
            <span>{detail}</span>
          </div>
          {!!presentation.failedFields.length && (
            <p className="text-xs mt-2" style={{ color: 'var(--color-error)' }}>
              Campos divergentes: {presentation.failedFields.join(', ')}
            </p>
          )}
        </div>
      </div>
    </div>
  )
}

function QueryFailure({ onRetry }: { onRetry: () => void }) {
  return (
    <div
      className="rounded-xl p-4 flex items-center justify-between gap-3"
      style={{ border: '1px solid var(--color-divider)' }}
      role="alert"
    >
      <span className="text-xs" style={{ color: 'var(--color-error)' }}>
        Não foi possível validar esta reconciliação.
      </span>
      <button type="button" className="btn-secondary flex items-center gap-1" onClick={onRetry}>
        <RefreshCw size={12} />
        Tentar novamente
      </button>
    </div>
  )
}

export default function PortfolioReconciliationPanel({ portfolioId }: { portfolioId: number }) {
  const classQuery = useClassReconciliation(portfolioId)
  const intradayQuery = useIntradayReconciliation(portfolioId)

  return (
    <section className="card" aria-labelledby="portfolio-reconciliation-title">
      <div className="section-card-header">
        <div>
          <span id="portfolio-reconciliation-title" className="section-card-title">
            Integridade dos contratos
          </span>
          <p className="text-xs mt-1" style={{ color: 'var(--color-text-faint)' }}>
            Cada validação respeita sua própria data e base; fechamento e intradiário não são comparados entre si.
          </p>
        </div>
      </div>
      <div className="p-4 grid grid-cols-1 lg:grid-cols-2 gap-3">
        {intradayQuery.isLoading ? (
          <div className="h-36 skeleton rounded-xl" aria-label="Validando valuation atual" />
        ) : intradayQuery.isError || !intradayQuery.data ? (
          <QueryFailure onRetry={() => { void intradayQuery.refetch() }} />
        ) : (
          <ReconciliationCard
            label="Valuation intradiário"
            presentation={presentIntradayReconciliation(intradayQuery.data)}
            reference={`Referência: ${formatReferenceDate(intradayQuery.data.valuation_updated_at) ?? 'sem horário'}`}
            detail={`${intradayQuery.data.positions_groups_count} grupos · ${intradayQuery.data.distribution_classes_count} classes`}
          />
        )}

        {classQuery.isLoading ? (
          <div className="h-36 skeleton rounded-xl" aria-label="Validando snapshots por classe" />
        ) : classQuery.isError || !classQuery.data ? (
          <QueryFailure onRetry={() => { void classQuery.refetch() }} />
        ) : (
          <ReconciliationCard
            label="Snapshot consolidado × classes"
            presentation={presentClassReconciliation(classQuery.data)}
            reference={`Fechamento: ${classQuery.data.snapshot_date ?? 'ainda indisponível'}`}
            detail={classQuery.data.is_comparable ? 'Mesma data de referência' : 'Bases não comparáveis'}
          />
        )}
      </div>
    </section>
  )
}
