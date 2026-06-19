import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { MoreHorizontal, Plus, List, BarChart2 as AnalyseIcon } from 'lucide-react'
import { formatBRL, formatPercent } from '@/utils/format'
import { formatTreasuryName } from '@/utils/treasury'
import AssetLogo from '@/components/ui/AssetLogo'
import { useAppStore } from '@/store/appStore'
import type { PositionGroup } from '@/hooks/usePortfolio'

// ── helpers ──────────────────────────────────────────────────────────────────────────
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

// ── style tokens ──────────────────────────────────────────────────────────────────────────
const cellText  = { color: 'var(--color-text)' }
const cellMuted = { color: 'var(--color-text-muted)' }
const cellFaint = { color: 'var(--color-text-faint)' }

// ── hook de breakpoint ────────────────────────────────────────────────────────────────────────
function useIsDesktop(breakpoint = 768) {
  const [isDesktop, setIsDesktop] = useState(() => window.innerWidth >= breakpoint)
  useEffect(() => {
    const mq = window.matchMedia(`(min-width: ${breakpoint}px)`)
    const handler = (e: MediaQueryListEvent) => setIsDesktop(e.matches)
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  }, [breakpoint])
  return isDesktop
}

// ── AssetMenu ─────────────────────────────────────────────────────────────────────────────
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
    <div ref={ref} style={{ position: 'relative', display: 'inline-block' }}>
      <button
        type="button"
        onClick={(e) => { e.stopPropagation(); setOpen(v => !v) }}
        style={{
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          width: 28, height: 28, borderRadius: 'var(--radius-md)',
          border: 'none', background: 'transparent',
          color: 'var(--color-text-faint)', cursor: 'pointer', flexShrink: 0,
        }}
        onMouseEnter={e => (e.currentTarget.style.color = 'var(--color-text-muted)')}
        onMouseLeave={e => (e.currentTarget.style.color = 'var(--color-text-faint)')}
        aria-label="Opções"
      >
        <MoreHorizontal size={14} />
      </button>
      {open && (
        <div style={{
          position: 'absolute', right: 0, top: '100%', zIndex: 50, marginTop: 4,
          width: 210, borderRadius: 'var(--radius-lg)', overflow: 'hidden',
          background: 'var(--color-surface)', boxShadow: 'var(--shadow-lg)',
          border: '1px solid oklch(from var(--color-text) l c h / 0.1)',
        }}>
          {items.map((item, i) => (
            <button
              key={i} type="button" onClick={item.onClick}
              style={{
                width: '100%', display: 'flex', alignItems: 'center', gap: 8,
                padding: '8px 12px', border: 'none', background: 'transparent',
                cursor: 'pointer', textAlign: 'left',
                fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)',
                borderBottom: i < items.length - 1 ? '1px solid oklch(from var(--color-text) l c h / 0.06)' : 'none',
              }}
              onMouseEnter={e => { e.currentTarget.style.background = 'var(--color-surface-offset)'; e.currentTarget.style.color = 'var(--color-text)' }}
              onMouseLeave={e => { e.currentTarget.style.background = ''; e.currentTarget.style.color = 'var(--color-text-muted)' }}
            >
              <span style={cellFaint}>{item.icon}</span>
              <span style={{ flex: 1 }}>{item.label}</span>
              {item.badge && (
                <span style={{
                  fontSize: '0.65rem', fontWeight: 600, padding: '1px 6px',
                  borderRadius: 'var(--radius-full)',
                  background: 'oklch(from var(--color-primary) l c h / 0.12)',
                  color: 'var(--color-primary)',
                }}>{item.badge}</span>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

// ── PositionCard (mobile) ─────────────────────────────────────────────────────────────────────────
interface PositionCardProps { item: PositionGroup['positions'][number] }

function PositionCard({ item }: PositionCardProps) {
  const isTesouro = item.asset_type.toUpperCase() === 'TESOURO_DIRETO' || item.asset_type.toUpperCase() === 'TESOURO'
  const name = displayName(item.ticker, item.asset_type)
  const hasQuote = item.current_price !== null && item.current_price !== undefined
  const varColor = (item.variation_value ?? 0) >= 0 ? 'var(--color-success)' : 'var(--color-error)'
  const investedValue = item.invested_value ?? item.quantity * item.average_price

  return (
    <div style={{
      borderRadius: 'var(--radius-xl)', padding: '1rem',
      background: 'var(--color-surface-offset)',
      border: '1px solid oklch(from var(--color-text) l c h / 0.07)',
      display: 'flex', flexDirection: 'column', gap: '0.75rem',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 0 }}>
          <AssetLogo ticker={item.ticker} assetType={item.asset_type} size={34} logoUrl={item.logo_url} />
          <div style={{ minWidth: 0 }}>
            <div style={{ fontWeight: 600, fontSize: 'var(--text-sm)', ...cellText }}>{name}</div>
            <div style={{ fontSize: '0.68rem', marginTop: 2, color: 'var(--color-text-faint)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {isTesouro ? item.ticker : item.asset_label}
            </div>
          </div>
        </div>
        <AssetMenu ticker={item.ticker} assetLabel={isTesouro ? item.ticker : (item.asset_label ?? item.ticker)} assetType={item.asset_type} />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.625rem 1rem' }}>
        {[
          { label: 'Qtd',         value: fmtQty(item.quantity)        },
          { label: 'P. Médio',   value: formatBRL(item.average_price) },
          { label: 'Total Inv.',  value: formatBRL(investedValue)     },
          { label: 'Valor Atual', value: fmtPrice(item.current_price !== null && item.current_price !== undefined ? item.current_value : null) },
        ].map(({ label, value }) => (
          <div key={label}>
            <div style={{ fontSize: '0.65rem', marginBottom: 2, color: 'var(--color-text-faint)' }}>{label}</div>
            <div style={{ fontWeight: 500, fontSize: 'var(--text-xs)', ...cellText, fontVariantNumeric: 'tabular-nums' }}>{value}</div>
          </div>
        ))}
        <div style={{ gridColumn: '1 / -1' }}>
          <div style={{ fontSize: '0.65rem', marginBottom: 2, color: 'var(--color-text-faint)' }}>Resultado</div>
          {hasQuote ? (
            <div style={{ fontWeight: 600, fontSize: 'var(--text-xs)', color: varColor, fontVariantNumeric: 'tabular-nums' }}>
              {formatBRL(item.variation_value ?? 0)}
              <span style={{ marginLeft: 6, fontSize: '0.65rem', fontWeight: 500, opacity: 0.8 }}>
                ({formatPercent(item.variation_percent ?? 0)})
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

// ── ClassTable — tabela de uma classe de ativo ────────────────────────────────────────────────────────
function ClassTable({ group }: { group: PositionGroup }) {
  const isDesktop = useIsDesktop()

  const COLS = [
    { key: 'ativo',      label: 'Ativo',       align: 'left',  width: '30%' },
    { key: 'qtd',        label: 'Qtd',         align: 'right', width: '8%'  },
    { key: 'pm',         label: 'P. Médio',   align: 'right', width: '11%' },
    { key: 'pa',         label: 'P. Atual',    align: 'right', width: '11%', info: 'Cotação via BRAPI/yfinance' },
    { key: 'inv',        label: 'Total Inv.',  align: 'right', width: '13%' },
    { key: 'atual',      label: 'Valor Atual', align: 'right', width: '13%' },
    { key: 'resultado',  label: 'Resultado',   align: 'right', width: '11%' },
    { key: 'acoes',      label: '',            align: 'right', width: '3%'  },
  ]

  return (
    <div className="card" style={{ overflow: 'hidden' }}>
      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8,
        padding: '0.75rem 1.25rem',
        borderBottom: '1px solid oklch(from var(--color-text) l c h / 0.06)',
      }}>
        <span style={{
          fontSize: 'var(--text-sm)', fontWeight: 600,
          letterSpacing: '-0.005em', color: 'var(--color-text)',
        }}>
          {group.label}
        </span>
        <span style={{
          fontSize: 'var(--text-xs)', fontWeight: 500,
          color: 'var(--color-text-muted)',
          background: 'var(--color-surface-offset)',
          border: '1px solid oklch(from var(--color-text) l c h / 0.07)',
          borderRadius: 'var(--radius-full)', padding: '1px 8px',
        }}>
          {group.count}
        </span>
      </div>

      {/* Mobile: cards */}
      {!isDesktop && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', padding: '1rem' }}>
          {group.positions.map(item => (
            <PositionCard key={`${item.ticker}-${item.id ?? item.ticker}`} item={item} />
          ))}
        </div>
      )}

      {/* Desktop: tabela */}
      {isDesktop && (
        <table style={{ width: '100%', borderCollapse: 'collapse', tableLayout: 'fixed', fontSize: 'var(--text-xs)' }}>
          <colgroup>
            {COLS.map(c => <col key={c.key} style={{ width: c.width }} />)}
          </colgroup>
          <thead>
            <tr style={{ borderBottom: '1px solid oklch(from var(--color-text) l c h / 0.06)' }}>
              {COLS.map(col => (
                <th
                  key={col.key}
                  style={{
                    padding: '0.5rem 1rem',
                    textAlign: col.align as any,
                    fontWeight: 500,
                    fontSize: '0.68rem',
                    letterSpacing: '0.04em',
                    textTransform: 'uppercase',
                    color: 'var(--color-text-muted)',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {col.info ? (
                    <span style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'flex-end', gap: 3 }}>
                      {col.label}
                      <span title={col.info} style={{ cursor: 'help', display: 'inline-flex', alignItems: 'center' }}>
                        <svg xmlns="http://www.w3.org/2000/svg" width="9" height="9" viewBox="0 0 24 24"
                          fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
                          style={cellFaint}>
                          <circle cx="12" cy="12" r="10" />
                          <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
                          <path d="M12 17h.01" />
                        </svg>
                      </span>
                    </span>
                  ) : col.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {group.positions.map(item => {
              const hasQuote      = item.current_price !== null && item.current_price !== undefined
              const name          = displayName(item.ticker, item.asset_type)
              const isTesouro     = item.asset_type.toUpperCase() === 'TESOURO_DIRETO' || item.asset_type.toUpperCase() === 'TESOURO'
              const varColor      = (item.variation_value ?? 0) >= 0 ? 'var(--color-success)' : 'var(--color-notification)'
              const investedValue = item.invested_value ?? item.quantity * item.average_price

              return (
                <tr
                  key={`${item.ticker}-${item.id ?? item.ticker}`}
                  style={{ borderBottom: '1px solid oklch(from var(--color-text) l c h / 0.045)' }}
                  onMouseEnter={e => (e.currentTarget.style.background = 'oklch(from var(--color-primary) l c h / 0.03)')}
                  onMouseLeave={e => (e.currentTarget.style.background = '')}
                >
                  {/* Ativo */}
                  <td style={{ padding: '0.75rem 1rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <AssetLogo ticker={item.ticker} assetType={item.asset_type} size={28} logoUrl={item.logo_url} />
                      <div style={{ minWidth: 0 }}>
                        <div style={{ fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', ...cellText }}>{name}</div>
                        <div style={{ fontSize: '0.65rem', marginTop: 2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', ...cellFaint }}>
                          {isTesouro ? item.ticker : item.asset_label}
                        </div>
                      </div>
                    </div>
                  </td>
                  {/* Qtd */}
                  <td style={{ padding: '0.75rem 1rem', textAlign: 'right', fontVariantNumeric: 'tabular-nums', whiteSpace: 'nowrap', ...cellText }}>
                    {fmtQty(item.quantity)}
                  </td>
                  {/* P. Médio */}
                  <td style={{ padding: '0.75rem 1rem', textAlign: 'right', fontVariantNumeric: 'tabular-nums', whiteSpace: 'nowrap', ...cellText }}>
                    {formatBRL(item.average_price)}
                  </td>
                  {/* P. Atual */}
                  <td style={{ padding: '0.75rem 1rem', textAlign: 'right', fontVariantNumeric: 'tabular-nums', whiteSpace: 'nowrap' }}>
                    <span style={hasQuote ? cellText : cellFaint}>{fmtPrice(item.current_price)}</span>
                  </td>
                  {/* Total Inv. */}
                  <td style={{ padding: '0.75rem 1rem', textAlign: 'right', fontVariantNumeric: 'tabular-nums', whiteSpace: 'nowrap', ...cellText }}>
                    {formatBRL(investedValue)}
                  </td>
                  {/* Valor Atual */}
                  <td style={{ padding: '0.75rem 1rem', textAlign: 'right', fontVariantNumeric: 'tabular-nums', whiteSpace: 'nowrap', ...cellText }}>
                    {hasQuote ? formatBRL(item.current_value) : <span style={cellFaint}>—</span>}
                  </td>
                  {/* Resultado */}
                  <td style={{ padding: '0.75rem 1rem', textAlign: 'right', fontVariantNumeric: 'tabular-nums', whiteSpace: 'nowrap' }}>
                    {hasQuote ? (
                      <div style={{ color: varColor }}>
                        <div style={{ fontWeight: 600 }}>{formatBRL(item.variation_value ?? 0)}</div>
                        <div style={{ fontSize: '0.65rem', fontWeight: 500, opacity: 0.8 }}>{formatPercent(item.variation_percent ?? 0)}</div>
                      </div>
                    ) : (
                      <span style={cellFaint}>—</span>
                    )}
                  </td>
                  {/* Ações */}
                  <td style={{ padding: '0.5rem 0.75rem', textAlign: 'right' }}>
                    <AssetMenu
                      ticker={item.ticker}
                      assetLabel={isTesouro ? item.ticker : (item.asset_label ?? item.ticker)}
                      assetType={item.asset_type}
                    />
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      )}
    </div>
  )
}

// ── PositionTable — exibe uma ClassTable por grupo ────────────────────────────────────────────────
interface Props { groups: PositionGroup[] }

export default function PositionTable({ groups }: Props) {
  if (!groups || groups.length === 0) return null
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      {groups.map(group => (
        <ClassTable key={group.label} group={group} />
      ))}
    </div>
  )
}
