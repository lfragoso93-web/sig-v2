import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts'
import { AssetTypeDistribution } from '@/services/portfolioService'
import { formatBRL } from '@/utils/format'

const ASSET_COLORS: Record<string, string> = {
  ACAO_NACIONAL:      '#3b82f6',
  FII:                '#22c55e',
  ETF_NACIONAL:       '#f97316',
  TESOURO_DIRETO:     '#a78bfa',
  STOCK:              '#f43f5e',
  ETF_INTERNACIONAL:  '#2dd4bf',
  CRIPTO:             '#fbbf24',
  RENDA_FIXA:         '#94a3b8',
}

interface Props {
  data: AssetTypeDistribution[]
}

function CustomTooltip({ active, payload }: { active?: boolean; payload?: { name: string; value: number; payload: AssetTypeDistribution }[] }) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div className="bg-white dark:bg-dark-600 border border-light-border dark:border-dark-border rounded-lg p-3 shadow-lg text-xs">
      <p className="font-semibold mb-1 text-gray-800 dark:text-gray-200">{d.label}</p>
      <p className="text-muted">{formatBRL(d.value)} <span className="text-gray-700 dark:text-gray-300">({d.percentage.toFixed(2)}%)</span></p>
    </div>
  )
}

export default function AssetDonutChart({ data }: Props) {
  return (
    <div className="flex flex-col gap-4">
      <ResponsiveContainer width="100%" height={180}>
        <PieChart>
          <Pie
            data={data}
            dataKey="value"
            nameKey="label"
            cx="50%"
            cy="50%"
            innerRadius={55}
            outerRadius={80}
            paddingAngle={2}
          >
            {data.map(entry => (
              <Cell key={entry.type} fill={ASSET_COLORS[entry.type] ?? '#64748b'} />
            ))}
          </Pie>
          <Tooltip content={<CustomTooltip />} />
        </PieChart>
      </ResponsiveContainer>

      {/* Legenda */}
      <div className="flex flex-col gap-1.5">
        {data.map(entry => (
          <div key={entry.type} className="flex items-center justify-between text-xs">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: ASSET_COLORS[entry.type] ?? '#64748b' }} />
              <span className="text-muted">{entry.label}</span>
            </div>
            <span className="font-medium tabular-nums text-gray-700 dark:text-gray-300">
              {entry.percentage.toFixed(2)}%
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
