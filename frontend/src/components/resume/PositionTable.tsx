import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ChevronDown, ChevronRight,
  MoreHorizontal, Plus, List, BarChart2 as AnalyseIcon,
} from 'lucide-react'
import { formatBRL, formatPercent } from '@/utils/format'
import { formatTreasuryName } from '@/utils/treasury'
import AssetLogo from '@/components/ui/AssetLogo'
import { useAppStore } from '@/store/appStore'
import type { PositionGroup } from '@/hooks/usePortfolio'

// ─── helpers ────────────────────────────────────────────────────────────────
function assetTypeToTab(assetType: string): string {
  const map: Record<string, string> = {
    ACAO: 'acao', FII: 'fii', ETF_NACIONAL: 'etf_br',
    STOCK: 'stock', ETF_INTERNACIONAL: 'etf_int',
    TESOURO_DIRETO: 'tesouro', TESOURO: 'tesouro',
    RENDA_FIXA: 'renda_fixa', CRIPTO: 'cripto',
  }
  return map[assetType.toUpperCase()] ?? 'acao'
}

function fmtQty(v: number) {
  return v % 1 === 0
    ? v.toLocaleString('pt-BR')
    : v.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 8 })
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

// ─── style tokens ────────────────────────────────────────────────────────────
const cellText  = { color: 'var(--color-text)' }
const cellMuted = { color: 'var(--color-text-muted)' }
const cellFaint = { color: 'var(--color-text-faint)' }

