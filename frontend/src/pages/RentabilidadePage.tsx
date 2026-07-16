import { useState } from 'react'
import {
  useRentabilidadeKpis,
  useRentabilidadeAtivos,
  useRentabilidadeClasses,
} from '@/hooks/useRentabilidade'
import type { RentabilidadeAtivo, RentabilidadeClasse } from '@/hooks/useRentabilidade'
import { formatBRL, formatPercent } from '@/utils/format'
import KpiCard from '@/components/ui/KpiCard'
import RentabilidadeChart from '@/components/charts/RentabilidadeChart'
import EmptyState from '@/components/ui/EmptyState'
import { TrendingUp } from 'lucide-react'
import { useAppStore } from '@/store/appStore'

function safeNum(v: unknown): number {
  const n = Number(v)
  return isFinite(n) ? n : 0
}

function pnlColor(value: unknown): string {
  const n = safeNum(value)
  if (n > 0) return 'var(--color-success)'
  if (n < 0) return 'var(--color-notification)'
  return 'var(--color-text-muted)'
}

function pnlSign(value: unknown): string {
  return safeNum(value) > 0 ? '+' : ''
}

function formatTwr(value: number | null | undefined): string {
  if (value == null) return '—'
  return `${pnlSign(value)}${formatPercent(value)}`
}

const ASSET_TYPE_LABEL: Record<string, string> = {
  ACAO: 'Ações',
  FII: 'FIIs',
  ETF_NACIONAL: 'ETFs Nacionais',
  STOCK: 'Stocks',
  ETF_INTERNACIONAL: 'ETFs Internacionais',
  BDR: 'BDRs',
  CRIPTO: 'Criptomoedas',
  TESOURO_DIRETO: 'Tesouro Direto',
  RENDA_FIXA: 'Renda Fixa',
}

function labelTipo(tipo: string) {
  return ASSET_TYPE_LABEL[tipo] ?? tipo
}

const ASSET_TYPE_OPTIONS = [
  { label: 'Todos', value: '' },
  { label: 'Ações', value: 'ACAO' },
  { label: 'FIIs', value: 'FII' },
  { label: 'ETFs Nacionais', value: 'ETF_NACIONAL' },
  { label: 'Stocks', value: 'STOCK' },
  { label: 'ETFs Internacionais', value: 'ETF_INTERNACIONAL' },
  { label: 'BDRs', value: 'BDR' },
  { label: 'Criptomoedas', value: 'CRIPTO' },
  { label: 'Tesouro Direto', value: 'TESOURO_DIRETO' },
  { label: 'Renda Fixa', value: 'RENDA_FIXA' },
]

function formatReference(value: string | null): string | null {
  if (!value) return null
  const parsed = new Date(`${value.slice(0, 10)}T00:00:00`)
  if (Number.isNaN(parsed.getTime())) return null
  return parsed.toLocaleDateString('pt-BR')
}

