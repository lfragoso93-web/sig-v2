import { CheckCircle2, CircleDashed, RefreshCw, ShieldCheck, TriangleAlert } from 'lucide-react'

import {
  useClassReconciliation,
  useIntradayReconciliation,
  type ClassReconciliation,
  type IntradayReconciliation,
  type ReconciliationCheck,
} from '@/hooks/useReconciliation'
import { assetTypeLabel } from '@/utils/assetTypes'
import { formatBRL } from '@/utils/format'
import { formatReferenceDate } from '@/utils/portfolioSummary'

type Tone = 'success' | 'warning' | 'error' | 'neutral'

interface ReconciliationPresentation {
  title: string
  description: string
  impact: string
  tone: Tone
  failedFields: string[]
}

const TONE_COLOR: Record<Tone, string> = {
  success: 'var(--color-success)',
  warning: 'var(--color-warning)',
  error: 'var(--color-error)',
  neutral: 'var(--color-text-muted)',
}

const TONE_SURFACE: Record<Tone, string> = {
  success: 'oklch(from var(--color-success) l c h / 0.08)',
  warning: 'oklch(from var(--color-warning) l c h / 0.08)',
  error: 'oklch(from var(--color-error) l c h / 0.08)',
  neutral: 'var(--color-surface)',
}

const FIELD_LABELS: Record<string, string> = {
  market_value: 'Valor de mercado (Patrimônio)',
  cost_basis: 'Custo de aquisição (Investido)',
  net_external_flow: 'Fluxo líquido do dia (Aportes/Resgates)',
  dividends_day: 'Proventos recebidos no dia',
  'positions.total_patrimonio': 'Patrimônio atual (Resumo × Posições)',
  'positions.total_investido': 'Total investido (Resumo × Posições)',
  'positions.ganho_nao_realizado': 'Resultado não realizado (Resumo × Posições)',
  'asset_distribution.total_patrimonio': 'Patrimônio atual (Resumo × Distribuição por classe)',
}

