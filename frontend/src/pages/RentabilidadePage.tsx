import { useState } from 'react'
import { usePortfolioList } from '@/hooks/usePortfolio'
import type { PortfolioListItem } from '@/hooks/usePortfolio'
import {
  useRentabilidadeKpis,
  useRentabilidadeAtivos,
  useRentabilidadeClasses,
} from '@/hooks/useRentabilidade'
import type { RentabilidadeAtivo, RentabilidadeClasse } from '@/hooks/useRentabilidade'
import { formatBRL, formatPercent } from '@/utils/format'
import KpiCard from '@/components/ui/KpiCard'
import RentabilidadeChart from '@/components/charts/RentabilidadeChart'
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

const ASSET_TYPE_LABEL: Record<string, string> = {
  ACAO:              'Ações',
  FII:               'FIIs',
  ETF_NACIONAL:      'ETFs Nacionais',
  STOCK:             'Stocks',
  ETF_INTERNACIONAL: 'ETFs Internacionais',
  TESOURO:           'Tesouro Direto',
  RENDA_FIXA:        'Renda Fixa',
}

function labelTipo(tipo: string) {
  return ASSET_TYPE_LABEL[tipo] ?? tipo
}

const ASSET_TYPE_OPTIONS = [
  { label: 'Todos',                value: '' },
  { label: 'Ações',                value: 'ACAO' },
  { label: 'FIIs',                 value: 'FII' },
  { label: 'ETFs Nacionais',       value: 'ETF_NACIONAL' },
  { label: 'Stocks',               value: 'STOCK' },
  { label: 'ETFs Internacionais',  value: 'ETF_INTERNACIONAL' },
]

function ClasseBar({ classe }: { classe: RentabilidadeClasse }) {
  const alocacao  = safeNum(classe.alocacao_pct)
  const pnlPct    = safeNum(classe.total_pnl_pct)
  const currValue = safeNum(classe.current_value)

  return (
    <div className="rounded-xl p-3" style={{ background: 'var(--color-surface-offset)', border: '1px solid var(--color-divider)' }}>
      <div className="flex items-center justify-between gap-3 mb-2">
        <span className="text-xs font-semibold" style={{ color: 'var(--color-text)' }}>{labelTipo(classe.asset_type)}</span>
        <span className="text-xs tabular-nums" style={{ color: pnlColor(pnlPct) }}>{pnlSign(pnlPct)}{formatPercent(pnlPct)}</span>
      </div>
      <div className="flex items-center justify-between gap-3 mb-2">
        <span className="text-xs tabular-nums" style={{ color: 'var(--color-text-muted)' }}>{formatBRL(currValue)}</span>
        <span className="text-[10px]" style={{ color: 'var(--color-text-faint)' }}>{classe.count ?? 0} ativo{(classe.count ?? 0) !== 1 ? 's' : ''}</span>
      </div>
      <div className="w-full rounded-full" style={{ height: 7, background: 'var(--color-surface-dynamic)' }}>
        <div className="h-full rounded-full transition-all" style={{ width: `${Math.min(alocacao, 100)}%`, background: 'var(--color-primary)' }} />
      </div>
      <div className="text-[10px] tabular-nums text-right mt-1" style={{ color: 'var(--color-text-faint)' }}>{alocacao.toFixed(1)}% do patrimônio</div>
    </div>
  )
}

