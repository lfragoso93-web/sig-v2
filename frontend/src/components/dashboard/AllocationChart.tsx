import type { Position } from '@/hooks/usePerformance'

interface Props {
  positions: Position[]
}

// Agrupa por tipo e calcula % de alocação
function groupByType(positions: Position[]) {
  const map: Record<string, number> = {}
  let total = 0
  for (const p of positions) {
    map[p.asset_type] = (map[p.asset_type] ?? 0) + p.current_value
    total += p.current_value
  }
  return Object.entries(map)
    .map(([type, value]) => ({ type, value, pct: total > 0 ? (value / total) * 100 : 0 }))
    .sort((a, b) => b.value - a.value)
}

const TYPE_COLORS: Record<string, string> = {
  'acao nacional':     'var(--color-blue)',
  'fii':               'var(--color-gold)',
  'etf nacional':      'var(--color-purple)',
  'tesouro direto':    'var(--color-success)',
  'stock':             'var(--color-primary)',
  'etf internacional': 'var(--color-blue)',
  'criptomoeda':       'var(--color-orange)',
  'renda fixa':        'var(--color-warning)',
}

function getColor(type: string) {
  return TYPE_COLORS[type.toLowerCase()] ?? 'var(--color-text-muted)'
}

export default function AllocationChart({ positions }: Props) {
  const groups = groupByType(positions)

  if (groups.length === 0) {
    return (
      <div className="bg-surface border border-[var(--color-border)] rounded-xl p-6 flex items-center justify-center h-full">
        <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>Sem dados</p>
      </div>
    )
  }

  // Gera SVG de donut simples
  const size = 140
  const cx = size / 2
  const cy = size / 2
  const r = 52
  const innerR = 34
  const gap = 2

  let cumAngle = -90 // começa no topo
  const slices = groups.map(g => {
    const angle = (g.pct / 100) * 360
    const slice = { ...g, startAngle: cumAngle, angle }
    cumAngle += angle + gap
    return slice
  })

  function polarToCart(angle: number, radius: number) {
    const rad = (angle * Math.PI) / 180
    return { x: cx + radius * Math.cos(rad), y: cy + radius * Math.sin(rad) }
  }

  function describeArc(startAngle: number, angle: number) {
    if (angle >= 358) angle = 357.99
    const start = polarToCart(startAngle, r)
    const end = polarToCart(startAngle + angle, r)
    const iStart = polarToCart(startAngle + angle, innerR)
    const iEnd = polarToCart(startAngle, innerR)
    const large = angle > 180 ? 1 : 0
    return [
      `M ${start.x} ${start.y}`,
      `A ${r} ${r} 0 ${large} 1 ${end.x} ${end.y}`,
      `L ${iStart.x} ${iStart.y}`,
      `A ${innerR} ${innerR} 0 ${large} 0 ${iEnd.x} ${iEnd.y}`,
      'Z',
    ].join(' ')
  }

  return (
    <div className="bg-surface border border-[var(--color-border)] rounded-xl p-5 flex flex-col gap-4">
      <h3 className="text-sm font-semibold">Alocação</h3>

      {/* Donut SVG */}
      <div className="flex justify-center">
        <svg viewBox={`0 0 ${size} ${size}`} width={size} height={size}>
          {slices.map((s) => (
            <path
              key={s.type}
              d={describeArc(s.startAngle, s.angle)}
              fill={getColor(s.type)}
              opacity={0.85}
            />
          ))}
          {/* Centro */}
          <circle cx={cx} cy={cy} r={innerR - 2} fill="var(--color-surface)" />
          <text x={cx} y={cy - 5} textAnchor="middle" fontSize="11"
            fill="var(--color-text-muted)" fontFamily="inherit">
            {groups.length}
          </text>
          <text x={cx} y={cy + 9} textAnchor="middle" fontSize="10"
            fill="var(--color-text-muted)" fontFamily="inherit">
            tipos
          </text>
        </svg>
      </div>

      {/* Legenda */}
      <ul className="flex flex-col gap-2">
        {groups.map(g => (
          <li key={g.type} className="flex items-center justify-between text-xs">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full shrink-0"
                style={{ background: getColor(g.type) }} />
              <span className="capitalize" style={{ color: 'var(--color-text-muted)' }}>{g.type}</span>
            </div>
            <span className="font-semibold tabular-nums">{g.pct.toFixed(1)}%</span>
          </li>
        ))}
      </ul>
    </div>
  )
}
