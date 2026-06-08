import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ResponsiveContainer
} from 'recharts'
import { PatrimonioHistorico } from '@/services/portfolioService'
import { formatBRL } from '@/utils/format'

const COLORS = { aplicado: '#4f98a3', ganho: '#22c55e' }

interface Props {
  data: PatrimonioHistorico[]
}

function CustomTooltip({ active, payload, label }: { active?: boolean; payload?: { value: number; name: string }[]; label?: string }) {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-white dark:bg-dark-600 border border-light-border dark:border-dark-border rounded-lg p-3 shadow-lg text-xs">
      <p className="font-semibold mb-2 text-gray-800 dark:text-gray-200">{label}</p>
      {payload.map(p => (
        <div key={p.name} className="flex items-center gap-2 mb-1">
          <span className="w-2 h-2 rounded-full" style={{ backgroundColor: p.name === 'valor_aplicado' ? COLORS.aplicado : COLORS.ganho }} />
          <span className="text-muted">{p.name === 'valor_aplicado' ? 'Valor aplicado' : 'Ganho de Capital'}:</span>
          <span className="font-medium text-gray-800 dark:text-gray-200">{formatBRL(p.value)}</span>
        </div>
      ))}
    </div>
  )
}

export default function PatrimonioBarChart({ data }: Props) {
  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} margin={{ top: 4, right: 4, left: 0, bottom: 0 }} barSize={14}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(128,128,128,0.1)" vertical={false} />
        <XAxis
          dataKey="month"
          tick={{ fontSize: 10, fill: 'currentColor' }}
          className="text-gray-400"
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tick={{ fontSize: 10, fill: 'currentColor' }}
          className="text-gray-400"
          axisLine={false}
          tickLine={false}
          tickFormatter={v => formatBRL(v, true)}
          width={60}
        />
        <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(128,128,128,0.05)' }} />
        <Legend
          wrapperStyle={{ fontSize: 11, paddingTop: 8 }}
          formatter={(value) => value === 'valor_aplicado' ? 'Valor aplicado' : 'Ganho de Capital'}
        />
        <Bar dataKey="valor_aplicado" stackId="a" fill={COLORS.aplicado} radius={[0, 0, 2, 2]} />
        <Bar dataKey="ganho_capital" stackId="a" fill={COLORS.ganho} radius={[2, 2, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}
