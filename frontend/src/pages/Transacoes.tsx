import { useState, useMemo, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Search, Trash2, Pencil, ChevronDown, BarChart2 } from 'lucide-react'
import { useAppStore } from '@/store/appStore'
import {
  useTransactions,
  useDeleteTransaction,
  type Transaction,
} from '@/hooks/useTransactions'
import { usePortfolios } from '@/hooks/usePortfolios'
import { formatBRL, formatDate, assetBadgeClass } from '@/utils/format'
import TransactionsBarChart from '@/components/charts/TransactionsBarChart'

// Mapeia asset_type da API para a aba do AddTransactionModal
function assetTypeToTab(assetType: string): string {
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
  return map[assetType] ?? 'acao'
}

const ASSET_TYPES: { label: string; value: string }[] = [
  { label: 'Todos',               value: '' },
  { label: 'Ações',               value: 'ACAO_NACIONAL' },
  { label: 'FII',                 value: 'FII' },
  { label: 'ETF Nacional',        value: 'ETF_NACIONAL' },
  { label: 'ETF Internacional',   value: 'ETF_INTERNACIONAL' },
  { label: 'Tesouro Direto',      value: 'TESOURO_DIRETO' },
  { label: 'Stock',               value: 'STOCK' },
  { label: 'Criptomoeda',         value: 'CRIPTO' },
  { label: 'Renda Fixa',          value: 'RENDA_FIXA' },
]

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

// ── Card mobile ──────────────────────────────────────────────────────────
function TransactionCard({
  t, onDelete, onEdit,
}: { t: Transaction; onDelete: () => void; onEdit: () => void }) {
  const isBuy   = t.operation === 'buy'
  const fees    = t.fees ?? 0
  const total   = t.quantity * t.price + (isBuy ? fees : -fees)
  const opColor = isBuy ? 'var(--color-success)' : 'var(--color-notification)'
  const opBg    = isBuy
    ? 'oklch(from var(--color-success) l c h / 0.12)'
    : 'oklch(from var(--color-notification) l c h / 0.12)'

  return (
    <div
      className="rounded-xl p-3 flex flex-col gap-2"
      style={{ background: 'var(--color-surface-offset)', border: '1px solid var(--color-divider)' }}
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <span className="font-bold text-sm" style={{ color: 'var(--color-text)' }}>{t.ticker}</span>
          <span className="px-2 py-0.5 rounded text-[10px] font-semibold" style={{ background: opBg, color: opColor }}>
            {isBuy ? 'Compra' : 'Venda'}
          </span>
          <span className={`asset-badge ${assetBadgeClass(t.asset_type)} text-[9px]`}>{t.asset_type}</span>
        </div>
        <div className="flex items-center gap-1">
          <button onClick={onEdit}
            className="p-1.5 rounded transition-colors flex items-center justify-center"
            style={{ color: 'var(--color-text-muted)', minWidth: 32, minHeight: 32 }}
            aria-label="Editar transação"
          >
            <Pencil size={13} />
          </button>
          <button onClick={onDelete}
            className="p-1.5 rounded transition-colors flex items-center justify-center"
            style={{ color: 'var(--color-text-faint)', minWidth: 32, minHeight: 32 }}
            aria-label="Excluir transação"
          >
            <Trash2 size={13} />
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-xs">
        <div>
          <div className="text-[10px]" style={{ color: 'var(--color-text-faint)' }}>Data</div>
          <div className="font-medium" style={{ color: 'var(--color-text-muted)' }}>{formatDate(t.date)}</div>
        </div>
        <div>
          <div className="text-[10px]" style={{ color: 'var(--color-text-faint)' }}>Qtd</div>
          <div className="font-medium tabular-nums" style={{ color: 'var(--color-text)' }}>{t.quantity}</div>
        </div>
        <div>
          <div className="text-[10px]" style={{ color: 'var(--color-text-faint)' }}>Preço unit.</div>
          <div className="font-medium tabular-nums" style={{ color: 'var(--color-text)' }}>{formatBRL(t.price)}</div>
        </div>
        <div>
          <div className="text-[10px]" style={{ color: 'var(--color-text-faint)' }}>Total</div>
          <div className="font-semibold tabular-nums" style={{ color: 'var(--color-text)' }}>{formatBRL(total)}</div>
        </div>
        {fees > 0 && (
          <div>
            <div className="text-[10px]" style={{ color: 'var(--color-text-faint)' }}>Taxas</div>
            <div className="tabular-nums" style={{ color: 'var(--color-text-muted)' }}>{formatBRL(fees)}</div>
          </div>
        )}
      </div>
    </div>
  )
}

