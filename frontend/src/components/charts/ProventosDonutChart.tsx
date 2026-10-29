import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts'
import { ProventoDistribution } from '@/services/proventosService'
import { formatBRL } from '@/utils/format'

/**
 * Paleta semântica usando apenas CSS vars do design system.
 *
 * As variáveis --color-chart-1..10 são definidas no tema global e
 * mudam automaticamente entre modo claro e escuro, garantindo
 * consistência visual com o resto da aplicação.
 *
 * Fallbacks em oklch para ambientes sem suporte a CSS vars.
 */
const PALETTE = [
  'var(--color-primary)',
  'var(--color-chart-2,  oklch(0.65 0.17 145))',  // verde
  'var(--color-chart-3,  oklch(0.68 0.19 47))',   // laranja
  'var(--color-chart-4,  oklch(0.65 0.18 295))',  // violeta
  'var(--color-chart-5,  oklch(0.60 0.22 10))',   // rosa-vermelho
  'var(--color-chart-6,  oklch(0.72 0.14 187))',  // teal
  'var(--color-chart-7,  oklch(0.78 0.17 88))',   // amarelo
  'var(--color-chart-8,  oklch(0.63 0.04 255))',  // slate
  'var(--color-chart-9,  oklch(0.63 0.22 355))',  // pink
  'var(--color-chart-10, oklch(0.67 0.18 160))',  // esmeralda
]

function CustomTooltip({ active, payload }: {
  active?: boolean
  payload?: { payload: ProventoDistribution }[]
}) {
  if (!active || !payload?.length) return null
  const d = payload[0].payload
  return (
    <div
      className="rounded-lg p-3 text-xs"
      style={{
        background:  'var(--color-surface)',
        border:      '1px solid var(--color-border)',
        boxShadow:   'var(--shadow-lg)',
      }}
    >
      <p className="font-semibold mb-1" style={{ color: 'var(--color-text)' }}>{d.ticker}</p>
      <p style={{ color: 'var(--color-text-muted)' }}>
        {formatBRL(d.total)}
        <span className="ml-1" style={{ color: 'var(--color-text)' }}>({d.percentage.toFixed(2)}%)</span>
      </p>
    </div>
  )
}

export default function ProventosDonutChart({ data }: { data: ProventoDistribution[] }) {
  const top = data.slice(0, 10)
  return (
    <div className="flex flex-col md:flex-row md:items-center gap-6 py-2">
      <div className="w-full md:w-[220px] shrink-0">
        <ResponsiveContainer width="100%" height={180}>
          <PieChart>
            <Pie
              data={top}
              dataKey="total"
              nameKey="ticker"
              cx="50%" cy="50%"
              innerRadius={52}
              outerRadius={80}
              paddingAngle={2}
            >
              {top.map((entry, i) => (
                <Cell key={entry.ticker} fill={PALETTE[i % PALETTE.length]} />
              ))}
            </Pie>
            <Tooltip content={<CustomTooltip />} />
          </PieChart>
        </ResponsiveContainer>
      </div>

      {/* Legenda horizontal em grid */}
      <div className="flex-1 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-x-6 gap-y-2.5">
        {top.map((entry, i) => (
          <div
            key={entry.ticker}
            className="flex flex-col gap-1 p-2.5 rounded-lg"
            style={{ background: 'var(--color-surface-offset)' }}
          >
            <div className="flex items-center justify-between text-xs gap-2">
              <div className="flex items-center gap-2 min-w-0">
                <span
                  className="w-2.5 h-2.5 rounded-full shrink-0"
                  style={{ backgroundColor: PALETTE[i % PALETTE.length] }}
                />
                <span className="font-semibold truncate" style={{ color: 'var(--color-text)' }}>
                  {entry.ticker}
                </span>
              </div>
              <span className="font-medium tabular-nums shrink-0" style={{ color: 'var(--color-primary)' }}>
                {entry.percentage.toFixed(2)}%
              </span>
            </div>
            <div className="flex items-center justify-between text-[11px] pl-4.5">
              <span className="tabular-nums" style={{ color: 'var(--color-text-muted)' }}>
                {formatBRL(entry.total)}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
