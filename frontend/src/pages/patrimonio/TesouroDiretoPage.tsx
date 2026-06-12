import { useState } from 'react'
import { useTreasury, TreasuryItem } from '../../hooks/useTreasury'
import { useAppStore } from '../../store/appStore'

// ── helpers ────────────────────────────────────────────────────────────────
const fmtBRL = (v: number | null | undefined) =>
  v == null ? '—' : v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })

const fmtDate = (s: string | null | undefined) => {
  if (!s) return '—'
  const [y, m, d] = s.split('-')
  return `${d}/${m}/${y}`
}

// ── DeleteConfirm ────────────────────────────────────────────────────────────
interface DeleteConfirmProps {
  item: TreasuryItem
  onConfirm: () => Promise<void>
  onClose: () => void
}

function DeleteConfirm({ item, onConfirm, onClose }: DeleteConfirmProps) {
  const [loading, setLoading] = useState(false)

  const handleConfirm = async () => {
    setLoading(true)
    try { await onConfirm() } finally { setLoading(false) }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end md:items-center justify-center bg-black/50">
      <div className="w-full max-w-sm bg-white dark:bg-gray-900 rounded-t-2xl md:rounded-2xl p-6 shadow-xl">
        <h2 className="text-lg font-semibold text-gray-800 dark:text-white mb-2">Excluir investimento</h2>
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">
          Tem certeza que deseja excluir <strong>{item.brapi_name}</strong>? Esta ação não pode ser desfeita.
        </p>
        <div className="flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 border rounded-lg py-2 text-sm text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800"
          >Cancelar</button>
          <button
            onClick={handleConfirm}
            disabled={loading}
            className="flex-1 bg-red-600 text-white rounded-lg py-2 text-sm font-medium hover:bg-red-700 disabled:opacity-50"
          >{loading ? 'Excluindo...' : 'Excluir'}</button>
        </div>
      </div>
    </div>
  )
}

// ── TesouroDiretoPage ────────────────────────────────────────────────────────
export default function TesouroDiretoPage() {
  const portfolioId        = useAppStore((s) => s.selectedPortfolioId)
  const openTransactionModal = useAppStore((s) => s.openTransactionModal)
  const { items, loading, error, remove } = useTreasury()

  const [deleteItem, setDeleteItem] = useState<TreasuryItem | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)

  if (!portfolioId) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-gray-400">
        <p className="text-base">Selecione uma carteira para ver o Tesouro Direto.</p>
      </div>
    )
  }

  // Abre o AddTransactionModal global já existente, pré-preenchido com os dados do título
  const handleEdit = (item: TreasuryItem) => {
    openTransactionModal({
      tab:       'tesouro',
      ticker:    item.brapi_name,
      assetName: item.brapi_name,
    })
  }

  const handleDelete = async () => {
    if (!deleteItem) return
    setActionError(null)
    try {
      await remove(deleteItem.id)
      setDeleteItem(null)
    } catch (e: any) {
      setActionError(e?.response?.data?.detail || 'Erro ao excluir')
    }
  }

  return (
    <div className="p-4 md:p-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-bold text-gray-800 dark:text-white">Tesouro Direto</h1>
        <button
          onClick={() => openTransactionModal({ tab: 'tesouro' })}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
        >
          + Novo Lançamento
        </button>
      </div>

      {actionError && (
        <div className="mb-4 bg-red-50 border border-red-200 text-red-700 rounded-lg px-4 py-3 text-sm">
          {actionError}
        </div>
      )}

      {loading && (
        <div className="flex justify-center py-12">
          <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
        </div>
      )}

      {!loading && error && (
        <div className="bg-red-50 border border-red-200 text-red-600 rounded-lg px-4 py-3 text-sm">{error}</div>
      )}

      {!loading && !error && items.length === 0 && (
        <div className="flex flex-col items-center justify-center h-48 text-gray-400">
          <p>Nenhum investimento em Tesouro Direto cadastrado.</p>
          <p className="text-sm mt-1">
            Clique em <strong>+ Novo Lançamento</strong> para adicionar.
          </p>
        </div>
      )}

      {!loading && items.length > 0 && (
        <div className="overflow-x-auto rounded-xl border border-gray-200 dark:border-gray-700">
          <table className="min-w-full text-sm">
            <thead className="bg-gray-50 dark:bg-gray-800 text-gray-500 dark:text-gray-400 uppercase text-xs">
              <tr>
                <th className="px-4 py-3 text-left">Título</th>
                <th className="px-4 py-3 text-right">Valor Investido</th>
                <th className="px-4 py-3 text-right">Preço Atual</th>
                <th className="px-4 py-3 text-center hidden md:table-cell">Compra</th>
                <th className="px-4 py-3 text-center hidden md:table-cell">Vencimento</th>
                <th className="px-4 py-3 text-center">Status</th>
                <th className="px-4 py-3 text-center">Ações</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-700 bg-white dark:bg-gray-900">
              {items.map((item) => (
                <tr key={item.id} className="hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
                  <td className="px-4 py-3 font-medium text-gray-800 dark:text-white max-w-[200px] truncate">
                    {item.brapi_name}
                  </td>
                  <td className="px-4 py-3 text-right text-gray-700 dark:text-gray-300">
                    {fmtBRL(item.invested_value)}
                  </td>
                  <td className="px-4 py-3 text-right text-gray-700 dark:text-gray-300">
                    {fmtBRL(item.current_price)}
                  </td>
                  <td className="px-4 py-3 text-center text-gray-500 hidden md:table-cell">
                    {fmtDate(item.purchase_date)}
                  </td>
                  <td className="px-4 py-3 text-center text-gray-500 hidden md:table-cell">
                    {fmtDate(item.maturity_date)}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      item.is_active
                        ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                        : 'bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400'
                    }`}>
                      {item.is_active ? 'Ativo' : 'Encerrado'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <div className="flex items-center justify-center gap-2">
                      {/* Lápis: abre AddTransactionModal já na aba Tesouro pré-preenchido */}
                      <button
                        onClick={() => handleEdit(item)}
                        title="Adicionar novo lançamento para este título"
                        className="text-blue-500 hover:text-blue-700 p-1 rounded hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors"
                      >
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                            d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                        </svg>
                      </button>
                      {/* Lixeira: confirmação local antes de excluir */}
                      <button
                        onClick={() => setDeleteItem(item)}
                        title="Excluir"
                        className="text-red-400 hover:text-red-600 p-1 rounded hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
                      >
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                            d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {deleteItem && (
        <DeleteConfirm
          item={deleteItem}
          onConfirm={handleDelete}
          onClose={() => setDeleteItem(null)}
        />
      )}
    </div>
  )
}
