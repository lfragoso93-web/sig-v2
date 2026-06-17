import { useState, useMemo } from 'react'
import { Search, Trash2, ArrowDownLeft, ArrowUpRight, FileText } from 'lucide-react'
import { useAppStore } from '@/store/appStore'
import { useTransactions, useDeleteTransaction, type Transaction } from '@/hooks/useTransactions'
import { usePortfolios } from '@/hooks/usePortfolios'
import AddTransactionModal from '@/components/modals/AddTransactionModal'

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
  ACAO: 'Ação', FII: 'FII', ETF_NACIONAL: 'ETF BR',
  STOCK: 'Stock', ETF_INTERNACIONAL: 'ETF INT',
  TESOURO_DIRETO: 'Tesouro', RENDA_FIXA: 'Renda Fixa', CRIPTO: 'Cripto',
}

const ASSET_COLORS: Record<string, { bg: string; text: string }> = {
  ACAO:              { bg: 'var(--color-blue-highlight)',    text: 'var(--color-blue)'    },
  FII:               { bg: 'var(--color-purple-highlight)', text: 'var(--color-purple)'  },
  ETF_NACIONAL:      { bg: 'var(--color-primary-highlight)',text: 'var(--color-primary)' },
  STOCK:             { bg: 'var(--color-blue-highlight)',   text: 'var(--color-blue)'    },
  ETF_INTERNACIONAL: { bg: 'var(--color-blue-highlight)',   text: 'var(--color-blue)'    },
  TESOURO_DIRETO:    { bg: 'var(--color-gold-highlight)',   text: 'var(--color-gold)'    },
  RENDA_FIXA:        { bg: 'var(--color-orange-highlight)', text: 'var(--color-orange)'  },
  CRIPTO:            { bg: 'var(--color-error-highlight)',  text: 'var(--color-error)'   },
}
const FALLBACK_COLOR = { bg: 'var(--color-surface-dynamic)', text: 'var(--color-text-muted)' }

const ALL_TYPES = ['Todos', ...Object.keys(ASSET_LABELS)]

