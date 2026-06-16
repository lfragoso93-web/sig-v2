import { useMemo } from 'react'
import { formatBRL } from '@/utils/format'

interface MonthPoint { month: string; amount: number }
interface Props { data: MonthPoint[] }

export default function DividendChart({ data }: Props) {
  const WIDTH  = 600
  const HEIGHT = 180
  const PAD    = { top: 20, right: 16, bottom: 36, left: 64 }

  const chartW = WIDTH  - PAD.left - PAD.right
  const chartH = HEIGHT - PAD.top  - PAD.bottom

  const { bars, yTicks } = useMemo(() => {
    const maxV   = Math.max(...data.map(d => d.amount), 1)
    const barW   = Math.max(6, (chartW / data.length) * 0.55)
    const gap    = chartW / data.length

    const bars = data.map((d, i) => {
      const barH = (d.amount / maxV) * chartH
      const x    = PAD.left + gap * i + gap / 2 - barW / 2
      const y    = PAD.top + chartH - barH
      return { ...d, x, y, barH, barW }
    })

    const yTicks = Array.from({ length: 4 }, (_, i) => {
      const v = (maxV * i) / 3
      const y = PAD.top + chartH - (v / maxV) * chartH
      return { v, y }
    })

    return { bars, yTicks }
  }, [data])

  return (
    <svg
      viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
      style={{ width: '100%', height: 'auto' }}
      aria-label="Gráfico de proventos mensais"
    >
      {yTicks.map((t, i) => (
        <g key={i}>
          <line
            x1={PAD.left} y1={t.y}
            x2={PAD.left + chartW} y2={t.y}
            stroke="var(--color-divider)" strokeWidth="1"
          />
          <text
            x={PAD.left - 6} y={t.y + 4}
            textAnchor="end" fontSize="9"
            fill="var(--color-text-faint)" fontFamily="inherit"
          >
            {formatBRL(t.v).replace('R$\u00a0', '')}
          </text>
        </g>
      ))}

      {bars.map((b, i) => (
        <g key={i}>
          <rect
            x={b.x} y={b.y}
            width={b.barW} height={b.barH}
            rx="3"
            fill="var(--color-gold)"
            opacity="0.85"
          />
          {b.barH > 20 && (
            <text
              x={b.x + b.barW / 2}
              y={b.y - 4}
              textAnchor="middle"
              fontSize="8"
              fill="var(--color-text-muted)"
              fontFamily="inherit"
            >
              {formatBRL(b.amount).replace('R$\u00a0', '')}
            </text>
          )}
          <text
            x={b.x + b.barW / 2}
            y={PAD.top + chartH + 14}
            textAnchor="middle"
            fontSize="9"
            fill="var(--color-text-faint)"
            fontFamily="inherit"
          >
            {b.month.slice(0, 7)}
          </text>
        </g>
      ))}
    </svg>
  )
}
