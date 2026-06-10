import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts'
import type { AssetTypeDistribution } from '@/hooks/usePortfolio'

interface Props {
  data: AssetTypeDistribution[]
}

function CustomTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload as AssetTypeDistribution
  return (
    <div className="bg-surface-900 border border-surface-700 rounded-lg p-3 shadow-lg text-xs">
      <p className="font-semibold text-slate-200 mb-1">{d.label}</p>
      <p className="text-slate-400">{d.percentage.toFixed(1)}%</p>
    </div>
  )
}

export default function AssetDonutChart({ data }: Props) {
  if (!data || data.length === 0) return null
  return (
    <ResponsiveContainer width="100%" height={200}>
      <PieChart>
        <Pie
          data={data}
          cx="50%" cy="50%"
          innerRadius={55}
          outerRadius={80}
          paddingAngle={3}
          dataKey="value"
        >
          {data.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={entry.color} />
          ))}
        </Pie>
        <Tooltip content={<CustomTooltip />} />
      </PieChart>
    </ResponsiveContainer>
  )
}