function AtivoRow({ ativo }: { ativo: RentabilidadeAtivo }) {
  const unrealizedPnl = safeNum(ativo.unrealized_pnl)
  const unrealizedPct = safeNum(ativo.unrealized_pct)
  const realizedPnl   = safeNum(ativo.realized_pnl)
  const totalPnl      = safeNum(ativo.total_pnl)
  const totalPnlPct   = safeNum(ativo.total_pnl_pct)
  const currentValue  = safeNum(ativo.current_value)
  const avgPrice      = safeNum(ativo.avg_price)
  const quantity      = safeNum(ativo.quantity)

  return (
    <tr className="border-b" style={{ borderColor: 'oklch(from var(--color-text) l c h / 0.06)' }}>
      <td className="py-3 pr-3">
        <div className="flex flex-col">
          <span className="text-xs font-semibold" style={{ color: 'var(--color-text)' }}>{ativo.ticker}</span>
          <span className="text-[10px] truncate max-w-[180px]" style={{ color: 'var(--color-text-faint)' }}>{ativo.name}</span>
        </div>
      </td>
      <td className="py-3 pr-3 text-right"><span className="text-xs tabular-nums" style={{ color: 'var(--color-text-muted)' }}>{ativo.is_open ? quantity.toLocaleString('pt-BR') : '—'}</span></td>
      <td className="py-3 pr-3 text-right"><span className="text-xs tabular-nums" style={{ color: 'var(--color-text-muted)' }}>{ativo.is_open ? formatBRL(avgPrice) : '—'}</span></td>
      <td className="py-3 pr-3 text-right"><span className="text-xs tabular-nums" style={{ color: 'var(--color-text)' }}>{ativo.is_open ? formatBRL(currentValue) : '—'}</span></td>
      <td className="py-3 pr-3 text-right">
        <div className="flex flex-col items-end">
          <span className="text-xs tabular-nums font-medium" style={{ color: pnlColor(unrealizedPnl) }}>{ativo.is_open ? `${pnlSign(unrealizedPnl)}${formatBRL(unrealizedPnl)}` : '—'}</span>
          {ativo.is_open && <span className="text-[10px] tabular-nums" style={{ color: pnlColor(unrealizedPct) }}>{pnlSign(unrealizedPct)}{formatPercent(unrealizedPct)}</span>}
        </div>
      </td>
      <td className="py-3 pr-3 text-right"><span className="text-xs tabular-nums font-medium" style={{ color: pnlColor(realizedPnl) }}>{realizedPnl !== 0 ? `${pnlSign(realizedPnl)}${formatBRL(realizedPnl)}` : '—'}</span></td>
      <td className="py-3 text-right">
        <div className="flex flex-col items-end">
          <span className="text-xs tabular-nums font-semibold" style={{ color: pnlColor(totalPnl) }}>{pnlSign(totalPnl)}{formatBRL(totalPnl)}</span>
          <span className="text-[10px] tabular-nums" style={{ color: pnlColor(totalPnlPct) }}>{pnlSign(totalPnlPct)}{formatPercent(totalPnlPct)}</span>
        </div>
      </td>
    </tr>
  )
}

