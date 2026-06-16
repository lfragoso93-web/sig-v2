import { useState } from 'react'
import { ChevronUp, ChevronDown } from 'lucide-react'
import type { Position } from '@/hooks/usePerformance'
import { formatBRL, formatPct, assetBadgeClass } from '@/utils/format'

interface Props {
  positions: Position[]
}

type SortKey = 'gain_pct' | 'gain' | 'current_value' | 'invested'

export default function PerformanceTable({ positions }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>('gain_pct')
  const [sortAsc, setSortAsc] = useState(false)

  function toggleSort(key: SortKey) {
    if (sortKey === key) setSortAsc(a => !a)
    else { setSortKey(key); setSortAsc(false) }
  }

  const sorted = [...positions].sort((a, b) => {
    const diff = a[sortKey] - b[sortKey]
    return sortAsc ? diff : -diff
  })

  function SortIcon({ k }: { k: SortKey }) {
    if (sortKey !== k) return <ChevronDown size={12} style={{ opacity: 0.3 }} />
    return sortAsc
      ? <ChevronUp    size={12} style={{ color: 'var(--color-primary)' }} />
      : <ChevronDown  size={12} style={{ color: 'var(--color-primary)' }} />
  }

  function Th({ label, k }: { label: string; k: SortKey }) {
    return (
      <th
        className="text-right cursor-pointer select-none hover:text-[var(--color-text)] transition-colors"
        onClick={() => toggleSort(k)}
      >
        <span className="inline-flex items-center justify-end gap-1">
          {label} <SortIcon k={k} />
        </span>
      </th>
    )
  }

  if (sorted.length === 0) return null

  return (
    <div className="bg-surface border border-[var(--color-border)] rounded-xl overflow-hidden">
      <div className="px-4 py-3 border-b border-[var(--color-divider)]">
        <h3 className="text-sm font-semibold">Performance por ativo</h3>
      </div>
      <div className="overflow-x-auto">
        <table className="positions-table">
          <thead>
            <tr>
              <th className="text-left">Ativo</th>
              <Th label="Investido"   k="invested"      />
              <Th label="Valor atual" k="current_value" />
              <Th label="Resultado"   k="gain"          />
              <Th label="Rentab. %"   k="gain_pct"      />
            </tr>
          </thead>
          <tbody>
            {sorted.map(p => {
              const pos   = p.gain >= 0
              const color = pos ? 'var(--color-success)' : 'var(--color-notification)'
              // asset_type pode ser undefined no tipo Position — usa fallback ''
              const assetType = p.asset_type ?? ''
              return (
                <tr key={p.ticker}>
                  <td>
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-sm">{p.ticker}</span>
                      <span className={`asset-badge ${assetBadgeClass(assetType)}`}>
                        {assetType}
                      </span>
                    </div>
                    {p.name && (
                      <p className="text-xs mt-0.5" style={{ color: 'var(--color-text-muted)' }}>{p.name}</p>
                    )}
                  </td>
                  <td className="text-right text-sm">{formatBRL(p.invested)}</td>
                  <td className="text-right text-sm font-medium">{formatBRL(p.current_value)}</td>
                  <td className="text-right text-sm" style={{ color }}>
                    {pos ? '+' : ''}{formatBRL(p.gain)}
                  </td>
                  <td className="text-right">
                    <span
                      className="inline-flex items-center justify-end px-2 py-0.5 rounded text-xs font-semibold"
                      style={{ background: `oklch(from ${color} l c h / 0.12)`, color }}
                    >
                      {formatPct(p.gain_pct)}
                    </span>
                  </td>
                </tr>
              )
            })}
          </tbody>
          <tfoot>
            <tr style={{ borderTop: '2px solid var(--color-divider)', background: 'var(--color-surface-offset)' }}>
              <td className="text-sm font-semibold py-3 px-3">Total</td>
              <td className="text-right text-sm font-semibold">
                {formatBRL(sorted.reduce((s, p) => s + p.invested, 0))}
              </td>
              <td className="text-right text-sm font-semibold">
                {formatBRL(sorted.reduce((s, p) => s + p.current_value, 0))}
              </td>
              <td
                className="text-right text-sm font-semibold"
                style={{ color: sorted.reduce((s, p) => s + p.gain, 0) >= 0 ? 'var(--color-success)' : 'var(--color-notification)' }}
              >
                {formatBRL(sorted.reduce((s, p) => s + p.gain, 0))}
              </td>
              <td />
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  )
}