// ─── AssetMenu ───────────────────────────────────────────────────────────────
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
        <div
          className="absolute right-0 top-full z-50 mt-1 w-52 rounded-lg overflow-hidden"
          style={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)', boxShadow: 'var(--shadow-lg)' }}
        >
          {items.map((item, i) => (
            <button
              key={i} type="button" onClick={item.onClick}
              className="w-full flex items-center gap-2.5 px-3 py-2.5 text-xs transition-colors"
              style={cellMuted}
              onMouseEnter={e => { e.currentTarget.style.background = 'var(--color-surface-offset)'; e.currentTarget.style.color = 'var(--color-text)' }}
              onMouseLeave={e => { e.currentTarget.style.background = ''; e.currentTarget.style.color = 'var(--color-text-muted)' }}
            >
              <span style={cellFaint}>{item.icon}</span>
              <span className="flex-1 text-left">{item.label}</span>
              {item.badge && (
                <span
                  className="text-[9px] font-semibold px-1.5 py-0.5 rounded-full"
                  style={{ background: 'var(--color-primary-highlight)', color: 'var(--color-primary)' }}
                >
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

// ─── PositionCard (mobile) ────────────────────────────────────────────────────
interface PositionCardProps { item: PositionGroup['positions'][number] }

function PositionCard({ item }: PositionCardProps) {
  const isTesouro = item.asset_type.toUpperCase() === 'TESOURO_DIRETO' || item.asset_type.toUpperCase() === 'TESOURO'
  const name = displayName(item.ticker, item.asset_type)
  const hasQuote = item.variation_value !== 0 || item.current_price !== item.average_price
  const varColor = item.variation_value >= 0 ? 'var(--color-success)' : 'var(--color-error)'
  const investedValue = item.invested_value ?? item.quantity * item.average_price

  return (
    <div
      className="rounded-xl p-4 flex flex-col gap-3"
      style={{ background: 'var(--color-surface-offset)', border: '1px solid var(--color-divider)' }}
    >
      {/* Header */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2.5 min-w-0">
          <AssetLogo ticker={item.ticker} assetType={item.asset_type} size={34} />
          <div className="min-w-0">
            <div className="font-semibold text-sm leading-tight" style={cellText}>{name}</div>
            <div className="text-[11px] mt-0.5 truncate" style={cellFaint}>
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

      {/* Grid de métricas */}
      <div className="grid grid-cols-2 gap-x-4 gap-y-2.5 text-xs">
        {[
          { label: 'Qtd',           value: fmtQty(item.quantity) },
          { label: 'P. Médio',      value: formatBRL(item.average_price) },
          { label: 'Total Inv.',    value: formatBRL(investedValue) },
          { label: 'Valor Atual',   value: formatBRL(item.current_value) },
        ].map(({ label, value }) => (
          <div key={label}>
            <div className="text-[10px] mb-0.5" style={cellFaint}>{label}</div>
            <div className="font-medium tabular-nums" style={cellText}>{value}</div>
          </div>
        ))}

        {/* Resultado — ocupa linha inteira */}
        <div className="col-span-2">
          <div className="text-[10px] mb-0.5" style={cellFaint}>Resultado</div>
          {hasQuote ? (
            <div className="font-semibold tabular-nums" style={{ color: varColor }}>
              {formatBRL(item.variation_value)}
              <span className="ml-1.5 text-[10px] font-medium opacity-80">
                ({formatPercent(item.variation_percent)})
              </span>
            </div>
          ) : (
            <span style={cellFaint}>—</span>
          )}
        </div>
      </div>
    </div>
  )
}

// ─── PositionTable (desktop) ─────────────────────────────────────────────────
interface Props { groups: PositionGroup[] }

export default function PositionTable({ groups }: Props) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>(
    Object.fromEntries((groups ?? []).map(g => [g.label, true]))
  )
  const toggle = (label: string) => setExpanded(prev => ({ ...prev, [label]: !prev[label] }))

  if (!groups || groups.length === 0) return null

  return (
    <>
      {/* ── Mobile: cards empilhados ── */}
      <div className="flex flex-col gap-4 p-4 md:hidden">
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
              <span
                className="ml-1 px-1.5 py-0.5 rounded text-[10px]"
                style={{ background: 'var(--color-surface-dynamic)', color: 'var(--color-text-muted)' }}
              >
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

      {/* ── Desktop: tabela ── */}
      <div className="hidden md:block">
        <table className="w-full text-xs border-collapse" style={{ tableLayout: 'fixed' }}>
          <colgroup>
            {/* Ativo: espaço generoso, absorve overflow do layout */}
            <col style={{ width: '30%' }} />
            {/* Qtd */}
            <col style={{ width: '8%' }} />
            {/* P. Médio */}
            <col style={{ width: '11%' }} />
            {/* P. Atual */}
            <col style={{ width: '11%' }} />
            {/* Total Inv. */}
            <col style={{ width: '13%' }} />
            {/* Valor Atual */}
            <col style={{ width: '13%' }} />
            {/* Resultado */}
            <col style={{ width: '11%' }} />
            {/* Ações */}
            <col style={{ width: '3%' }} />
          </colgroup>

          <thead>
            <tr style={{ borderBottom: '1px solid var(--color-divider)' }}>
              {[
                { label: 'Ativo',       align: 'left'  },
                { label: 'Qtd',         align: 'right' },
                { label: 'P. Médio',    align: 'right' },
                { label: 'P. Atual',    align: 'right', tooltip: true },
                { label: 'Total Inv.',  align: 'right' },
                { label: 'Valor Atual', align: 'right' },
                { label: 'Resultado',   align: 'right' },
                { label: '',            align: 'right' },
              ].map(({ label, align, tooltip }) => (
                <th
                  key={label}
                  className={`px-4 py-3 font-medium whitespace-nowrap text-${align}`}
                  style={cellMuted}
                >
                  {tooltip ? (
                    <span className="inline-flex items-center justify-end gap-1">
                      {label}
                      <span
                        aria-label="Cotação via BRAPI/yfinance."
                        title="Cotação via BRAPI/yfinance."
                        style={{ display: 'inline-flex', alignItems: 'center', cursor: 'help' }}
                      >
                        <svg
                          xmlns="http://www.w3.org/2000/svg"
                          width="10" height="10" viewBox="0 0 24 24"
                          fill="none" stroke="currentColor" strokeWidth="2"
                          strokeLinecap="round" strokeLinejoin="round"
                          style={cellFaint}
                        >
                          <circle cx="12" cy="12" r="10" />
                          <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
                          <path d="M12 17h.01" />
                        </svg>
                      </span>
                    </span>
                  ) : label}
                </th>
              ))}
            </tr>
          </thead>

          <tbody>
            {groups.map(group => (
              <>
                {/* Linha de grupo */}
                <tr
                  key={`g-${group.label}`}
                  onClick={() => toggle(group.label)}
                  className="cursor-pointer transition-colors"
                  style={{ background: 'var(--color-surface-offset)', borderBottom: '1px solid var(--color-divider)' }}
                  onMouseEnter={e => (e.currentTarget.style.background = 'var(--color-surface-offset-2)')}
                  onMouseLeave={e => (e.currentTarget.style.background = 'var(--color-surface-offset)')}
                >
                  <td colSpan={8} className="px-4 py-2.5">
                    <div className="flex items-center gap-2">
                      {expanded[group.label]
                        ? <ChevronDown  size={13} style={cellFaint} />
                        : <ChevronRight size={13} style={cellFaint} />}
                      <span className="font-semibold text-xs" style={cellText}>{group.label}</span>
                      <span
                        className="px-1.5 py-0.5 rounded text-[10px]"
                        style={{ background: 'var(--color-surface-dynamic)', color: 'var(--color-text-muted)' }}
                      >
                        {group.count}
                      </span>
                    </div>
                  </td>
                </tr>

                {/* Linhas de posição */}
                {expanded[group.label] && (group.positions ?? []).map(item => {
                  const hasQuote     = item.current_price !== item.average_price || item.variation_value !== 0
                  const name         = displayName(item.ticker, item.asset_type)
                  const isTesouro    = item.asset_type.toUpperCase() === 'TESOURO_DIRETO' || item.asset_type.toUpperCase() === 'TESOURO'
                  const varColor     = item.variation_value >= 0 ? 'var(--color-success)' : 'var(--color-error)'
                  const investedValue = item.invested_value ?? item.quantity * item.average_price

                  return (
                    <tr
                      key={`${item.ticker}-${item.asset_type}-${item.id}`}
                      className="transition-colors"
                      style={{ borderBottom: '1px solid var(--color-divider)' }}
                      onMouseEnter={e => (e.currentTarget.style.background = 'var(--color-surface-offset)')}
                      onMouseLeave={e => (e.currentTarget.style.background = '')}
                    >
                      {/* Ativo */}
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2.5">
                          <AssetLogo ticker={item.ticker} assetType={item.asset_type} size={28} />
                          <div className="min-w-0">
                            <div className="font-semibold leading-tight truncate" style={cellText}>{name}</div>
                            <div className="text-[10px] mt-0.5 truncate" style={cellFaint}>
                              {isTesouro ? item.ticker : item.asset_label}
                            </div>
                          </div>
                        </div>
                      </td>

                      {/* Qtd */}
                      <td className="text-right px-4 py-3 tabular-nums whitespace-nowrap" style={cellText}>
                        {fmtQty(item.quantity)}
                      </td>

                      {/* P. Médio */}
                      <td className="text-right px-4 py-3 tabular-nums whitespace-nowrap" style={cellText}>
                        {formatBRL(item.average_price)}
                      </td>

                      {/* P. Atual */}
                      <td className="text-right px-4 py-3 tabular-nums whitespace-nowrap">
                        <span style={hasQuote ? cellText : cellFaint}>{fmtPrice(item.current_price)}</span>
                      </td>

                      {/* Total Inv. */}
                      <td className="text-right px-4 py-3 tabular-nums whitespace-nowrap" style={cellText}>
                        {formatBRL(investedValue)}
                      </td>

                      {/* Valor Atual */}
                      <td className="text-right px-4 py-3 tabular-nums whitespace-nowrap" style={cellText}>
                        {formatBRL(item.current_value)}
                      </td>

                      {/* Resultado — valor + % na mesma célula */}
                      <td className="text-right px-4 py-3 tabular-nums whitespace-nowrap">
                        {hasQuote ? (
                          <div style={{ color: varColor }}>
                            <div className="font-semibold leading-tight">{formatBRL(item.variation_value)}</div>
                            <div className="text-[10px] font-medium opacity-80">{formatPercent(item.variation_percent)}</div>
                          </div>
                        ) : (
                          <span style={cellFaint} aria-label="Cotação indisponível">—</span>
                        )}
                      </td>

                      {/* Ações */}
                      <td className="px-2 py-3 text-right">
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