// ── Linha desktop ─────────────────────────────────────────────────────────
function TransactionRow({
  t, onDelete, onEdit,
}: { t: Transaction; onDelete: () => void; onEdit: () => void }) {
  const isBuy = t.operation === 'buy'
  const fees  = t.fees ?? 0
  const total = t.quantity * t.price + (isBuy ? fees : -fees)
  return (
    <tr>
      <td className="text-sm" style={{ color: 'var(--color-text-muted)' }}>{formatDate(t.date)}</td>
      <td><span className="font-semibold text-sm">{t.ticker}</span></td>
      <td><span className={`asset-badge ${assetBadgeClass(t.asset_type)}`}>{t.asset_type}</span></td>
      <td className="text-center">
        <span
          className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold"
          style={{
            background: isBuy
              ? 'oklch(from var(--color-success) l c h / 0.12)'
              : 'oklch(from var(--color-notification) l c h / 0.12)',
            color: isBuy ? 'var(--color-success)' : 'var(--color-notification)',
          }}
        >
          {isBuy ? 'Compra' : 'Venda'}
        </span>
      </td>
      <td className="text-right text-sm tabular-nums">{t.quantity}</td>
      <td className="text-right text-sm tabular-nums">{formatBRL(t.price)}</td>
      <td className="text-right text-sm tabular-nums" style={{ color: 'var(--color-text-muted)' }}>
        {fees > 0 ? formatBRL(fees) : '—'}
      </td>
      <td className="text-right text-sm font-medium tabular-nums">{formatBRL(total)}</td>
      <td className="text-right pr-3">
        <div className="flex items-center justify-end gap-0.5">
          <button onClick={onEdit} className="btn btn-ghost p-1.5 rounded" style={{ color: 'var(--color-text-muted)' }} aria-label="Editar">
            <Pencil size={13} />
          </button>
          <button onClick={onDelete} className="btn btn-ghost p-1.5 rounded" style={{ color: 'var(--color-text-faint)' }} aria-label="Excluir">
            <Trash2 size={13} />
          </button>
        </div>
      </td>
    </tr>
  )
}

