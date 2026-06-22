import { useMemo } from 'react'
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import type { ValueType, NameType } from 'recharts/types/component/DefaultTooltipContent'
import { formatBRL } from '@/utils/format'

const COLORS: Record<string, string> = {
  ACAO:              'var(--color-blue)',
  ACAO_NACIONAL:     'var(--color-blue)',
  FII:               'var(--color-purple)',
  ETF_NACIONAL:      'var(--color-primary)',
  ETF_INTERNACIONAL: 'var(--color-teal)',
  ETF_INT:           'var(--color-teal)',
  STOCK:             'var(--color-cyan)',
  STOCKS:            'var(--color-cyan)',
  TESOURO:           'var(--color-gold)',
  TESOURO_DIRETO:    'var(--color-gold)',
  RENDA_FIXA:        'var(--color-orange)',
  CRIPTO:            'var(--color-error)',
  CRIPTOMOEDA:       'var(--color-error)',
}
const FALLBACK_COLORS = [
  'var(--color-blue)','var(--color-purple)','var(--color-primary)',
  'var(--color-teal)','var(--color-gold)','var(--color-orange)',
]

interface AllocItem {
  asset_type: string
  label?: string
  value: number
  percentage: number
}

interface Props {
  data: AllocItem[]
  loading?: boolean
}

function colorFor(assetType: string, idx: number): string {
  return COLORS[assetType.toUpperCase()] ?? FALLBACK_COLORS[idx % FALLBACK_COLORS.length]
}

export default function AllocationChart({ data, loading }: Props) {
  const chartData = useMemo(() =>
    data.map(d => ({ name: d.label ?? d.asset_type, value: d.value, asset_type: d.asset_type }))
  , [data])

  if (loading) {
    return <div className="skeleton h-64 w-full rounded-xl" />
  }

  if (!data.length) {
    return (
      <div className="flex items-center justify-center h-48" style={{ color: 'var(--color-text-faint)' }}>
        <p className="text-sm">Sem dados de alocação</p>
      </div>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={260}>
      <PieChart>
        <Pie
          data={chartData}
          cx="50%" cy="50%"
          innerRadius={60} outerRadius={100}
          paddingAngle={2}
          dataKey="value"
        >
          {chartData.map((entry, idx) => (
            <Cell key={`cell-${idx}`} fill={colorFor(entry.asset_type, idx)} />
          ))}
        </Pie>
        <Tooltip
          formatter={(value: ValueType, _name: NameType) => {
            if (typeof value !== 'number') return ['-', 'Valor']
            return [formatBRL(value), 'Valor']
          }}
          contentStyle={{
            background: 'var(--color-surface)',
            border: '1px solid var(--color-border)',
            borderRadius: 8,
            fontSize: 12,
          }}
        />
        <Legend
          formatter={(value: string) => (
            <span style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>{value}</span>
          )}
        />
      </PieChart>
    </ResponsiveContainer>
  )
}
