import { useState, useMemo } from 'react'
import { Search, Trash2, TrendingUp, ArrowDownLeft, ArrowUpRight, FileText } from 'lucide-react'
import { useAppStore } from '@/store/appStore'
import { useTransactions, useDeleteTransaction, type Transaction } from '@/hooks/useTransactions'
import { usePortfolios } from '@/hooks/usePortfolios'
import AddTransactionModal from '@/components/modals/AddTransactionModal'

// ─── helpers ────────────────────────────────────────────────────────────────
function fmtBRL(v: number) {
  return v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
}
function fmtNum(v: number) {
  return v.toLocaleString('pt-BR', { minimumFractionDigits: 0, maximumFractionDigits: 6 })
}
function fmtDate(s: string) {
  if (!s) return '—'
  const [y, m, d] = s.split('T')[0].split('-')
  return `${d}/${m}/${y}`
}

const ASSET_LABELS: Record<string, string> = {
  ACAO:              'Ação',
  FII:               'FII',
  ETF_NACIONAL:      'ETF BR',
  STOCK:             'Stock',
  ETF_INTERNACIONAL: 'ETF INT',
  TESOURO_DIRETO:    'Tesouro',
  RENDA_FIXA:        'Renda Fixa',
  CRIPTO:            'Cripto',
}

const ASSET_COLORS: Record<string, string> = {
  ACAO:              'bg-blue-500/15 text-blue-400',
  FII:               'bg-purple-500/15 text-purple-400',
  ETF_NACIONAL:      'bg-teal-500/15 text-teal-400',
  STOCK:             'bg-sky-500/15 text-sky-400',
  ETF_INTERNACIONAL: 'bg-cyan-500/15 text-cyan-400',
  TESOURO_DIRETO:    'bg-yellow-500/15 text-yellow-400',
  RENDA_FIXA:        'bg-orange-500/15 text-orange-400',
  CRIPTO:            'bg-rose-500/15 text-rose-400',
}

const ALL_TYPES = ['Todos', ...Object.keys(ASSET_LABELS)]

const inputCls = [
  'rounded-md px-3 py-1.5 text-xs',
  'bg-surface-800 border border-surface-600',
  'text-slate-200 placeholder-slate-500',
  'focus:outline-none focus:ring-1 focus:ring-brand-500',
  'transition-colors duration-150',
].join(' ')

