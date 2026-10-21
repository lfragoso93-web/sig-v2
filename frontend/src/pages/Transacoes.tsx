import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Search, Trash2, Pencil, ChevronDown, BarChart2, ChevronLeft, ChevronRight } from 'lucide-react'
import { useAppStore } from '@/store/appStore'
import {
  useTransactions,
  useTransactionClasses,
  useDeleteTransaction,
  type Transaction,
} from '@/hooks/useTransactions'
import { usePortfolios } from '@/hooks/usePortfolios'
import { formatBRL, fmtMoney, formatDate, assetBadgeClass } from '@/utils/format'
import TransactionsBarChart from '@/components/charts/TransactionsBarChart'

function assetTypeToTab(assetType: string | null | undefined): string {
  if (!assetType) return 'acao'
  const map: Record<string, string> = {
    ACAO:              'acao',
    ACAO_NACIONAL:     'acao',
    FII:               'fii',
    ETF_NACIONAL:      'etf_br',
    ETF_INTERNACIONAL: 'etf_int',
    STOCK:             'stock',
    TESOURO_DIRETO:    'tesouro',
    RENDA_FIXA:        'renda_fixa',
    CRIPTO:            'cripto',
  }
  return map[assetType.toUpperCase()] ?? 'acao'
}

const ASSET_TYPE_LABEL: Record<string, string> = {
  ACAO:              'Ações',
  ACAO_NACIONAL:     'Ações',
  FII:               'FIIs',
  ETF_NACIONAL:      'ETFs Nacionais',
  ETF_INTERNACIONAL: 'ETFs Internacionais',
  STOCK:             'Stocks',
  TESOURO_DIRETO:    'Tesouro Direto',
  RENDA_FIXA:        'Renda Fixa',
  CRIPTO:            'Criptomoedas',
}

function txCurrency(t: Transaction): string {
  if (t.currency && t.currency.toUpperCase() === 'USD') return 'USD'
  const norm = (t.asset_type ?? '').toUpperCase()
  if (norm === 'STOCK' || norm === 'ETF_INTERNACIONAL') return 'USD'
  return 'BRL'
}

function TransactionCard({
  t, onDelete, onEdit,
}: { t: Transaction; onDelete: () => void; onEdit: () => void }) {
  const isBuy   = t.operation === 'buy'
  const fees    = t.fees ?? 0
  const total   = t.quantity * t.price + (isBuy ? fees : -fees)
  const opColor = isBuy ? 'var(--color-success)' : 'var(--color-notification)'
  const opBg    = isBuy ? 'oklch(from var(--color-success) l c h / 0.12)' : 'oklch(from var(--color-notification) l c h / 0.12)'
  const currency = txCurrency(t)

  return (
    <div className="rounded-xl p-3 flex flex-col gap-2" style={{ background: 'var(--color-surface-offset)', border: '1px solid var(--color-divider)' }}>
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <span className="font-bold text-xs" style={{ color: 'var(--color-text)' }}>{t.ticker}</span>
          <span className="px-2 py-0.5 rounded text-[10px] font-semibold" style={{ background: opBg, color: opColor }}>{isBuy ? 'Compra' : 'Venda'}</span>
          <span className={`asset-badge ${assetBadgeClass(t.asset_type)} text-[9px]`}>{t.asset_type ?? '—'}</span>
        </div>
        <div className="flex items-center gap-1">
          <button onClick={onEdit} className="p-1.5 rounded transition-colors flex items-center justify-center" style={{ color: 'var(--color-text-muted)', minWidth: 30, minHeight: 30 }} aria-label="Editar transação"><Pencil size={12} /></button>
          <button onClick={onDelete} className="p-1.5 rounded transition-colors flex items-center justify-center" style={{ color: 'var(--color-text-faint)', minWidth: 30, minHeight: 30 }} aria-label="Excluir transação"><Trash2 size={12} /></button>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-[11px]">
        <div><div className="text-[10px]" style={{ color: 'var(--color-text-faint)' }}>Data</div><div className="font-medium" style={{ color: 'var(--color-text-muted)' }}>{formatDate(t.date)}</div></div>
        <div><div className="text-[10px]" style={{ color: 'var(--color-text-faint)' }}>Qtd</div><div className="font-medium tabular-nums" style={{ color: 'var(--color-text)' }}>{t.quantity}</div></div>
        <div><div className="text-[10px]" style={{ color: 'var(--color-text-faint)' }}>Preço unit.</div><div className="font-medium tabular-nums" style={{ color: 'var(--color-text)' }}>{fmtMoney(t.price, currency)}</div></div>
        <div><div className="text-[10px]" style={{ color: 'var(--color-text-faint)' }}>Total</div><div className="font-semibold tabular-nums" style={{ color: 'var(--color-text)' }}>{fmtMoney(total, currency)}</div></div>
        {fees > 0 && <div><div className="text-[10px]" style={{ color: 'var(--color-text-faint)' }}>Taxas</div><div className="tabular-nums" style={{ color: 'var(--color-text-muted)' }}>{fmtMoney(fees, currency)}</div></div>}
      </div>
    </div>
  )
}

