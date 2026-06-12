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

  const handleCreate = () => {
    if (!newName.trim()) return
    createPortfolio({ name: newName.trim() }, { onSuccess: () => setNewName('') })
  }

  const startEdit = (id: number, name: string) => { setEditingId(id); setEditName(name) }

  const confirmEdit = (id: number) => {
    if (!editName.trim()) return
    updatePortfolio({ id, name: editName.trim() }, { onSuccess: () => setEditingId(null) })
  }

  const handleDelete = (id: number, name: string) => {
    if (!confirm(`Excluir carteira "${name}"? Esta ação não pode ser desfeita.`)) return
    setDeletingId(id)
    deletePortfolio(id, { onSettled: () => setDeletingId(null) })
  }

  return (
    <div className="p-6 max-w-lg space-y-6">
      <h1 className="text-xl font-bold">Configurações</h1>

      {/* Carteiras */}
      <section
        className="rounded-xl p-4 space-y-3"
        style={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)' }}
      >
        <h2
          className="text-xs font-semibold uppercase tracking-wide"
          style={{ color: 'var(--color-text-muted)' }}
        >
          Carteiras
        </h2>

        <ul className="space-y-2">
          {portfolios.map((p) => (
            <li
              key={p.id}
              className="flex items-center justify-between rounded-lg px-3 py-2 gap-2"
              style={{ background: 'var(--color-surface-offset)', border: '1px solid var(--color-divider)' }}
            >
              {editingId === p.id ? (
                <>
                  <input
                    value={editName}
                    onChange={e => setEditName(e.target.value)}
                    onKeyDown={e => {
                      if (e.key === 'Enter')  confirmEdit(p.id)
                      if (e.key === 'Escape') setEditingId(null)
                    }}
                    autoFocus
                    className="input flex-1 text-sm"
                  />
                  <button
                    onClick={() => confirmEdit(p.id)}
                    disabled={isUpdating}
                    className="p-1 transition"
                    style={{ color: 'var(--color-primary)' }}
                    title="Salvar"
                  >
                    {isUpdating ? <Loader2 size={14} className="animate-spin" /> : <Check size={14} />}
                  </button>
                  <button
                    onClick={() => setEditingId(null)}
                    className="p-1 transition"
                    style={{ color: 'var(--color-text-faint)' }}
                    title="Cancelar"
                  >
                    <X size={14} />
                  </button>
                </>
              ) : (
                <>
                  <span className="text-sm flex-1 truncate" style={{ color: 'var(--color-text)' }}>{p.name}</span>
                  <button
                    onClick={() => startEdit(p.id, p.name)}
                    className="p-1 transition"
                    style={{ color: 'var(--color-text-faint)' }}
                    onMouseEnter={e => (e.currentTarget.style.color = 'var(--color-primary)')}
                    onMouseLeave={e => (e.currentTarget.style.color = 'var(--color-text-faint)')}
                    title="Renomear"
                  >
                    <Pencil size={14} />
                  </button>
                  <button
                    onClick={() => handleDelete(p.id, p.name)}
                    disabled={isDeleting && deletingId === p.id}
                    className="p-1 transition disabled:opacity-50"
                    style={{ color: 'var(--color-text-faint)' }}
                    onMouseEnter={e => (e.currentTarget.style.color = 'var(--color-error)')}
                    onMouseLeave={e => (e.currentTarget.style.color = 'var(--color-text-faint)')}
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
            <li className="text-center text-sm py-4" style={{ color: 'var(--color-text-muted)' }}>
              Nenhuma carteira cadastrada.
            </li>
          )}
        </ul>

        {/* Nova carteira */}
        <div className="flex gap-2">
          <input
            value={newName}
            onChange={e => setNewName(e.target.value)}
            placeholder="Nome da nova carteira"
            className="input flex-1 text-sm"
            onKeyDown={e => e.key === 'Enter' && handleCreate()}
          />
          <button
            onClick={handleCreate}
            disabled={isCreating || !newName.trim()}
            className="btn btn-primary px-3 py-2 disabled:opacity-50"
            title="Criar carteira"
          >
            {isCreating ? <Loader2 size={16} className="animate-spin" /> : <Plus size={16} />}
          </button>
        </div>
      </section>

      {isSuperAdmin && <AdminPanel />}
    </div>
  )
}