// ─── main ───────────────────────────────────────────────────────────────────
export default function LancamentosPage() {
  const { selectedPortfolioId } = useAppStore()
  const { data: portfolios = [] } = usePortfolios()
  const { data: transactions = [], isLoading } = useTransactions(selectedPortfolioId)
  const deleteTransaction = useDeleteTransaction()

  const [showModal,      setShowModal]      = useState(false)
  const [search,         setSearch]         = useState('')
  const [typeFilter,     setTypeFilter]     = useState('Todos')
  const [opFilter,       setOpFilter]       = useState<'todos' | 'buy' | 'sell'>('todos')
  const [confirmDelete,  setConfirmDelete]  = useState<number | null>(null)

  const filtered = useMemo(() => {
    return transactions.filter(t => {
      const matchSearch = t.ticker.toLowerCase().includes(search.toLowerCase())
      const matchType   = typeFilter === 'Todos' || t.asset_type === typeFilter
      const matchOp     = opFilter  === 'todos'  || t.operation  === opFilter
      return matchSearch && matchType && matchOp
    })
  }, [transactions, search, typeFilter, opFilter])

  const totalCompras = useMemo(() =>
    filtered.filter(t => t.operation === 'buy')
      .reduce((s, t) => s + t.quantity * t.price + (t.fees ?? 0), 0)
  , [filtered])

  const totalVendas = useMemo(() =>
    filtered.filter(t => t.operation === 'sell')
      .reduce((s, t) => s + t.quantity * t.price - (t.fees ?? 0), 0)
  , [filtered])

  async function handleDelete(id: number) {
    if (!selectedPortfolioId) return
    await deleteTransaction.mutateAsync({ id, portfolio_id: selectedPortfolioId })
    setConfirmDelete(null)
  }

  const portfolioName = portfolios.find(p => p.id === selectedPortfolioId)?.name ?? ''

  // ── sem carteira selecionada ─────────────────────────────────────────────
  if (!selectedPortfolioId) {
    return (
      <div className="flex flex-col items-center justify-center py-28 gap-3">
        <FileText size={36} className="text-slate-600" />
        <p className="text-sm text-slate-400">Selecione uma carteira para ver os lançamentos.</p>
      </div>
    )
  }

  return (
    <div className="px-4 py-5 max-w-screen-xl mx-auto flex flex-col gap-4">

      {/* ── cabeçalho ────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-base font-semibold text-slate-100">Lançamentos</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            {portfolioName && <span className="font-medium text-slate-400">{portfolioName} · </span>}
            {transactions.length} registro{transactions.length !== 1 ? 's' : ''}
          </p>
        </div>
      </div>

      {/* ── filtros ──────────────────────────────────────────────────────── */}
      <div className="flex flex-wrap gap-2">
        {/* busca */}
        <div className="relative">
          <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none" />
          <input
            className={inputCls + ' pl-7 w-40'}
            placeholder="Buscar ticker…"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>

        {/* tipo de ativo */}
        <select
          className={inputCls + ' w-40'}
          value={typeFilter}
          onChange={e => setTypeFilter(e.target.value)}
        >
          {ALL_TYPES.map(t => (
            <option key={t} value={t}>
              {t === 'Todos' ? 'Todos os tipos' : ASSET_LABELS[t] ?? t}
            </option>
          ))}
        </select>

        {/* compra / venda */}
        <div className="flex rounded-md overflow-hidden border border-surface-600 text-xs font-medium">
          {(['todos', 'buy', 'sell'] as const).map(op => (
            <button
              key={op}
              type="button"
              onClick={() => setOpFilter(op)}
              className={[
                'px-3 py-1.5 transition-colors duration-150',
                opFilter === op
                  ? 'bg-brand-600 text-white'
                  : 'bg-surface-800 text-slate-400 hover:bg-surface-700 hover:text-slate-200',
              ].join(' ')}
            >
              {op === 'todos' ? 'Todos' : op === 'buy' ? 'Compras' : 'Vendas'}
            </button>
          ))}
        </div>
      </div>

      {/* ── tabela ───────────────────────────────────────────────────────── */}
      <div className="rounded-xl overflow-hidden border border-surface-700">
        {isLoading ? (
          <div className="p-5 flex flex-col gap-2">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="h-9 rounded bg-surface-800 animate-pulse" />
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 gap-2 text-center">
            <TrendingUp size={28} className="text-slate-600" />
            <p className="text-sm font-medium text-slate-300">
              {transactions.length === 0 ? 'Nenhum lançamento ainda' : 'Nenhum resultado para os filtros'}
            </p>
            <p className="text-xs text-slate-500">
              {transactions.length === 0
                ? 'Clique em "Adicionar Lançamento" na barra superior para começar.'
                : 'Tente ajustar os filtros acima.'}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-surface-700 bg-surface-800">
                  <th className="text-left px-3 py-2.5 font-medium text-slate-400 whitespace-nowrap">Data</th>
                  <th className="text-left px-3 py-2.5 font-medium text-slate-400">Ativo</th>
                  <th className="text-left px-3 py-2.5 font-medium text-slate-400">Tipo</th>
                  <th className="text-center px-3 py-2.5 font-medium text-slate-400">Op.</th>
                  <th className="text-right px-3 py-2.5 font-medium text-slate-400">Qtd</th>
                  <th className="text-right px-3 py-2.5 font-medium text-slate-400">Preço unit.</th>
                  <th className="text-right px-3 py-2.5 font-medium text-slate-400">Taxas</th>
                  <th className="text-right px-3 py-2.5 font-medium text-slate-400">Total</th>
                  <th className="px-3 py-2.5" />
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-700">
                {filtered.map(t => (
                  <TransactionRow
                    key={t.id}
                    t={t}
                    onDelete={() => setConfirmDelete(t.id)}
                  />
                ))}
              </tbody>
              <tfoot>
                <tr className="border-t-2 border-surface-600 bg-surface-800">
                  <td colSpan={7} className="px-3 py-2.5 text-slate-500 font-medium">
                    {filtered.length} lançamento{filtered.length !== 1 ? 's' : ''}
                  </td>
                  <td className="text-right px-3 py-2.5 font-semibold whitespace-nowrap">
                    <span className="text-positive">{fmtBRL(totalCompras)}</span>
                    <span className="text-slate-600 mx-1">·</span>
                    <span className="text-negative">{fmtBRL(totalVendas)}</span>
                  </td>
                  <td />
                </tr>
              </tfoot>
            </table>
          </div>
        )}
      </div>

      {/* ── modal novo lançamento ────────────────────────────────────────── */}
      {showModal && <AddTransactionModal onClose={() => setShowModal(false)} />}

      {/* ── confirmar delete ─────────────────────────────────────────────── */}
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

// ─── sub-componentes ────────────────────────────────────────────────────────
function TransactionRow({ t, onDelete }: { t: Transaction; onDelete: () => void }) {
  const isBuy  = t.operation === 'buy'
  const fees   = t.fees ?? 0
  const total  = t.quantity * t.price + (isBuy ? fees : -fees)
  const badgeCls = ASSET_COLORS[t.asset_type] ?? 'bg-slate-500/15 text-slate-400'
  const label    = ASSET_LABELS[t.asset_type] ?? t.asset_type

  return (
    <tr className="bg-surface-900 hover:bg-surface-800 transition-colors duration-100">
      <td className="px-3 py-2.5 text-slate-400 whitespace-nowrap tabular-nums">{fmtDate(t.date)}</td>
      <td className="px-3 py-2.5 font-semibold text-slate-100 whitespace-nowrap">{t.ticker}</td>
      <td className="px-3 py-2.5">
        <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium ${badgeCls}`}>
          {label}
        </span>
      </td>
      <td className="px-3 py-2.5 text-center">
        <span className={[
          'inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold',
          isBuy
            ? 'bg-positive/10 text-positive'
            : 'bg-negative/10 text-negative',
        ].join(' ')}>
          {isBuy
            ? <ArrowDownLeft size={11} />
            : <ArrowUpRight  size={11} />}
          {isBuy ? 'Compra' : 'Venda'}
        </span>
      </td>
      <td className="px-3 py-2.5 text-right text-slate-200 tabular-nums">{fmtNum(t.quantity)}</td>
      <td className="px-3 py-2.5 text-right text-slate-200 tabular-nums">{fmtBRL(t.price)}</td>
      <td className="px-3 py-2.5 text-right text-slate-500 tabular-nums">
        {fees > 0 ? fmtBRL(fees) : '—'}
      </td>
      <td className="px-3 py-2.5 text-right font-medium text-slate-100 tabular-nums">{fmtBRL(total)}</td>
      <td className="px-3 py-2.5 text-right">
        <button
          onClick={onDelete}
          className="p-1 rounded text-slate-600 hover:text-red-400 hover:bg-red-500/10 transition-colors"
          aria-label="Excluir"
        >
          <Trash2 size={13} />
        </button>
      </td>
    </tr>
  )
}

function ConfirmDeleteModal({
  onCancel, onConfirm, loading,
}: { onCancel: () => void; onConfirm: () => void; loading: boolean }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center px-4">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onCancel} />
      <div className="relative z-10 w-full max-w-sm rounded-xl bg-surface-900 border border-surface-700 shadow-2xl p-6">
        <h2 className="text-sm font-semibold text-slate-100 mb-2">Excluir lançamento?</h2>
        <p className="text-xs text-slate-400 mb-6">
          Esta ação não pode ser desfeita. O preço médio e o patrimônio serão recalculados.
        </p>
        <div className="flex justify-end gap-2">
          <button
            onClick={onCancel}
            disabled={loading}
            className="px-4 py-1.5 rounded-md text-xs font-medium bg-surface-700 hover:bg-surface-600 text-slate-300 transition-colors"
          >
            Cancelar
          </button>
          <button
            onClick={onConfirm}
            disabled={loading}
            className="px-4 py-1.5 rounded-md text-xs font-medium bg-red-600 hover:bg-red-500 disabled:opacity-50 text-white transition-colors"
          >
            {loading ? 'Excluindo...' : 'Excluir'}
          </button>
        </div>
      </div>
    </div>
  )
}
