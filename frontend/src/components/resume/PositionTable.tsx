import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { useLocation, useNavigate } from 'react-router-dom'
import { MoreHorizontal, Plus, List, ChevronDown, Target, Clock } from 'lucide-react'
import { formatBRL, formatPercent, fmtMoney } from '@/utils/format'
import { formatTreasuryName } from '@/utils/treasury'
import AssetLogo from '@/components/ui/AssetLogo'
import AssetDetailDrawer from '@/components/portfolio/AssetDetailDrawer'
import { useAppStore } from '@/store/appStore'
import { useUpsertClassTarget } from '@/hooks/useClassTargets'
import type { PositionGroup } from '@/hooks/usePortfolio'

function safeNum(v: unknown): number {
  const n = Number(v)
  return Number.isFinite(n) ? n : 0
}

const USD_TYPES = new Set(['STOCK', 'ETF_INTERNACIONAL'])

function isUsdAsset(assetType: string | null | undefined): boolean {
  return !!assetType && USD_TYPES.has(assetType.toUpperCase())
}

function isRendaFixa(assetType: string | null | undefined): boolean {
  return !!assetType && assetType.toUpperCase() === 'RENDA_FIXA'
}

function assetTypeToTab(assetType: string | null | undefined): string {
  if (!assetType) return 'acao'
  const map: Record<string, string> = {
    ACAO: 'acao', FII: 'fii', ETF_NACIONAL: 'etf_br', BDR: 'bdr',
    STOCK: 'stock', ETF_INTERNACIONAL: 'etf_int',
    TESOURO_DIRETO: 'tesouro', TESOURO: 'tesouro',
    RENDA_FIXA: 'renda_fixa', CRIPTO: 'cripto',
  }
  return map[assetType.toUpperCase()] ?? 'acao'
}

function fmtQty(v: unknown) {
  const n = safeNum(v)
  return n % 1 === 0
    ? n.toLocaleString('pt-BR')
    : n.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 8 })
}

function displayName(ticker: string, assetType: string | null | undefined): string {
  if (!assetType) return ticker
  const norm = assetType.toUpperCase()
  if (norm === 'TESOURO_DIRETO' || norm === 'TESOURO') return formatTreasuryName(ticker)
  return ticker
}

export function investedValueOf(p: PositionGroup['positions'][number]): number {
  return p.invested_value
}

function getGroupQuoteTimestamp(group: PositionGroup): string | null {
  const timestamps: number[] = []
  for (const p of group.positions) {
    const ts = (p as any).quote_updated_at
    if (!ts) continue
    const ms = typeof ts === 'number' ? ts * 1000 : Date.parse(ts)
    if (!isNaN(ms)) timestamps.push(ms)
  }
  if (timestamps.length === 0) return null

  const d = new Date(Math.max(...timestamps))
  const now = new Date()
  const diffMs = now.getTime() - d.getTime()
  const diffMin = Math.floor(diffMs / 60_000)
  const diffH = Math.floor(diffMs / 3_600_000)

  if (d.toDateString() === now.toDateString()) {
    if (diffMin < 1) return 'agora mesmo'
    if (diffMin < 60) return `há ${diffMin} min`
    if (diffH < 24) return `há ${diffH}h`
  }

  const yesterday = new Date(now)
  yesterday.setDate(now.getDate() - 1)
  if (d.toDateString() === yesterday.toDateString()) return 'ontem'

  return d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: '2-digit' })
}

const cellText = { color: 'var(--color-text)' }
const cellFaint = { color: 'var(--color-text-faint)' }

function MissingQuoteValue() {
  return (
    <span
      title="Cotação atual indisponível; nenhum resultado foi calculado"
      style={{ color: 'var(--color-text-faint)', fontSize: '0.68rem', whiteSpace: 'nowrap' }}
    >
      Sem cotação
    </span>
  )
}

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

interface AssetMenuProps { ticker: string; assetLabel: string; assetType: string }

interface MenuCoords {
  top: number
  left: number
  maxHeight: number
}

interface AssetMenuItem {
  icon: React.ReactNode
  label: string
  onClick: () => void
  badge?: string
}

