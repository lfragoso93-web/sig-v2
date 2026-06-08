import { useState } from 'react'
import clsx from 'clsx'
import { Plus, Trash2, Filter, TrendingUp, TrendingDown } from 'lucide-react'
import { format, parseISO } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import { usePortfolioList } from '@/hooks/usePortfolio'
import { useTransactionList, useDeleteTransaction } from '@/hooks/useTransactions'
import { formatBRL, formatQuantity } from '@/utils/format'
import TransactionForm from '@/components/transactions/TransactionForm'
import EmptyState from '@/components/ui/EmptyState'
import Modal from '@/components/ui/Modal'

const ASSET_TYPE_LABELS: Record<string, string> = {
  ACAO_NACIONAL: 'Ação', FII: 'FII', ETF_NACIONAL: 'ETF',
  TESOURO_DIRETO: 'Tesouro', STOCK: 'Stock',
  ETF_INTERNACIONAL: 'ETF Int.', CRIPTO: 'Cripto', RENDA_FIXA: 'Renda Fixa',
}

const TX_TYPE_CONFIG: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
  COMPRA: { label: 'Compra', color: 'badge-green', icon: <TrendingUp size={11} /> },
  VENDA: { label: 'Venda', color: 'badge-red', icon: <TrendingDown size={11} /> },
  BONIFICACAO: { label: 'Bonificação', color: 'badge-blue', icon: null },
  DESDOBRAMENTO: { label: 'Desdobramento', color: 'badge-gray', icon: null },
  GRUPAMENTO: { label: 'Grupamento', color: 'badge-gray', icon: null },
}

const YEARS = Array.from({ length: 6 }, (_, i) => new Date().getFullYear() - i)