function TransactionRow({
  t, onDelete, onEdit,
}: { t: Transaction; onDelete: () => void; onEdit: () => void }) {
  const isBuy    = t.operation === 'buy'
  const fees     = t.fees ?? 0
  const total    = t.quantity * t.price + (isBuy ? fees : -fees)
  const currency = txCurrency(t)
  return (
    <tr>
      <td className="text-xs" style={{ color: 'var(--color-text-muted)' }}>{formatDate(t.date)}</td>
      <td><span className="font-semibold text-xs">{t.ticker}</span></td>
      <td><span className={`asset-badge ${assetBadgeClass(t.asset_type)} text-[10px]`}>{t.asset_type ?? '—'}</span></td>
      <td className="text-center">
        <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-semibold" style={{ background: isBuy ? 'oklch(from var(--color-success) l c h / 0.12)' : 'oklch(from var(--color-notification) l c h / 0.12)', color: isBuy ? 'var(--color-success)' : 'var(--color-notification)' }}>{isBuy ? 'Compra' : 'Venda'}</span>
      </td>
      <td className="text-right text-xs tabular-nums">{t.quantity}</td>
      <td className="text-right text-xs tabular-nums">{fmtMoney(t.price, currency)}</td>
      <td className="text-right text-xs tabular-nums" style={{ color: 'var(--color-text-muted)' }}>{fees > 0 ? fmtMoney(fees, currency) : '—'}</td>
      <td className="text-right text-xs font-medium tabular-nums">{fmtMoney(total, currency)}</td>
      <td className="text-right pr-3">
        <div className="flex items-center justify-end gap-0.5">
          <button onClick={onEdit} className="btn btn-ghost p-1.5 rounded" style={{ color: 'var(--color-text-muted)' }} aria-label="Editar"><Pencil size={12} /></button>
          <button onClick={onDelete} className="btn btn-ghost p-1.5 rounded" style={{ color: 'var(--color-text-faint)' }} aria-label="Excluir"><Trash2 size={12} /></button>
        </div>
      </td>
    </tr>
  )
}

function ConfirmDeleteModal({ onCancel, onConfirm, loading }: { onCancel: () => void; onConfirm: () => void; loading: boolean }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center px-4" style={{ background: 'oklch(0 0 0 / 0.45)' }}>
      <div className="w-full max-w-sm rounded-xl border p-6" style={{ background: 'var(--color-surface)', borderColor: 'var(--color-border)', boxShadow: 'var(--shadow-lg)' }}>
        <h2 className="text-base font-semibold mb-2">Excluir transação?</h2>
        <p className="text-sm mb-6" style={{ color: 'var(--color-text-muted)' }}>Esta ação não pode ser desfeita. O preço médio e o patrimônio serão recalculados.</p>
        <div className="flex justify-end gap-2">
          <button className="btn btn-secondary" onClick={onCancel} disabled={loading}>Cancelar</button>
          <button className="btn" style={{ background: 'var(--color-notification)', color: '#fff' }} onClick={onConfirm} disabled={loading}>{loading ? 'Excluindo...' : 'Excluir'}</button>
        </div>
      </div>
    </div>
  )
}

