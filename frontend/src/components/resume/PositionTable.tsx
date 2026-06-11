import { useState } from 'react'
import { ChevronDown, ChevronRight, HelpCircle } from 'lucide-react'
import clsx from 'clsx'
import { formatBRL, formatPercent, signClass } from '@/utils/format'
import { formatTreasuryName } from '@/utils/treasury'
import type { PositionGroup } from '@/hooks/usePortfolio'

interface Props {
  groups: PositionGroup[]
}

function fmtPrice(val: number | null | undefined): string {
  if (val === null || val === undefined) return '—'
  return formatBRL(val)
}

/** Retorna o nome de exibição do ativo: amigável para Tesouro, ticker puro para demais. */
function displayName(ticker: string, assetType: string): string {
  const norm = assetType.toUpperCase()
  if (norm === 'TESOURO_DIRETO' || norm === 'TESOURO') {
    return formatTreasuryName(ticker)
  }
  return ticker
}

export default function PositionTable({ groups }: Props) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>(
    Object.fromEntries((groups ?? []).map(g => [g.label, true]))
  )

  const toggle = (label: string) =>
    setExpanded(prev => ({ ...prev, [label]: !prev[label] }))

  if (!groups || groups.length === 0) return null

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
                <HelpCircle
                  size={10}
                  className="text-slate-600"
                  title="Cotação via BRAPI/yfinance. '—' quando indisponível."
                />
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
              {expanded[group.label] && (group.positions ?? []).map(item => {
                const hasQuote = item.current_price !== item.average_price
                  || item.variation_value !== 0

                const name = displayName(item.ticker, item.asset_type)
                const isTesouro = item.asset_type.toUpperCase() === 'TESOURO_DIRETO'
                  || item.asset_type.toUpperCase() === 'TESOURO'

                return (
                  <tr
                    key={`${item.ticker}-${item.asset_type}-${item.id}`}
                    className="border-b border-surface-700/50 hover:bg-surface-800/30 transition-colors"
                  >
                    <td className="px-4 py-2.5">
                      <div
                        className="font-semibold text-slate-200 truncate max-w-[200px]"
                        title={item.ticker}
                      >
                        {name}
                      </div>
                      {/* Para Tesouro, exibe o ticker como subtítulo discreto; para demais, exibe o asset_label */}
                      <div className="text-[10px] text-slate-500">
                        {isTesouro ? item.ticker : item.asset_label}
                      </div>
                    </td>

                    <td className="text-right px-4 py-2.5 tabular-nums text-slate-300">
                      {item.quantity % 1 === 0
                        ? item.quantity.toLocaleString('pt-BR')
                        : item.quantity.toLocaleString('pt-BR', {
                            minimumFractionDigits: 2,
                            maximumFractionDigits: 8,
                          })}
                    </td>

                    <td className="text-right px-4 py-2.5 tabular-nums text-slate-300">
                      {formatBRL(item.average_price)}
                    </td>

                    {/* P. Atual */}
                    <td className="text-right px-4 py-2.5 tabular-nums">
                      <span className={hasQuote ? 'text-slate-200' : 'text-slate-600'}>
                        {fmtPrice(item.current_price)}
                      </span>
                    </td>

                    <td className="text-right px-4 py-2.5 tabular-nums text-slate-300">
                      {formatBRL(item.current_value)}
                    </td>

                    <td className="text-right px-4 py-2.5 tabular-nums text-slate-300">
                      {formatBRL(item.current_value)}
                    </td>

                    {/* Resultado */}
                    <td className="text-right px-4 py-2.5 tabular-nums">
                      {hasQuote ? (
                        <div className={clsx('font-medium', signClass(item.variation_value))}>
                          <div>{formatBRL(item.variation_value)}</div>
                          <div className="text-[10px]">{formatPercent(item.variation_percent)}</div>
                        </div>
                      ) : (
                        <span className="text-slate-600" title="Cotação indisponível">—</span>
                      )}
                    </td>
                  </tr>
                )
              })}
            </>
          ))}
        </tbody>
      </table>
    </div>
  )
}