function ClasseBar({ classe }: { classe: RentabilidadeClasse }) {
  const allocation = safeNum(classe.allocation_pct)
  const currentValue = safeNum(classe.current_value)
  const capitalResult = classe.capital_result_value
  const accumulatedTwr = classe.accumulated_twr_pct
  const reference = formatReference(classe.performance_as_of)

  return (
    <div className="rounded-xl p-3" style={{ background: 'var(--color-surface-offset)', border: '1px solid var(--color-divider)' }}>
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="flex flex-col">
          <span className="text-xs font-semibold" style={{ color: 'var(--color-text)' }}>{labelTipo(classe.asset_type)}</span>
          <span className="text-[10px]" style={{ color: 'var(--color-text-faint)' }}>{classe.asset_count} ativo{classe.asset_count !== 1 ? 's' : ''}</span>
        </div>
        {classe.twr_available && accumulatedTwr != null ? (
          <div className="flex flex-col items-end">
            <span className="text-xs tabular-nums font-semibold" style={{ color: pnlColor(accumulatedTwr) }}>{formatTwr(accumulatedTwr)}</span>
            <span className="text-[10px]" style={{ color: 'var(--color-text-faint)' }}>TWR acumulado{classe.return_is_estimated ? ' estimado' : ''}</span>
          </div>
        ) : (
          <div className="flex flex-col items-end max-w-[170px]">
            <span className="text-[10px] font-semibold" style={{ color: 'var(--color-text-muted)' }}>TWR indisponível</span>
            <span className="text-[10px] text-right" style={{ color: 'var(--color-text-faint)' }}>
              {classe.performance_status === 'awaiting_backfill' ? 'Histórico aguardando materialização' : 'Série diária dedicada ainda não disponível'}
            </span>
          </div>
        )}
      </div>

      <div className="grid grid-cols-2 gap-3 mb-2">
        <div className="flex flex-col">
          <span className="text-[10px]" style={{ color: 'var(--color-text-faint)' }}>Patrimônio atual</span>
          <span className="text-xs tabular-nums" style={{ color: 'var(--color-text)' }}>{formatBRL(currentValue)}</span>
        </div>
        <div className="flex flex-col items-end">
          <span className="text-[10px] text-right" style={{ color: 'var(--color-text-faint)' }}>{classe.result_label}</span>
          <span className="text-xs tabular-nums" style={{ color: pnlColor(capitalResult) }}>{capitalResult == null ? '—' : `${pnlSign(capitalResult)}${formatBRL(capitalResult)}`}</span>
        </div>
      </div>

      <div className="w-full rounded-full" style={{ height: 7, background: 'var(--color-surface-dynamic)' }}>
        <div className="h-full rounded-full transition-all" style={{ width: `${Math.min(allocation, 100)}%`, background: 'var(--color-primary)' }} />
      </div>
      <div className="flex justify-between gap-2 mt-1 text-[10px]" style={{ color: 'var(--color-text-faint)' }}>
        <span>{allocation.toFixed(1)}% do patrimônio</span>
        <span>{reference ? `TWR até ${reference}` : classe.valuation_label}</span>
      </div>

      {!classe.twr_available && classe.performance_reason && (
        <p className="text-[10px] mt-2" style={{ color: 'var(--color-text-faint)' }}>{classe.performance_reason}</p>
      )}
      {classe.has_partial_prices && <p className="text-[10px] mt-1" style={{ color: 'var(--color-warning)' }}>Cobertura parcial de preços no fechamento da classe</p>}
    </div>
  )
}

function AtivoRow({ ativo }: { ativo: RentabilidadeAtivo }) {
  const unrealizedPnl = safeNum(ativo.unrealized_pnl)
  const unrealizedPct = safeNum(ativo.unrealized_pct)
  const realizedPnl = safeNum(ativo.realized_pnl)
  const totalPnl = safeNum(ativo.total_pnl)
  const totalPnlPct = safeNum(ativo.total_pnl_pct)
  const currentValue = safeNum(ativo.current_value)
  const avgPrice = safeNum(ativo.avg_price)
  const quantity = safeNum(ativo.quantity)

  return (
    <tr className="border-b" style={{ borderColor: 'oklch(from var(--color-text) l c h / 0.06)' }}>
      <td className="py-3 pr-3"><div className="flex flex-col"><span className="text-xs font-semibold" style={{ color: 'var(--color-text)' }}>{ativo.ticker}</span><span className="text-[10px] truncate max-w-[180px]" style={{ color: 'var(--color-text-faint)' }}>{ativo.name}</span></div></td>
      <td className="py-3 pr-3 text-right"><span className="text-xs tabular-nums" style={{ color: 'var(--color-text-muted)' }}>{ativo.is_open ? quantity.toLocaleString('pt-BR') : '—'}</span></td>
      <td className="py-3 pr-3 text-right"><span className="text-xs tabular-nums" style={{ color: 'var(--color-text-muted)' }}>{ativo.is_open ? formatBRL(avgPrice) : '—'}</span></td>
      <td className="py-3 pr-3 text-right"><span className="text-xs tabular-nums" style={{ color: 'var(--color-text)' }}>{ativo.is_open ? formatBRL(currentValue) : '—'}</span></td>
      <td className="py-3 pr-3 text-right"><div className="flex flex-col items-end"><span className="text-xs tabular-nums font-medium" style={{ color: pnlColor(unrealizedPnl) }}>{ativo.is_open ? `${pnlSign(unrealizedPnl)}${formatBRL(unrealizedPnl)}` : '—'}</span>{ativo.is_open && <span className="text-[10px] tabular-nums" style={{ color: pnlColor(unrealizedPct) }}>{pnlSign(unrealizedPct)}{formatPercent(unrealizedPct)}</span>}</div></td>
      <td className="py-3 pr-3 text-right"><span className="text-xs tabular-nums font-medium" style={{ color: pnlColor(realizedPnl) }}>{realizedPnl !== 0 ? `${pnlSign(realizedPnl)}${formatBRL(realizedPnl)}` : '—'}</span></td>
      <td className="py-3 text-right"><div className="flex flex-col items-end"><span className="text-xs tabular-nums font-semibold" style={{ color: pnlColor(totalPnl) }}>{pnlSign(totalPnl)}{formatBRL(totalPnl)}</span><span className="text-[10px] tabular-nums" style={{ color: pnlColor(totalPnlPct) }}>{pnlSign(totalPnlPct)}{formatPercent(totalPnlPct)}</span></div></td>
    </tr>
  )
}