function Pagination({ page, pages, onPrev, onNext }: { page: number; pages: number; onPrev: () => void; onNext: () => void }) {
  if (pages <= 1) return null
  return (
    <div className="flex items-center justify-end gap-2 pt-2 pr-1">
      <button className="btn btn-ghost p-1.5 rounded" style={{ color: page <= 1 ? 'var(--color-text-faint)' : 'var(--color-text-muted)', minWidth: 32, minHeight: 32 }} onClick={onPrev} disabled={page <= 1} aria-label="Página anterior"><ChevronLeft size={14} /></button>
      <span className="text-xs tabular-nums" style={{ color: 'var(--color-text-muted)' }}>{page} / {pages}</span>
      <button className="btn btn-ghost p-1.5 rounded" style={{ color: page >= pages ? 'var(--color-text-faint)' : 'var(--color-text-muted)', minWidth: 32, minHeight: 32 }} onClick={onNext} disabled={page >= pages} aria-label="Próxima página"><ChevronRight size={14} /></button>
    </div>
  )
}

interface ClassSectionProps {
  portfolioId: number
  assetType: string
  label: string
  globalSearch: string
  opFilter: 'todos' | 'buy' | 'sell'
  onEdit: (t: Transaction) => void
  onDelete: (id: number) => void
}

function ClassSection({
  portfolioId,
  assetType,
  label,
  globalSearch,
  opFilter,
  onEdit,
  onDelete,
}: ClassSectionProps) {
  const [open, setOpen] = useState(true)
  const [groupSearch, setGroupSearch] = useState('')
  const [page, setPage] = useState(1)

  useEffect(() => {
    setPage(1)
  }, [globalSearch, opFilter, groupSearch])

  const activeTicker = (groupSearch.trim() || globalSearch.trim()) || undefined

  const { data: paged, isLoading } = useTransactions(portfolioId, {
    asset_type: assetType,
    page,
    page_size: 15,
    ticker: activeTicker,
    operation: opFilter !== 'todos' ? opFilter : undefined,
  })

  const items = paged?.items ?? []
  const total = paged?.total ?? 0
  const pages = paged?.pages ?? 1

  return (
    <div
      className="rounded-xl overflow-hidden"
      data-testid={`class-section-${assetType}`}
      style={{ background: 'var(--color-surface-offset)', border: '1px solid var(--color-border)' }}
    >
      <div className="px-4 py-2.5 flex items-center justify-between" style={{ borderBottom: '1px solid var(--color-divider)' }}>
        <button
          type="button"
          className="flex items-center gap-2 text-left"
          onClick={() => setOpen(o => !o)}
          aria-expanded={open}
        >
          <ChevronDown
            size={14}
            className="transition-transform"
            style={{ transform: open ? 'rotate(0deg)' : 'rotate(-90deg)', color: 'var(--color-text-muted)' }}
          />
          <span className="text-xs font-semibold">{label}</span>
          <span className="text-xs text-muted">· {total} registro{total !== 1 ? 's' : ''}</span>
        </button>
        <input
          className="input input-xs w-32"
          placeholder="Buscar no grupo…"
          value={groupSearch}
          onChange={e => setGroupSearch(e.target.value)}
        />
      </div>

      {open && (
        <>
          {isLoading ? (
            <div className="p-4 flex flex-col gap-2">
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="skeleton h-8 w-full rounded" />
              ))}
            </div>
          ) : items.length === 0 ? (
            <p className="text-xs text-center py-6 text-muted">
              Nenhuma transação encontrada para este filtro no grupo {label}.
            </p>
          ) : (
            <div className="p-3">
              {/* Mobile cards */}
              <div className="flex flex-col gap-2 md:hidden">
                {items.map(t => (
                  <TransactionCard
                    key={t.id}
                    t={t}
                    onDelete={() => onDelete(t.id)}
                    onEdit={() => onEdit(t)}
                  />
                ))}
              </div>

              {/* Desktop table */}
              <div className="hidden md:block table-responsive">
                <table className="positions-table">
                  <thead>
                    <tr>
                      <th>Data</th>
                      <th>Ativo</th>
                      <th>Tipo</th>
                      <th className="text-center">Op.</th>
                      <th className="text-right">Qtd</th>
                      <th className="text-right">Preço unit.</th>
                      <th className="text-right">Taxas</th>
                      <th className="text-right">Total</th>
                      <th style={{ width: '4rem' }} />
                    </tr>
                  </thead>
                  <tbody>
                    {items.map(t => (
                      <TransactionRow
                        key={t.id}
                        t={t}
                        onDelete={() => onDelete(t.id)}
                        onEdit={() => onEdit(t)}
                      />
                    ))}
                  </tbody>
                </table>
              </div>

              <Pagination
                page={page}
                pages={pages}
                onPrev={() => setPage(p => Math.max(1, p - 1))}
                onNext={() => setPage(p => Math.min(pages, p + 1))}
              />
            </div>
          )}
        </>
      )}
    </div>
  )
}

