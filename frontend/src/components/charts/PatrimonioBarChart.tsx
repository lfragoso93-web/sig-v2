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
import { formatBRL, formatPercent, signClass } from '@/utils/format'

export interface PatrimonioEvolutionPoint {
  date: string
  period?: string
  market_value: number
  cost_basis: number
  unrealized_pnl: number
  accumulated_return_pct?: number
  has_partial_prices?: boolean
  return_is_estimated?: boolean
  history_source?: 'portfolio_snapshot' | 'portfolio_class_snapshot' | string
  is_realtime?: boolean
}

interface Props {
  data: PatrimonioEvolutionPoint[]
  loading?: boolean
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
  is_realtime?: boolean
}

export function buildPatrimonioChartData(data: PatrimonioEvolutionPoint[]): ChartPoint[] {
  return data.map(point => {
    const patrimonio = Number(point.market_value)
    const aplicado = Number(point.cost_basis)
    const resultado = Number(point.unrealized_pnl)
    const isRealTime = Boolean(point.is_realtime || point.history_source === 'realtime')

    const basePoint: ChartPoint = {
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

    if (isRealTime) {
      basePoint.is_realtime = true
    }

    return basePoint
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

  const isRealTime = point.source === 'realtime' || Boolean(point.is_realtime)
  const referenceLabel = isRealTime
    ? 'Posição Atual (Tempo Real)'
    : point.source === 'portfolio_class_snapshot'
      ? 'Snapshot mensal da classe'
      : 'Snapshot consolidado'

  return (
    <div
      className="chart-glass-tooltip"
      style={{
        minWidth: 180,
        padding: '0.85rem 1rem',
        fontSize: 'var(--text-xs)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 6, fontWeight: 700, marginBottom: 10 }}>
        <span style={{ fontSize: '0.825rem', letterSpacing: '-0.01em' }}>{point.name}</span>
        {isRealTime && (
          <span
            style={{
              fontSize: '0.625rem',
              fontWeight: 650,
              padding: '2px 7px',
              borderRadius: 'var(--radius-full)',
              background: 'oklch(from var(--color-primary) l c h / 0.18)',
              color: 'var(--color-primary)',
              border: '1px solid oklch(from var(--color-primary) l c h / 0.35)',
              boxShadow: '0 1px 3px oklch(0 0 0 / 0.06)',
            }}
          >
            Tempo Real
          </span>
        )}
      </div>
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
      <div
        style={{
          marginTop: 10,
          paddingTop: 8,
          borderTop: '1px solid var(--glass-border)',
          color: isRealTime ? 'var(--color-primary)' : 'var(--color-text-faint)',
          fontSize: '0.68rem',
          fontWeight: isRealTime ? 600 : 400,
        }}
      >
        {referenceLabel}{isRealTime ? ` · ${fullDate(point.date)}` : ` de ${fullDate(point.date)}`}{point.partial ? ' · cobertura parcial' : ''}
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
    <div style={{ touchAction: 'pan-y' }}>
      <ChartLegend />
      <ResponsiveContainer width="100%" height={270}>
        <BarChart
          data={chartData}
          margin={{ top: 8, right: 8, left: -10, bottom: 4 }}
          barCategoryGap="20%"
          stackOffset="sign"
        >
          <defs>
            <linearGradient id="grad-patrimonio-aplicado" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--color-success)" stopOpacity={0.95} />
              <stop offset="100%" stopColor="var(--color-success)" stopOpacity={0.72} />
            </linearGradient>
            <linearGradient id="grad-patrimonio-ganho" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="oklch(from var(--color-success) l c h / 0.85)" />
              <stop offset="100%" stopColor="oklch(from var(--color-success) l c h / 0.45)" />
            </linearGradient>
            <linearGradient id="grad-patrimonio-perda" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="oklch(from var(--color-notification) l c h / 0.65)" />
              <stop offset="100%" stopColor="var(--color-notification)" />
            </linearGradient>
          </defs>
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="oklch(from var(--color-text) l c h / 0.08)"
            vertical={false}
          />
          <ReferenceLine y={0} stroke="oklch(from var(--color-text) l c h / 0.35)" strokeWidth={1.5} />
          <XAxis
            dataKey="name"
            tick={{ fontSize: 10, fill: 'var(--color-text-muted)' }}
            axisLine={false}
            tickLine={false}
            angle={-38}
            textAnchor="end"
            height={44}
            interval="preserveStartEnd"
          />
          <YAxis
            domain={[-axisLimit, axisLimit]}
            tickFormatter={(value: number) => formatBRL(value, true)}
            tick={{ fontSize: 9, fill: 'var(--color-text-muted)' }}
            axisLine={false}
            tickLine={false}
            width={62}
          />
          <Tooltip
            content={<EvolutionTooltip />}
            cursor={{ fill: 'oklch(from var(--color-text) l c h / 0.05)', radius: 4 }}
          />
          <Bar
            dataKey="aplicado"
            stackId="patrimonio"
            fill="url(#grad-patrimonio-aplicado)"
            radius={[4, 4, 0, 0]}
            maxBarSize={40}
          />
          <Bar
            dataKey="ganho"
            stackId="patrimonio"
            fill="url(#grad-patrimonio-ganho)"
            radius={[5, 5, 0, 0]}
            maxBarSize={40}
          />
          <Bar
            dataKey="perda"
            stackId="patrimonio"
            fill="url(#grad-patrimonio-perda)"
            radius={[0, 0, 5, 5]}
            maxBarSize={40}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
