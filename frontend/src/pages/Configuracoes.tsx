import { useState } from 'react'
import { useAuthStore } from '@/store/authStore'
import { useAppStore } from '@/store/appStore'
import { usePortfolios, useCreatePortfolio, useDeletePortfolio } from '@/hooks/usePortfolios'
import { Plus, Trash2, Moon, Sun, User, Briefcase } from 'lucide-react'

export default function Configuracoes() {
  const { user, logout } = useAuthStore()
  const { theme, setTheme } = useAppStore()
  const { data: portfolios = [] } = usePortfolios()
  const createPortfolio = useCreatePortfolio()
  const deletePortfolio = useDeletePortfolio()

  const [newName, setNewName]         = useState('')
  const [newDesc, setNewDesc]         = useState('')
  const [creating, setCreating]       = useState(false)
  const [confirmDel, setConfirmDel]   = useState<number | null>(null)
  const [deleting, setDeleting]       = useState(false)

  async function handleCreatePortfolio(e: React.FormEvent) {
    e.preventDefault()
    if (!newName.trim()) return
    setCreating(true)
    try {
      await createPortfolio.mutateAsync({ name: newName.trim(), description: newDesc.trim() || undefined })
      setNewName('')
      setNewDesc('')
    } finally {
      setCreating(false)
    }
  }

  async function handleDelete(id: number) {
    setDeleting(true)
    try {
      await deletePortfolio.mutateAsync(id)
      setConfirmDel(null)
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div className="flex flex-col gap-8 max-w-2xl">
      <div>
        <h1 className="text-xl font-bold">Configurações</h1>
        <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>Preferências e gestão de carteiras</p>
      </div>

      {/* Perfil */}
      <section className="bg-surface border border-[var(--color-border)] rounded-xl p-5 flex flex-col gap-4">
        <div className="flex items-center gap-2 mb-1">
          <User size={15} style={{ color: 'var(--color-primary)' }} />
          <h2 className="text-sm font-semibold">Perfil</h2>
        </div>
        <div className="flex items-center gap-4">
          <div
            className="w-12 h-12 rounded-full flex items-center justify-center text-lg font-bold"
            style={{ background: 'var(--color-primary-highlight)', color: 'var(--color-primary)' }}
          >
            {user?.name?.[0]?.toUpperCase() ?? 'U'}
          </div>
          <div>
            <p className="font-semibold text-sm">{user?.name ?? 'Usuário'}</p>
            <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>{user?.email}</p>
          </div>
        </div>
        <div className="pt-2 border-t border-[var(--color-divider)]">
          <button
            className="btn text-sm"
            style={{ color: 'var(--color-notification)', background: 'oklch(from var(--color-notification) l c h / 0.08)' }}
            onClick={logout}
          >
            Sair da conta
          </button>
        </div>
      </section>

      {/* Tema */}
      <section className="bg-surface border border-[var(--color-border)] rounded-xl p-5 flex flex-col gap-3">
        <div className="flex items-center gap-2 mb-1">
          <Sun size={15} style={{ color: 'var(--color-primary)' }} />
          <h2 className="text-sm font-semibold">Tema</h2>
        </div>
        <div className="flex gap-2">
          {(['light', 'dark', 'system'] as const).map(t => (
            <button
              key={t}
              onClick={() => setTheme(t)}
              className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium border transition-colors"
              style={{
                background: theme === t ? 'oklch(from var(--color-primary) l c h / 0.12)' : 'var(--color-surface-offset)',
                color: theme === t ? 'var(--color-primary)' : 'var(--color-text-muted)',
                borderColor: theme === t ? 'var(--color-primary)' : 'var(--color-border)',
              }}
            >
              {t === 'light' ? <Sun size={14} /> : t === 'dark' ? <Moon size={14} /> : null}
              {t === 'light' ? 'Claro' : t === 'dark' ? 'Escuro' : 'Sistema'}
            </button>
          ))}
        </div>
      </section>

      {/* Carteiras */}
      <section className="bg-surface border border-[var(--color-border)] rounded-xl p-5 flex flex-col gap-4">
        <div className="flex items-center gap-2 mb-1">
          <Briefcase size={15} style={{ color: 'var(--color-primary)' }} />
          <h2 className="text-sm font-semibold">Minhas carteiras</h2>
        </div>

        {/* Lista */}
        <div className="flex flex-col gap-2">
          {portfolios.length === 0 ? (
            <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>Nenhuma carteira criada.</p>
          ) : portfolios.map(p => (
            <div
              key={p.id}
              className="flex items-center justify-between px-4 py-3 rounded-lg border"
              style={{ background: 'var(--color-surface-offset)', borderColor: 'var(--color-border)' }}
            >
              <div>
                <p className="text-sm font-medium">{p.name}</p>
                {p.description && (
                  <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>{p.description}</p>
                )}
              </div>
              <button
                onClick={() => setConfirmDel(p.id)}
                className="btn btn-ghost p-1 rounded"
                style={{ color: 'var(--color-text-faint)' }}
                aria-label="Excluir carteira"
              >
                <Trash2 size={14} />
              </button>
            </div>
          ))}
        </div>

        {/* Criar nova */}
        <form onSubmit={handleCreatePortfolio} className="flex flex-col gap-2 pt-2 border-t border-[var(--color-divider)]">
          <p className="text-xs font-semibold" style={{ color: 'var(--color-text-muted)' }}>Nova carteira</p>
          <div className="flex gap-2">
            <input
              className="input flex-1 text-sm"
              placeholder="Nome da carteira"
              value={newName}
              onChange={e => setNewName(e.target.value)}
              required
            />
            <input
              className="input flex-1 text-sm"
              placeholder="Descrição (opcional)"
              value={newDesc}
              onChange={e => setNewDesc(e.target.value)}
            />
            <button
              type="submit"
              className="btn btn-primary flex items-center gap-1 text-sm"
              disabled={creating || !newName.trim()}
            >
              <Plus size={14} />{creating ? '...' : 'Criar'}
            </button>
          </div>
        </form>
      </section>

      {/* Modal confirm delete */}
      {confirmDel !== null && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center px-4"
          style={{ background: 'oklch(0 0 0 / 0.45)' }}
        >
          <div
            className="w-full max-w-sm rounded-xl border p-6"
            style={{ background: 'var(--color-surface)', borderColor: 'var(--color-border)', boxShadow: 'var(--shadow-lg)' }}
          >
            <h2 className="text-base font-semibold mb-2">Excluir carteira?</h2>
            <p className="text-sm mb-6" style={{ color: 'var(--color-text-muted)' }}>
              Todos os ativos, transações e proventos desta carteira serão removidos permanentemente.
            </p>
            <div className="flex justify-end gap-2">
              <button className="btn btn-secondary" onClick={() => setConfirmDel(null)} disabled={deleting}>Cancelar</button>
              <button
                className="btn"
                style={{ background: 'var(--color-notification)', color: '#fff' }}
                onClick={() => handleDelete(confirmDel)}
                disabled={deleting}
              >
                {deleting ? 'Excluindo...' : 'Excluir'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