function AssetMenu({ ticker, assetLabel, assetType }: AssetMenuProps) {
  const [open, setOpen] = useState(false)
  const [coords, setCoords] = useState<MenuCoords | null>(null)
  const buttonRef = useRef<HTMLButtonElement>(null)
  const menuRef = useRef<HTMLDivElement>(null)
  const navigate = useNavigate()
  const location = useLocation()
  const openTransactionModal = useAppStore(s => s.openTransactionModal)

  const updateCoords = () => {
    const rect = buttonRef.current?.getBoundingClientRect()
    if (!rect) return
    const menuWidth = 210
    const estimatedMenuHeight = 116
    const margin = 8
    const left = Math.min(
      Math.max(margin, rect.right - menuWidth),
      window.innerWidth - menuWidth - margin,
    )
    const spaceBelow = window.innerHeight - rect.bottom - margin
    const spaceAbove = rect.top - margin
    const opensUp = spaceBelow < estimatedMenuHeight && spaceAbove > spaceBelow
    const availableHeight = Math.max(
      96,
      opensUp ? spaceAbove - 4 : spaceBelow - 4,
    )
    const menuHeight = Math.min(estimatedMenuHeight, availableHeight)
    const rawTop = opensUp ? rect.top - menuHeight - 4 : rect.bottom + 4
    const top = Math.min(
      Math.max(margin, rawTop),
      window.innerHeight - menuHeight - margin,
    )
    setCoords({ top, left, maxHeight: availableHeight })
  }

  useLayoutEffect(() => {
    if (open) updateCoords()
  }, [open])

  useEffect(() => {
    if (!open) return

    function handleMouseDown(e: MouseEvent) {
      const target = e.target as Node
      if (buttonRef.current?.contains(target) || menuRef.current?.contains(target)) return
      setOpen(false)
    }

    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') setOpen(false)
    }

    function handleReposition() {
      updateCoords()
    }

    document.addEventListener('mousedown', handleMouseDown)
    document.addEventListener('keydown', handleKeyDown)
    window.addEventListener('resize', handleReposition)
    window.addEventListener('scroll', handleReposition, true)

    return () => {
      document.removeEventListener('mousedown', handleMouseDown)
      document.removeEventListener('keydown', handleKeyDown)
      window.removeEventListener('resize', handleReposition)
      window.removeEventListener('scroll', handleReposition, true)
    }
  }, [open])

  useEffect(() => {
    setOpen(false)
  }, [location.pathname, location.search])

  const items: AssetMenuItem[] = [
    {
      icon: <Plus size={13} />,
      label: 'Adicionar Lançamento',
      onClick: () => {
        setOpen(false)
        openTransactionModal({ tab: assetTypeToTab(assetType), ticker, assetName: assetLabel })
      },
    },
    {
      icon: <List size={13} />,
      label: 'Ver Lançamentos',
      onClick: () => {
        setOpen(false)
        navigate(`/carteira/transacoes?ticker=${encodeURIComponent(ticker)}`)
      },
    },
  ]

  return (
    <>
      <button
        ref={buttonRef}
        type="button"
        onClick={(e) => { e.stopPropagation(); setOpen(v => !v) }}
        style={{
          display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
          width: 28, height: 28, borderRadius: 'var(--radius-md)',
          border: 'none', background: 'transparent',
          color: 'var(--color-text-faint)', cursor: 'pointer', flexShrink: 0,
        }}
        onMouseEnter={e => (e.currentTarget.style.color = 'var(--color-text-muted)')}
        onMouseLeave={e => (e.currentTarget.style.color = 'var(--color-text-faint)')}
        aria-label="Opções"
        aria-haspopup="menu"
        aria-expanded={open}
      >
        <MoreHorizontal size={14} />
      </button>

      {open && coords && createPortal(
        <div
          ref={menuRef}
          style={{
            position: 'fixed',
            top: coords.top,
            left: coords.left,
            zIndex: 120,
            width: 210,
            maxHeight: coords.maxHeight,
            borderRadius: 'var(--radius-lg)',
            overflowY: 'auto',
            overflowX: 'hidden',
            background: 'var(--color-surface)',
            boxShadow: 'var(--shadow-lg)',
            border: '1px solid oklch(from var(--color-text) l c h / 0.1)',
          }}
          onClick={e => e.stopPropagation()}
          role="menu"
        >
          {items.map((item, i) => (
            <button
              key={item.label}
              type="button"
              onClick={item.onClick}
              role="menuitem"
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
        </div>,
        document.body,
      )}
    </>
  )
}

interface PositionCardProps {
  item: PositionGroup['positions'][number]
  onAssetClick?: (asset: PositionGroup['positions'][number]) => void
}

function PositionCard({ item, onAssetClick }: PositionCardProps) {
  const safeType = item.asset_type ?? ''
  const isTesouro = safeType.toUpperCase() === 'TESOURO_DIRETO' || safeType.toUpperCase() === 'TESOURO'
  const isRF = isRendaFixa(safeType)
  const name = displayName(item.ticker, safeType)
  const hasQuote = item.current_price !== null && item.current_price !== undefined
  const result = safeNum(item.variation_value)
  const varColor = result >= 0 ? 'var(--color-success)' : 'var(--color-error)'
  const investedValue = investedValueOf(item)
  const currency = isUsdAsset(safeType) ? 'USD' : 'BRL'

  const fields = isRF
    ? [
        { label: 'Custo Atual', value: fmtMoney(investedValue, 'BRL') },
        { label: 'Valor Atual', value: hasQuote ? fmtMoney(safeNum(item.current_value), 'BRL') : <MissingQuoteValue /> },
      ]
    : [
        { label: 'Qtd', value: fmtQty(item.quantity) },
        { label: 'P. Médio', value: fmtMoney(safeNum(item.average_price), currency) },
        { label: 'Custo Atual', value: fmtMoney(investedValue, 'BRL') },
        { label: 'Valor Atual', value: hasQuote ? fmtMoney(safeNum(item.current_value), 'BRL') : <MissingQuoteValue /> },
      ]

  return (
    <button
      type="button"
      onClick={() => onAssetClick?.(item)}
      style={{
        borderRadius: 'var(--radius-xl)', padding: '1rem',
        background: 'var(--color-surface-offset)',
        border: '1px solid oklch(from var(--color-text) l c h / 0.07)',
        display: 'flex', flexDirection: 'column', gap: '0.75rem',
        cursor: 'pointer', transition: 'all 0.2s', textAlign: 'left',
      }}
      onMouseEnter={e => (e.currentTarget.style.borderColor = 'var(--color-primary)')}
      onMouseLeave={e => (e.currentTarget.style.borderColor = 'oklch(from var(--color-text) l c h / 0.07)')}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, minWidth: 0 }}>
          <AssetLogo ticker={item.ticker} assetType={safeType} size={34} logoUrl={item.logo_url} />
          <div style={{ minWidth: 0 }}>
            <div style={{ fontWeight: 600, fontSize: 'var(--text-sm)', ...cellText }}>{name}</div>
            <div style={{ fontSize: '0.68rem', marginTop: 2, color: 'var(--color-text-faint)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {isTesouro ? item.ticker : item.asset_label}
            </div>
          </div>
        </div>
        <AssetMenu ticker={item.ticker} assetLabel={isTesouro ? item.ticker : (item.asset_label ?? item.ticker)} assetType={safeType} />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.625rem 1rem' }}>
        {fields.map(({ label, value }) => (
          <div key={label}>
            <div style={{ fontSize: '0.65rem', marginBottom: 2, color: 'var(--color-text-faint)' }}>{label}</div>
            <div style={{ fontWeight: 500, fontSize: 'var(--text-xs)', ...cellText, fontVariantNumeric: 'tabular-nums' }}>{value}</div>
          </div>
        ))}
        <div style={{ gridColumn: '1 / -1' }}>
          <div style={{ fontSize: '0.65rem', marginBottom: 2, color: 'var(--color-text-faint)' }}>Resultado de Capital</div>
          {hasQuote ? (
            <div style={{ fontWeight: 600, fontSize: 'var(--text-xs)', color: varColor, fontVariantNumeric: 'tabular-nums' }}>
              {fmtMoney(result, 'BRL')}
              <span style={{ marginLeft: 6, fontSize: '0.65rem', fontWeight: 500, opacity: 0.8 }}>
                ({formatPercent(safeNum(item.variation_percent))})
              </span>
            </div>
          ) : <MissingQuoteValue />}
        </div>
      </div>
    </button>
  )
}

interface TargetModalProps {
  assetType: string
  label: string
  currentTarget: number | null
  portfolioId: number
  onClose: () => void
}

function TargetModal({ assetType, label, currentTarget, portfolioId, onClose }: TargetModalProps) {
  const [value, setValue] = useState(String(currentTarget ?? ''))
  const { mutate, isPending } = useUpsertClassTarget(portfolioId)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handler(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose()
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [onClose])

  const handleSave = () => {
    const num = parseFloat(value.replace(',', '.'))
    if (isNaN(num) || num < 0 || num > 100) return
    mutate({ asset_type: assetType, target_pct: num }, { onSuccess: onClose })
  }

  return (
    <div
      ref={ref}
      onClick={e => e.stopPropagation()}
      style={{
        position: 'absolute', top: 'calc(100% + 6px)', right: 0, zIndex: 60,
        width: 220, borderRadius: 'var(--radius-lg)',
        background: 'var(--color-surface)', boxShadow: 'var(--shadow-lg)',
        border: '1px solid oklch(from var(--color-text) l c h / 0.1)',
        padding: '14px 16px',
      }}
    >
      <div style={{ fontSize: 'var(--text-xs)', fontWeight: 600, marginBottom: 10, ...cellText }}>
        Meta de alocação — {label}
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <input
          autoFocus
          type="number"
          min={0} max={100} step={0.5}
          value={value}
          onChange={e => setValue(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter') handleSave(); if (e.key === 'Escape') onClose() }}
          placeholder="ex: 30"
          style={{
            flex: 1, padding: '6px 10px', borderRadius: 'var(--radius-md)',
            border: '1px solid oklch(from var(--color-text) l c h / 0.15)',
            background: 'var(--color-surface-offset)', color: 'var(--color-text)',
            fontSize: 'var(--text-sm)', outline: 'none',
          }}
        />
        <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', flexShrink: 0 }}>%</span>
      </div>
      <div style={{ display: 'flex', gap: 6, marginTop: 10 }}>
        <button
          type="button"
          onClick={onClose}
          style={{
            flex: 1, padding: '5px 0', borderRadius: 'var(--radius-md)',
            border: '1px solid oklch(from var(--color-text) l c h / 0.12)',
            background: 'transparent', color: 'var(--color-text-muted)',
            fontSize: 'var(--text-xs)', cursor: 'pointer',
          }}
        >
          Cancelar
        </button>
        <button
          type="button"
          onClick={handleSave}
          disabled={isPending}
          style={{
            flex: 1, padding: '5px 0', borderRadius: 'var(--radius-md)',
            border: 'none', background: 'var(--color-primary)', color: '#fff',
            fontSize: 'var(--text-xs)', cursor: 'pointer', opacity: isPending ? 0.7 : 1,
          }}
        >
          {isPending ? 'Salvando…' : 'Salvar'}
        </button>
      </div>
    </div>
  )
}

interface ClassGroupHeaderProps {
  group: PositionGroup
  collapsed: boolean
  onToggle: () => void
  portfolioId: number
}

function ClassGroupHeader({ group, collapsed, onToggle, portfolioId }: ClassGroupHeaderProps) {
  const variationPct = typeof group.daily_variation_pct === 'number' ? group.daily_variation_pct : null
  const target = group.target_pct ?? null
  const assetType = group.positions[0]?.asset_type ?? ''
  const [showTargetModal, setShowTargetModal] = useState(false)

  const varColor = variationPct === null ? 'var(--color-text-faint)' : variationPct >= 0 ? 'var(--color-success)' : 'var(--color-error)'

  const Divider = () => <span style={{ width: 1, height: 12, background: 'oklch(from var(--color-text) l c h / 0.1)', flexShrink: 0 }} />
  const LabeledValue = ({ label, children }: { label: string; children: React.ReactNode }) => (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 3, whiteSpace: 'nowrap', flexShrink: 0 }}>
      <span style={{ fontSize: '0.65rem', color: 'var(--color-text-faint)' }}>{label}</span>
      {children}
    </span>
  )

  return (
    <div style={{ position: 'relative' }}>
      <button
        type="button"
        onClick={onToggle}
        style={{
          width: '100%', display: 'flex', alignItems: 'center', gap: 8,
          padding: '0.75rem 1.25rem',
          borderBottom: collapsed ? 'none' : '1px solid oklch(from var(--color-text) l c h / 0.06)',
          background: 'transparent', border: 'none', cursor: 'pointer', textAlign: 'left',
          transition: 'background 0.15s',
        }}
        onMouseEnter={e => (e.currentTarget.style.background = 'oklch(from var(--color-primary) l c h / 0.03)')}
        onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
      >
        <span style={{
          display: 'flex', alignItems: 'center', flexShrink: 0,
          color: 'var(--color-text-faint)',
          transform: collapsed ? 'rotate(-90deg)' : 'rotate(0deg)',
          transition: 'transform 0.2s',
        }}>
          <ChevronDown size={14} />
        </span>
        <span style={{ fontSize: 'var(--text-sm)', fontWeight: 600, letterSpacing: '-0.005em', ...cellText, flexShrink: 0 }}>
          {group.label}
        </span>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, flex: 1, overflow: 'hidden', minWidth: 0, flexWrap: 'nowrap' }}>
          <Divider />
          <span style={{
            fontSize: 'var(--text-xs)', fontWeight: 500,
            color: 'var(--color-text-muted)', background: 'var(--color-surface-offset)',
            border: '1px solid oklch(from var(--color-text) l c h / 0.07)',
            borderRadius: 'var(--radius-full)', padding: '1px 8px',
            whiteSpace: 'nowrap', flexShrink: 0,
          }}>
            {group.count} {group.count === 1 ? 'ativo' : 'ativos'}
          </span>
          <Divider />
          <LabeledValue label="Custo">
            <span style={{ fontSize: 'var(--text-xs)', fontWeight: 600, ...cellText, fontVariantNumeric: 'tabular-nums' }}>
              {formatBRL(safeNum(group.total_invested))}
            </span>
          </LabeledValue>
          <Divider />
          <LabeledValue label="Valor atual">
            <span style={{ fontSize: 'var(--text-xs)', fontWeight: 600, ...cellText, fontVariantNumeric: 'tabular-nums' }}>
              {formatBRL(safeNum(group.total_value))}
            </span>
          </LabeledValue>
          <Divider />
          <LabeledValue label="Variação diária">
            <span
              title={group.variation_reference_date ? `Referência: ${group.variation_reference_date}` : 'Sem referência histórica'}
              style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: varColor, fontVariantNumeric: 'tabular-nums' }}
            >
              {variationPct !== null ? `${variationPct >= 0 ? '+' : ''}${formatPercent(variationPct)}` : '—'}
            </span>
          </LabeledValue>
          <Divider />
          <span
            role="button"
            tabIndex={0}
            title="Definir meta de alocação"
            onClick={e => { e.stopPropagation(); setShowTargetModal(v => !v) }}
            onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.stopPropagation(); setShowTargetModal(v => !v) } }}
            style={{
              display: 'inline-flex', alignItems: 'center', gap: 4,
              fontSize: '0.68rem', fontWeight: 500,
              color: target !== null ? 'var(--color-primary)' : 'var(--color-text-faint)',
              whiteSpace: 'nowrap', flexShrink: 0, cursor: 'pointer',
              padding: '2px 6px', borderRadius: 'var(--radius-full)',
              border: `1px solid ${target !== null ? 'oklch(from var(--color-primary) l c h / 0.25)' : 'oklch(from var(--color-text) l c h / 0.1)'}`,
              background: target !== null ? 'oklch(from var(--color-primary) l c h / 0.08)' : 'transparent',
              transition: 'all 0.15s',
            }}
            onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'oklch(from var(--color-primary) l c h / 0.12)' }}
            onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = target !== null ? 'oklch(from var(--color-primary) l c h / 0.08)' : 'transparent' }}
          >
            <Target size={10} />
            {target !== null ? `Meta: ${target}%` : 'Definir meta'}
          </span>
        </div>
      </button>
      {showTargetModal && (
        <TargetModal
          assetType={assetType}
          label={group.label}
          currentTarget={target}
          portfolioId={portfolioId}
          onClose={() => setShowTargetModal(false)}
        />
      )}
    </div>
  )
}