export default function RentabilidadePage() {
  const portfolioId = useAppStore(s => s.selectedPortfolioId)
  const [assetTypeFilter, setAssetTypeFilter] = useState('')
  const [showZeradas, setShowZeradas] = useState(false)

  const { data: kpis, isLoading: loadingKpis } = useRentabilidadeKpis(portfolioId)
  const { data: ativos, isLoading: loadingAtivos } = useRentabilidadeAtivos(portfolioId)
  const { data: classes, isLoading: loadingClasses } = useRentabilidadeClasses(portfolioId)

  const ativosFiltrados = (ativos ?? []).filter(a => {
    if (!showZeradas && !a.is_open) return false
    if (assetTypeFilter && a.asset_type !== assetTypeFilter) return false
    return true
  })

  if (!portfolioId) return <div className="page-container"><EmptyState icon={TrendingUp} title="Nenhuma carteira selecionada" description="Selecione uma carteira no menu superior para visualizar a rentabilidade." /></div>

  const performanceReference = formatReference(kpis?.performance_as_of ?? null)
  const proventosReference = formatReference(kpis?.proventos_as_of ?? null)

  return (
    <div className="page-container">
      <div className="page-header">
        <div><h1 className="page-title">Rentabilidade</h1><p className="page-subtitle">TWR fechado, resultados financeiros e benchmarks</p></div>
        {performanceReference && <span className="text-xs" style={{ color: 'var(--color-text-faint)' }}>Performance até {performanceReference}{kpis?.return_is_estimated ? ' · estimada' : ''}</span>}
      </div>

      {loadingKpis ? <div className="kpi-grid">{[...Array(4)].map((_, i) => <div key={i} className="card h-[88px] skeleton" />)}</div> : (
        <>
          <div className="kpi-grid">
            <KpiCard label="Patrimônio atual" value={formatBRL(safeNum(kpis?.patrimonio_atual))} subValue={formatBRL(safeNum(kpis?.custo_posicoes_abertas))} subLabel="Custo das posições abertas" />
            <KpiCard label="Resultado total" value={formatBRL(safeNum(kpis?.resultado_total))} valueColor={pnlColor(kpis?.resultado_total)} />
            <KpiCard label="TWR no mês" value={formatTwr(kpis?.twr_mes_pct)} valueColor={pnlColor(kpis?.twr_mes_pct)} />
            <KpiCard label="TWR em 12 meses" value={formatTwr(kpis?.twr_12m_pct)} valueColor={pnlColor(kpis?.twr_12m_pct)} />
          </div>
          <div className="kpi-grid">
            <KpiCard label="TWR desde o início" value={formatTwr(kpis?.twr_desde_inicio_pct)} valueColor={pnlColor(kpis?.twr_desde_inicio_pct)} subValue={formatTwr(kpis?.twr_dia_pct)} subLabel="Último fechamento" />
            <KpiCard label="Resultado realizado" value={formatBRL(safeNum(kpis?.resultado_realizado))} valueColor={pnlColor(kpis?.resultado_realizado)} />
            <KpiCard label="Proventos recebidos" value={formatBRL(safeNum(kpis?.proventos_total))} subValue={formatBRL(safeNum(kpis?.proventos_12m))} subLabel="Últimos 12 meses" />
            <KpiCard label="Resultado não realizado" value={formatBRL(safeNum(kpis?.resultado_nao_realizado))} valueColor={pnlColor(kpis?.resultado_nao_realizado)} />
          </div>
        </>
      )}

      {kpis && <p className="text-[10px]" style={{ color: 'var(--color-text-faint)' }}>Valuation intradiário · TWR até {performanceReference ?? 'indisponível'} · Proventos até {proventosReference ?? 'indisponível'} · Cobertura {kpis.price_coverage_pct.toFixed(1)}%</p>}
      {kpis?.has_partial_prices && <p className="text-xs" style={{ color: 'var(--color-warning)' }}>A performance fechada possui cobertura parcial de preços e deve ser interpretada como estimada.</p>}

      <RentabilidadeChart portfolioId={portfolioId} />

      <div className="flex flex-col gap-4">
        <div className="card overflow-hidden">
          <div className="section-card-header"><span className="text-xs font-semibold">TWR e resultado por classe</span></div>
          <div className="p-4">{loadingClasses ? <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">{[...Array(3)].map((_, i) => <div key={i} className="h-24 skeleton rounded" />)}</div> : (classes ?? []).length === 0 ? <p className="text-xs" style={{ color: 'var(--color-text-faint)' }}>Sem dados</p> : <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">{(classes ?? []).map(c => <ClasseBar key={c.asset_type} classe={c} />)}</div>}</div>
        </div>

        <div className="card overflow-hidden">
          <div className="section-card-header flex-wrap gap-2">
            <div className="flex flex-col"><span className="text-xs font-semibold">Resultado por ativo</span><span className="text-[10px]" style={{ color: 'var(--color-text-faint)' }}>Percentuais simples de resultado; não representam TWR individual</span></div>
            <div className="flex items-center gap-2 flex-wrap"><select value={assetTypeFilter} onChange={e => setAssetTypeFilter(e.target.value)} className="input text-xs" style={{ width: 220 }}>{ASSET_TYPE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}</select><button onClick={() => setShowZeradas(v => !v)} className="px-3 py-1 rounded text-xs font-medium transition-colors" style={{ background: showZeradas ? 'oklch(from var(--color-primary) l c h / 0.15)' : 'var(--color-surface-offset)', color: showZeradas ? 'var(--color-primary)' : 'var(--color-text-muted)' }}>Posições zeradas</button></div>
          </div>
          <div className="p-4 table-responsive">
            {loadingAtivos ? <div className="flex flex-col gap-2">{[...Array(5)].map((_, i) => <div key={i} className="h-10 skeleton rounded" />)}</div> : ativosFiltrados.length === 0 ? <p className="text-xs py-4 text-center" style={{ color: 'var(--color-text-faint)' }}>Nenhum ativo encontrado</p> : <table className="w-full min-w-[920px]"><thead><tr style={{ borderBottom: '1px solid oklch(from var(--color-text) l c h / 0.08)' }}>{['Ativo', 'Qtd', 'P.M.', 'Val. atual', 'Resultado n.r.', 'Resultado real.', 'Resultado total'].map(h => <th key={h} className={`pb-2 text-xs font-medium ${h === 'Ativo' ? 'text-left' : 'text-right'} ${h !== 'Resultado total' ? 'pr-3' : ''}`} style={{ color: 'var(--color-text-faint)' }}>{h}</th>)}</tr></thead><tbody>{ativosFiltrados.map(a => <AtivoRow key={a.ticker} ativo={a} />)}</tbody></table>}
            {ativosFiltrados.length > 0 && <p className="text-[10px] mt-3 text-right" style={{ color: 'var(--color-text-faint)' }}>{ativosFiltrados.length} ativo{ativosFiltrados.length !== 1 ? 's' : ''}{!showZeradas && (ativos ?? []).some(a => !a.is_open) && <> · <button onClick={() => setShowZeradas(true)} style={{ color: 'var(--color-primary)', textDecoration: 'underline' }}>ver posições zeradas</button></>}</p>}
          </div>
        </div>
      </div>
    </div>
  )
}
