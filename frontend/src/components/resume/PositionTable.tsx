import { useState } from 'react'
import { ChevronDown, ChevronRight, HelpCircle } from 'lucide-react'
import clsx from 'clsx'
import { formatBRL, formatPercent, signClass } from '@/utils/format'

interface PositionItem {
  ticker:         string
  asset_type:     string
  asset_label:    string
  quantity:       number
  avg_price:      number
  total_invested: number
  current_price:  number | null   // null = cotacao indisponivel
  current_value:  number
  result_abs:     number
  result_pct:     number
}

interface PositionGroup {
  label:    string
  count:    number
  items:    PositionItem[]
}

interface Props {
  groups: PositionGroup[]
}

function fmtPrice(val: number | null, fallback = '—'): string {
  if (val === null || val === undefined) return fallback
  return formatBRL(val)
}

export default function PositionTable({ groups }: Props) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>(
    Object.fromEntries(groups.map(g => [g.label, true]))
  )

  const toggle = (label: string) =>
    setExpanded(prev => ({ ...prev, [label]: !prev[label] }))

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-surface-700 text-slate-500">
            <th className="text-left px-4 py-2 font-medium">Ativo</th>
            <th className="text-right px-4 py-2 font-medium">Qtd</th>
            <th className="text-right px-4 py-2 font-medium">P. Médio</th>
            <th className="text-right px-4 py-2 font-medium">
              <span className="flex items-center justify-end gap-1">
                P. Atual
                <HelpCircle size={10} className="text-slate-600" title="Cotação via BRAPI/yfinance. '—' quando indisponível." />
              </span>
            </th>
            <th className="text-right px-4 py-2 font-medium">Total Inv.</th>
            <th className="text-right px-4 py-2 font-medium">Valor Atual</th>
            <th className="text-right px-4 py-2 font-medium">Resultado</th>
          </tr>
        </thead>
        <tbody>
          {groups.map(group => (
            <>
              {/* Linha de grupo */}
              <tr
                key={`g-${group.label}`}
                onClick={() => toggle(group.label)}
                className="cursor-pointer bg-surface-800/60 hover:bg-surface-800 border-b border-surface-700 transition-colors"
              >
                <td colSpan={7} className="px-4 py-2">
                  <div className="flex items-center gap-2">
                    {expanded[group.label]
                      ? <ChevronDown  size={13} className="text-slate-500" />
                      : <ChevronRight size={13} className="text-slate-500" />}
                    <span className="font-semibold text-slate-300">{group.label}</span>
                    <span className="ml-1 px-1.5 rounded bg-surface-700 text-slate-500 text-[10px]">
                      {group.count}
                    </span>
                  </div>
                </td>
              </tr>

              {/* Linhas de posicao */}
              {expanded[group.label] && group.items.map(item => (
                <tr
                  key={`${item.ticker}-${item.asset_type}`}
                  className="border-b border-surface-700/50 hover:bg-surface-800/30 transition-colors"
                >
                  <td className="px-4 py-2.5">
                    <div className="font-semibold text-slate-200 truncate max-w-[140px]" title={item.ticker}>
                      {item.ticker}
                    </div>
                    <div className="text-[10px] text-slate-500">{item.asset_label}</div>
                  </td>
                  <td className="text-right px-4 py-2.5 tabular-nums text-slate-300">
                    {item.quantity % 1 === 0
                      ? item.quantity.toLocaleString('pt-BR')
                      : item.quantity.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 8 })}
                  </td>
                  <td className="text-right px-4 py-2.5 tabular-nums text-slate-300">
                    {formatBRL(item.avg_price)}
                  </td>
                  {/* P. Atual — mostra '—' quando null (cotacao indisponivel) */}
                  <td className="text-right px-4 py-2.5 tabular-nums">
                    {item.current_price !== null && item.current_price !== undefined
                      ? (
                        <span className="text-slate-200">{formatBRL(item.current_price)}</span>
                      ) : (
                        <span className="text-slate-600" title="Cotação indisponível">—</span>
                      )
                    }
                  </td>
                  <td className="text-right px-4 py-2.5 tabular-nums text-slate-300">
                    {formatBRL(item.total_invested)}
                  </td>
                  <td className="text-right px-4 py-2.5 tabular-nums text-slate-300">
                    {formatBRL(item.current_value)}
                  </td>
                  <td className="text-right px-4 py-2.5 tabular-nums">
                    {item.current_price !== null && item.current_price !== undefined ? (
                      <div className={clsx('font-medium', signClass(item.result_abs))}>
                        <div>{formatBRL(item.result_abs)}</div>
                        <div className="text-[10px]">{formatPercent(item.result_pct)}</div>
                      </div>
                    ) : (
                      <span className="text-slate-600">—</span>
                    )}
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