const COLS_DEFAULT = [
  { key: 'ativo', label: 'Ativo', align: 'left', width: '30%' },
  { key: 'qtd', label: 'Qtd', align: 'right', width: '8%' },
  { key: 'pm', label: 'P. Médio', align: 'right', width: '11%' },
  { key: 'pa', label: 'P. Atual', align: 'right', width: '11%', info: 'Cotação via provedor de mercado' },
  { key: 'inv', label: 'Custo Atual', align: 'right', width: '13%' },
  { key: 'atual', label: 'Valor Atual', align: 'right', width: '13%' },
  { key: 'resultado', label: 'Resultado de Capital', align: 'right', width: '11%' },
  { key: 'acoes', label: '', align: 'right', width: '3%' },
]

const COLS_RENDA_FIXA = [
  { key: 'ativo', label: 'Ativo', align: 'left', width: '45%' },
  { key: 'inv', label: 'Custo Atual', align: 'right', width: '20%' },
  { key: 'atual', label: 'Valor Atual', align: 'right', width: '20%' },
  { key: 'resultado', label: 'Resultado de Capital', align: 'right', width: '12%' },
  { key: 'acoes', label: '', align: 'right', width: '3%' },
]

function ClassTable({ group, portfolioId, onAssetClick }: { group: PositionGroup; portfolioId: number; onAssetClick?: (asset: PositionGroup['positions'][number]) => void }) {
  const isDesktop = useIsDesktop()
  const [collapsed, setCollapsed] = useState(false)
  const quoteTimestamp = getGroupQuoteTimestamp(group)

  const groupType = group.positions[0]?.asset_type ?? ''
  const isRF = isRendaFixa(groupType)
  const COLS = isRF ? COLS_RENDA_FIXA : COLS_DEFAULT

  return (
    <div className="card" style={{ overflow: 'visible' }}>
      <ClassGroupHeader
        group={group}
        collapsed={collapsed}
        onToggle={() => setCollapsed(v => !v)}
        portfolioId={portfolioId}
      />

      {!collapsed && (
        <>
          {!isDesktop && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', padding: '1rem', overflow: 'visible' }}>
              {group.positions.map(item => (
                <PositionCard key={`${item.ticker}-${item.id ?? item.ticker}`} item={item} onAssetClick={onAssetClick} />
              ))}
            </div>
          )}

          {isDesktop && (
            <table style={{ width: '100%', borderCollapse: 'collapse', tableLayout: 'fixed', fontSize: 'var(--text-xs)', overflow: 'visible' }}>
              <colgroup>
                {COLS.map(c => <col key={c.key} style={{ width: c.width }} />)}
              </colgroup>
              <thead>
                <tr style={{ borderBottom: '1px solid oklch(from var(--color-text) l c h / 0.06)' }}>
                  {COLS.map(col => (
                    <th key={col.key} style={{ padding: '0.5rem 1rem', textAlign: col.align as any, fontWeight: 500, fontSize: '0.68rem', letterSpacing: '0.04em', textTransform: 'uppercase', color: 'var(--color-text-muted)', whiteSpace: 'nowrap' }}>
                      {(col as any).info ? (
                        <span style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'flex-end', gap: 3 }}>
                          {col.label}
                          <span title={(col as any).info} style={{ cursor: 'help', display: 'inline-flex', alignItems: 'center' }}>
                            <svg xmlns="http://www.w3.org/2000/svg" width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={cellFaint}>
                              <circle cx="12" cy="12" r="10" /><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" /><path d="M12 17h.01" />
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
                  const safeType = item.asset_type ?? ''
                  const hasQuote = item.current_price !== null && item.current_price !== undefined
                  const name = displayName(item.ticker, safeType)
                  const isTesouro = safeType.toUpperCase() === 'TESOURO_DIRETO' || safeType.toUpperCase() === 'TESOURO'
                  const itemIsRF = isRendaFixa(safeType)
                  const result = safeNum(item.variation_value)
                  const varColor = result >= 0 ? 'var(--color-success)' : 'var(--color-error)'
                  const investedValue = investedValueOf(item)
                  const currency = isUsdAsset(safeType) ? 'USD' : 'BRL'

                  return (
                    <tr
                      key={`${item.ticker}-${item.id ?? item.ticker}`}
                      onClick={() => onAssetClick?.(item)}
                      style={{ borderBottom: '1px solid oklch(from var(--color-text) l c h / 0.045)', cursor: 'pointer', overflow: 'visible' }}
                      onMouseEnter={e => (e.currentTarget.style.background = 'oklch(from var(--color-primary) l c h / 0.03)')}
                      onMouseLeave={e => (e.currentTarget.style.background = '')}
                    >
                      <td style={{ padding: '0.75rem 1rem', overflow: 'visible' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                          <AssetLogo ticker={item.ticker} assetType={safeType} size={28} logoUrl={item.logo_url} />
                          <div style={{ minWidth: 0 }}>
                            <div style={{ fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', ...cellText }}>{name}</div>
                            <div style={{ fontSize: '0.65rem', marginTop: 2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', ...cellFaint }}>
                              {isTesouro ? item.ticker : item.asset_label}
                            </div>
                          </div>
                        </div>
                      </td>

                      {!itemIsRF && (
                        <>
                          <td style={{ padding: '0.75rem 1rem', textAlign: 'right', fontVariantNumeric: 'tabular-nums', whiteSpace: 'nowrap', ...cellText }}>
                            {fmtQty(item.quantity)}
                          </td>
                          <td style={{ padding: '0.75rem 1rem', textAlign: 'right', fontVariantNumeric: 'tabular-nums', whiteSpace: 'nowrap', ...cellText }}>
                            {fmtMoney(safeNum(item.average_price), currency)}
                          </td>
                          <td style={{ padding: '0.75rem 1rem', textAlign: 'right', fontVariantNumeric: 'tabular-nums', whiteSpace: 'nowrap' }}>
                            {hasQuote ? fmtMoney(safeNum(item.current_price), currency) : <MissingQuoteValue />}
                          </td>
                        </>
                      )}

                      <td style={{ padding: '0.75rem 1rem', textAlign: 'right', fontVariantNumeric: 'tabular-nums', whiteSpace: 'nowrap', ...cellText }}>
                        {fmtMoney(investedValue, 'BRL')}
                      </td>
                      <td style={{ padding: '0.75rem 1rem', textAlign: 'right', fontVariantNumeric: 'tabular-nums', whiteSpace: 'nowrap', ...cellText }}>
                        {hasQuote ? fmtMoney(safeNum(item.current_value), 'BRL') : <MissingQuoteValue />}
                      </td>
                      <td style={{ padding: '0.75rem 1rem', textAlign: 'right', fontVariantNumeric: 'tabular-nums', whiteSpace: 'nowrap' }}>
                        {hasQuote ? (
                          <div style={{ color: varColor }}>
                            <div style={{ fontWeight: 600 }}>{fmtMoney(result, 'BRL')}</div>
                            <div style={{ fontSize: '0.65rem', fontWeight: 500, opacity: 0.8 }}>{formatPercent(safeNum(item.variation_percent))}</div>
                          </div>
                        ) : <MissingQuoteValue />}
                      </td>
                      <td style={{ padding: '0.5rem 0.75rem', textAlign: 'right', overflow: 'visible' }}>
                        <AssetMenu ticker={item.ticker} assetLabel={isTesouro ? item.ticker : (item.asset_label ?? item.ticker)} assetType={safeType} />
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}

          {quoteTimestamp && (
            <div style={{
              display: 'flex', alignItems: 'center', gap: 4,
              padding: '0.4rem 1rem',
              borderTop: '1px solid oklch(from var(--color-text) l c h / 0.05)',
              background: 'oklch(from var(--color-text) l c h / 0.02)',
            }}>
              <Clock size={10} style={{ color: 'var(--color-text-faint)', flexShrink: 0 }} />
              <span style={{ fontSize: '0.65rem', color: 'var(--color-text-faint)' }}>
                Cotações atualizadas {quoteTimestamp}
              </span>
            </div>
          )}
        </>
      )}
    </div>
  )
}

interface Props { groups: PositionGroup[]; portfolioId: number }

export default function PositionTable({ groups, portfolioId }: Props) {
  const [selectedAsset, setSelectedAsset] = useState<PositionGroup['positions'][number] | null>(null)

  if (!groups || groups.length === 0) return null

  return (
    <>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', overflow: 'visible' }}>
        {groups.map(group => (
          <ClassTable key={group.label} group={group} portfolioId={portfolioId} onAssetClick={setSelectedAsset} />
        ))}
      </div>
      <AssetDetailDrawer
        asset={selectedAsset}
        portfolioId={portfolioId}
        onClose={() => setSelectedAsset(null)}
      />
    </>
  )
}
