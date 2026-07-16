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
  const [showIbov, setShowIbov] = useState(true)
  const [showCdi, setShowCdi] = useState(true)
  const [showIpca, setShowIpca] = useState(false)

  const { data: monthly, isLoading: loadingMonthly } = useMonthlyEvolution(portfolioId, period)
  const benchmarkMonths = period === 'all' ? 0 : period === '24m' ? 24 : period === '12m' ? 12 : 6
  const { data: benchmarks, isLoading: loadingBenchmarks } = useMonthlyBenchmarks(portfolioId, benchmarkMonths)

  const chartData = useMemo<ChartPoint[]>(() => {
    const benchmarkByPeriod = new Map((benchmarks?.points ?? []).map(point => [point.period, point]))
    return (monthly ?? []).map(point => {
      const periodKey = point.period || point.date.slice(0, 7)
      const benchmark = benchmarkByPeriod.get(periodKey)
      return {
        period: periodKey,
        label: ymToLabel(periodKey),
        carteira: Number(point.monthly_return_pct ?? 0),
        ibov: benchmark?.ibov_monthly_pct ?? undefined,
        cdi: benchmark?.cdi_monthly_pct ?? undefined,
        ipca: benchmark?.ipca_monthly_pct ?? undefined,
        estimated: Boolean(point.return_is_estimated),
        partial: Boolean(point.has_partial_prices),
        snapshotDate: point.date,
      }
    })
  }, [benchmarks, monthly])

  const availability = benchmarks?.availability
  const benchmarkButtons = [
    { label: 'IBOV', active: showIbov, available: availability?.IBOV.available ?? false, toggle: () => setShowIbov(value => !value) },
    { label: 'CDI', active: showCdi, available: availability?.CDI.available ?? false, toggle: () => setShowCdi(value => !value) },
    { label: 'IPCA', active: showIpca, available: availability?.IPCA.available ?? false, toggle: () => setShowIpca(value => !value) },
  ]

  const loading = loadingMonthly || loadingBenchmarks

  return (
    <div className="card p-4">
      <div className="flex items-center justify-between flex-wrap gap-2 mb-4">
        <div className="flex flex-col">
          <span className="section-card-title">TWR mensal</span>
          <span className="text-[10px]" style={{ color: 'var(--color-text-faint)' }}>
            Carteira e benchmarks mensais servidos por séries persistidas
          </span>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {benchmarkButtons.map(item => (
            <button
              key={item.label}
              onClick={item.toggle}
              disabled={!item.available}
              title={item.available ? undefined : 'Histórico persistido ainda indisponível'}
              className="px-2 py-1 rounded-full text-xs font-semibold disabled:opacity-40 disabled:cursor-not-allowed"
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
            {showIbov && availability?.IBOV.available && <Line type="monotone" dataKey="ibov" name="IBOV" connectNulls dot={false} strokeWidth={2} />}
            {showCdi && availability?.CDI.available && <Line type="monotone" dataKey="cdi" name="CDI" connectNulls dot={false} strokeWidth={2} />}
            {showIpca && availability?.IPCA.available && <Line type="monotone" dataKey="ipca" name="IPCA" connectNulls dot={false} strokeWidth={2} />}
          </ComposedChart>
        </ResponsiveContainer>
      )}

      <p className="text-[10px] mt-2" style={{ color: 'var(--color-text-faint)' }}>
        Nenhuma consulta externa é realizada pelo navegador. Benchmarks sem histórico materializado permanecem indisponíveis.
      </p>
    </div>
  )
}
