import clsx from 'clsx'
import { useState } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'
import type { PositionGroup } from '@/hooks/usePortfolio'
import { formatBRL, formatPercent, signClass, assetBadgeClass } from '@/utils/format'

interface Props {
  groups: PositionGroup[]
}

export default function PositionTable({ groups }: Props) {
  const [open, setOpen] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(groups.map(g => [g.asset_type, true]))
  )
  if (!groups || groups.length === 0) return null
  return (
    <div className="w-full overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-xs text-slate-500 border-b border-surface-700">
            <th className="text-left px-4 py-2 font-medium">Ativo</th>
            <th className="text-right px-3 py-2 font-medium">Qtd</th>
            <th className="text-right px-3 py-2 font-medium">P. Médio</th>
            <th className="text-right px-3 py-2 font-medium">P. Atual</th>
            <th className="text-right px-3 py-2 font-medium">Total</th>
            <th className="text-right px-4 py-2 font-medium">Result.</th>
          </tr>
        </thead>
        <tbody>
          {groups.map(group => (
            <>
              {/* Linha de grupo */}
              <tr
                key={`group-${group.asset_type}`}
                className="bg-surface-800/50 cursor-pointer hover:bg-surface-800 transition-colors"
                onClick={() => setOpen(o => ({ ...o, [group.asset_type]: !o[group.asset_type] }))}
              >
                <td colSpan={4} className="px-4 py-2">
                  <div className="flex items-center gap-2">
                    {open[group.asset_type]
                      ? <ChevronDown size={14} className="text-slate-500" />
                      : <ChevronRight size={14} className="text-slate-500" />}
                    <span className="text-xs font-semibold text-slate-300">{group.label}</span>
                    <span className="text-xs text-slate-500">({group.count})</span>
                  </div>
                </td>
                <td className="text-right px-3 py-2 text-xs font-semibold text-slate-300">
                  {formatBRL(group.total_value)}
                </td>
                <td className={clsx('text-right px-4 py-2 text-xs font-semibold', signClass(group.variation_percent))}>
                  {formatPercent(group.variation_percent)}
                </td>
              </tr>

              {/* Linhas de posição */}
              {open[group.asset_type] && group.positions.map(p => (
                <tr
                  key={`pos-${p.id}`}
                  className="border-b border-surface-800 hover:bg-surface-800/30 transition-colors"
                >
                  <td className="px-4 py-2.5">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-slate-200">{p.ticker}</span>
                      <span className={`asset-badge ${assetBadgeClass(p.asset_type)}`}>
                        {p.asset_type}
                      </span>
                    </div>
                  </td>
                  <td className="text-right px-3 py-2.5 tabular-nums text-slate-400">
                    {p.quantity}
                  </td>
                  <td className="text-right px-3 py-2.5 tabular-nums text-slate-400">
                    {formatBRL(p.average_price)}
                  </td>
                  <td className="text-right px-3 py-2.5 tabular-nums text-slate-400">
                    {formatBRL(p.current_price)}
                  </td>
                  <td className="text-right px-3 py-2.5 tabular-nums font-medium text-slate-200">
                    {formatBRL(p.current_value)}
                  </td>
                  <td className="text-right px-4 py-2.5">
                    <span className={clsx('tabular-nums font-semibold', signClass(p.variation_percent))}>
                      {formatPercent(p.variation_percent)}
                    </span>
                  </td>
                </tr>
              ))}
            </>
          ))}
        </tbody>
      </table>
    </div>
  )
}
