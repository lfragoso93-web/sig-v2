import { useMemo } from 'react'

interface TreemapItem {
  label: string
  value: number
  color: string
}

interface Rect { x: number; y: number; w: number; h: number }

// Squarified treemap algorithm
function squarify(items: { v: number; idx: number }[], rect: Rect): ({ idx: number } & Rect)[] {
  if (items.length === 0) return []
  const total = items.reduce((s, i) => s + i.v, 0)
  if (total === 0) return []

  const result: ({ idx: number } & Rect)[] = []

  function worst(row: number[], w: number, total: number) {
    const s = row.reduce((a, b) => a + b, 0)
    const max = Math.max(...row)
    const min = Math.min(...row)
    return Math.max((w * w * max) / (s * s), (s * s) / (w * w * min))
  }

  function layoutRow(row: { v: number; idx: number }[], r: Rect, horizontal: boolean) {
    const rowTotal = row.reduce((s, i) => s + i.v, 0)
    const rectTotal = r.w * r.h
    let offset = 0
    row.forEach(item => {
      const ratio = item.v / rowTotal
      if (horizontal) {
        const cellH = (rowTotal / total) * r.h
        const cellW = ratio * r.w
        result.push({ idx: item.idx, x: r.x + offset, y: r.y, w: Math.max(cellW, 1), h: Math.max(cellH, 1) })
        offset += cellW
      } else {
        const cellW = (rowTotal / total) * r.w
        const cellH = ratio * r.h
        result.push({ idx: item.idx, x: r.x, y: r.y + offset, w: Math.max(cellW, 1), h: Math.max(cellH, 1) })
        offset += cellH
      }
    })
  }

  function layout(nodes: { v: number; idx: number }[], r: Rect) {
    if (nodes.length === 0) return
    if (nodes.length === 1) {
      result.push({ idx: nodes[0].idx, x: r.x, y: r.y, w: r.w, h: r.h })
      return
    }

    const horizontal = r.w >= r.h
    const w = horizontal ? r.h : r.w
    let row: { v: number; idx: number }[] = []
    let remaining = [...nodes]
    const scale = (r.w * r.h) / total

    while (remaining.length > 0) {
      const next = remaining[0]
      const scaled = next.v * scale
      if (row.length === 0 || worst(row.map(i => i.v * scale), w, row.reduce((s, i) => s + i.v * scale, 0)) >=
          worst([...row.map(i => i.v * scale), scaled], w, row.reduce((s, i) => s + i.v * scale, 0) + scaled)) {
        row.push(next)
        remaining = remaining.slice(1)
      } else {
        const rowTotal = row.reduce((s, i) => s + i.v, 0)
        const frac = rowTotal / total
        const newRect: Rect = horizontal
          ? { x: r.x, y: r.y + frac * r.h, w: r.w, h: r.h * (1 - frac) }
          : { x: r.x + frac * r.w, y: r.y, w: r.w * (1 - frac), h: r.h }
        layoutRow(row, r, horizontal)
        layout(remaining, newRect)
        return
      }
    }
    if (row.length > 0) layoutRow(row, r, horizontal)
  }

  const scaled = items.map(i => ({ ...i, v: (i.v / total) * rect.w * rect.h }))
  layout(scaled, rect)
  return result
}

const W = 600
const H = 340
const GAP = 2

export default function ConcentrationTreemap({ items }: { items: TreemapItem[] }) {
  const rects = useMemo(() => {
    const sorted = [...items]
      .filter(i => i.value > 0)
      .sort((a, b) => b.value - a.value)
    const total = sorted.reduce((s, i) => s + i.value, 0)
    const input = sorted.map((item, idx) => ({ v: item.value / total, idx }))
    const raw = squarify(input, { x: 0, y: 0, w: W, h: H })
    return raw.map(r => ({ ...r, item: sorted[r.idx] }))
  }, [items])

  if (rects.length === 0) return (
    <div style={{ height: H, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--color-text-faint)', fontSize: 'var(--text-sm)' }}>
      Nenhum dado
    </div>
  )

  const total = items.filter(i => i.value > 0).reduce((s, i) => s + i.value, 0)

  return (
    <div style={{ width: '100%', overflowX: 'auto' }}>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        style={{ width: '100%', height: 'auto', display: 'block', minWidth: 280 }}
        aria-label="Treemap de concentração de ativos"
      >
        {rects.map(({ x, y, w, h, item, idx }) => {
          const pct = total > 0 ? (item.value / total) * 100 : 0
          const showLabel = w > 48 && h > 28
          const showPct   = w > 56 && h > 44
          return (
            <g key={idx}>
              <rect
                x={x + GAP / 2} y={y + GAP / 2}
                width={Math.max(w - GAP, 1)} height={Math.max(h - GAP, 1)}
                rx={4} fill={item.color}
                style={{ opacity: 0.88, transition: 'opacity 150ms' }}
              />
              {showLabel && (
                <text
                  x={x + GAP / 2 + 8} y={y + GAP / 2 + 18}
                  fontSize={Math.min(13, Math.max(9, w / 8))}
                  fontWeight={600} fill="white"
                  style={{ pointerEvents: 'none', textShadow: '0 1px 2px rgba(0,0,0,.4)' }}
                >
                  {item.label}
                </text>
              )}
              {showPct && (
                <text
                  x={x + GAP / 2 + 8} y={y + GAP / 2 + 34}
                  fontSize={Math.min(11, Math.max(8, w / 10))}
                  fill="rgba(255,255,255,0.82)"
                  style={{ pointerEvents: 'none' }}
                >
                  {pct.toFixed(1)}%
                </text>
              )}
            </g>
          )
        })}
      </svg>
    </div>
  )
}
