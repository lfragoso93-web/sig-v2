import { useState } from 'react'
import {
  PieChart,
  ArrowUpRight,
  ArrowDownRight,
  CheckCircle2,
  TrendingUp,
  AlertTriangle,
  Layers,
  Info,
  RefreshCw,
} from 'lucide-react'
import { useAppStore } from '@/store/appStore'
import {
  usePortfolioAnalysis,
  type ClassAnalysisDetail,
} from '@/hooks/usePortfolioAnalysis'
import { formatBRL } from '@/utils/format'
import KpiCard from '@/components/ui/KpiCard'
import EmptyState from '@/components/ui/EmptyState'

function healthColor(score: number): string {
  if (score >= 80) return 'var(--color-success)'
  if (score >= 60) return 'var(--color-primary)'
  if (score >= 40) return 'var(--color-warning)'
  return 'var(--color-notification)'
}

function healthLabel(score: number): string {
  if (score >= 80) return 'Excelente'
  if (score >= 60) return 'Equilibrada'
  if (score >= 40) return 'Atenção'
  return 'Desbalanceada'
}

function concentrationBadge(level: string): { bg: string; text: string; label: string } {
  switch (level) {
    case 'critical':
      return { bg: 'oklch(from var(--color-notification) l c h / 0.12)', text: 'var(--color-notification)', label: 'Crítico' }
    case 'warning':
      return { bg: 'oklch(from var(--color-warning) l c h / 0.15)', text: 'var(--color-warning)', label: 'Atenção' }
    case 'balanced':
      return { bg: 'oklch(from var(--color-primary) l c h / 0.12)', text: 'var(--color-primary)', label: 'Equilibrado' }
    default:
      return { bg: 'oklch(from var(--color-success) l c h / 0.12)', text: 'var(--color-success)', label: 'Baixo' }
  }
}

