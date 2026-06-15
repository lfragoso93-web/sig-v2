import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ChevronDown, ChevronRight, HelpCircle,
  MoreHorizontal, Plus, List, BarChart2 as AnalyseIcon,
} from 'lucide-react'
import { formatBRL, formatPercent } from '@/utils/format'
import { formatTreasuryName } from '@/utils/treasury'
import AssetLogo from '@/components/ui/AssetLogo'
import { useAppStore } from '@/store/appStore'
import type { PositionGroup } from '@/hooks/usePortfolio'

function assetTypeToTab(assetType: string): string {
  const map: Record<string, string> = {
    ACAO: 'acao', FII: 'fii', ETF_NACIONAL: 'etf_br',
    STOCK: 'stock', ETF_INTERNACIONAL: 'etf_int',
    TESOURO_DIRETO: 'tesouro', TESOURO: 'tesouro',
    RENDA_FIXA: 'renda_fixa', CRIPTO: 'cripto',
  }
  return map[assetType.toUpperCase()] ?? 'acao'
}

const cellText     = { color: 'var(--color-text)' }
const cellMuted    = { color: 'var(--color-text-muted)' }
const cellFaint    = { color: 'var(--color-text-faint)' }
const rowHover     = 'hover:bg-[var(--color-surface-offset)] transition-colors'
const groupRowBg   = 'cursor-pointer transition-colors'
const surfaceStyle = { background: 'var(--color-surface-offset)', borderColor: 'var(--color-divider)' }
const dropdownBg   = { background: 'var(--color-surface)', border: '1px solid var(--color-border)', boxShadow: 'var(--shadow-lg)' }

interface Props { groups: PositionGroup[] }

function fmtPrice(val: number | null | undefined): string {
  if (val === null || val === undefined) return '—'
  return formatBRL(val)
}

function displayName(ticker: string, assetType: string): string {
  const norm = assetType.toUpperCase()
  if (norm === 'TESOURO_DIRETO' || norm === 'TESOURO') return formatTreasuryName(ticker)
  return ticker
}

interface AssetMenuProps { ticker: string; assetLabel: string; assetType: string }