export default function Transacoes() {
  const { selectedPortfolioId, openTransactionModal } = useAppStore()
  const { data: portfolios = [] } = usePortfolios()
  const [searchParams] = useSearchParams()

  const [search, setSearch]     = useState(() => searchParams.get('ticker') ?? '')
  const [opFilter, setOpFilter] = useState<'todos' | 'buy' | 'sell'>('todos')

  const { data: classSummaries = [], isLoading: loadingClasses } = useTransactionClasses(selectedPortfolioId)

  // Consultar resumo global para o gráfico de evolução e totais
  const { data: globalPaged, isLoading: loadingGlobal } = useTransactions(selectedPortfolioId, {
    page: 1,
    page_size: 100,
    ticker:    search || undefined,
    operation: opFilter !== 'todos' ? opFilter : undefined,
  })

  const globalTransactions = globalPaged?.items ?? []
  const totalRecords = globalPaged?.total ?? 0
  const deleteTransaction = useDeleteTransaction()
  const [confirmDelete, setConfirmDelete] = useState<number | null>(null)

  useEffect(() => {
    const ticker = searchParams.get('ticker')
    if (ticker) { setSearch(ticker) }
  }, [searchParams])

  const totalCompras = globalTransactions
    .filter(t => t.operation === 'buy')
    .reduce((s, t) => s + t.quantity * t.price + (t.fees ?? 0), 0)
  const totalVendas = globalTransactions
    .filter(t => t.operation === 'sell')
    .reduce((s, t) => s + t.quantity * t.price - (t.fees ?? 0), 0)

  function handleEdit(t: Transaction) {
    openTransactionModal({
      tab: assetTypeToTab(t.asset_type),
      ticker: t.ticker,
      assetName: t.notes?.split(' - ')[0] ?? '',
      transactionId: t.id,
      fixedIncomeContractId: t.fixed_income_contract_id,
      operation: t.operation,
      quantity: t.quantity,
      price: t.price,
      fees: t.fees,
      date: t.date,
      notes: t.notes,
      currency: t.currency,
    })
  }

  async function handleDelete(id: number) {
    if (!selectedPortfolioId) return
    await deleteTransaction.mutateAsync({ id, portfolioId: selectedPortfolioId })
    setConfirmDelete(null)
  }

  if (!selectedPortfolioId) {
    return (
      <div className="page-container">
        <div className="flex flex-col items-center justify-center py-24 gap-3">
          <p className="text-sm font-medium">Nenhuma carteira selecionada</p>
          <p className="text-xs text-muted">Selecione ou crie uma carteira na barra lateral.</p>
        </div>
      </div>
    )
  }

  const portfolioName = portfolios.find(p => p.id === selectedPortfolioId)?.name ?? 'Carteira'

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1 className="page-title">Transações</h1>
          <p className="page-subtitle">
            {portfolioName} · {totalRecords} registro{totalRecords !== 1 ? 's' : ''}
            {search && <span className="ml-2 px-2 py-0.5 rounded-full text-xs font-medium" style={{ background: 'var(--color-primary-highlight)', color: 'var(--color-primary)' }}>Filtrado: {search.toUpperCase()}</span>}
          </p>
        </div>
      </div>

      <div className="card p-4">
        <div className="flex items-center gap-2 mb-3"><BarChart2 size={16} className="text-brand-400" /><span className="section-card-title">Consolidação de aportes</span></div>
        <div className="h-56"><TransactionsBarChart transactions={globalTransactions} /></div>
      </div>

      <div className="filter-bar">
        <div className="relative" style={{ width: 'min(220px, 100%)' }}>
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" style={{ color: 'var(--color-text-muted)' }} />
          <input className="input" placeholder="Buscar ticker…" value={search} onChange={e => setSearch(e.target.value)} style={{ fontSize: 13, paddingLeft: 36, paddingRight: search ? 28 : 12, height: 38 }} />
          {search && <button type="button" className="absolute right-2 top-1/2 -translate-y-1/2 text-xs" style={{ color: 'var(--color-text-faint)' }} onClick={() => setSearch('')} title="Limpar filtro">×</button>}
        </div>

        <div className="flex items-center gap-1 p-1 rounded-lg" style={{ background: 'var(--color-surface-offset)' }}>
          {(['todos', 'buy', 'sell'] as const).map(op => (
            <button key={op} onClick={() => setOpFilter(op)} className="px-3 py-1 rounded text-xs font-medium transition-colors" style={{ background: opFilter === op ? 'var(--color-surface)' : 'transparent', color: opFilter === op ? 'var(--color-text)' : 'var(--color-text-muted)', boxShadow: opFilter === op ? 'var(--shadow-sm)' : 'none', minHeight: 32 }}>
              {op === 'todos' ? 'Todos' : op === 'buy' ? 'Compras' : 'Vendas'}
            </button>
          ))}
        </div>
      </div>

      <div className="flex flex-col gap-4">
        {loadingClasses || loadingGlobal ? (
          <div className="card p-4 flex flex-col gap-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="skeleton h-12 w-full rounded-xl" />
            ))}
          </div>
        ) : classSummaries.length === 0 && totalRecords === 0 ? (
          <div className="card p-12 flex flex-col items-center justify-center text-center">
            <p className="text-sm font-medium mb-1">Nenhuma transação encontrada</p>
            <p className="text-xs text-muted">Registre sua primeira transação para acompanhar seu histórico.</p>
          </div>
        ) : (
          <>
            {classSummaries.map(cls => (
              <ClassSection
                key={cls.asset_type}
                portfolioId={selectedPortfolioId}
                assetType={cls.asset_type}
                label={cls.label || ASSET_TYPE_LABEL[cls.asset_type] || cls.asset_type}
                globalSearch={search}
                opFilter={opFilter}
                onEdit={handleEdit}
                onDelete={id => setConfirmDelete(id)}
              />
            ))}

            <div className="flex justify-between items-center text-xs px-2 py-1 text-muted">
              <span>{totalRecords} transação(ões) no total</span>
              <span>
                <span style={{ color: 'var(--color-success)' }}>Compras: {formatBRL(totalCompras)}</span>
                {' · '}
                <span style={{ color: 'var(--color-notification)' }}>Vendas: {formatBRL(totalVendas)}</span>
              </span>
            </div>
          </>
        )}
      </div>

      {confirmDelete !== null && (
        <ConfirmDeleteModal
          onCancel={() => setConfirmDelete(null)}
          onConfirm={() => handleDelete(confirmDelete)}
          loading={deleteTransaction.isPending}
        />
      )}
    </div>
  )
}