// ── Modal confirmar exclusao ────────────────────────────────────────────────
function ConfirmDeleteModal({ onCancel, onConfirm, loading }: { onCancel: () => void; onConfirm: () => void; loading: boolean }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center px-4"
      style={{ background: 'oklch(0 0 0 / 0.45)' }}>
      <div className="w-full max-w-sm rounded-xl border p-6"
        style={{ background: 'var(--color-surface)', borderColor: 'var(--color-border)', boxShadow: 'var(--shadow-lg)' }}>
        <h2 className="text-base font-semibold mb-2">Excluir transação?</h2>
        <p className="text-sm mb-6" style={{ color: 'var(--color-text-muted)' }}>
          Esta ação não pode ser desfeita. O preço médio e o patrimônio serão recalculados.
        </p>
        <div className="flex justify-end gap-2">
          <button className="btn btn-secondary" onClick={onCancel} disabled={loading}>Cancelar</button>
          <button className="btn" style={{ background: 'var(--color-notification)', color: '#fff' }} onClick={onConfirm} disabled={loading}>
            {loading ? 'Excluindo...' : 'Excluir'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Pagina principal ──────────────────────────────────────────────────────────
export default function Transacoes() {
  const { selectedPortfolioId, openTransactionModal } = useAppStore()
  const { data: portfolios = [] } = usePortfolios()
  const [searchParams] = useSearchParams()

  const { data: transactions = [], isLoading } = useTransactions(selectedPortfolioId)
  const deleteTransaction = useDeleteTransaction()

  const [search, setSearch]               = useState(() => searchParams.get('ticker') ?? '')
  const [typeFilter, setTypeFilter]       = useState('')
  const [opFilter, setOpFilter]           = useState<'todos' | 'buy' | 'sell'>('todos')
  const [confirmDelete, setConfirmDelete] = useState<number | null>(null)
  const [openGroups, setOpenGroups]       = useState<Record<string, boolean>>({})
  const [groupSearch, setGroupSearch]     = useState<Record<string, string>>({})

  function toggleGroup(assetType: string) {
    setOpenGroups(prev => ({
      ...prev,
      [assetType]: !(prev[assetType] ?? true),
    }))
  }

  function isGroupOpen(assetType: string) {
    return openGroups[assetType] ?? true
  }

  function handleGroupSearchChange(assetType: string, value: string) {
    setGroupSearch(prev => ({ ...prev, [assetType]: value }))
  }

  useEffect(() => {
    const ticker = searchParams.get('ticker')
    if (ticker) setSearch(ticker)
  }, [searchParams])

  const filtered = useMemo(() => {
    return transactions.filter(t => {
      const matchSearch = t.ticker.toLowerCase().includes(search.toLowerCase())
      const matchType   = !typeFilter || t.asset_type === typeFilter
      const matchOp     = opFilter === 'todos' || t.operation === opFilter
      return matchSearch && matchType && matchOp
    })
  }, [transactions, search, typeFilter, opFilter])

  const groupedByType = useMemo(() => {
    const groups: Record<string, Transaction[]> = {}
    for (const t of filtered) {
      if (!groups[t.asset_type]) groups[t.asset_type] = []
      groups[t.asset_type].push(t)
    }
    return groups
  }, [filtered])

  const totalCompras = filtered
    .filter(t => t.operation === 'buy')
    .reduce((s, t) => s + t.quantity * t.price + (t.fees ?? 0), 0)
  const totalVendas = filtered
    .filter(t => t.operation === 'sell')
    .reduce((s, t) => s + t.quantity * t.price - (t.fees ?? 0), 0)

  function handleEdit(t: Transaction) {
    openTransactionModal({
      tab:           assetTypeToTab(t.asset_type),
      ticker:        t.ticker,
      assetName:     t.notes?.split(' - ')[0] ?? '',
      transactionId: t.id,
      operation:     t.operation,
      quantity:      t.quantity,
      price:         t.price,
      fees:          t.fees,
      date:          t.date,
      notes:         t.notes,
      currency:      t.currency,
    })
  }

  async function handleDelete(id: number) {
    if (!selectedPortfolioId) return
    await deleteTransaction.mutateAsync({ id, portfolioId: selectedPortfolioId })
    setConfirmDelete(null)
  }

  if (!selectedPortfolioId) {
    return (
      <div className="flex flex-col items-center justify-center py-24 gap-3">
        <p className="text-sm font-medium">Nenhuma carteira selecionada</p>
        <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>Selecione ou crie uma carteira na barra lateral.</p>
      </div>
    )
  }

  const portfolioName = portfolios.find(p => p.id === selectedPortfolioId)?.name ?? 'Carteira'

  return (
    <div className="flex flex-col gap-5">
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div>
          <h1 className="text-xl font-bold">Transações</h1>
          <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>
            {portfolioName} · {transactions.length} registro{transactions.length !== 1 ? 's' : ''}
            {search && (
              <span
                className="ml-2 px-2 py-0.5 rounded-full text-xs font-medium"
                style={{ background: 'var(--color-primary-highlight)', color: 'var(--color-primary)' }}
              >
                Filtrado: {search.toUpperCase()}
              </span>
            )}
          </p>
        </div>
      </div>

      {/* Gráfico de Consolidação de aportes */}
      <div className="card p-4">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <BarChart2 size={16} className="text-brand-400" />
            <span className="text-sm font-semibold" style={{ color: 'var(--color-text)' }}>
              Consolidação de aportes
            </span>
          </div>
        </div>
        <div className="h-56">
          <TransactionsBarChart transactions={transactions} />
        </div>
      </div>

      {/* Filtros */}
      <div className="flex flex-wrap gap-2">
        <div className="relative">
          <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2" style={{ color: 'var(--color-text-muted)' }} />
          <input
            className="input pl-8 w-40 text-sm"
            placeholder="Buscar ticker…"
            value={search}
            onChange={e => setSearch(e.target.value)}
            style={{ fontSize: 16 }}
          />
          {search && (
            <button type="button"
              className="absolute right-2 top-1/2 -translate-y-1/2 text-xs"
              style={{ color: 'var(--color-text-faint)' }}
              onClick={() => setSearch('')}
              title="Limpar filtro"
            >
              ×
            </button>
          )}
        </div>

        <select className="input text-sm" value={typeFilter} onChange={e => setTypeFilter(e.target.value)} style={{ fontSize: 16 }}>
          {ASSET_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
        </select>

        <div className="flex items-center gap-1 p-1 rounded-lg" style={{ background: 'var(--color-surface-offset)' }}>
          {(['todos', 'buy', 'sell'] as const).map(op => (
            <button key={op} onClick={() => setOpFilter(op)}
              className="px-3 py-1 rounded text-xs font-medium transition-colors"
              style={{
                background: opFilter === op ? 'var(--color-surface)' : 'transparent',
                color:      opFilter === op ? 'var(--color-text)'    : 'var(--color-text-muted)',
                boxShadow:  opFilter === op ? 'var(--shadow-sm)'     : 'none',
                minHeight: 32,
              }}
            >
              {op === 'todos' ? 'Todos' : op === 'buy' ? 'Compras' : 'Vendas'}
            </button>
          ))}
        </div>
      </div>

      {/* Conteúdo */}
      <div className="rounded-xl overflow-hidden" style={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)' }}>
        {isLoading ? (
          <div className="p-4 flex flex-col gap-3">
            {Array.from({ length: 5 }).map((_, i) => <div key={i} className="skeleton h-10 w-full rounded" />)}
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <p className="text-sm font-medium mb-1">Nenhuma transação encontrada</p>
            <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
              {transactions.length === 0 ? 'Registre sua primeira transação.' : 'Tente ajustar os filtros.'}
            </p>
          </div>
        ) : (
          <>
            {/* VIEW MOBILE - grupos por classe */}
            <div className="flex flex-col gap-3 p-3 md:hidden">
              {Object.entries(groupedByType).map(([assetType, list]) => {
                const query = (groupSearch[assetType] ?? '').toLowerCase()
                const groupList = query
                  ? list.filter(t => t.ticker.toLowerCase().includes(query))
                  : list

                if (groupList.length === 0) return null

                const open = isGroupOpen(assetType)

                return (
                  <div key={assetType} className="flex flex-col rounded-xl" style={{ background: 'var(--color-surface-offset)', border: '1px solid var(--color-border)' }}>
                    <div className="flex items-center justify-between px-3 py-2 border-b" style={{ borderColor: 'var(--color-divider)' }}>
                      <button
                        type="button"
                        className="flex items-center gap-2 text-left"
                        onClick={() => toggleGroup(assetType)}
                      >
                        <ChevronDown
                          size={14}
                          className="transition-transform"
                          style={{ transform: open ? 'rotate(0deg)' : 'rotate(-90deg)', color: 'var(--color-text-muted)' }}
                        />
                        <span className="text-xs font-semibold">
                          {ASSET_TYPE_LABEL[assetType] ?? assetType}
                        </span>
                        <span className="text-[11px]" style={{ color: 'var(--color-text-muted)' }}>
                          · {groupList.length} transação(ões)
                        </span>
                      </button>
                      <input
                        className="input input-xs w-24 text-[11px]"
                        placeholder="Buscar..."
                        value={groupSearch[assetType] ?? ''}
                        onChange={e => handleGroupSearchChange(assetType, e.target.value)}
                      />
                    </div>

                    {open && (
                      <div className="flex flex-col gap-2 p-3">
                        {groupList.map(t => (
                          <TransactionCard
                            key={t.id}
                            t={t}
                            onDelete={() => setConfirmDelete(t.id)}
                            onEdit={() => handleEdit(t)}
                          />
                        ))}
                      </div>
                    )}
                  </div>
                )
              })}

              <div className="flex justify-between text-xs pt-2"
                style={{ color: 'var(--color-text-muted)', borderTop: '1px solid var(--color-divider)' }}>
                <span>{filtered.length} transação(ões)</span>
                <span>
                  <span style={{ color: 'var(--color-success)' }}>C: {formatBRL(totalCompras)}</span>
                  {' · '}
                  <span style={{ color: 'var(--color-notification)' }}>V: {formatBRL(totalVendas)}</span>
                </span>
              </div>
            </div>

            {/* VIEW DESKTOP - um bloco por classe de ativo */}
            <div className="hidden md:flex flex-col gap-4 p-3">
              {Object.entries(groupedByType).map(([assetType, list]) => {
                const query = (groupSearch[assetType] ?? '').toLowerCase()
                const groupList = query
                  ? list.filter(t => t.ticker.toLowerCase().includes(query))
                  : list

                if (groupList.length === 0) return null

                const open = isGroupOpen(assetType)

                return (
                  <div key={assetType} className="overflow-x-auto rounded-xl"
                    style={{ background: 'var(--color-surface-offset)', border: '1px solid var(--color-border)' }}
                  >
                    <div className="px-4 pt-3 pb-2 flex items-center justify-between border-b" style={{ borderColor: 'var(--color-divider)' }}>
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          className="flex items-center gap-2 text-left"
                          onClick={() => toggleGroup(assetType)}
                        >
                          <ChevronDown
                            size={14}
                            className="transition-transform"
                            style={{ transform: open ? 'rotate(0deg)' : 'rotate(-90deg)', color: 'var(--color-text-muted)' }}
                          />
                          <span className="text-sm font-semibold">
                            {ASSET_TYPE_LABEL[assetType] ?? assetType}
                          </span>
                          <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                            · {groupList.length} transação(ões)
                          </span>
                        </button>
                      </div>
                      <input
                        className="input input-xs w-32 text-[11px]"
                        placeholder="Buscar ticker..."
                        value={groupSearch[assetType] ?? ''}
                        onChange={e => handleGroupSearchChange(assetType, e.target.value)}
                      />
                    </div>

                    {open && (
                      <table className="positions-table">
                        <thead>
                          <tr>
                            <th>Data</th><th>Ativo</th><th>Tipo</th>
                            <th className="text-center">Op.</th>
                            <th className="text-right">Qtd</th>
                            <th className="text-right">Preço unit.</th>
                            <th className="text-right">Taxas</th>
                            <th className="text-right">Total</th>
                            <th />
                          </tr>
                        </thead>
                        <tbody>
                          {groupList.map(t => (
                            <TransactionRow
                              key={t.id}
                              t={t}
                              onDelete={() => setConfirmDelete(t.id)}
                              onEdit={() => handleEdit(t)}
                            />
                          ))}
                        </tbody>
                      </table>
                    )}
                  </div>
                )
              })}

              <div className="flex justify-end text-xs pr-1 pb-1" style={{ color: 'var(--color-text-muted)' }}>
                <span>
                  <span style={{ color: 'var(--color-success)' }}>C: {formatBRL(totalCompras)}</span>
                  {' · '}
                  <span style={{ color: 'var(--color-notification)' }}>V: {formatBRL(totalVendas)}</span>
                </span>
              </div>
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