export default function RentabilidadePage() {
  const { data: portfolios } = usePortfolioList()
  const globalPortfolioId = useAppStore(s => s.selectedPortfolioId)
  const [selectedPortfolio, setSelectedPortfolio] = useState<number | null>(null)
  const portfolioId = selectedPortfolio ?? globalPortfolioId ?? (portfolios?.[0]?.id ?? 0)
  const [assetTypeFilter, setAssetTypeFilter] = useState('')
  const [showZeradas, setShowZeradas] = useState(false)

  const { data: kpis, isLoading: loadingKpis } = useRentabilidadeKpis(portfolioId || null)
  const { data: ativos, isLoading: loadingAtivos } = useRentabilidadeAtivos(portfolioId || null)
  const { data: classes, isLoading: loadingClasses } = useRentabilidadeClasses(portfolioId || null)

  const ativosFiltrados = (ativos ?? []).filter(a => {
    if (!showZeradas && !a.is_open) return false
    if (assetTypeFilter && a.asset_type !== assetTypeFilter) return false
    return true
  })

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1 className="page-title">Rentabilidade</h1>
          <p className="page-subtitle">Performance e retorno da carteira</p>
        </div>
        {kpis?.snapshot_date && (
          <span className="text-xs" style={{ color: 'var(--color-text-faint)' }}>Atualizado em {new Date(kpis.snapshot_date + 'T00:00:00').toLocaleDateString('pt-BR')}</span>
        )}
      </div>

      {(portfolios?.length ?? 0) > 1 && (
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>Carteira:</span>
          {(portfolios ?? []).map((p: PortfolioListItem) => (
            <button key={p.id} onClick={() => setSelectedPortfolio(p.id)} className="px-3 py-1 rounded text-xs font-medium transition-colors" style={{ background: portfolioId === p.id ? 'oklch(from var(--color-primary) l c h / 0.15)' : 'var(--color-surface-offset)', color: portfolioId === p.id ? 'var(--color-primary)' : 'var(--color-text-muted)' }}>{p.name}</button>
          ))}
        </div>
      )}

      {loadingKpis ? (
        <div className="kpi-grid">{[...Array(4)].map((_, i) => <div key={i} className="card h-[88px] skeleton" />)}</div>
      ) : (
        <>
          <div className="kpi-grid">
            <KpiCard label="Patrimônio atual" value={formatBRL(safeNum(kpis?.patrimonio_atual))} subValue={formatBRL(safeNum(kpis?.total_aportado))} subLabel="Valor investido" />
            <KpiCard label="Resultado total" value={formatBRL(safeNum(kpis?.total_pnl))} valueColor={pnlColor(kpis?.total_pnl)} change={safeNum(kpis?.retorno_total_pct)} />
            <KpiCard label="Retorno no mês" value={kpis ? `${pnlSign(kpis.retorno_mes_pct)}${formatPercent(safeNum(kpis.retorno_mes_pct))}` : '—'} valueColor={pnlColor(kpis?.retorno_mes_pct)} />
            <KpiCard label="Retorno 12 meses" value={kpis ? `${pnlSign(kpis.retorno_12m_pct)}${formatPercent(safeNum(kpis.retorno_12m_pct))}` : '—'} valueColor={pnlColor(kpis?.retorno_12m_pct)} />
          </div>

          <div className="kpi-grid">
            <KpiCard label="Ganho não realizado" value={formatBRL(safeNum(kpis?.ganho_nao_realizado))} valueColor={pnlColor(kpis?.ganho_nao_realizado)} subValue={kpis ? `${pnlSign(kpis.retorno_desde_inicio_pct)}${formatPercent(safeNum(kpis.retorno_desde_inicio_pct))}` : '—'} subLabel="Variação atual" />
            <KpiCard label="Ganho realizado" value={formatBRL(safeNum(kpis?.ganho_realizado))} valueColor={pnlColor(kpis?.ganho_realizado)} />
            <KpiCard label="Proventos recebidos" value={formatBRL(safeNum(kpis?.proventos_total))} subValue={formatBRL(safeNum(kpis?.proventos_12m))} subLabel="Últimos 12 meses" />
            <KpiCard label="Capital empregado" value={formatBRL(safeNum(kpis?.custo_total))} />
          </div>
        </>
      )}

      {portfolioId > 0 && <RentabilidadeChart portfolioId={portfolioId} />}

      <div className="flex flex-col gap-4">
        <div className="card overflow-hidden">
          <div className="section-card-header"><span className="text-xs font-semibold">Por classe</span></div>
          <div className="p-4">
            {loadingClasses ? (
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">{[...Array(3)].map((_, i) => <div key={i} className="h-20 skeleton rounded" />)}</div>
            ) : (classes ?? []).length === 0 ? (
              <p className="text-xs" style={{ color: 'var(--color-text-faint)' }}>Sem dados</p>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">{(classes ?? []).map(c => <ClasseBar key={c.asset_type} classe={c} />)}</div>
            )}
          </div>
        </div>

        <div className="card overflow-hidden">
          <div className="section-card-header flex-wrap gap-2">
            <span className="text-xs font-semibold">Por ativo</span>
            <div className="flex items-center gap-2 flex-wrap">
              <select value={assetTypeFilter} onChange={e => setAssetTypeFilter(e.target.value)} className="input text-xs" style={{ width: 220 }}>{ASSET_TYPE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}</select>
              <button onClick={() => setShowZeradas(v => !v)} className="px-3 py-1 rounded text-xs font-medium transition-colors" style={{ background: showZeradas ? 'oklch(from var(--color-primary) l c h / 0.15)' : 'var(--color-surface-offset)', color: showZeradas ? 'var(--color-primary)' : 'var(--color-text-muted)' }}>Posições zeradas</button>
            </div>
          </div>

          <div className="p-4 table-responsive">
            {loadingAtivos ? (
              <div className="flex flex-col gap-2">{[...Array(5)].map((_, i) => <div key={i} className="h-10 skeleton rounded" />)}</div>
            ) : ativosFiltrados.length === 0 ? (
              <p className="text-xs py-4 text-center" style={{ color: 'var(--color-text-faint)' }}>Nenhum ativo encontrado</p>
            ) : (
              <table className="w-full min-w-[920px]">
                <thead>
                  <tr style={{ borderBottom: '1px solid oklch(from var(--color-text) l c h / 0.08)' }}>
                    {['Ativo', 'Qtd', 'P.M.', 'Val. atual', 'Ganho n.r.', 'Ganho real.', 'Total'].map(h => (
                      <th key={h} className={`pb-2 text-xs font-medium ${h === 'Ativo' ? 'text-left' : 'text-right'} ${h !== 'Total' ? 'pr-3' : ''}`} style={{ color: 'var(--color-text-faint)' }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>{ativosFiltrados.map(a => <AtivoRow key={a.ticker} ativo={a} />)}</tbody>
              </table>
            )}

            {ativosFiltrados.length > 0 && (
              <p className="text-[10px] mt-3 text-right" style={{ color: 'var(--color-text-faint)' }}>
                {ativosFiltrados.length} ativo{ativosFiltrados.length !== 1 ? 's' : ''}
                {!showZeradas && (ativos ?? []).some(a => !a.is_open) && (
                  <> · <button onClick={() => setShowZeradas(true)} style={{ color: 'var(--color-primary)', textDecoration: 'underline' }}>ver posições zeradas</button></>
                )}
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
