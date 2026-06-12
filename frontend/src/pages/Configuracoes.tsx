import { useState } from 'react'
import { Trash2, Plus, Pencil, Check, X, Loader2 } from 'lucide-react'
import { usePortfolios, useCreatePortfolio, useUpdatePortfolio, useDeletePortfolio } from '@/hooks/usePortfolios'
import { useAuth } from '@/contexts/AuthContext'
import AdminPanel from '@/components/admin/AdminPanel'

export default function Configuracoes() {
  const { user } = useAuth()
  const isSuperAdmin = user?.role === 'superadmin'

  const { data: portfolios = [] } = usePortfolios()
  const { mutate: createPortfolio, isPending: isCreating } = useCreatePortfolio()
  const { mutate: updatePortfolio, isPending: isUpdating } = useUpdatePortfolio()
  const { mutate: deletePortfolio, isPending: isDeleting } = useDeletePortfolio()

  const [newName,    setNewName]    = useState('')
  const [editingId,  setEditingId]  = useState<number | null>(null)
  const [editName,   setEditName]   = useState('')
  const [deletingId, setDeletingId] = useState<number | null>(null)

  // ── Criar
  const handleCreate = () => {
    if (!newName.trim()) return
    createPortfolio(
      { name: newName.trim() },
      { onSuccess: () => setNewName('') },
    )
  }

  // ── Iniciar edição inline
  const startEdit = (id: number, name: string) => {
    setEditingId(id)
    setEditName(name)
  }

  // ── Confirmar edição
  const confirmEdit = (id: number) => {
    if (!editName.trim()) return
    updatePortfolio(
      { id, name: editName.trim() },
      { onSuccess: () => setEditingId(null) },
    )
  }

  // ── Excluir — usa useMutation do React Query (invalida cache automaticamente)
  const handleDelete = (id: number, name: string) => {
    if (!confirm(`Excluir carteira "${name}"? Esta ação não pode ser desfeita.`)) return
    setDeletingId(id)
    deletePortfolio(id, {
      onSettled: () => setDeletingId(null),
    })
  }

  return (
    <div className="p-6 max-w-lg space-y-6">
      <h1 className="text-xl font-bold text-white">Configurações</h1>

      {/* ── Carteiras ── */}
      <section className="bg-gray-900 rounded-xl p-4 space-y-3">
        <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Carteiras</h2>

        <ul className="space-y-2">
          {portfolios.map((p) => (
            <li key={p.id} className="flex items-center justify-between bg-gray-800 rounded-lg px-3 py-2 gap-2">
              {editingId === p.id ? (
                /* ─ modo edição inline */
                <>
                  <input
                    value={editName}
                    onChange={e => setEditName(e.target.value)}
                    onKeyDown={e => {
                      if (e.key === 'Enter')  confirmEdit(p.id)
                      if (e.key === 'Escape') setEditingId(null)
                    }}
                    autoFocus
                    className="flex-1 bg-gray-700 text-white text-sm rounded px-2 py-1 border border-teal-600 focus:outline-none"
                  />
                  <button
                    onClick={() => confirmEdit(p.id)}
                    disabled={isUpdating}
                    className="text-teal-400 hover:text-teal-300 p-1 transition"
                    title="Salvar"
                  >
                    {isUpdating ? <Loader2 size={14} className="animate-spin" /> : <Check size={14} />}
                  </button>
                  <button
                    onClick={() => setEditingId(null)}
                    className="text-gray-500 hover:text-white p-1 transition"
                    title="Cancelar"
                  >
                    <X size={14} />
                  </button>
                </>
              ) : (
                /* ─ modo normal */
                <>
                  <span className="text-white text-sm flex-1 truncate">{p.name}</span>
                  <button
                    onClick={() => startEdit(p.id, p.name)}
                    className="text-gray-500 hover:text-teal-400 p-1 transition"
                    title="Renomear"
                  >
                    <Pencil size={14} />
                  </button>
                  <button
                    onClick={() => handleDelete(p.id, p.name)}
                    disabled={isDeleting && deletingId === p.id}
                    className="text-gray-500 hover:text-red-400 p-1 transition disabled:opacity-50"
                    title="Excluir carteira"
                  >
                    {isDeleting && deletingId === p.id
                      ? <Loader2 size={14} className="animate-spin" />
                      : <Trash2 size={14} />}
                  </button>
                </>
              )}
            </li>
          ))}

          {portfolios.length === 0 && (
            <li className="text-center text-gray-500 text-sm py-4">Nenhuma carteira cadastrada.</li>
          )}
        </ul>

        {/* Nova carteira */}
        <div className="flex gap-2">
          <input
            value={newName}
            onChange={e => setNewName(e.target.value)}
            placeholder="Nome da nova carteira"
            className="flex-1 bg-gray-800 text-white text-sm rounded-lg px-3 py-2 border border-gray-700 focus:outline-none focus:border-teal-500"
            onKeyDown={e => e.key === 'Enter' && handleCreate()}
          />
          <button
            onClick={handleCreate}
            disabled={isCreating || !newName.trim()}
            className="bg-teal-600 hover:bg-teal-500 disabled:opacity-50 text-white px-3 py-2 rounded-lg transition"
            title="Criar carteira"
          >
            {isCreating ? <Loader2 size={16} className="animate-spin" /> : <Plus size={16} />}
          </button>
        </div>
      </section>

      {/* ── Painel Admin (superadmin only) ── */}
      {isSuperAdmin && <AdminPanel />}
    </div>
  )
}