export default function TransacoesPage() {
  const { data: portfolios } = usePortfolioList()
  const [selectedPortfolio, setSelectedPortfolio] = useState<number | null>(null)
  const portfolioId = selectedPortfolio ?? (portfolios?.[0]?.id ?? 0)

  const [showForm, setShowForm] = useState(false)
  const [filters, setFilters] = useState({ ticker: '', asset_type: '', tx_type: '', year: '' })

  const { data: transactions, isLoading } = useTransactionList(portfolioId, {
    ticker: filters.ticker || undefined,
    asset_type: filters.asset_type || undefined,
    tx_type: filters.tx_type || undefined,
    year: filters.year ? Number(filters.year) : undefined,
  })

  const { mutate: deleteTx } = useDeleteTransaction(portfolioId)

  const totalCompras = transactions?.filter(t => t.transaction_type === 'COMPRA').reduce((s, t) => s + t.total_value, 0) ?? 0
  const totalVendas = transactions?.filter(t => t.transaction_type === 'VENDA').reduce((s, t) => s + t.total_value, 0) ?? 0

  function confirmDelete(id: number) {
    if (window.confirm('Remover esta transação? Esta ação não pode ser desfeita.')) {
      deleteTx(id)
    }
  }

  return (
    <div className="p-4 md:p-6 flex flex-col gap-5 max-w-[1400px] mx-auto">

      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-bold text-gray-900 dark:text-gray-100">Transações</h1>
          <p className="text-xs text-muted mt-0.5">Registre compras, vendas e eventos corporativos</p>
        </div>
        <button onClick={() => setShowForm(true)} className="btn-primary flex items-center gap-2 px-4 py-2 text-sm">
          <Plus size={16} />
          Nova transação
        </button>
      </div>

      {/* Seletor de carteira */}
      {(portfolios?.length ?? 0) > 1 && (
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted">Carteira:</span>
          {portfolios!.map(p => (
            <button key={p.id} onClick={() => setSelectedPortfolio(p.id)}
              className={clsx('px-3 py-1 rounded text-xs font-medium transition-colors',
                portfolioId === p.id ? 'bg-brand-primary text-white' : 'btn-secondary'
              )}>{p.name}</button>
          ))}
        </div>
      )}

      {/* KPIs rápidos */}
      {transactions && transactions.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="card p-3">
            <span className="text-xs text-muted">Total de transações</span>
            <span className="text-xl font-bold tabular-nums block mt-0.5">{transactions.length}</span>
          </div>
          <div className="card p-3">
            <span className="text-xs text-muted">Total comprado</span>
            <span className="text-xl font-bold tabular-nums block mt-0.5 text-gray-800 dark:text-gray-200">{formatBRL(totalCompras)}</span>
          </div>
          <div className="card p-3">
            <span className="text-xs text-muted">Total vendido</span>
            <span className="text-xl font-bold tabular-nums block mt-0.5 text-positive">{formatBRL(totalVendas)}</span>
          </div>
          <div className="card p-3">
            <span className="text-xs text-muted">Saldo líquido</span>
            <span className={clsx('text-xl font-bold tabular-nums block mt-0.5',
              totalCompras - totalVendas >= 0 ? 'text-gray-800 dark:text-gray-200' : 'text-positive'
            )}>{formatBRL(Math.abs(totalCompras - totalVendas))}</span>
          </div>
        </div>
      )}

      {/* Filtros */}
      <div className="card p-3 flex flex-wrap items-center gap-2">
        <Filter size={14} className="text-muted shrink-0" />
        <input
          type="text"
          placeholder="Filtrar por ticker…"
          className="input py-1 text-xs w-32"
          value={filters.ticker}
          onChange={e => setFilters(f => ({ ...f, ticker: e.target.value.toUpperCase() }))}
        />
        <select className="input py-1 text-xs w-auto" value={filters.asset_type} onChange={e => setFilters(f => ({ ...f, asset_type: e.target.value }))}>
          <option value="">Todos os tipos</option>
          {Object.entries(ASSET_TYPE_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>
        <select className="input py-1 text-xs w-auto" value={filters.tx_type} onChange={e => setFilters(f => ({ ...f, tx_type: e.target.value }))}>
          <option value="">Todas operações</option>
          <option value="COMPRA">Compra</option>
          <option value="VENDA">Venda</option>
          <option value="BONIFICACAO">Bonificação</option>
          <option value="DESDOBRAMENTO">Desdobramento</option>
          <option value="GRUPAMENTO">Grupamento</option>
        </select>
        <select className="input py-1 text-xs w-auto" value={filters.year} onChange={e => setFilters(f => ({ ...f, year: e.target.value }))}>
          <option value="">Todos os anos</option>
          {YEARS.map(y => <option key={y} value={y}>{y}</option>)}
        </select>
        {Object.values(filters).some(Boolean) && (
          <button onClick={() => setFilters({ ticker: '', asset_type: '', tx_type: '', year: '' })} className="text-xs text-muted hover:text-negative transition-colors">Limpar</button>
        )}
      </div>

      {/* Tabela */}
      <div className="card">
        {isLoading ? (
          <div className="p-8 flex flex-col gap-3">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-10 animate-pulse bg-light-200 dark:bg-dark-500 rounded" />
            ))}
          </div>
        ) : !transactions?.length ? (
          <EmptyState
            icon={TrendingUp}
            title="Nenhuma transação encontrada"
            description="Registre sua primeira compra para começar."
            action={{ label: 'Nova transação', onClick: () => setShowForm(true) }}
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[820px]">
              <thead>
                <tr className="border-b border-light-border dark:border-dark-border">
                  {['Data', 'Tipo', 'Ativo', 'Categoria', 'Operação', 'Quantidade', 'Preço', 'Corretagem', 'Total', 'Corretora', ''].map(h => (
                    <th key={h} className="px-3 py-2.5 text-xs font-medium text-muted text-left first:pl-4 last:pr-4">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {transactions.map(tx => {
                  const cfg = TX_TYPE_CONFIG[tx.transaction_type] ?? { label: tx.transaction_type, color: 'badge-gray', icon: null }
                  return (
                    <tr key={tx.id} className="border-b border-light-border/30 dark:border-dark-border/30 hover:bg-light-100 dark:hover:bg-dark-700 transition-colors group">
                      <td className="px-3 py-2.5 pl-4 text-xs tabular-nums text-muted whitespace-nowrap">
                        {format(parseISO(tx.transaction_date), 'dd/MM/yyyy', { locale: ptBR })}
                      </td>
                      <td className="px-3 py-2.5">
                        <span className={clsx('badge flex items-center gap-1 w-fit', cfg.color)}>
                          {cfg.icon}{cfg.label}
                        </span>
                      </td>
                      <td className="px-3 py-2.5">
                        <span className="text-xs font-bold text-gray-800 dark:text-gray-200">{tx.ticker}</span>
                      </td>
                      <td className="px-3 py-2.5">
                        <span className="badge-gray">{ASSET_TYPE_LABELS[tx.asset_type] ?? tx.asset_type}</span>
                      </td>
                      <td className="px-3 py-2.5 text-xs tabular-nums text-right">{formatQuantity(tx.quantity)}</td>
                      <td className="px-3 py-2.5 text-xs tabular-nums text-right">{formatBRL(tx.price)}</td>
                      <td className="px-3 py-2.5 text-xs tabular-nums text-right text-muted">
                        {tx.fees > 0 ? formatBRL(tx.fees) : '—'}
                      </td>
                      <td className="px-3 py-2.5 text-xs tabular-nums text-right font-semibold text-gray-800 dark:text-gray-200">
                        {formatBRL(tx.total_value)}
                      </td>
                      <td className="px-3 py-2.5 text-xs text-muted">{tx.broker ?? '—'}</td>
                      <td className="px-3 py-2.5 pr-4">
                        <button
                          onClick={() => confirmDelete(tx.id)}
                          className="opacity-0 group-hover:opacity-100 text-muted hover:text-negative transition-all p-1 rounded"
                          title="Remover transação"
                        >
                          <Trash2 size={13} />
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Modal nova transação */}
      <Modal
        open={showForm}
        onClose={() => setShowForm(false)}
        title="Nova transação"
        size="lg"
      >
        <TransactionForm portfolioId={portfolioId} onClose={() => setShowForm(false)} />
      </Modal>
    </div>
  )
}
