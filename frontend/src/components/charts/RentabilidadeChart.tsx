import { useMemo, useState } from 'react'
import {
  ResponsiveContainer,
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
} from 'recharts'
import { useMonthlyEvolution, type PeriodOption } from '@/hooks/useEvolution'
import { useMonthlyBenchmarks } from '@/hooks/useRentabilidade'
import { formatBRL, formatPercent } from '@/utils/format'
import TwrHelpPopover from '@/components/ui/TwrHelpPopover'

export type ChartViewMode = 'monthly' | 'cumulative'
export type TableViewMode = 'progressive' | 'matrix'

interface ChartPoint {
  period: string
  label: string
  carteiraMes: number
  carteiraCrescimento: number
  carteiraDesdeInicio: number
  ibovMes?: number
  cdiMes?: number
  ipcaMes?: number
  ibovCrescimento?: number
  cdiCrescimento?: number
  ipcaCrescimento?: number
  pctCdiCrescimento?: number | null
  patrimonioFechamento: number
  resultadoAcumulado: number
  estimated: boolean
  partial: boolean
  snapshotDate: string
}

interface YearMatrixRow {
  year: string
  months: (number | null)[]
  ytdPct: number
  cumulativePct: number
}

const MONTH_SHORT = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
const PERIOD_OPTIONS: { label: string; value: PeriodOption }[] = [
  { label: '6 meses', value: '6m' },
  { label: '12 meses', value: '12m' },
  { label: '24 meses', value: '24m' },
  { label: 'Todo período', value: 'all' },
]

function ymToLabel(ym: string): string {
  const [year, month] = ym.split('-')
  return `${MONTH_SHORT[Number(month) - 1]}/${year.slice(2)}`
}