function ClassAnalysisCard({ detail }: { detail: ClassAnalysisDetail }) {
  const [expanded, setExpanded] = useState(false)
  const isBuy = detail.allocation.rebalance_action === 'buy'
  const isReduce = detail.allocation.rebalance_action === 'reduce'
  const concBadge = concentrationBadge(detail.concentration.risk_level)

  return (
    <div
      className="rounded-xl overflow-hidden"
      style={{
        background: 'var(--color-surface)',
        border: '1px solid var(--color-border)',
        boxShadow: 'var(--shadow-sm)',
      }}
    >
      {/* Header */}
      <div
        className="p-4 flex items-center justify-between flex-wrap gap-3 cursor-pointer"
        onClick={() => setExpanded(e => !e)}
        style={{ borderBottom: '1px solid var(--color-divider)' }}
      >
        <div className="flex items-center gap-3">
          <div
            className="w-10 h-10 rounded-lg flex items-center justify-center font-bold text-sm"
            style={{
              background: 'var(--color-surface-offset)',
              color: 'var(--color-primary)',
            }}
          >
            {detail.label.slice(0, 2).toUpperCase()}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-semibold text-sm">{detail.label}</span>
              <span
                className="text-[10px] px-2 py-0.5 rounded-full font-medium"
                style={{ background: concBadge.bg, color: concBadge.text }}
              >
                Risco {concBadge.label}
              </span>
            </div>
            <p className="text-xs text-muted">
              {detail.concentration.asset_count} ativo{detail.concentration.asset_count !== 1 ? 's' : ''} · {formatBRL(detail.allocation.current_value)}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-6">
          {/* Target comparison */}
          <div className="text-right">
            <div className="text-xs font-semibold tabular-nums">
              {detail.allocation.current_weight_pct.toFixed(1)}%
              {detail.allocation.target_weight_pct !== null && (
                <span className="text-muted font-normal"> / meta {detail.allocation.target_weight_pct.toFixed(1)}%</span>
              )}
            </div>
            {detail.allocation.gap_weight_pct !== null && (
              <span
                className="text-[11px] font-medium flex items-center justify-end gap-0.5"
                style={{
                  color: isBuy ? 'var(--color-primary)' : isReduce ? 'var(--color-warning)' : 'var(--color-success)',
                }}
              >
                {isBuy && <ArrowUpRight size={12} />}
                {isReduce && <ArrowDownRight size={12} />}
                {detail.allocation.gap_weight_pct > 0 ? `+${detail.allocation.gap_weight_pct.toFixed(1)}%` : `${detail.allocation.gap_weight_pct.toFixed(1)}%`}
              </span>
            )}
          </div>

          {/* Health Score Pill */}
          <div
            className="px-2.5 py-1 rounded-lg font-bold text-xs flex items-center gap-1"
            style={{
              background: 'var(--color-surface-offset)',
              color: healthColor(detail.health_score),
            }}
          >
            <span>{detail.health_score}</span>
            <span className="text-[10px] font-normal text-muted">/100</span>
          </div>
        </div>
      </div>

      {/* Body */}
      <div className="p-4 flex flex-col gap-4">
        {/* Allocation Progress Bar */}
        <div>
          <div className="flex justify-between text-xs mb-1.5">
            <span className="text-muted">Alocação no patrimônio</span>
            <span className="font-medium tabular-nums">
              {detail.allocation.current_weight_pct.toFixed(1)}%
              {detail.allocation.target_weight_pct !== null && ` de ${detail.allocation.target_weight_pct.toFixed(1)}%`}
            </span>
          </div>
          <div
            className="w-full rounded-full overflow-hidden"
            style={{ height: 8, background: 'var(--color-surface-offset)' }}
          >
            <div
              className="h-full rounded-full transition-all"
              style={{
                width: `${Math.min(detail.allocation.current_weight_pct, 100)}%`,
                background: isBuy ? 'var(--color-primary)' : isReduce ? 'var(--color-warning)' : 'var(--color-success)',
              }}
            />
          </div>
        </div>

        {/* Suggestion / Rebalance alert */}
        <div
          className="p-3 rounded-lg flex items-start gap-2.5 text-xs"
          style={{
            background: isBuy
              ? 'oklch(from var(--color-primary) l c h / 0.08)'
              : isReduce
              ? 'oklch(from var(--color-warning) l c h / 0.08)'
              : 'oklch(from var(--color-success) l c h / 0.08)',
            border: `1px solid ${
              isBuy
                ? 'oklch(from var(--color-primary) l c h / 0.2)'
                : isReduce
                ? 'oklch(from var(--color-warning) l c h / 0.2)'
                : 'oklch(from var(--color-success) l c h / 0.2)'
            }`,
          }}
        >
          {isBuy ? (
            <ArrowUpRight size={16} className="shrink-0 mt-0.5" style={{ color: 'var(--color-primary)' }} />
          ) : isReduce ? (
            <AlertTriangle size={16} className="shrink-0 mt-0.5" style={{ color: 'var(--color-warning)' }} />
          ) : (
            <CheckCircle2 size={16} className="shrink-0 mt-0.5" style={{ color: 'var(--color-success)' }} />
          )}
          <div className="flex flex-col gap-0.5">
            <span className="font-semibold" style={{ color: 'var(--color-text)' }}>
              {detail.allocation.suggested_action_label}
            </span>
            {detail.allocation.gap_value !== null && isBuy && (
              <span className="text-[11px] text-muted">
                Faltam {formatBRL(Math.abs(detail.allocation.gap_value))} para atingir a meta estipulada.
              </span>
            )}
          </div>
        </div>

        {/* KPI Grid for Class */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
          {/* Top Asset */}
          <div className="p-2.5 rounded-lg" style={{ background: 'var(--color-surface-offset)' }}>
            <span className="text-[10px] text-muted block mb-0.5">Top Ativo</span>
            <span className="font-semibold text-xs block truncate">
              {detail.concentration.top_asset?.ticker ?? '—'}
            </span>
            <span className="text-[10px] text-muted tabular-nums">
              {detail.concentration.top_asset
                ? `${detail.concentration.top_asset.weight_in_class_pct.toFixed(1)}% da classe`
                : 'Sem posições'}
            </span>
          </div>

          {/* Income (Proventos) */}
          <div className="p-2.5 rounded-lg" style={{ background: 'var(--color-surface-offset)' }}>
            <span className="text-[10px] text-muted block mb-0.5">Proventos Acumulados</span>
            <span className="font-semibold text-xs block tabular-nums">
              {detail.income.is_applicable ? formatBRL(detail.income.total_proventos) : 'N/A'}
            </span>
            <span className="text-[10px] text-muted truncate block">
              {detail.income.is_applicable && detail.income.weighted_dy_pct !== null
                ? `DY Histórico: ${detail.income.weighted_dy_pct.toFixed(1)}%`
                : 'Classe de valorização'}
            </span>
          </div>

          {/* Fixed Income / Indexer */}
          {detail.fixed_income.is_applicable ? (
            <div className="p-2.5 rounded-lg" style={{ background: 'var(--color-surface-offset)' }}>
              <span className="text-[10px] text-muted block mb-0.5">Indexadores RF</span>
              <span className="font-semibold text-xs block">
                CDI {detail.fixed_income.cdi_allocation_pct ?? 0}% · IPCA {detail.fixed_income.ipca_allocation_pct ?? 0}%
              </span>
              <span className="text-[10px] text-muted">
                Pré: {detail.fixed_income.pre_allocation_pct ?? 0}%
              </span>
            </div>
          ) : (
            <div className="p-2.5 rounded-lg" style={{ background: 'var(--color-surface-offset)' }}>
              <span className="text-[10px] text-muted block mb-0.5">Índice HHI</span>
              <span className="font-semibold text-xs block tabular-nums">
                {detail.concentration.hhi_score ?? '—'}
              </span>
              <span className="text-[10px] text-muted">
                {detail.concentration.risk_label}
              </span>
            </div>
          )}

          {/* Health Score */}
          <div className="p-2.5 rounded-lg" style={{ background: 'var(--color-surface-offset)' }}>
            <span className="text-[10px] text-muted block mb-0.5">Saúde da Classe</span>
            <span className="font-semibold text-xs block" style={{ color: healthColor(detail.health_score) }}>
              {detail.health_score}/100 · {healthLabel(detail.health_score)}
            </span>
            <span className="text-[10px] text-muted">Equilíbrio & risco</span>
          </div>
        </div>

        {/* Key findings bullets if expanded */}
        {expanded && detail.key_findings.length > 0 && (
          <div className="pt-2 border-t" style={{ borderColor: 'var(--color-divider)' }}>
            <span className="text-[11px] font-semibold text-muted block mb-1.5">Diagnósticos da Classe:</span>
            <ul className="list-disc list-inside text-xs space-y-1 text-muted">
              {detail.key_findings.map((f, i) => (
                <li key={i} style={{ color: 'var(--color-text)' }}>{f}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  )
}

export default function AnalisePage() {
  const { selectedPortfolioId } = useAppStore()
  const { data: analysis, isLoading, error, refetch } = usePortfolioAnalysis(selectedPortfolioId)

  if (!selectedPortfolioId) {
    return (
      <div className="page-container">
        <EmptyState
          icon={PieChart}
          title="Nenhuma carteira selecionada"
          description="Selecione uma carteira na barra lateral para visualizar os diagnósticos e análises por classe."
        />
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="page-container flex flex-col gap-4">
        <div className="skeleton h-8 w-64 rounded" />
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="skeleton h-24 rounded-xl" />
          ))}
        </div>
        <div className="skeleton h-48 w-full rounded-xl" />
      </div>
    )
  }

  if (error || !analysis) {
    return (
      <div className="page-container">
        <div className="card p-8 flex flex-col items-center justify-center text-center gap-3">
          <AlertTriangle size={32} style={{ color: 'var(--color-notification)' }} />
          <h2 className="text-base font-semibold">Não foi possível carregar a análise da carteira</h2>
          <p className="text-xs text-muted max-w-md">
            Verifique sua conexão ou se a carteira possui lançamentos cadastrados.
          </p>
          <button onClick={() => refetch()} className="btn btn-secondary text-xs flex items-center gap-2">
            <RefreshCw size={14} /> Tentar novamente
          </button>
        </div>
      </div>
    )
  }

  const score = analysis.overall_health_score
  const scoreColor = healthColor(score)

  return (
    <div className="page-container flex flex-col gap-6">
      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title flex items-center gap-2">
            <PieChart size={24} style={{ color: 'var(--color-primary)' }} />
            Análise de Carteira
          </h1>
          <p className="page-subtitle">
            {analysis.portfolio_name} · Diagnóstico determinístico por classe de ativos e rebalanceamento
          </p>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <KpiCard
          label="Score de Alocação"
          value={`${score}/100`}
          valueColor={scoreColor}
          subLabel={`Classificação: ${healthLabel(score)}`}
        />
        <KpiCard
          label="Patrimônio Analisado"
          value={formatBRL(analysis.total_value)}
          subLabel={`${analysis.classes_analyzed_count} classes ativas`}
        />
        <KpiCard
          label="Classes com Desvio"
          value={analysis.rebalance_priority_classes.length.toString()}
          valueColor={analysis.rebalance_priority_classes.length > 0 ? 'var(--color-warning)' : 'var(--color-success)'}
          subLabel={
            analysis.rebalance_priority_classes.length > 0
              ? `${analysis.rebalance_priority_classes.join(', ')}`
              : 'Nenhuma classe crítica'
          }
        />
        <KpiCard
          label="Maior Divergência"
          value={analysis.max_divergence_class ?? 'Nenhuma'}
          subLabel="Prioridade máxima de rebalanceamento"
        />
      </div>

      {/* Rebalance Priority Alert */}
      {analysis.rebalance_priority_classes.length > 0 && (
        <div
          className="rounded-xl p-4 flex items-start gap-3"
          style={{
            background: 'oklch(from var(--color-primary) l c h / 0.08)',
            border: '1px solid oklch(from var(--color-primary) l c h / 0.2)',
          }}
        >
          <TrendingUp size={20} style={{ color: 'var(--color-primary)' }} className="shrink-0 mt-0.5" />
          <div className="flex flex-col gap-1">
            <span className="font-semibold text-xs" style={{ color: 'var(--color-text)' }}>
              Oportunidades de Rebalanceamento Identificadas
            </span>
            <p className="text-xs text-muted">
              Para convergir à alocação estratégica de longo prazo, priorize aportes em: <strong>{analysis.rebalance_priority_classes.join(', ')}</strong>.
            </p>
          </div>
        </div>
      )}

      {/* Classes Breakdown */}
      <div className="flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold flex items-center gap-2">
            <Layers size={16} /> Diagnóstico Detalhado por Classe
          </h2>
          <span className="text-xs text-muted">
            {analysis.classes_analyzed_count} classe{analysis.classes_analyzed_count !== 1 ? 's' : ''} avaliada{analysis.classes_analyzed_count !== 1 ? 's' : ''}
          </span>
        </div>

        {analysis.classes.length === 0 ? (
          <div className="card p-8 text-center text-xs text-muted">
            Nenhuma classe de ativos encontrada com posições ativas.
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            {analysis.classes.map(cls => (
              <ClassAnalysisCard key={cls.asset_type} detail={cls} />
            ))}
          </div>
        )}
      </div>

      {/* Provenance Box */}
      <div
        className="rounded-xl p-4 flex items-start gap-3 text-xs"
        style={{
          background: 'var(--color-surface-offset)',
          border: '1px solid var(--color-divider)',
        }}
      >
        <Info size={16} className="text-muted shrink-0 mt-0.5" />
        <div className="flex flex-col gap-1">
          <span className="font-semibold text-muted">Proveniência Canônica dos Dados:</span>
          <p className="text-[11px] text-muted">
            Cálculo 100% determinístico baseado nos serviços canônicos de valuation intradiário, histórico de proventos e metas de <code>portfolio_class_targets</code>. Nenhuma chamada externa a provedores de rede é realizada no caminho de análise.
          </p>
        </div>
      </div>
    </div>
  )
}
