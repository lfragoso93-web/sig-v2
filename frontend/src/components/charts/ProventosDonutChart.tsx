import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts'
import { ProventoDistribution } from '@/services/proventosService'
import { formatBRL } from '@/utils/format'

const PALETTE = ['#3b82f6','#22c55e','#f97316','#a78bfa','#f43f5e','#2dd4bf','#fbbf24','#94a3b8','#ec4899','#10b981']

function CustomTooltip({ active, payload }: { active?: boolean; payload?: { payload: ProventoDistribution }[] }) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div className="bg-white dark:bg-dark-600 border border-light-border dark:border-dark-border rounded-lg p-3 shadow-lg text-xs">
      <p className="font-semibold mb-1 text-gray-800 dark:text-gray-200">{d.ticker}</p>
      <p className="text-muted">{formatBRL(d.total)} <span className="text-gray-700 dark:text-gray-300">({d.percentage.toFixed(2)}%)</span></p>
    </div>
  )
}

export default function ProventosDonutChart({ data }: { data: ProventoDistribution[] }) {
  const top = data.slice(0, 10)
  return (
    <div className="flex flex-col gap-3">
      <ResponsiveContainer width="100%" height={160}>
        <PieChart>
          <Pie data={top} dataKey="total" nameKey="ticker" cx="50%" cy="50%" innerRadius={45} outerRadius={70} paddingAngle={2}>
            {top.map((entry, i) => (
              <Cell key={entry.ticker} fill={PALETTE[i % PALETTE.length]} />
            ))}
          </Pie>
          <Tooltip content={<CustomTooltip />} />
        </PieChart>
      </ResponsiveContainer>
      <div className="flex flex-col gap-1.5">
        {top.map((entry, i) => (
          <div key={entry.ticker} className="flex items-center justify-between text-xs">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: PALETTE[i % PALETTE.length] }} />
              <span className="text-muted">{entry.ticker}</span>
            </div>
            <span className="font-medium tabular-nums text-gray-700 dark:text-gray-300">{entry.percentage.toFixed(2)}%</span>
          </div>
        ))}
      </div>
    </div>
  )
}
