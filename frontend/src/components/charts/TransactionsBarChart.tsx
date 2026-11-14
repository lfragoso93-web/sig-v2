import {
  ComposedChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts'
import { formatBRL } from '@/utils/format'
import type { Transaction } from '@/hooks/useTransactions'

interface Props {
  transactions: Transaction[]
}

interface MonthlyPoint {
  month: string
  label: string
  buy: number
  sell: number
}

function buildMonthlyData(transactions: Transaction[]): MonthlyPoint[] {
  const acc: Record<string, MonthlyPoint> = {}

  for (const t of transactions) {
    if (!t.date) continue
    const parts = t.date.split('T')[0].split('-')
    if (parts.length < 2) continue
    const [year, month] = parts
    if (!year || !month || year.length !== 4) continue

    const key = `${year}-${month}`
    const label = `${month}/${year.slice(-2)}`

    if (!acc[key]) {
      acc[key] = { month: key, label, buy: 0, sell: 0 }
    }

    const fees = t.fees ?? 0
    const gross = t.quantity * t.price
    const value = gross + fees

    if (t.operation === 'buy') {
      acc[key].buy += value
    } else if (t.operation === 'sell') {
      // vendas como valor negativo — aparecem abaixo do eixo zero
      acc[key].sell -= value
    }
  }

  return Object.values(acc).sort((a, b) => (a.month < b.month ? -1 : 1))
}

function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null

  const rawBuy  = payload.find((p: any) => p.dataKey === 'buy')?.value  ?? 0
  const rawSell = payload.find((p: any) => p.dataKey === 'sell')?.value ?? 0

  const buy  = Math.max(0, rawBuy)
  const sell = Math.abs(rawSell)

  return (
    <div
      className="chart-glass-tooltip"
      style={{
        padding: '10px 14px',
        fontSize: 'var(--text-xs)',
        minWidth: 180,
      }}
    >
      <p className="font-semibold mb-2" style={{ color: 'var(--color-text)', fontSize: '0.825rem' }}>{label}</p>

      <div className="flex items-center justify-between gap-4 mb-1.5">
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full" style={{ background: 'var(--color-success)' }} />
          <span style={{ color: 'var(--color-text-muted)' }}>Compras</span>
        </div>
        <span className="font-semibold tabular-nums" style={{ color: 'var(--color-success)' }}>
          {formatBRL(buy)}
        </span>
      </div>

      {sell > 0 && (
        <div className="flex items-center justify-between gap-4 pt-1.5 border-t" style={{ borderColor: 'var(--glass-border)' }}>
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full" style={{ background: 'var(--color-notification)' }} />
            <span style={{ color: 'var(--color-text-muted)' }}>Vendas</span>
          </div>
          <span className="font-semibold tabular-nums" style={{ color: 'var(--color-notification)' }}>
            {formatBRL(sell)}
          </span>
        </div>
      )}
    </div>
  )
}

export default function TransactionsBarChart({ transactions }: Props) {
  const data = buildMonthlyData(transactions)
  if (!data.length) return null

  const tickStyle = { fontSize: 10, fill: 'var(--color-text-faint)' }

  return (
    <div style={{ touchAction: 'pan-y' }}>
      <ResponsiveContainer width="100%" height={220}>
        <ComposedChart data={data} margin={{ top: 8, right: 8, left: -14, bottom: 0 }} barCategoryGap="30%">
          <defs>
            <linearGradient id="grad-tx-buy" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--color-success)" stopOpacity={0.95} />
              <stop offset="100%" stopColor="oklch(from var(--color-success) l c h / 0.72)" />
            </linearGradient>
            <linearGradient id="grad-tx-sell" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="oklch(from var(--color-notification) l c h / 0.72)" />
              <stop offset="100%" stopColor="var(--color-notification)" />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--color-divider)" vertical={false} />
          <XAxis dataKey="label" tick={tickStyle} axisLine={false} tickLine={false} />
          <YAxis
            tick={tickStyle}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v: number) => formatBRL(Math.abs(v), true)}
            width={58}
          />
          <Tooltip
            content={<CustomTooltip />}
            cursor={{ fill: 'oklch(from var(--color-text) l c h / 0.04)', radius: 4 }}
          />
          <ReferenceLine y={0} stroke="var(--color-divider)" strokeWidth={1.5} />

          {/* Compras: valores positivos — barras acima do zero com gradiente sutil */}
          <Bar
            dataKey="buy"
            name="Compras"
            fill="url(#grad-tx-buy)"
            radius={[5, 5, 0, 0]}
            maxBarSize={32}
          />

          {/* Vendas: valores negativos — barras abaixo do zero com gradiente sutil */}
          <Bar
            dataKey="sell"
            name="Vendas"
            fill="url(#grad-tx-sell)"
            radius={[0, 0, 5, 5]}
            maxBarSize={32}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}
