import { useState, useMemo } from 'react'
import { useParams } from 'react-router-dom'
import { Plus, Search, Trash2 } from 'lucide-react'
import { useAppStore } from '@/store/appStore'
import {
  useTransactions,
  useDeleteTransaction,
  type Transaction,
} from '@/hooks/useTransactions'
import ModalNovaTransacao from '@/components/transactions/ModalNovaTransacao'
import { formatBRL, formatDate, assetBadgeClass } from '@/utils/format'

const ASSET_TYPES = [
  'Todos',
  'Acao Nacional',
  'FII',
  'ETF Nacional',
  'Tesouro Direto',
  'Stock',
  'ETF Internacional',
  'Criptomoeda',
  'Renda Fixa',
]

export default function Transacoes() {
  const { portfolioId } = useParams()
  const { selectedPortfolioId } = useAppStore()
  const activeId = portfolioId ? Number(portfolioId) : selectedPortfolioId

  const { data: transactions = [], isLoading } = useTransactions(activeId)
  const deleteTransaction = useDeleteTransaction(activeId!)

  const [showModal, setShowModal]   = useState(false)
  const [search, setSearch]         = useState('')
  const [typeFilter, setTypeFilter] = useState('Todos')
  const [opFilter, setOpFilter]     = useState<'todos' | 'buy' | 'sell'>('todos')
  const [confirmDelete, setConfirmDelete] = useState<number | null>(null)

  // Filtros aplicados
  const filtered = useMemo(() => {
    return transactions.filter(t => {
      const matchSearch = t.ticker.toLowerCase().includes(search.toLowerCase())
      const matchType   = typeFilter === 'Todos' || t.asset_type.toLowerCase() === typeFilter.toLowerCase()
      const matchOp     = opFilter === 'todos' || t.operation === opFilter
      return matchSearch && matchType && matchOp
    })
  }, [transactions, search, typeFilter, opFilter])

  // Totais do rodapé
  const totalCompras = filtered
    .filter(t => t.operation === 'buy')
    .reduce((s, t) => s + t.quantity * t.price + t.fees, 0)
  const totalVendas = filtered
    .filter(t => t.operation === 'sell')
    .reduce((s, t) => s + t.quantity * t.price - t.fees, 0)

  async function handleDelete(id: number) {
    await deleteTransaction.mutateAsync(id)
    setConfirmDelete(null)
  }

  if (!activeId) {
    return (
      <div className="flex items-center justify-center py-24">
        <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>Selecione uma carteira.</p>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold">Transações</h1>
          <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>
            {transactions.length} registro{transactions.length !== 1 ? 's' : ''}
          </p>
        </div>
        <button
          className="btn btn-primary flex items-center gap-1.5 text-sm"
          onClick={() => setShowModal(true)}
        >
          <Plus size={15} /> Nova transação
        </button>
      </div>

      {/* Filtros */}
      <div className="flex flex-wrap gap-2">
        {/* Busca por ticker */}
        <div className="relative">
          <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2" style={{ color: 'var(--color-text-muted)' }} />
          <input
            className="input pl-8 w-44 text-sm"
            placeholder="Buscar ticker…"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>

        {/* Filtro por tipo */}
        <select
          className="input text-sm w-44"
          value={typeFilter}
          onChange={e => setTypeFilter(e.target.value)}
        >
          {ASSET_TYPES.map(t => <option key={t}>{t}</option>)}
        </select>

        {/* Filtro compra/venda */}
        <div className="flex items-center gap-1 p-1 rounded-lg" style={{ background: 'var(--color-surface-offset)' }}>
          {(['todos', 'buy', 'sell'] as const).map(op => (
            <button
              key={op}
              onClick={() => setOpFilter(op)}
              className="px-3 py-1 rounded text-xs font-medium transition-colors"
              style={{
                background: opFilter === op ? 'var(--color-surface)' : 'transparent',
                color: opFilter === op ? 'var(--color-text)' : 'var(--color-text-muted)',
                boxShadow: opFilter === op ? 'var(--shadow-sm)' : 'none',
              }}
            >
              {op === 'todos' ? 'Todos' : op === 'buy' ? 'Compras' : 'Vendas'}
            </button>
          ))}
        </div>
      </div>

      {/* Tabela */}
      <div className="bg-surface border border-[var(--color-border)] rounded-xl overflow-hidden">
        {isLoading ? (
          <div className="p-6 flex flex-col gap-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="skeleton h-10 w-full rounded" />
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <p className="text-sm font-medium mb-1">Nenhuma transação encontrada</p>
            <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
              {transactions.length === 0
                ? 'Registre sua primeira transação clicando em "Nova transação".'
                : 'Tente ajustar os filtros.'}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
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
                  <th />
                </tr>
              </thead>
              <tbody>
                {filtered.map(t => (
                  <TransactionRow
                    key={t.id}
                    t={t}
                    onDelete={() => setConfirmDelete(t.id)}
                  />
                ))}
              </tbody>
              <tfoot>
                <tr style={{ background: 'var(--color-surface-offset)', borderTop: '2px solid var(--color-divider)' }}>
                  <td colSpan={7} className="px-3 py-2.5 text-xs font-semibold" style={{ color: 'var(--color-text-muted)' }}>
                    {filtered.length} transação(ões) filtrada(s)
                  </td>
                  <td className="text-right px-3 py-2.5 text-xs font-semibold">
                    <span style={{ color: 'var(--color-success)' }}>C: {formatBRL(totalCompras)}</span>
                    {' · '}
                    <span style={{ color: 'var(--color-notification)' }}>V: {formatBRL(totalVendas)}</span>
                  </td>
                  <td />
                </tr>
              </tfoot>
            </table>
          </div>
        )}
      </div>

      {/* Modal nova transação */}
      {showModal && activeId && (
        <ModalNovaTransacao
          portfolioId={activeId}
          onClose={() => setShowModal(false)}
        />
      )}

      {/* Confirm delete */}
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

// ─ Linha da tabela ────────────────────────────────────────────────────────
function TransactionRow({ t, onDelete }: { t: Transaction; onDelete: () => void }) {
  const isBuy  = t.operation === 'buy'
  const total  = t.quantity * t.price + (isBuy ? t.fees : -t.fees)

  return (
    <tr>
      <td className="text-sm" style={{ color: 'var(--color-text-muted)' }}>{formatDate(t.date)}</td>
      <td>
        <span className="font-semibold text-sm">{t.ticker}</span>
      </td>
      <td>
        <span className={`asset-badge ${assetBadgeClass(t.asset_type)}`}>{t.asset_type}</span>
      </td>
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
        {t.fees > 0 ? formatBRL(t.fees) : '—'}
      </td>
      <td className="text-right text-sm font-medium tabular-nums">{formatBRL(total)}</td>
      <td className="text-right pr-3">
        <button
          onClick={onDelete}
          className="btn btn-ghost p-1 rounded text-[var(--color-text-faint)] hover:text-[var(--color-notification)] transition-colors"
          aria-label="Excluir transação"
        >
          <Trash2 size={14} />
        </button>
      </td>
    </tr>
  )
}

// ─ Modal confirmação de exclusão ──────────────────────────────────────────
function ConfirmDeleteModal({
  onCancel,
  onConfirm,
  loading,
}: {
  onCancel: () => void
  onConfirm: () => void
  loading: boolean
}) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center px-4"
      style={{ background: 'oklch(0 0 0 / 0.45)' }}
    >
      <div
        className="w-full max-w-sm rounded-xl border p-6"
        style={{ background: 'var(--color-surface)', borderColor: 'var(--color-border)', boxShadow: 'var(--shadow-lg)' }}
      >
        <h2 className="text-base font-semibold mb-2">Excluir transação?</h2>
        <p className="text-sm mb-6" style={{ color: 'var(--color-text-muted)' }}>
          Esta ação não pode ser desfeita. O preço médio e o patrimônio serão recalculados.
        </p>
        <div className="flex justify-end gap-2">
          <button className="btn btn-secondary" onClick={onCancel} disabled={loading}>Cancelar</button>
          <button
            className="btn"
            style={{ background: 'var(--color-notification)', color: '#fff' }}
            onClick={onConfirm}
            disabled={loading}
          >
            {loading ? 'Excluindo...' : 'Excluir'}
          </button>
        </div>
      </div>
    </div>
  )
}
