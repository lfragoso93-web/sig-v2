import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ChevronDown, ChevronRight, HelpCircle,
  MoreHorizontal, Plus, List, BarChart2 as AnalyseIcon,
} from 'lucide-react'
import clsx from 'clsx'
import { formatBRL, formatPercent, signClass } from '@/utils/format'
import { formatTreasuryName } from '@/utils/treasury'
import AssetLogo from '@/components/ui/AssetLogo'
import { useAppStore } from '@/store/appStore'
import type { PositionGroup } from '@/hooks/usePortfolio'

/** Mapeia asset_type -> chave de aba do AddTransactionModal */
function assetTypeToTab(assetType: string): string {
  const map: Record<string, string> = {
    ACAO:              'acao',
    FII:               'fii',
    ETF_NACIONAL:      'etf_br',
    STOCK:             'stock',
    ETF_INTERNACIONAL: 'etf_int',
    TESOURO_DIRETO:    'tesouro',
    TESOURO:           'tesouro',
    RENDA_FIXA:        'renda_fixa',
    CRIPTO:            'cripto',
  }
  return map[assetType.toUpperCase()] ?? 'acao'
}

interface Props {
  groups: PositionGroup[]
}

function fmtPrice(val: number | null | undefined): string {
  if (val === null || val === undefined) return '—'
  return formatBRL(val)
}

function displayName(ticker: string, assetType: string): string {
  const norm = assetType.toUpperCase()
  if (norm === 'TESOURO_DIRETO' || norm === 'TESOURO') return formatTreasuryName(ticker)
  return ticker
}

// ── Componente de dropdown de opções por ativo ────────────────────────────
interface AssetMenuProps {
  ticker: string
  assetLabel: string
  assetType: string
}

function AssetMenu({ ticker, assetLabel, assetType }: AssetMenuProps) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  const navigate = useNavigate()
  const openTransactionModal = useAppStore(s => s.openTransactionModal)

  // fecha ao clicar fora
  useEffect(() => {
    function handler(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const items = [
    {
      icon: <Plus size={13} />,
      label: 'Adicionar Lançamento',
      onClick: () => {
        setOpen(false)
        openTransactionModal({
          tab:       assetTypeToTab(assetType),
          ticker,
          assetName: assetLabel,
        })
      },
    },
    {
      icon: <List size={13} />,
      label: 'Ver Lançamentos',
      onClick: () => {
        setOpen(false)
        navigate(`/transactions?ticker=${encodeURIComponent(ticker)}`)
      },
    },
    {
      icon: <AnalyseIcon size={13} />,
      label: 'Análise do Ativo',
      badge: 'Em breve',
      onClick: () => {
        setOpen(false)
        navigate(`/analysis?ticker=${encodeURIComponent(ticker)}`)
      },
    },
  ]

  return (
    <div ref={ref} className="relative inline-block">
      <button
        type="button"
        onClick={(e) => { e.stopPropagation(); setOpen(v => !v) }}
        className="p-1.5 rounded hover:bg-surface-700 text-slate-500 hover:text-slate-300 transition-colors"
        aria-label="Opções"
      >
        <MoreHorizontal size={14} />
      </button>

      {open && (
        <div className="absolute right-0 top-full z-50 mt-1 w-52 rounded-lg border border-surface-600 bg-surface-800 shadow-xl overflow-hidden">
          {items.map((item, i) => (
            <button
              key={i}
              type="button"
              onClick={item.onClick}
              className="w-full flex items-center gap-2.5 px-3 py-2.5 text-xs text-slate-300 hover:bg-surface-700 transition-colors"
            >
              <span className="text-slate-500">{item.icon}</span>
              <span className="flex-1 text-left">{item.label}</span>
              {item.badge && (
                <span className="text-[9px] font-semibold px-1.5 py-0.5 rounded-full bg-brand-500/20 text-brand-400 border border-brand-500/30">
                  {item.badge}
                </span>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Tabela principal ──────────────────────────────────────────────────────
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
                <HelpCircle size={10} className="text-slate-600" title="Cotação via BRAPI/yfinance. '—' quando indisponível." />
              </span>
            </th>
            <th className="text-right px-4 py-2 font-medium">Total Inv.</th>
            <th className="text-right px-4 py-2 font-medium">Valor Atual</th>
            <th className="text-right px-4 py-2 font-medium">Resultado</th>
            <th className="px-4 py-2" />{/* coluna Opções */}
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
                <td colSpan={8} className="px-4 py-2">
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

              {/* Linhas de posição */}
              {expanded[group.label] && (group.positions ?? []).map(item => {
                const hasQuote  = item.current_price !== item.average_price || item.variation_value !== 0
                const name      = displayName(item.ticker, item.asset_type)
                const isTesouro = item.asset_type.toUpperCase() === 'TESOURO_DIRETO'
                  || item.asset_type.toUpperCase() === 'TESOURO'

                return (
                  <tr
                    key={`${item.ticker}-${item.asset_type}-${item.id}`}
                    className="border-b border-surface-700/50 hover:bg-surface-800/30 transition-colors"
                  >
                    {/* Coluna Ativo */}
                    <td className="px-4 py-2">
                      <div className="flex items-center gap-2.5">
                        <AssetLogo ticker={item.ticker} assetType={item.asset_type} size={28} />
                        <div className="min-w-0">
                          <div
                            className="font-semibold text-slate-200 truncate max-w-[180px]"
                            title={item.ticker}
                          >
                            {name}
                          </div>
                          <div className="text-[10px] text-slate-500 truncate max-w-[180px]">
                            {isTesouro ? item.ticker : item.asset_label}
                          </div>
                        </div>
                      </div>
                    </td>

                    <td className="text-right px-4 py-2 tabular-nums text-slate-300">
                      {item.quantity % 1 === 0
                        ? item.quantity.toLocaleString('pt-BR')
                        : item.quantity.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 8 })}
                    </td>

                    <td className="text-right px-4 py-2 tabular-nums text-slate-300">
                      {formatBRL(item.average_price)}
                    </td>

                    <td className="text-right px-4 py-2 tabular-nums">
                      <span className={hasQuote ? 'text-slate-200' : 'text-slate-600'}>
                        {fmtPrice(item.current_price)}
                      </span>
                    </td>

                    <td className="text-right px-4 py-2 tabular-nums text-slate-300">
                      {formatBRL(item.current_value)}
                    </td>

                    <td className="text-right px-4 py-2 tabular-nums text-slate-300">
                      {formatBRL(item.current_value)}
                    </td>

                    <td className="text-right px-4 py-2 tabular-nums">
                      {hasQuote ? (
                        <div className={clsx('font-medium', signClass(item.variation_value))}>
                          <div>{formatBRL(item.variation_value)}</div>
                          <div className="text-[10px]">{formatPercent(item.variation_percent)}</div>
                        </div>
                      ) : (
                        <span className="text-slate-600" title="Cotação indisponível">—</span>
                      )}
                    </td>

                    {/* Coluna Opções */}
                    <td className="px-2 py-2 text-right">
                      <AssetMenu
                        ticker={item.ticker}
                        assetLabel={isTesouro ? item.ticker : (item.asset_label ?? item.ticker)}
                        assetType={item.asset_type}
                      />
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
