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
    const date = new Date(t.date)
    if (Number.isNaN(date.getTime())) continue

    const key = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`
    const label = `${String(date.getMonth() + 1).padStart(2, '0')}/${String(date.getFullYear()).slice(-2)}`

    if (!acc[key]) {
      acc[key] = { month: key, label, buy: 0, sell: 0 }
    }

    const fees = t.fees ?? 0
    const gross = t.quantity * t.price
    const value = gross + fees

    if (t.operation === 'buy') {
      acc[key].buy += value
    } else if (t.operation === 'sell') {
      // vendas negativas para aparecerem abaixo da linha zero no gráfico,
      // mas não afetam o valor de compra
      acc[key].sell -= value
    }
  }

  return Object.values(acc).sort((a, b) => (a.month < b.month ? -1 : 1))
}

function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null

  // No payload, o Recharts passa o valor exato usado no gráfico (buy positivo, sell negativo).
  const rawBuy = payload.find((p: any) => p.dataKey === 'buy')?.value ?? 0
  const rawSell = payload.find((p: any) => p.dataKey === 'sell')?.value ?? 0

  const buy = Math.max(0, rawBuy)
  const sell = Math.abs(rawSell)

  return (
    <div
      className="rounded-lg p-3 text-xs min-w-[180px]"
      style={{
        background: 'var(--color-surface)',
        border: '1px solid var(--color-border)',
        boxShadow: 'var(--shadow-lg)',
      }}
    >
      <p className="font-semibold mb-2" style={{ color: 'var(--color-text)' }}>{label}</p>

      <div className="flex items-center justify-between gap-4 mb-1">
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full" style={{ background: 'var(--color-success)' }} />
          <span style={{ color: 'var(--color-text-muted)' }}>Compras</span>
        </div>
        <span className="font-semibold tabular-nums" style={{ color: 'var(--color-text)' }}>
          {formatBRL(buy)}
        </span>
      </div>

      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full" style={{ background: 'var(--color-notification)' }} />
          <span style={{ color: 'var(--color-text-muted)' }}>Vendas</span>
        </div>
        <span className="font-semibold tabular-nums" style={{ color: 'var(--color-notification)' }}>
          {formatBRL(sell)}
        </span>
      </div>
    </div>
  )
}

export default function TransactionsBarChart({ transactions }: Props) {
  const data = buildMonthlyData(transactions)
  if (!data.length) return null

  const tickStyle = { fontSize: 10, fill: 'var(--color-text-faint)' }

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }} barCategoryGap="30%">
        <CartesianGrid strokeDasharray="3 3" stroke="var(--color-divider)" vertical={false} />
        <XAxis dataKey="label" tick={tickStyle} axisLine={false} tickLine={false} />
        <YAxis
          tick={tickStyle}
          axisLine={false}
          tickLine={false}
          tickFormatter={(v: number) => formatBRL(v, true)}
          width={60}
        />
        <Tooltip
          content={<CustomTooltip />}
          cursor={{ fill: 'oklch(from var(--color-text) l c h / 0.04)' }}
        />
        <ReferenceLine y={0} stroke="var(--color-divider)" />

        {/* Vendas negativas abaixo da linha zero */}
        <Bar
          dataKey="sell"
          name="Vendas"
          stackId="flows"
          fill="var(--color-notification)"
          radius={[0, 0, 4, 4]}
        />
        {/* Compras positivas acima da linha zero */}
        <Bar
          dataKey="buy"
          name="Compras"
          stackId="flows"
          fill="var(--color-success)"
          radius={[4, 4, 0, 0]}
        />
      </BarChart>
    </ResponsiveContainer>
  )
}
