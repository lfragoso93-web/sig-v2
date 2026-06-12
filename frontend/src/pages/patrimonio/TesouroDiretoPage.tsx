import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useTreasury, TreasuryItem, TreasuryUpdate } from '../../hooks/useTreasury'
import { useAppStore } from '../../store/appStore'

// ── helpers ────────────────────────────────────────────────────────────────
const fmtBRL = (v: number | null | undefined) =>
  v == null ? '—' : v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })

const fmtDate = (s: string | null | undefined) => {
  if (!s) return '—'
  const [y, m, d] = s.split('-')
  return `${d}/${m}/${y}`
}

// ── EditModal ───────────────────────────────────────────────────────────────
interface EditModalProps {
  item: TreasuryItem
  onSave: (data: TreasuryUpdate) => Promise<void>
  onClose: () => void
}

function EditModal({ item, onSave, onClose }: EditModalProps) {
  const { register, handleSubmit, formState: { isSubmitting, errors } } = useForm<TreasuryUpdate>({
    defaultValues: {
      brapi_name: item.brapi_name,
      invested_value: item.invested_value,
      purchase_date: item.purchase_date,
      maturity_date: item.maturity_date ?? undefined,
      is_active: item.is_active,
    },
  })

  const onSubmit = async (data: TreasuryUpdate) => {
    await onSave(data)
    onClose()
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end md:items-center justify-center bg-black/50">
      <div className="w-full max-w-md bg-white dark:bg-gray-900 rounded-t-2xl md:rounded-2xl p-6 shadow-xl">
        <h2 className="text-lg font-semibold mb-4 text-gray-800 dark:text-white">Editar Tesouro Direto</h2>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">

          <div>
            <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1">Título</label>
            <input
              {...register('brapi_name', { required: 'Campo obrigatório' })}
              className="w-full border rounded-lg px-3 py-2 text-sm dark:bg-gray-800 dark:border-gray-700 dark:text-white"
            />
            {errors.brapi_name && <p className="text-red-500 text-xs mt-1">{errors.brapi_name.message}</p>}
          </div>

          <div>
            <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1">Valor Investido (R$)</label>
            <input
              type="number"
              step="0.01"
              {...register('invested_value', { required: 'Campo obrigatório', valueAsNumber: true, min: { value: 0.01, message: 'Deve ser positivo' } })}
              className="w-full border rounded-lg px-3 py-2 text-sm dark:bg-gray-800 dark:border-gray-700 dark:text-white"
            />
            {errors.invested_value && <p className="text-red-500 text-xs mt-1">{errors.invested_value.message}</p>}
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1">Data de Compra</label>
              <input
                type="date"
                {...register('purchase_date', { required: 'Obrigatório' })}
                className="w-full border rounded-lg px-3 py-2 text-sm dark:bg-gray-800 dark:border-gray-700 dark:text-white"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1">Vencimento</label>
              <input
                type="date"
                {...register('maturity_date')}
                className="w-full border rounded-lg px-3 py-2 text-sm dark:bg-gray-800 dark:border-gray-700 dark:text-white"
              />
            </div>
          </div>

          <div className="flex items-center gap-2">
            <input type="checkbox" id="is_active" {...register('is_active')} className="rounded" />
            <label htmlFor="is_active" className="text-sm text-gray-700 dark:text-gray-300">Ativo</label>
          </div>

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 border rounded-lg py-2 text-sm text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800"
            >Cancelar</button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="flex-1 bg-blue-600 text-white rounded-lg py-2 text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
            >{isSubmitting ? 'Salvando...' : 'Salvar'}</button>
          </div>
        </form>
      </div>
    </div>
  )
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
  const portfolioId = useAppStore((s) => s.selectedPortfolioId)
  const { items, loading, error, update, remove } = useTreasury()

  const [editItem, setEditItem] = useState<TreasuryItem | null>(null)
  const [deleteItem, setDeleteItem] = useState<TreasuryItem | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)

  if (!portfolioId) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-gray-400">
        <p className="text-base">Selecione uma carteira para ver o Tesouro Direto.</p>
      </div>
    )
  }

  const handleUpdate = async (data: TreasuryUpdate) => {
    if (!editItem) return
    setActionError(null)
    try {
      await update(editItem.id, data)
    } catch (e: any) {
      setActionError(e?.response?.data?.detail || 'Erro ao atualizar')
      throw e
    }
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
      <h1 className="text-xl font-bold text-gray-800 dark:text-white mb-6">Tesouro Direto</h1>

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
          <p className="text-sm mt-1">Use o botão <strong>Novo Lançamento</strong> para adicionar.</p>
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
                      <button
                        onClick={() => setEditItem(item)}
                        title="Editar"
                        className="text-blue-500 hover:text-blue-700 p-1 rounded hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors"
                      >
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                            d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                        </svg>
                      </button>
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

      {editItem && (
        <EditModal
          item={editItem}
          onSave={handleUpdate}
          onClose={() => setEditItem(null)}
        />
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