function pct(value: number): string {
  return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`
}

function pnlColor(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value) || value === 0) return 'var(--color-text-muted)'
  return value > 0 ? 'var(--color-success)' : 'var(--color-notification)'
}

function formatSignedPct(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) return '—'
  return `${value > 0 ? '+' : ''}${formatPercent(value)}`
}

function CustomTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null
  const point = payload[0]?.payload as ChartPoint | undefined
  if (!point) return null

  return (
    <div
      style={{
        background: 'var(--color-surface-2)',
        border: '1px solid oklch(from var(--color-text) l c h / 0.1)',
        borderRadius: 'var(--radius-md)',
        padding: '8px 12px',
        fontSize: 'var(--text-xs)',
        boxShadow: '0 4px 12px oklch(0 0 0 / 0.15)',
        minWidth: 196,
      }}
    >
      <p style={{ fontWeight: 700, color: 'var(--color-text)', marginBottom: 6 }}>{point.label}</p>
      {payload.map((entry: any) => (
        <div key={entry.dataKey} style={{ display: 'flex', justifyContent: 'space-between', gap: 16, color: entry.color }}>
          <span>{entry.name}</span>
          <span style={{ fontWeight: 600, fontVariantNumeric: 'tabular-nums' }}>
            {entry.value != null ? pct(Number(entry.value)) : '—'}
          </span>
        </div>
      ))}
      <p style={{ marginTop: 6, color: 'var(--color-text-faint)', fontSize: 10 }}>
        Fechamento de {new Date(`${point.snapshotDate}T00:00:00`).toLocaleDateString('pt-BR')}
        {point.estimated ? ' · estimado' : ''}
        {point.partial ? ' · cobertura parcial' : ''}
      </p>
    </div>
  )
}

export default function RentabilidadeChart({ portfolioId }: { portfolioId: number }) {
  const [period, setPeriod] = useState<PeriodOption>('12m')
  const [chartMode, setChartMode] = useState<ChartViewMode>('cumulative')
  const [tableMode, setTableMode] = useState<TableViewMode>('progressive')
  const [showIbov, setShowIbov] = useState(true)
  const [showCdi, setShowCdi] = useState(true)
  const [showIpca, setShowIpca] = useState(false)

  const { data: monthly, isLoading: loadingMonthly } = useMonthlyEvolution(portfolioId, period)
  const { data: allMonthly } = useMonthlyEvolution(portfolioId, 'all')
  const benchmarkMonths = period === 'all' ? 0 : period === '24m' ? 24 : period === '12m' ? 12 : 6
  const { data: benchmarks, isLoading: loadingBenchmarks } = useMonthlyBenchmarks(portfolioId, benchmarkMonths)

  const chartData = useMemo<ChartPoint[]>(() => {
    const benchmarkByPeriod = new Map((benchmarks?.points ?? []).map(point => [point.period, point]))
    let accCarteiraFactor = 1
    let accIbovFactor = 1
    let accCdiFactor = 1
    let accIpcaFactor = 1
    let hasIbov = false
    let hasCdi = false
    let hasIpca = false

    return (monthly ?? []).map(point => {
      const periodKey = point.period || point.date.slice(0, 7)
      const benchmark = benchmarkByPeriod.get(periodKey)
      const carteiraMes = Number(point.monthly_return_pct ?? 0)
      accCarteiraFactor *= 1 + carteiraMes / 100
      const carteiraCrescimento = Number(((accCarteiraFactor - 1) * 100).toFixed(4))
      const carteiraDesdeInicio = Number(point.accumulated_return_pct ?? carteiraCrescimento)

      const ibovMes = benchmark?.ibov_monthly_pct ?? undefined
      if (ibovMes != null && Number.isFinite(ibovMes)) {
        accIbovFactor *= 1 + ibovMes / 100
        hasIbov = true
      }
      const cdiMes = benchmark?.cdi_monthly_pct ?? undefined
      if (cdiMes != null && Number.isFinite(cdiMes)) {
        accCdiFactor *= 1 + cdiMes / 100
        hasCdi = true
      }
      const ipcaMes = benchmark?.ipca_monthly_pct ?? undefined
      if (ipcaMes != null && Number.isFinite(ipcaMes)) {
        accIpcaFactor *= 1 + ipcaMes / 100
        hasIpca = true
      }

      const ibovCrescimento = hasIbov ? Number(((accIbovFactor - 1) * 100).toFixed(4)) : undefined
      const cdiCrescimento = hasCdi ? Number(((accCdiFactor - 1) * 100).toFixed(4)) : undefined
      const ipcaCrescimento = hasIpca ? Number(((accIpcaFactor - 1) * 100).toFixed(4)) : undefined
      const pctCdiCrescimento =
        cdiCrescimento != null && Math.abs(cdiCrescimento) > 0.0001
          ? Number(((carteiraCrescimento / cdiCrescimento) * 100).toFixed(1))
          : null

      return {
        period: periodKey,
        label: ymToLabel(periodKey),
        carteiraMes,
        carteiraCrescimento,
        carteiraDesdeInicio,
        ibovMes,
        cdiMes,
        ipcaMes,
        ibovCrescimento,
        cdiCrescimento,
        ipcaCrescimento,
        pctCdiCrescimento,
        patrimonioFechamento: Number(point.market_value ?? point.value ?? 0),
        resultadoAcumulado: Number(point.total_pnl ?? 0),
        estimated: Boolean(point.return_is_estimated),
        partial: Boolean(point.has_partial_prices),
        snapshotDate: point.date,
      }
    })
  }, [benchmarks, monthly])

  const yearMatrix = useMemo<YearMatrixRow[]>(() => {
    const source = (allMonthly && allMonthly.length > 0 ? allMonthly : monthly) ?? []
    if (source.length === 0) return []

    const byYear = new Map<string, (number | null)[]>()
    let runningFactor = 1
    const cumulativeByYear = new Map<string, number>()

    for (const point of source) {
      const periodKey = point.period || point.date.slice(0, 7)
      const [year, monthStr] = periodKey.split('-')
      const monthIdx = Number(monthStr) - 1
      if (!year || monthIdx < 0 || monthIdx > 11) continue

      if (!byYear.has(year)) {
        byYear.set(year, Array(12).fill(null))
      }
      const mRet = Number(point.monthly_return_pct ?? 0)
      byYear.get(year)![monthIdx] = mRet
      runningFactor *= 1 + mRet / 100
      const persistedAcc = point.accumulated_return_pct
      cumulativeByYear.set(
        year,
        persistedAcc != null && Number.isFinite(Number(persistedAcc))
          ? Number(persistedAcc)
          : Number(((runningFactor - 1) * 100).toFixed(2)),
      )
    }

    const rows: YearMatrixRow[] = []
    for (const [year, months] of byYear.entries()) {
      let ytdFactor = 1
      for (const val of months) {
        if (val != null) {
          ytdFactor *= 1 + val / 100
        }
      }
      rows.push({
        year,
        months,
        ytdPct: Number(((ytdFactor - 1) * 100).toFixed(2)),
        cumulativePct: cumulativeByYear.get(year) ?? Number(((ytdFactor - 1) * 100).toFixed(2)),
      })
    }
    return rows.sort((a, b) => b.year.localeCompare(a.year))
  }, [allMonthly, monthly])

  const availability = benchmarks?.availability
  const benchmarkButtons = [
    { label: 'IBOV', active: showIbov, available: availability?.IBOV.available ?? false, toggle: () => setShowIbov(value => !value) },
    { label: 'CDI', active: showCdi, available: availability?.CDI.available ?? false, toggle: () => setShowCdi(value => !value) },
    { label: 'IPCA', active: showIpca, available: availability?.IPCA.available ?? false, toggle: () => setShowIpca(value => !value) },
  ]

  const loading = loadingMonthly || loadingBenchmarks
  const isCumulativeChart = chartMode === 'cumulative'
  const carteiraKey = isCumulativeChart ? 'carteiraCrescimento' : 'carteiraMes'
  const ibovKey = isCumulativeChart ? 'ibovCrescimento' : 'ibovMes'
  const cdiKey = isCumulativeChart ? 'cdiCrescimento' : 'cdiMes'
  const ipcaKey = isCumulativeChart ? 'ipcaCrescimento' : 'ipcaMes'

  const progressiveRows = useMemo(() => [...chartData].reverse(), [chartData])

  return (
    <div className="flex flex-col gap-5">
      <div className="card overflow-hidden">
        <div className="section-card-header flex-wrap gap-3">
          <div className="flex flex-col">
            <div className="flex items-center gap-1.5">
              <span className="section-card-title">
                {isCumulativeChart ? 'TWR em crescimento (acumulado)' : 'TWR mensal'}
              </span>
              <TwrHelpPopover />
            </div>
            <span className="text-xs mt-0.5" style={{ color: 'var(--color-text-faint)' }}>
              {isCumulativeChart
                ? 'Evolução composta acumulada da carteira vs benchmarks no período selecionado'
                : 'Carteira e benchmarks mensais servidos por séries persistidas'}
            </span>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            <div
              className="inline-flex rounded-full p-0.5"
              style={{ background: 'var(--color-surface-offset)', border: '1px solid var(--color-divider)' }}
            >
              <button
                type="button"
                onClick={() => setChartMode('cumulative')}
                className="px-2.5 py-1 rounded-full text-xs font-semibold transition-colors"
                style={{
                  background: isCumulativeChart ? 'var(--color-primary)' : 'transparent',
                  color: isCumulativeChart ? '#fff' : 'var(--color-text-muted)',
                }}
              >
                Em crescimento
              </button>
              <button
                type="button"
                onClick={() => setChartMode('monthly')}
                className="px-2.5 py-1 rounded-full text-xs font-semibold transition-colors"
                style={{
                  background: !isCumulativeChart ? 'var(--color-primary)' : 'transparent',
                  color: !isCumulativeChart ? '#fff' : 'var(--color-text-muted)',
                }}
              >
                Mês a mês
              </button>
            </div>

            {benchmarkButtons.map(item => (
              <button
                key={item.label}
                onClick={item.toggle}
                disabled={!item.available}
                title={item.available ? undefined : 'Histórico persistido ainda indisponível'}
                className="px-2.5 py-1 rounded-full text-xs font-semibold disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                style={{
                  border: '1px solid var(--color-divider)',
                  background: item.active && item.available ? 'oklch(from var(--color-primary) l c h / 0.12)' : 'transparent',
                  color: item.active && item.available ? 'var(--color-primary)' : 'var(--color-text-faint)',
                }}
              >
                {item.label}
              </button>
            ))}
            {PERIOD_OPTIONS.map(option => (
              <button
                key={option.value}
                onClick={() => setPeriod(option.value)}
                className="px-2.5 py-1 rounded-full text-xs font-semibold transition-colors"
                style={{
                  border: '1px solid var(--color-divider)',
                  background: period === option.value ? 'oklch(from var(--color-primary) l c h / 0.12)' : 'transparent',
                  color: period === option.value ? 'var(--color-primary)' : 'var(--color-text-muted)',
                }}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>

        <div className="section-card-body">
          {loading ? (
            <div className="animate-pulse rounded-lg" style={{ height: 280, background: 'var(--color-surface-offset)' }} />
          ) : chartData.length === 0 ? (
            <div className="flex items-center justify-center" style={{ height: 280 }}>
              <span className="text-xs" style={{ color: 'var(--color-text-faint)' }}>Sem snapshots para o período selecionado</span>
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <ComposedChart data={chartData} margin={{ top: 6, right: 8, left: -10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="oklch(from var(--color-text) l c h / 0.06)" vertical={false} />
                <XAxis dataKey="label" tick={{ fontSize: 10, fill: 'var(--color-text-faint)' }} axisLine={false} tickLine={false} interval="preserveStartEnd" />
                <YAxis tickFormatter={value => `${value > 0 ? '+' : ''}${Number(value).toFixed(1)}%`} tick={{ fontSize: 10, fill: 'var(--color-text-faint)' }} axisLine={false} tickLine={false} width={54} />
                <Tooltip content={<CustomTooltip />} />
                <ReferenceLine y={0} stroke="oklch(from var(--color-text) l c h / 0.18)" />
                {isCumulativeChart ? (
                  <Line
                    type="monotone"
                    dataKey={carteiraKey}
                    name="Carteira (TWR Acum.)"
                    stroke="var(--color-primary)"
                    strokeWidth={2.5}
                    dot={{ r: 3 }}
                  />
                ) : (
                  <Bar dataKey={carteiraKey} name="Carteira (TWR)" fill="var(--color-primary)" radius={[3, 3, 0, 0]} maxBarSize={30} />
                )}
                {showIbov && availability?.IBOV.available && (
                  <Line type="monotone" dataKey={ibovKey} name={isCumulativeChart ? 'IBOV Acum.' : 'IBOV'} stroke="#f59e0b" connectNulls dot={false} strokeWidth={2} />
                )}
                {showCdi && availability?.CDI.available && (
                  <Line type="monotone" dataKey={cdiKey} name={isCumulativeChart ? 'CDI Acum.' : 'CDI'} stroke="#10b981" connectNulls dot={false} strokeWidth={2} />
                )}
                {showIpca && availability?.IPCA.available && (
                  <Line type="monotone" dataKey={ipcaKey} name={isCumulativeChart ? 'IPCA Acum.' : 'IPCA'} stroke="#a855f7" connectNulls dot={false} strokeWidth={2} />
                )}
              </ComposedChart>
            </ResponsiveContainer>
          )}

          <p className="text-[10px] mt-3" style={{ color: 'var(--color-text-faint)' }}>
            Nenhuma consulta externa é realizada pelo navegador. Benchmarks sem histórico materializado permanecem indisponíveis.
          </p>
        </div>
      </div>

      {/* Tabela de Rentabilidade em Crescimento e Mês a Mês */}
      <div className="card overflow-hidden">
        <div className="section-card-header flex-wrap gap-3">
          <div className="flex flex-col">
            <div className="flex items-center gap-1.5">
              <span className="section-card-title">Tabela de rentabilidade em crescimento e mensal</span>
              <TwrHelpPopover />
            </div>
            <span className="text-xs mt-0.5" style={{ color: 'var(--color-text-faint)' }}>
              {tableMode === 'progressive'
                ? 'Evolução progressiva acumulada mês a mês comparada aos benchmarks'
                : 'Matriz histórica anual (Ano × Mês) com acumulado no ano (YTD) e crescimento desde o início'}
            </span>
          </div>

          <div
            className="inline-flex rounded-full p-0.5"
            style={{ background: 'var(--color-surface-offset)', border: '1px solid var(--color-divider)' }}
          >
            <button
              type="button"
              onClick={() => setTableMode('progressive')}
              className="px-3 py-1 rounded-full text-xs font-semibold transition-colors"
              style={{
                background: tableMode === 'progressive' ? 'var(--color-primary)' : 'transparent',
                color: tableMode === 'progressive' ? '#fff' : 'var(--color-text-muted)',
              }}
            >
              Evolução em crescimento
            </button>
            <button
              type="button"
              onClick={() => setTableMode('matrix')}
              className="px-3 py-1 rounded-full text-xs font-semibold transition-colors"
              style={{
                background: tableMode === 'matrix' ? 'var(--color-primary)' : 'transparent',
                color: tableMode === 'matrix' ? '#fff' : 'var(--color-text-muted)',
              }}
            >
              Matriz anual (Ano × Mês)
            </button>
          </div>
        </div>

        <div className="section-card-body table-responsive">
          {loading ? (
            <div className="flex flex-col gap-2">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="h-9 skeleton rounded" />
              ))}
            </div>
          ) : chartData.length === 0 ? (
            <p className="text-xs py-4 text-center" style={{ color: 'var(--color-text-faint)' }}>
              Sem dados de rentabilidade para o período selecionado
            </p>
          ) : tableMode === 'progressive' ? (
            <table className="w-full min-w-[860px]" data-testid="rentabilidade-crescimento-table">
              <thead>
                <tr style={{ borderBottom: '1px solid oklch(from var(--color-text) l c h / 0.08)' }}>
                  {[
                    'Mês',
                    'TWR no mês',
                    'TWR em crescimento (período)',
                    'TWR desde o início',
                    'CDI acum.',
                    '% do CDI',
                    'IBOV acum.',
                    'IPCA acum.',
                    'Patrimônio fechado',
                  ].map((header, idx) => (
                    <th
                      key={header}
                      className={`pb-2.5 text-xs font-medium ${idx === 0 ? 'text-left' : 'text-right'} ${idx < 8 ? 'pr-3' : ''}`}
                      style={{ color: 'var(--color-text-faint)' }}
                    >
                      {header}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {progressiveRows.map(row => (
                  <tr
                    key={row.period}
                    className="border-b"
                    style={{ borderColor: 'oklch(from var(--color-text) l c h / 0.06)' }}
                  >
                    <td className="py-2.5 pr-3">
                      <div className="flex flex-col">
                        <span className="text-xs font-semibold" style={{ color: 'var(--color-text)' }}>
                          {row.label}
                        </span>
                        <span className="text-[10px]" style={{ color: 'var(--color-text-faint)' }}>
                          {new Date(`${row.snapshotDate}T00:00:00`).toLocaleDateString('pt-BR')}
                        </span>
                      </div>
                    </td>
                    <td className="py-2.5 pr-3 text-right">
                      <span className="text-xs tabular-nums font-medium" style={{ color: pnlColor(row.carteiraMes) }}>
                        {formatSignedPct(row.carteiraMes)}
                      </span>
                    </td>
                    <td className="py-2.5 pr-3 text-right">
                      <span className="text-xs tabular-nums font-semibold" style={{ color: pnlColor(row.carteiraCrescimento) }}>
                        {formatSignedPct(row.carteiraCrescimento)}
                      </span>
                    </td>
                    <td className="py-2.5 pr-3 text-right">
                      <span className="text-xs tabular-nums font-semibold" style={{ color: pnlColor(row.carteiraDesdeInicio) }}>
                        {formatSignedPct(row.carteiraDesdeInicio)}
                      </span>
                    </td>
                    <td className="py-2.5 pr-3 text-right">
                      <span className="text-xs tabular-nums" style={{ color: 'var(--color-text-muted)' }}>
                        {formatSignedPct(row.cdiCrescimento)}
                      </span>
                    </td>
                    <td className="py-2.5 pr-3 text-right">
                      <span
                        className="text-xs tabular-nums font-medium"
                        style={{
                          color:
                            row.pctCdiCrescimento == null
                              ? 'var(--color-text-muted)'
                              : row.pctCdiCrescimento >= 100
                                ? 'var(--color-success)'
                                : 'var(--color-text-muted)',
                        }}
                      >
                        {row.pctCdiCrescimento != null ? formatPercent(row.pctCdiCrescimento) : '—'}
                      </span>
                    </td>
                    <td className="py-2.5 pr-3 text-right">
                      <span className="text-xs tabular-nums" style={{ color: pnlColor(row.ibovCrescimento) }}>
                        {formatSignedPct(row.ibovCrescimento)}
                      </span>
                    </td>
                    <td className="py-2.5 pr-3 text-right">
                      <span className="text-xs tabular-nums" style={{ color: 'var(--color-text-muted)' }}>
                        {formatSignedPct(row.ipcaCrescimento)}
                      </span>
                    </td>
                    <td className="py-2.5 text-right">
                      <span className="text-xs tabular-nums font-medium" style={{ color: 'var(--color-text)' }}>
                        {formatBRL(row.patrimonioFechamento)}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <table className="w-full min-w-[980px]" data-testid="rentabilidade-matriz-anual-table">
              <thead>
                <tr style={{ borderBottom: '1px solid oklch(from var(--color-text) l c h / 0.08)' }}>
                  <th className="pb-2.5 pr-3 text-left text-xs font-medium" style={{ color: 'var(--color-text-faint)' }}>
                    Ano
                  </th>
                  {MONTH_SHORT.map(m => (
                    <th key={m} className="pb-2.5 pr-2 text-right text-xs font-medium" style={{ color: 'var(--color-text-faint)' }}>
                      {m}
                    </th>
                  ))}
                  <th className="pb-2.5 pr-3 text-right text-xs font-semibold" style={{ color: 'var(--color-text)' }}>
                    No Ano
                  </th>
                  <th className="pb-2.5 text-right text-xs font-semibold" style={{ color: 'var(--color-primary)' }}>
                    Em Crescimento
                  </th>
                </tr>
              </thead>
              <tbody>
                {yearMatrix.map(row => (
                  <tr
                    key={row.year}
                    className="border-b"
                    style={{ borderColor: 'oklch(from var(--color-text) l c h / 0.06)' }}
                  >
                    <td className="py-2.5 pr-3 text-xs font-semibold tabular-nums" style={{ color: 'var(--color-text)' }}>
                      {row.year}
                    </td>
                    {row.months.map((val, idx) => (
                      <td key={idx} className="py-2.5 pr-2 text-right text-xs tabular-nums" style={{ color: pnlColor(val) }}>
                        {val != null ? formatSignedPct(val) : '—'}
                      </td>
                    ))}
                    <td className="py-2.5 pr-3 text-right text-xs font-semibold tabular-nums" style={{ color: pnlColor(row.ytdPct) }}>
                      {formatSignedPct(row.ytdPct)}
                    </td>
                    <td className="py-2.5 text-right text-xs font-bold tabular-nums" style={{ color: pnlColor(row.cumulativePct) }}>
                      {formatSignedPct(row.cumulativePct)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  )
}
