import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts'
import type { PatrimonioHistoryPoint } from '@/hooks/usePortfolio'
import { formatBRL, formatPercent, signClass } from '@/utils/format'

interface Props {
  data: PatrimonioHistoryPoint[]
  loading?: boolean
  singleSeries?: boolean
}

function monthLabel(value: string) {
  const [year, month] = value.split('-')
  if (!year || !month) return value
  return `${month}/${year.slice(-2)}`
}

function fullDate(value: string) {
  const [year, month, day] = value.split('-')
  if (!year || !month) return value
  return day ? `${day}/${month}/${year}` : `${month}/${year}`
}

interface TooltipProps {
  active?: boolean
  payload?: Array<{ payload: ChartPoint }>
}

export interface ChartPoint {
  name: string
  date: string
  patrimonio: number
  aplicado: number
  resultado: number
  ganho: number
  perda: number
  twr: number | null
  partial: boolean
  estimated: boolean
  source: string
}

export function buildPatrimonioChartData(data: PatrimonioHistoryPoint[]): ChartPoint[] {
  return data.map(point => {
    const patrimonio = Number(point.value || 0)
    const aplicado = Number(point.invested || 0)
    const resultado = Number(point.capital_result ?? patrimonio - aplicado)

    return {
      name: monthLabel(point.period ?? point.date.slice(0, 7)),
      date: point.date,
      patrimonio,
      aplicado,
      resultado,
      ganho: Math.max(resultado, 0),
      perda: Math.min(resultado, 0),
      twr: point.accumulated_return_pct !== undefined
        && Number.isFinite(Number(point.accumulated_return_pct))
        ? Number(point.accumulated_return_pct)
        : null,
      partial: Boolean(point.has_partial_prices),
      estimated: Boolean(point.return_is_estimated),
      source: point.history_source ?? 'unknown',
    }
  })
}

export function getSymmetricAxisLimit(data: ChartPoint[]): number {
  const maxAbsolute = data.reduce(
    (maxValue, point) => Math.max(
      maxValue,
      Math.abs(point.aplicado + point.ganho),
      Math.abs(point.perda),
    ),
    0,
  )
  if (maxAbsolute === 0) return 1
  return Math.ceil(maxAbsolute * 1.08)
}

function EvolutionTooltip({ active, payload }: TooltipProps) {
  const point = payload?.[0]?.payload
  if (!active || !point) return null

  const referenceLabel = point.source === 'portfolio_snapshot'
    ? 'Snapshot'
    : 'Fechamento mensal da classe'

  return (
    <div
      style={{
        minWidth: 172,
        padding: '0.75rem 0.85rem',
        borderRadius: 8,
        border: '1px solid oklch(from var(--color-text) l c h / 0.14)',
        background: 'var(--color-surface-2)',
        boxShadow: '0 10px 28px oklch(0 0 0 / 0.2)',
        color: 'var(--color-text)',
        fontSize: 'var(--text-xs)',
      }}
    >
      <div style={{ fontWeight: 700, marginBottom: 10 }}>{point.name}</div>
      <TooltipRow label="Patrimônio" value={formatBRL(point.patrimonio)} marker="var(--color-primary)" />
      <TooltipRow label="Valor aplicado" value={formatBRL(point.aplicado)} marker="var(--color-success)" />
      <TooltipRow
        label={point.resultado >= 0 ? 'Ganho de capital' : 'Perda de capital'}
        value={formatBRL(point.resultado)}
        marker={point.resultado >= 0 ? 'var(--color-success)' : 'var(--color-notification)'}
        valueClass={signClass(point.resultado)}
      />
      {point.twr !== null && (
        <TooltipRow
          label={`Rentabilidade (TWR)${point.estimated ? ' estimada' : ''}`}
          value={`${point.twr >= 0 ? '+' : ''}${formatPercent(point.twr)}`}
          valueClass={signClass(point.twr)}
        />
      )}
      <div style={{ marginTop: 9, color: 'var(--color-text-faint)', fontSize: '0.68rem' }}>
        {referenceLabel} de {fullDate(point.date)}{point.partial ? ' · cobertura parcial' : ''}
      </div>
    </div>
  )
}

function TooltipRow({
  label,
  value,
  marker,
  valueClass,
}: {
  label: string
  value: string
  marker?: string
  valueClass?: string
}) {
  return (
    <div style={{ marginTop: 7 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--color-text-muted)' }}>
        {marker && <span style={{ width: 8, height: 8, borderRadius: 2, background: marker }} />}
        <span>{label}</span>
      </div>
      <div className={valueClass} style={{ marginTop: 2, fontWeight: 650, paddingLeft: marker ? 14 : 0 }}>
        {value}
      </div>
    </div>
  )
}

function ChartLegend() {
  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        gap: 14,
        height: 30,
        fontSize: '0.7rem',
        color: 'var(--color-text-muted)',
      }}
    >
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}>
        <span style={{ width: 10, height: 8, borderRadius: 2, background: 'var(--color-success)' }} />
        Valor aplicado
      </span>
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}>
        <span style={{ width: 10, height: 8, borderRadius: 2, background: 'oklch(from var(--color-success) l c h / 0.55)' }} />
        Ganho de capital
      </span>
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}>
        <span style={{ width: 10, height: 8, borderRadius: 2, background: 'var(--color-notification)' }} />
        Perda de capital
      </span>
    </div>
  )
}

export default function PatrimonioBarChart({ data, loading }: Props) {
  if (loading) return <div className="skeleton h-64 w-full rounded-xl" />

  if (!data.length) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 220 }}>
        <p style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-faint)' }}>
          Sem histórico para o período selecionado
        </p>
      </div>
    )
  }

  const chartData = buildPatrimonioChartData(data)
  const axisLimit = getSymmetricAxisLimit(chartData)

  return (
    <div>
      <ChartLegend />
      <ResponsiveContainer width="100%" height={270}>
        <BarChart data={chartData} margin={{ top: 0, right: 8, left: 4, bottom: 4 }} barCategoryGap="18%">
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="oklch(from var(--color-text) l c h / 0.08)"
            vertical={false}
          />
          <ReferenceLine y={0} stroke="oklch(from var(--color-text) l c h / 0.4)" strokeWidth={1.5} />
          <XAxis
            dataKey="name"
            tick={{ fontSize: 10, fill: 'var(--color-text-muted)' }}
            axisLine={false}
            tickLine={false}
            angle={-42}
            textAnchor="end"
            height={46}
            interval="preserveStartEnd"
          />
          <YAxis
            domain={[-axisLimit, axisLimit]}
            tickFormatter={(value: number) => formatBRL(value, true)}
            tick={{ fontSize: 9, fill: 'var(--color-text-muted)' }}
            axisLine={false}
            tickLine={false}
            width={70}
          />
          <Tooltip content={<EvolutionTooltip />} cursor={{ fill: 'oklch(from var(--color-text) l c h / 0.05)' }} />
          <Bar
            dataKey="aplicado"
            stackId="patrimonio"
            fill="var(--color-success)"
            radius={[3, 3, 0, 0]}
            maxBarSize={42}
          />
          <Bar
            dataKey="ganho"
            stackId="patrimonio"
            fill="oklch(from var(--color-success) l c h / 0.55)"
            radius={[3, 3, 0, 0]}
            maxBarSize={42}
          />
          <Bar
            dataKey="perda"
            stackId="patrimonio"
            fill="var(--color-notification)"
            radius={[0, 0, 3, 3]}
            maxBarSize={42}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
