import { useEffect, useMemo, useState } from 'react'
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

interface BenchmarkPoint {
  date: string
  ibov?: number
  cdi?: number
  ipca?: number
}

interface ChartPoint {
  period: string
  label: string
  carteira: number
  ibov?: number
  cdi?: number
  ipca?: number
  estimated: boolean
  partial: boolean
  snapshotDate: string
}

const MONTH_SHORT = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']

function ymToLabel(ym: string): string {
  const [year, month] = ym.split('-')
  return `${MONTH_SHORT[Number(month) - 1]}/${year.slice(2)}`
}

function pct(value: number): string {
  return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`
}

const PERIOD_OPTIONS: { label: string; value: PeriodOption }[] = [
  { label: '6 meses', value: '6m' },
  { label: '12 meses', value: '12m' },
  { label: '24 meses', value: '24m' },
  { label: 'Todo período', value: 'all' },
]

async function fetchIbovMonthly(months: number): Promise<Record<string, number>> {
  try {
    const range = months <= 24 ? '2y' : months <= 60 ? '5y' : '10y'
    const response = await fetch(`https://brapi.dev/api/quote/%5EBVSP?range=${range}&interval=1mo&fundamental=false`)
    if (!response.ok) return {}
    const json = await response.json()
    const history: { date: string; adjustedClose: number }[] = json?.results?.[0]?.historicalDataPrice ?? []
    const values: Record<string, number> = {}
    for (let index = 1; index < history.length; index += 1) {
      const previous = history[index - 1].adjustedClose
      const current = history[index].adjustedClose
      if (!previous) continue
      values[history[index].date.slice(0, 7)] = ((current - previous) / previous) * 100
    }
    return values
  } catch {
    return {}
  }
}

async function fetchBcbMonthly(series: number, months: number): Promise<Record<string, number>> {
  try {
    const amount = Math.max(months + 2, 8)
    const response = await fetch(`https://api.bcb.gov.br/dados/serie/bcdata.sgs.${series}/dados/ultimos/${amount}?formato=json`)
    if (!response.ok) return {}
    const json: { data: string; valor: string }[] = await response.json()
    const values: Record<string, number> = {}
    for (const point of json) {
      const [, month, year] = point.data.split('/')
      values[`${year}-${month.padStart(2, '0')}`] = Number.parseFloat(point.valor)
    }
    return values
  } catch {
    return {}
  }
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
        minWidth: 180,
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
  const [benchmarks, setBenchmarks] = useState<BenchmarkPoint[]>([])
  const [loadingBenchmarks, setLoadingBenchmarks] = useState(false)
  const [showIbov, setShowIbov] = useState(true)
  const [showCdi, setShowCdi] = useState(true)
  const [showIpca, setShowIpca] = useState(false)

  const { data: monthly, isLoading: loadingMonthly } = useMonthlyEvolution(portfolioId, period)
  const benchmarkMonths = Math.max(monthly?.length ?? 0, period === 'all' ? 120 : period === '24m' ? 24 : period === '12m' ? 12 : 6)

  useEffect(() => {
    let cancelled = false
    setLoadingBenchmarks(true)
    Promise.all([
      fetchIbovMonthly(benchmarkMonths),
      fetchBcbMonthly(4391, benchmarkMonths),
      fetchBcbMonthly(433, benchmarkMonths),
    ]).then(([ibov, cdi, ipca]) => {
      if (cancelled) return
      const periods = new Set([...Object.keys(ibov), ...Object.keys(cdi), ...Object.keys(ipca)])
      setBenchmarks(
        Array.from(periods)
          .sort()
          .map(date => ({ date, ibov: ibov[date], cdi: cdi[date], ipca: ipca[date] })),
      )
      setLoadingBenchmarks(false)
    })
    return () => {
      cancelled = true
    }
  }, [benchmarkMonths])

  const chartData = useMemo<ChartPoint[]>(() => {
    const benchmarkByPeriod = new Map(benchmarks.map(point => [point.date, point]))
    return (monthly ?? []).map(point => {
      const periodKey = point.period || point.date.slice(0, 7)
      const benchmark = benchmarkByPeriod.get(periodKey)
      return {
        period: periodKey,
        label: ymToLabel(periodKey),
        carteira: Number(point.monthly_return_pct ?? 0),
        ibov: benchmark?.ibov,
        cdi: benchmark?.cdi,
        ipca: benchmark?.ipca,
        estimated: Boolean(point.return_is_estimated),
        partial: Boolean(point.has_partial_prices),
        snapshotDate: point.date,
      }
    })
  }, [benchmarks, monthly])

  const loading = loadingMonthly || loadingBenchmarks

  return (
    <div className="card p-4">
      <div className="flex items-center justify-between flex-wrap gap-2 mb-4">
        <div className="flex flex-col">
          <span className="section-card-title">TWR mensal</span>
          <span className="text-[10px]" style={{ color: 'var(--color-text-faint)' }}>
            Retorno mensal composto a partir dos snapshots diários
          </span>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {[
            { label: 'IBOV', active: showIbov, toggle: () => setShowIbov(value => !value) },
            { label: 'CDI', active: showCdi, toggle: () => setShowCdi(value => !value) },
            { label: 'IPCA', active: showIpca, toggle: () => setShowIpca(value => !value) },
          ].map(item => (
            <button
              key={item.label}
              onClick={item.toggle}
              className="px-2 py-1 rounded-full text-xs font-semibold"
              style={{
                border: '1px solid var(--color-divider)',
                background: item.active ? 'oklch(from var(--color-primary) l c h / 0.12)' : 'transparent',
                color: item.active ? 'var(--color-primary)' : 'var(--color-text-faint)',
              }}
            >
              {item.label}
            </button>
          ))}
          {PERIOD_OPTIONS.map(option => (
            <button
              key={option.value}
              onClick={() => setPeriod(option.value)}
              className="px-2 py-1 rounded-full text-xs font-semibold"
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
            <Bar dataKey="carteira" name="Carteira (TWR)" fill="var(--color-primary)" radius={[3, 3, 0, 0]} maxBarSize={30} />
            {showIbov && <Line type="monotone" dataKey="ibov" name="IBOV" connectNulls dot={false} strokeWidth={2} />}
            {showCdi && <Line type="monotone" dataKey="cdi" name="CDI" connectNulls dot={false} strokeWidth={2} />}
            {showIpca && <Line type="monotone" dataKey="ipca" name="IPCA" connectNulls dot={false} strokeWidth={2} />}
          </ComposedChart>
        </ResponsiveContainer>
      )}

      <p className="text-[10px] mt-2" style={{ color: 'var(--color-text-faint)' }}>
        A carteira usa TWR canônico. Os benchmarks ainda são carregados por fonte pública e serão migrados para séries persistidas no próximo sub-bloco.
      </p>
    </div>
  )
}