export default function LancamentosPage() {
  const { selectedPortfolioId } = useAppStore()
  const { data: portfolios = [] } = usePortfolios()
  const { data: transactions = [], isLoading } = useTransactions(selectedPortfolioId)
  const deleteTransaction = useDeleteTransaction()

  const [showModal,     setShowModal]     = useState(false)
  const [search,        setSearch]        = useState('')
  const [typeFilter,    setTypeFilter]    = useState('Todos')
  const [opFilter,      setOpFilter]      = useState<'todos' | 'buy' | 'sell'>('todos')
  const [confirmDelete, setConfirmDelete] = useState<number | null>(null)

  const filtered = useMemo(() => transactions.filter(t => {
    const matchSearch = t.ticker.toLowerCase().includes(search.toLowerCase())
    const matchType   = typeFilter === 'Todos' || t.asset_type === typeFilter
    const matchOp     = opFilter  === 'todos'  || t.operation  === opFilter
    return matchSearch && matchType && matchOp
  }), [transactions, search, typeFilter, opFilter])

  const totalCompras = useMemo(() =>
    filtered.filter(t => t.operation === 'buy').reduce((s, t) => s + t.quantity * t.price + (t.fees ?? 0), 0)
  , [filtered])

  const totalVendas = useMemo(() =>
    filtered.filter(t => t.operation === 'sell').reduce((s, t) => s + t.quantity * t.price - (t.fees ?? 0), 0)
  , [filtered])

  async function handleDelete(id: number) {
    if (!selectedPortfolioId) return
    await deleteTransaction.mutateAsync({ id, portfolioId: selectedPortfolioId })
    setConfirmDelete(null)
  }

  const portfolioName = portfolios.find(p => p.id === selectedPortfolioId)?.name ?? ''

  if (!selectedPortfolioId) {
    return (
      <div className="page-container">
        <div className="flex flex-col items-center justify-center py-28 gap-3">
          <FileText size={36} style={{ color: 'var(--color-text-faint)' }} />
          <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>Selecione uma carteira para ver os lançamentos.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="page-container">

      {/* Cabeçalho */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Lançamentos</h1>
          <p className="page-subtitle">
            {portfolioName && <span className="font-medium">{portfolioName} · </span>}
            {transactions.length} registro{transactions.length !== 1 ? 's' : ''}
          </p>
        </div>
        <button className="btn btn-primary text-xs" onClick={() => setShowModal(true)}>
          + Novo Lançamento
        </button>
      </div>

      {/* Filtros */}
      <div className="flex flex-wrap gap-2">
        <div className="relative">
          <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2" style={{ color: 'var(--color-text-faint)' }} />
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Buscar ticker..."
            className="input pl-8 text-xs w-44"
          />
        </div>
        <select value={typeFilter} onChange={e => setTypeFilter(e.target.value)} className="input text-xs">
          {ALL_TYPES.map(t => (
            <option key={t} value={t}>{t === 'Todos' ? 'Todos os tipos' : (ASSET_LABELS[t] ?? t)}</option>
          ))}
        </select>
        <select value={opFilter} onChange={e => setOpFilter(e.target.value as typeof opFilter)} className="input text-xs">
          <option value="todos">Compra + Venda</option>
          <option value="buy">Apenas Compras</option>
          <option value="sell">Apenas Vendas</option>
        </select>
      </div>

      {/* Resumo rápido */}
      <div className="kpi-grid" style={{ gridTemplateColumns: 'repeat(3, 1fr)' }}>
        <div className="card" style={{ padding: '12px 16px' }}>
          <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>Total de registros</span>
          <div className="text-base font-bold tabular-nums mt-1">{filtered.length}</div>
        </div>
        <div className="card" style={{ padding: '12px 16px' }}>
          <span className="text-xs flex items-center gap-1" style={{ color: 'var(--color-success)' }}>
            <ArrowDownLeft size={11} /> Compras
          </span>
          <div className="text-base font-bold tabular-nums mt-1" style={{ color: 'var(--color-success)' }}>{fmtBRL(totalCompras)}</div>
        </div>
        <div className="card" style={{ padding: '12px 16px' }}>
          <span className="text-xs flex items-center gap-1" style={{ color: 'var(--color-warning)' }}>
            <ArrowUpRight size={11} /> Vendas
          </span>
          <div className="text-base font-bold tabular-nums mt-1" style={{ color: 'var(--color-warning)' }}>{fmtBRL(totalVendas)}</div>
        </div>
      </div>

      {/* Tabela */}
      {isLoading ? (
        <div className="flex flex-col gap-2">
          {[...Array(5)].map((_, i) => <div key={i} className="h-12 rounded-lg skeleton" />)}
        </div>
      ) : filtered.length === 0 ? (
        <div className="py-16 text-center">
          <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>
            {search || typeFilter !== 'Todos' || opFilter !== 'todos'
              ? 'Nenhum lançamento encontrado para os filtros aplicados.'
              : 'Nenhum lançamento cadastrado. Clique em "Novo Lançamento" para começar.'}
          </p>
        </div>
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full text-xs">
            <thead>
              <tr style={{ background: 'var(--color-surface-offset)', borderBottom: '1px solid var(--color-divider)' }}>
                <th className="text-left px-3 py-2 font-medium" style={{ color: 'var(--color-text-muted)' }}>Data</th>
                <th className="text-left px-3 py-2 font-medium" style={{ color: 'var(--color-text-muted)' }}>Ticker</th>
                <th className="text-left px-3 py-2 font-medium" style={{ color: 'var(--color-text-muted)' }}>Tipo</th>
                <th className="text-left px-3 py-2 font-medium" style={{ color: 'var(--color-text-muted)' }}>Operação</th>
                <th className="text-right px-3 py-2 font-medium" style={{ color: 'var(--color-text-muted)' }}>Qtd</th>
                <th className="text-right px-3 py-2 font-medium" style={{ color: 'var(--color-text-muted)' }}>Preço</th>
                <th className="text-right px-3 py-2 font-medium" style={{ color: 'var(--color-text-muted)' }}>Total</th>
                <th className="text-right px-3 py-2 font-medium" style={{ color: 'var(--color-text-muted)' }}>Taxas</th>
                <th className="px-2 py-2" />
              </tr>
            </thead>
            <tbody>
              {filtered.map((t: Transaction, idx: number) => {
                const clr = ASSET_COLORS[t.asset_type] ?? FALLBACK_COLOR
                const isConfirming = confirmDelete === t.id
                return (
                  <tr key={t.id} style={{ background: idx % 2 === 0 ? 'var(--color-surface)' : 'var(--color-surface-2)', borderBottom: '1px solid var(--color-divider)' }}>
                    <td className="px-3 py-2 tabular-nums" style={{ color: 'var(--color-text-muted)' }}>{fmtDate(t.date)}</td>
                    <td className="px-3 py-2 font-semibold">{t.ticker}</td>
                    <td className="px-3 py-2">
                      <span className="px-1.5 py-0.5 rounded text-xs font-medium" style={{ background: clr.bg, color: clr.text }}>
                        {ASSET_LABELS[t.asset_type] ?? t.asset_type}
                      </span>
                    </td>
                    <td className="px-3 py-2">
                      <span className="flex items-center gap-1 text-xs font-medium" style={{ color: t.operation === 'buy' ? 'var(--color-success)' : 'var(--color-warning)' }}>
                        {t.operation === 'buy' ? <><ArrowDownLeft size={11} /> Compra</> : <><ArrowUpRight size={11} /> Venda</>}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-right tabular-nums">{fmtNum(t.quantity)}</td>
                    <td className="px-3 py-2 text-right tabular-nums">{fmtBRL(t.price)}</td>
                    <td className="px-3 py-2 text-right tabular-nums font-medium">{fmtBRL(t.quantity * t.price)}</td>
                    <td className="px-3 py-2 text-right tabular-nums" style={{ color: 'var(--color-text-muted)' }}>{t.fees ? fmtBRL(t.fees) : '—'}</td>
                    <td className="px-2 py-2 text-right">
                      {isConfirming ? (
                        <div className="flex items-center gap-1 justify-end">
                          <button onClick={() => handleDelete(t.id)} className="text-xs px-2 py-0.5 rounded font-medium" style={{ background: 'var(--color-error-highlight)', color: 'var(--color-error)' }}>Confirmar</button>
                          <button onClick={() => setConfirmDelete(null)} className="text-xs px-2 py-0.5 rounded" style={{ color: 'var(--color-text-muted)' }}>Cancelar</button>
                        </div>
                      ) : (
                        <button
                          onClick={() => setConfirmDelete(t.id)}
                          className="p-1 rounded transition"
                          style={{ color: 'var(--color-text-faint)' }}
                          onMouseEnter={e => (e.currentTarget.style.color = 'var(--color-error)')}
                          onMouseLeave={e => (e.currentTarget.style.color = 'var(--color-text-faint)')}
                          aria-label="Excluir"
                        >
                          <Trash2 size={13} />
                        </button>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {showModal && (
        <AddTransactionModal onClose={() => setShowModal(false)} />
      )}
    </div>
  )
}
