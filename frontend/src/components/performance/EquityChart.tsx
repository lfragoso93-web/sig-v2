import { useMemo } from 'react'
import type { EquityPoint } from '@/hooks/usePerformance'
import { formatBRL, formatDateShort } from '@/utils/format'

interface Props {
  data: EquityPoint[]
}

export default function EquityChart({ data }: Props) {
  const WIDTH  = 600
  const HEIGHT = 200
  const PAD    = { top: 16, right: 16, bottom: 28, left: 64 }

  const chartW = WIDTH  - PAD.left - PAD.right
  const chartH = HEIGHT - PAD.top  - PAD.bottom

  const { minV, maxV, points, area, line, labels } = useMemo(() => {
    const values = data.map(d => d.value)
    const minV   = Math.min(...values) * 0.995
    const maxV   = Math.max(...values) * 1.005
    const range  = maxV - minV || 1

    const toX = (i: number) => PAD.left + (i / (data.length - 1)) * chartW
    const toY = (v: number) => PAD.top  + chartH - ((v - minV) / range) * chartH

    const pts = data.map((d, i) => ({ x: toX(i), y: toY(d.value), ...d }))

    // Linha
    const line = pts.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ')

    // Área (fecha pelo rodapé)
    const area = [
      ...pts.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`),
      `L ${pts[pts.length - 1].x} ${PAD.top + chartH}`,
      `L ${PAD.left} ${PAD.top + chartH}`,
      'Z',
    ].join(' ')

    // Labels do eixo X (até 6 datas distribuídas)
    const step  = Math.max(1, Math.floor(data.length / 6))
    const labels = pts.filter((_, i) => i % step === 0 || i === pts.length - 1)

    return { minV, maxV, points: pts, area, line, labels }
  }, [data])

  // Y ticks (4 níveis)
  const yTicks = useMemo(() => {
    const range = maxV - minV || 1
    return Array.from({ length: 4 }, (_, i) => {
      const v = minV + (range * i) / 3
      const y = PAD.top + chartH - ((v - minV) / range) * chartH
      return { v, y }
    })
  }, [minV, maxV])

  const lastPoint = points[points.length - 1]
  const firstVal  = data[0]?.value ?? 0
  const lastVal   = lastPoint?.y != null ? data[data.length - 1].value : 0
  const positive  = lastVal >= firstVal
  const lineColor = positive ? 'var(--color-success)' : 'var(--color-notification)'

  return (
    <div style={{ position: 'relative', width: '100%' }}>
      <svg
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        style={{ width: '100%', height: 'auto', overflow: 'visible' }}
        aria-label="Gráfico de evolução do patrimônio"
      >
        <defs>
          <linearGradient id="area-grad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%"  stopColor={lineColor} stopOpacity="0.18" />
            <stop offset="100%" stopColor={lineColor} stopOpacity="0.01" />
          </linearGradient>
        </defs>

        {/* Grid lines horizontais */}
        {yTicks.map((t, i) => (
          <g key={i}>
            <line
              x1={PAD.left} y1={t.y}
              x2={PAD.left + chartW} y2={t.y}
              stroke="var(--color-divider)" strokeWidth="1"
            />
            <text
              x={PAD.left - 6} y={t.y + 4}
              textAnchor="end"
              fontSize="9"
              fill="var(--color-text-faint)"
              fontFamily="inherit"
            >
              {formatBRL(t.v).replace('R$\u00a0', '')}
            </text>
          </g>
        ))}

        {/* Área */}
        <path d={area} fill="url(#area-grad)" />

        {/* Linha */}
        <path
          d={line}
          fill="none"
          stroke={lineColor}
          strokeWidth="2"
          strokeLinejoin="round"
          strokeLinecap="round"
        />

        {/* Labels eixo X */}
        {labels.map((p, i) => (
          <text
            key={i}
            x={p.x}
            y={PAD.top + chartH + 16}
            textAnchor="middle"
            fontSize="9"
            fill="var(--color-text-faint)"
            fontFamily="inherit"
          >
            {formatDateShort(p.date)}
          </text>
        ))}

        {/* Ponto final com tooltip */}
        {lastPoint && (
          <g>
            <circle
              cx={lastPoint.x} cy={lastPoint.y} r="4"
              fill={lineColor} stroke="var(--color-surface)" strokeWidth="2"
            />
            {/* Valor no ponto final */}
            <text
              x={lastPoint.x}
              y={lastPoint.y - 10}
              textAnchor={lastPoint.x > WIDTH * 0.7 ? 'end' : 'middle'}
              fontSize="10"
              fontWeight="600"
              fill={lineColor}
              fontFamily="inherit"
            >
              {formatBRL(data[data.length - 1].value)}
            </text>
          </g>
        )}
      </svg>
    </div>
  )
}