function AssetMenu({ ticker, assetLabel, assetType }: AssetMenuProps) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  const navigate = useNavigate()
  const openTransactionModal = useAppStore(s => s.openTransactionModal)

  useEffect(() => {
    function handler(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const items = [
    {
      icon: <Plus size={13} />, label: 'Adicionar Lançamento',
      onClick: () => { setOpen(false); openTransactionModal({ tab: assetTypeToTab(assetType), ticker, assetName: assetLabel }) },
    },
    {
      icon: <List size={13} />, label: 'Ver Lançamentos',
      onClick: () => { setOpen(false); navigate(`/carteira/transacoes?ticker=${encodeURIComponent(ticker)}`) },
    },
    {
      icon: <AnalyseIcon size={13} />, label: 'Análise do Ativo', badge: 'Em breve',
      onClick: () => { setOpen(false); navigate(`/carteira/analise?ticker=${encodeURIComponent(ticker)}`) },
    },
  ]

  return (
    <div ref={ref} className="relative inline-block">
      <button
        type="button"
        onClick={(e) => { e.stopPropagation(); setOpen(v => !v) }}
        className="p-1.5 rounded transition-colors"
        style={{ color: 'var(--color-text-faint)', minWidth: 32, minHeight: 32 }}
        onMouseEnter={e => (e.currentTarget.style.color = 'var(--color-text-muted)')}
        onMouseLeave={e => (e.currentTarget.style.color = 'var(--color-text-faint)')}
        aria-label="Opções"
      >
        <MoreHorizontal size={14} />
      </button>
      {open && (
        <div className="absolute right-0 top-full z-50 mt-1 w-52 rounded-lg overflow-hidden" style={dropdownBg}>
          {items.map((item, i) => (
            <button
              key={i} type="button" onClick={item.onClick}
              className="w-full flex items-center gap-2.5 px-3 py-2.5 text-xs transition-colors"
              style={{ color: 'var(--color-text-muted)' }}
              onMouseEnter={e => { e.currentTarget.style.background = 'var(--color-surface-offset)'; e.currentTarget.style.color = 'var(--color-text)' }}
              onMouseLeave={e => { e.currentTarget.style.background = ''; e.currentTarget.style.color = 'var(--color-text-muted)' }}
            >
              <span style={cellFaint}>{item.icon}</span>
              <span className="flex-1 text-left">{item.label}</span>
              {item.badge && (
                <span className="text-[9px] font-semibold px-1.5 py-0.5 rounded-full"
                  style={{ background: 'var(--color-primary-highlight)', color: 'var(--color-primary)', border: '1px solid var(--color-primary-highlight)' }}>
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

interface PositionCardProps {
  item: PositionGroup['positions'][number]
}

function PositionCard({ item }: PositionCardProps) {
  const isTesouro = item.asset_type.toUpperCase() === 'TESOURO_DIRETO' || item.asset_type.toUpperCase() === 'TESOURO'
  const name = displayName(item.ticker, item.asset_type)
  const hasQuote = item.variation_value !== 0 || item.current_price !== item.average_price
  const varColor = item.variation_value >= 0 ? 'var(--color-success)' : 'var(--color-error)'
  const investedValue = item.invested_value ?? item.quantity * item.average_price

  return (
    <div
      className="rounded-xl p-3 flex flex-col gap-2"
      style={{ background: 'var(--color-surface-offset)', border: '1px solid var(--color-divider)' }}
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <AssetLogo ticker={item.ticker} assetType={item.asset_type} size={32} />
          <div className="min-w-0">
            <div className="font-semibold text-sm truncate" style={cellText}>{name}</div>
            <div className="text-[10px] truncate" style={cellFaint}>
              {isTesouro ? item.ticker : item.asset_label}
            </div>
          </div>
        </div>
        <AssetMenu
          ticker={item.ticker}
          assetLabel={isTesouro ? item.ticker : (item.asset_label ?? item.ticker)}
          assetType={item.asset_type}
        />
      </div>

      <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-xs">
        <div>
          <div className="text-[10px]" style={cellFaint}>Qtd</div>
          <div className="font-medium tabular-nums" style={cellText}>
            {item.quantity % 1 === 0
              ? item.quantity.toLocaleString('pt-BR')
              : item.quantity.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 8 })}
          </div>
        </div>
        <div>
          <div className="text-[10px]" style={cellFaint}>Preço Médio</div>
          <div className="font-medium tabular-nums" style={cellText}>{formatBRL(item.average_price)}</div>
        </div>
        <div>
          <div className="text-[10px]" style={cellFaint}>Valor Investido</div>
          <div className="font-medium tabular-nums" style={cellText}>{formatBRL(investedValue)}</div>
        </div>
        <div>
          <div className="text-[10px]" style={cellFaint}>Valor Atual</div>
          <div className="font-medium tabular-nums" style={cellText}>{formatBRL(item.current_value)}</div>
        </div>
        <div>
          <div className="text-[10px]" style={cellFaint}>Resultado</div>
          {hasQuote ? (
            <div className="font-medium tabular-nums" style={{ color: varColor }}>
              {formatBRL(item.variation_value)}
              <span className="ml-1 text-[10px]">({formatPercent(item.variation_percent)})</span>
            </div>
          ) : (
            <span style={cellFaint}>—</span>
          )}
        </div>
      </div>
    </div>
  )
}

export default function PositionTable({ groups }: Props) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>(
    Object.fromEntries((groups ?? []).map(g => [g.label, true]))
  )
  const toggle = (label: string) => setExpanded(prev => ({ ...prev, [label]: !prev[label] }))

  if (!groups || groups.length === 0) return null

  return (
    <>
      <div className="flex flex-col gap-4 md:hidden">
        {groups.map(group => (
          <div key={group.label}>
            <button
              onClick={() => toggle(group.label)}
              className="w-full flex items-center gap-2 px-1 py-2 text-xs font-semibold transition-colors"
              style={cellText}
            >
              {expanded[group.label]
                ? <ChevronDown size={13} style={cellFaint} />
                : <ChevronRight size={13} style={cellFaint} />}
              {group.label}
              <span className="ml-1 px-1.5 rounded text-[10px]"
                style={{ background: 'var(--color-surface-dynamic)', color: 'var(--color-text-muted)' }}>
                {group.count}
              </span>
            </button>
            {expanded[group.label] && (
              <div className="flex flex-col gap-2">
                {(group.positions ?? []).map(item => (
                  <PositionCard key={`${item.ticker}-${item.asset_type}-${item.id}`} item={item} />
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="hidden md:block overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr style={{ borderBottom: '1px solid var(--color-divider)' }}>
              <th className="text-left px-4 py-2 font-medium" style={cellMuted}>Ativo</th>
              <th className="text-right px-4 py-2 font-medium" style={cellMuted}>Qtd</th>
              <th className="text-right px-4 py-2 font-medium" style={cellMuted}>P. Médio</th>
              <th className="text-right px-4 py-2 font-medium" style={cellMuted}>
                <span className="flex items-center justify-end gap-1">
                  P. Atual
                  <HelpCircle size={10} style={cellFaint} title="Cotação via BRAPI/yfinance." />
                </span>
              </th>
              <th className="text-right px-4 py-2 font-medium" style={cellMuted}>Total Inv.</th>
              <th className="text-right px-4 py-2 font-medium" style={cellMuted}>Valor Atual</th>
              <th className="text-right px-4 py-2 font-medium" style={cellMuted}>Resultado</th>
              <th className="px-4 py-2" />
            </tr>
          </thead>
          <tbody>
            {groups.map(group => (
              <>
                <tr
                  key={`g-${group.label}`}
                  onClick={() => toggle(group.label)}
                  className={groupRowBg}
                  style={surfaceStyle}
                  onMouseEnter={e => (e.currentTarget.style.background = 'var(--color-surface-offset-2)')}
                  onMouseLeave={e => (e.currentTarget.style.background = 'var(--color-surface-offset)')}
                >
                  <td colSpan={8} className="px-4 py-2" style={{ borderBottom: '1px solid var(--color-divider)' }}>
                    <div className="flex items-center gap-2">
                      {expanded[group.label]
                        ? <ChevronDown  size={13} style={cellFaint} />
                        : <ChevronRight size={13} style={cellFaint} />}
                      <span className="font-semibold" style={cellText}>{group.label}</span>
                      <span className="ml-1 px-1.5 rounded text-[10px]"
                        style={{ background: 'var(--color-surface-dynamic)', color: 'var(--color-text-muted)' }}>
                        {group.count}
                      </span>
                    </div>
                  </td>
                </tr>
                {expanded[group.label] && (group.positions ?? []).map(item => {
                  const hasQuote  = item.current_price !== item.average_price || item.variation_value !== 0
                  const name      = displayName(item.ticker, item.asset_type)
                  const isTesouro = item.asset_type.toUpperCase() === 'TESOURO_DIRETO' || item.asset_type.toUpperCase() === 'TESOURO'
                  const varColor  = item.variation_value >= 0 ? 'var(--color-success)' : 'var(--color-error)'
                  const investedValue = item.invested_value ?? item.quantity * item.average_price

                  return (
                    <tr key={`${item.ticker}-${item.asset_type}-${item.id}`} className={rowHover}
                      style={{ borderBottom: '1px solid var(--color-divider)' }}>
                      <td className="px-4 py-2">
                        <div className="flex items-center gap-2.5">
                          <AssetLogo ticker={item.ticker} assetType={item.asset_type} size={28} />
                          <div className="min-w-0">
                            <div className="font-semibold truncate max-w-[180px]" style={cellText} title={item.ticker}>{name}</div>
                            <div className="text-[10px] truncate max-w-[180px]" style={cellFaint}>
                              {isTesouro ? item.ticker : item.asset_label}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="text-right px-4 py-2 tabular-nums" style={cellText}>
                        {item.quantity % 1 === 0
                          ? item.quantity.toLocaleString('pt-BR')
                          : item.quantity.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 8 })}
                      </td>
                      <td className="text-right px-4 py-2 tabular-nums" style={cellText}>{formatBRL(item.average_price)}</td>
                      <td className="text-right px-4 py-2 tabular-nums">
                        <span style={hasQuote ? cellText : cellFaint}>{fmtPrice(item.current_price)}</span>
                      </td>
                      <td className="text-right px-4 py-2 tabular-nums" style={cellText}>{formatBRL(investedValue)}</td>
                      <td className="text-right px-4 py-2 tabular-nums" style={cellText}>{formatBRL(item.current_value)}</td>
                      <td className="text-right px-4 py-2 tabular-nums">
                        {hasQuote ? (
                          <div className="font-medium" style={{ color: varColor }}>
                            <div>{formatBRL(item.variation_value)}</div>
                            <div className="text-[10px]">{formatPercent(item.variation_percent)}</div>
                          </div>
                        ) : <span style={cellFaint} title="Cotação indisponível">—</span>}
                      </td>
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
    </>
  )
}