export function formatReconciliationFieldLabel(field: string): string {
  if (FIELD_LABELS[field]) return FIELD_LABELS[field]
  if (field.startsWith('groups.') && field.endsWith('.capital_result_value')) {
    const rawGroup = field.slice('groups.'.length, -'.capital_result_value'.length)
    return `Resultado de capital (${assetTypeLabel(rawGroup)})`
  }
  return field
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
      impact: 'Sem impacto no seu patrimônio atual nem nas posições abertas. O histórico diário por classe será consolidado no próximo processamento.',
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
        impact: 'A evolução histórica da carteira e os gráficos por classe estão 100% sincronizados até o último fechamento.',
        tone: 'success',
        failedFields: [],
      }
    : {
        title: 'Divergência no fechamento',
        description: 'O backend encontrou diferenças entre o consolidado e as classes.',
        impact: 'Impacto: Seu saldo atual e suas posições abertas NÃO são afetados. Apenas o gráfico de evolução histórica filtrada por classe pode apresentar diferença temporária no fechamento indicado até a sincronização automática dos snapshots.',
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
        impact: 'Os valores exibidos nos cards do topo, no gráfico de rosca e na tabela de posições estão consistentes entre si.',
        tone: 'success',
        failedFields: [],
      }
    : {
        title: 'Divergência no valuation atual',
        description: 'O backend encontrou diferenças entre consumidores da mesma referência intradiária.',
        impact: 'Impacto: Há diferença temporária de arredondamento ou cache entre os indicadores de resumo e a soma das posições abertas.',
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
  purpose,
  presentation,
  reference,
  detail,
  checks,
}: {
  label: string
  purpose: string
  presentation: ReconciliationPresentation
  reference: string
  detail: string
  checks?: ReconciliationCheck[]
}) {
  const color = TONE_COLOR[presentation.tone]
  const failedChecks = (checks ?? []).filter(check => !check.is_reconciled)

  return (
    <div
      className="rounded-xl p-4 flex flex-col justify-between gap-3"
      style={{
        border: presentation.tone === 'error'
          ? '1px solid oklch(from var(--color-error) l c h / 0.32)'
          : '1px solid var(--color-divider)',
        background: 'var(--color-surface-offset)',
      }}
    >
      <div className="flex items-start gap-3">
        <span
          className="mt-0.5 shrink-0"
          style={{
            color,
            width: 32,
            height: 32,
            borderRadius: 'var(--radius-md)',
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: TONE_SURFACE[presentation.tone],
          }}
        >
          <StatusIcon tone={presentation.tone} />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between gap-2 flex-wrap">
            <p className="text-xs font-semibold" style={{ color: 'var(--color-text-muted)' }}>{label}</p>
            <span
              className="text-[11px] font-medium px-2 py-0.5 rounded-full"
              style={{
                color: 'var(--color-text-faint)',
                background: 'var(--color-surface)',
                border: '1px solid var(--color-divider)',
              }}
            >
              {purpose}
            </span>
          </div>
          <p className="text-sm font-semibold mt-1" style={{ color }}>{presentation.title}</p>
          <p className="text-xs mt-1 leading-relaxed" style={{ color: 'var(--color-text-muted)' }}>
            {presentation.description}
          </p>
          <p
            className="text-xs mt-2 leading-relaxed rounded-lg px-3 py-2"
            style={{
              color: presentation.tone === 'error' ? 'var(--color-text)' : 'var(--color-text-faint)',
              background: TONE_SURFACE[presentation.tone],
              border: '1px solid oklch(from var(--color-text) l c h / 0.06)',
            }}
          >
            {presentation.impact}
          </p>

          {!!presentation.failedFields.length && (
            <div className="mt-2.5 flex flex-col gap-1.5">
              <p className="text-xs font-medium" style={{ color: 'var(--color-error)' }}>
                Indicadores com diferença ({presentation.failedFields.map(formatReconciliationFieldLabel).join(', ')}):
              </p>
              {failedChecks.length > 0 && (
                <div className="grid grid-cols-1 gap-1 text-[11px]" style={{ color: 'var(--color-text-muted)' }}>
                  {failedChecks.map(item => (
                    <div
                      key={item.field}
                      className="flex flex-wrap items-center justify-between gap-2 px-2.5 py-1 rounded-md"
                      style={{ background: 'var(--color-surface)' }}
                    >
                      <span className="font-medium" style={{ color: 'var(--color-text)' }}>
                        {formatReconciliationFieldLabel(item.field)}
                      </span>
                      <span className="tabular-nums">
                        Consolidado: <strong>{formatBRL(item.expected)}</strong> · Soma das classes: <strong>{formatBRL(item.observed)}</strong>
                      </span>
                    </div>
                  ))}
                </div>
              )}
              <p className="text-[11px]" style={{ color: 'var(--color-text-faint)' }}>
                Campos divergentes: {presentation.failedFields.join(', ')}
              </p>
            </div>
          )}

          <div
            className="flex flex-wrap gap-x-4 gap-y-1 mt-3 pt-2.5 text-xs"
            style={{
              color: 'var(--color-text-muted)',
              borderTop: '1px solid var(--color-divider)',
            }}
          >
            <span>{reference}</span>
            <span>{detail}</span>
          </div>
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
        <div className="flex items-start gap-2.5">
          <span
            aria-hidden="true"
            style={{
              width: 28,
              height: 28,
              borderRadius: 'var(--radius-md)',
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
              marginTop: 2,
              background: 'oklch(from var(--color-primary) l c h / 0.1)',
              color: 'var(--color-primary)',
            }}
          >
            <ShieldCheck size={15} strokeWidth={2} />
          </span>
          <div>
            <span id="portfolio-reconciliation-title" className="section-card-title">
              Auditoria e integridade dos dados (Integridade dos contratos)
            </span>
            <p className="text-xs mt-1 leading-relaxed" style={{ color: 'var(--color-text-faint)' }}>
              Este painel verifica automaticamente se os cálculos da sua carteira estão consistentes em duas frentes independentes: <strong>(1) Tempo real</strong> (se o patrimônio do topo bate exatamente com a soma das posições abertas e do gráfico de classes) e <strong>(2) Histórico diário</strong> (se o fechamento diário geral coincide com a soma dos históricos de cada classe de ativo).
            </p>
          </div>
        </div>
      </div>
      <div className="p-4 grid grid-cols-1 lg:grid-cols-2 gap-3.5">
        {intradayQuery.isLoading ? (
          <div className="h-36 skeleton rounded-xl" aria-label="Validando valuation atual" />
        ) : intradayQuery.isError || !intradayQuery.data ? (
          <QueryFailure onRetry={() => { void intradayQuery.refetch() }} />
        ) : (
          <ReconciliationCard
            label="Valuation intradiário"
            purpose="Auditoria em tempo real"
            presentation={presentIntradayReconciliation(intradayQuery.data)}
            reference={`Referência: ${formatReferenceDate(intradayQuery.data.valuation_updated_at) ?? 'sem horário'}`}
            detail={`${intradayQuery.data.positions_groups_count} grupos · ${intradayQuery.data.distribution_classes_count} classes`}
            checks={intradayQuery.data.checks}
          />
        )}

        {classQuery.isLoading ? (
          <div className="h-36 skeleton rounded-xl" aria-label="Validando snapshots por classe" />
        ) : classQuery.isError || !classQuery.data ? (
          <QueryFailure onRetry={() => { void classQuery.refetch() }} />
        ) : (
          <ReconciliationCard
            label="Snapshot consolidado × classes"
            purpose="Auditoria do histórico diário"
            presentation={presentClassReconciliation(classQuery.data)}
            reference={`Fechamento: ${formatReferenceDate(classQuery.data.snapshot_date) ?? classQuery.data.snapshot_date ?? 'ainda indisponível'}`}
            detail={classQuery.data.is_comparable ? 'Mesma data de referência' : 'Bases não comparáveis'}
            checks={classQuery.data.checks}
          />
        )}
      </div>
    </section>
  )
}
