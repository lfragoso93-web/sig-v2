import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer
} from 'recharts'
import { formatBRL } from '@/utils/format'

// Schema real retornado pelo backend/hook
export interface PatrimonioHistoryPoint {
  month: string
  value: number
}

interface Props {
  data: PatrimonioHistoryPoint[]
}

function CustomTooltip({
  active, payload, label,
}: {
  active?: boolean
  payload?: { value: number; name: string }[]
  label?: string
}) {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-white dark:bg-dark-600 border border-light-border dark:border-dark-border rounded-lg p-3 shadow-lg text-xs">
      <p className="font-semibold mb-2 text-gray-800 dark:text-gray-200">{label}</p>
      <div className="flex items-center gap-2">
        <span className="w-2 h-2 rounded-full" style={{ backgroundColor: '#4f98a3' }} />
        <span className="text-muted">Patrimônio:</span>
        <span className="font-medium text-gray-800 dark:text-gray-200">
          {formatBRL(payload[0].value)}
        </span>
      </div>
    </div>
  )
}

export default function PatrimonioBarChart({ data }: Props) {
  if (!data || data.length === 0) return null

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
          tickFormatter={(v: number) => formatBRL(v)}
          width={60}
        />
        <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(128,128,128,0.05)' }} />
        <Bar dataKey="value" fill="#4f98a3" radius={[4, 4, 0, 0]} name="value" />
      </BarChart>
    </ResponsiveContainer>
  )
}
