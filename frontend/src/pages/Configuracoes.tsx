import { useState, useRef, useEffect } from 'react'
import {
  Trash2, Plus, Pencil, Check, X, Loader2,
  Camera, KeyRound, UserCircle, AlertTriangle, ChevronDown, ChevronUp, Wallet,
} from 'lucide-react'
import { usePortfolios, useCreatePortfolio, useUpdatePortfolio, useDeletePortfolio } from '@/hooks/usePortfolios'
import { useAuth } from '@/contexts/AuthContext'
import { useUpdateProfile, useChangePassword, useUpdateAvatar, useDeleteAccount } from '@/hooks/useUser'
import AdminPanel from '@/components/admin/AdminPanel'
import PasswordInput from '@/components/ui/PasswordInput'

// ── Helpers ────────────────────────────────────────────

function SectionCard({ children }: { children: React.ReactNode }) {
  return (
    <section
      className="card p-5 flex flex-col gap-4"
    >
      {children}
    </section>
  )
}

function SectionTitle({ icon: Icon, children }: { icon: React.ElementType; children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-2">
      <Icon size={15} style={{ color: 'var(--color-primary)' }} />
      <h2 className="text-xs font-semibold uppercase tracking-wide" style={{ color: 'var(--color-text-muted)' }}>
        {children}
      </h2>
    </div>
  )
}

function FieldGroup({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-xs font-medium" style={{ color: 'var(--color-text-muted)' }}>{label}</label>
      {children}
    </div>
  )
}

function SaveFeedback({ msg, isError }: { msg: string; isError?: boolean }) {
  return (
    <p
      className="text-xs px-3 py-2 rounded-lg"
      style={{
        color:      isError ? 'var(--color-error)' : 'var(--color-success)',
        background: isError
          ? 'oklch(from var(--color-error) l c h / 0.1)'
          : 'oklch(from var(--color-success) l c h / 0.1)',
      }}
    >
      {msg}
    </p>
  )
}

// ── Subseção: Dados pessoais ─────────────────────────────

function ProfileSection() {
  const { user } = useAuth()
  const updateProfile = useUpdateProfile()
  const updateAvatar  = useUpdateAvatar()
  const fileRef = useRef<HTMLInputElement>(null)

  const [name,  setName]  = useState(user?.name  ?? '')
  const [email, setEmail] = useState(user?.email ?? '')
  const [feedback, setFeedback] = useState<{ msg: string; isError: boolean } | null>(null)
  const [avatarPreview, setAvatarPreview] = useState<string | null>(null)

  useEffect(() => {
    setName(user?.name  ?? '')
    setEmail(user?.email ?? '')
  }, [user?.name, user?.email])

  const dirty = name !== (user?.name ?? '') || email !== (user?.email ?? '')

  async function handleSave() {
    setFeedback(null)
    try {
      await updateProfile.mutateAsync({ name, email })
      setFeedback({ msg: 'Dados atualizados com sucesso.', isError: false })
    } catch (e: any) {
      const detail = e?.response?.data?.detail
      setFeedback({ msg: typeof detail === 'string' ? detail : 'Erro ao atualizar dados.', isError: true })
    }
  }

  function handleAvatarChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = ev => setAvatarPreview(ev.target?.result as string)
    reader.readAsDataURL(file)
    updateAvatar.mutate(file)
  }

  const avatarSrc = avatarPreview ?? user?.avatar_url

  return (
    <>
      <SectionTitle icon={UserCircle}>Minha conta</SectionTitle>

      {/* Avatar */}
      <div className="flex items-center gap-4">
        <div className="relative shrink-0">
          {avatarSrc ? (
            <img src={avatarSrc} alt="Avatar" className="w-16 h-16 rounded-full object-cover" style={{ border: '2px solid var(--color-border)' }} />
          ) : (
            <div
              className="w-16 h-16 rounded-full flex items-center justify-center text-2xl font-bold"
              style={{ background: 'oklch(from var(--color-primary) l c h / 0.15)', color: 'var(--color-primary)' }}
            >
              {(user?.name ?? user?.email ?? '?')[0].toUpperCase()}
            </div>
          )}
          <button
            onClick={() => fileRef.current?.click()}
            className="absolute -bottom-1 -right-1 w-6 h-6 rounded-full flex items-center justify-center shadow"
            style={{ background: 'var(--color-primary)', color: 'var(--color-text-inverse)', border: '2px solid var(--color-surface)' }}
            title="Alterar foto"
            disabled={updateAvatar.isPending}
          >
            {updateAvatar.isPending ? <Loader2 size={11} className="animate-spin" /> : <Camera size={11} />}
          </button>
          <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={handleAvatarChange} />
        </div>
        <div className="flex flex-col gap-0.5">
          <span className="text-sm font-semibold" style={{ color: 'var(--color-text)' }}>{user?.name || '—'}</span>
          <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>{user?.email}</span>
          <span className="text-xs mt-1 px-2 py-0.5 rounded-full self-start" style={{ background: 'oklch(from var(--color-primary) l c h / 0.12)', color: 'var(--color-primary)', fontWeight: 500 }}>
            {user?.role}
          </span>
        </div>
      </div>

      {/* Campos */}
      <div className="flex flex-col gap-3">
        <FieldGroup label="Nome">
          <input className="input" style={{ fontSize: 16 }} value={name} onChange={e => setName(e.target.value)} placeholder="Seu nome" />
        </FieldGroup>
        <FieldGroup label="E-mail">
          <input type="email" className="input" style={{ fontSize: 16 }} value={email} onChange={e => setEmail(e.target.value)} placeholder="seu@email.com" />
        </FieldGroup>
      </div>

      {feedback && <SaveFeedback msg={feedback.msg} isError={feedback.isError} />}

      <button onClick={handleSave} disabled={!dirty || updateProfile.isPending} className="btn btn-primary self-start disabled:opacity-40" style={{ minHeight: 38 }}>
        {updateProfile.isPending ? <Loader2 size={14} className="animate-spin" /> : 'Salvar dados'}
      </button>
    </>
  )
}

// ── Subseção: Alterar senha ─────────────────────────────

function PasswordSection() {
  const changePassword = useChangePassword()
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState({ current: '', next: '', confirm: '' })
  const [feedback, setFeedback] = useState<{ msg: string; isError: boolean } | null>(null)

  const set = (f: string, v: string) => setForm(p => ({ ...p, [f]: v }))

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setFeedback(null)
    if (form.next !== form.confirm) {
      setFeedback({ msg: 'As senhas não coincidem.', isError: true })
      return
    }
    if (form.next.length < 6) {
      setFeedback({ msg: 'A nova senha deve ter ao menos 6 caracteres.', isError: true })
      return
    }
    try {
      await changePassword.mutateAsync({ current_password: form.current, new_password: form.next })
      setFeedback({ msg: 'Senha alterada com sucesso.', isError: false })
      setForm({ current: '', next: '', confirm: '' })
      setTimeout(() => setOpen(false), 1500)
    } catch (e: any) {
      const detail = e?.response?.data?.detail
      setFeedback({ msg: typeof detail === 'string' ? detail : 'Senha atual incorreta.', isError: true })
    }
  }

  return (
    <SectionCard>
      <button onClick={() => setOpen(o => !o)} className="flex items-center justify-between w-full">
        <div className="flex items-center gap-2">
          <KeyRound size={15} style={{ color: 'var(--color-primary)' }} />
          <h2 className="text-xs font-semibold uppercase tracking-wide" style={{ color: 'var(--color-text-muted)' }}>Alterar senha</h2>
        </div>
        {open
          ? <ChevronUp size={14} style={{ color: 'var(--color-text-faint)' }} />
          : <ChevronDown size={14} style={{ color: 'var(--color-text-faint)' }} />}
      </button>

      {open && (
        <form onSubmit={handleSubmit} className="flex flex-col gap-3 mt-1">
          <FieldGroup label="Senha atual">
            <PasswordInput className="input w-full" style={{ fontSize: 16 }} value={form.current} onChange={e => set('current', e.target.value)} required />
          </FieldGroup>
          <FieldGroup label="Nova senha">
            <PasswordInput className="input w-full" style={{ fontSize: 16 }} value={form.next} onChange={e => set('next', e.target.value)} required />
          </FieldGroup>
          <FieldGroup label="Confirmar nova senha">
            <PasswordInput className="input w-full" style={{ fontSize: 16 }} value={form.confirm} onChange={e => set('confirm', e.target.value)} required />
          </FieldGroup>
          {feedback && <SaveFeedback msg={feedback.msg} isError={feedback.isError} />}
          <button type="submit" disabled={changePassword.isPending} className="btn btn-primary self-start disabled:opacity-40" style={{ minHeight: 38 }}>
            {changePassword.isPending ? <Loader2 size={14} className="animate-spin" /> : 'Alterar senha'}
          </button>
        </form>
      )}
    </SectionCard>
  )
}

// ── Subseção: Carteiras ──────────────────────────────────

function CarteirasSection() {
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
    <SectionCard>
      <SectionTitle icon={Wallet}>Carteiras</SectionTitle>
      <ul className="flex flex-col gap-2">
        {portfolios.map(p => (
          <li key={p.id} className="flex items-center justify-between rounded-lg px-3 py-2 gap-2" style={{ background: 'var(--color-surface-offset)', border: '1px solid var(--color-divider)' }}>
            {editingId === p.id ? (
              <>
                <input value={editName} onChange={e => setEditName(e.target.value)} onKeyDown={e => { if (e.key === 'Enter') confirmEdit(p.id); if (e.key === 'Escape') setEditingId(null) }} autoFocus className="input flex-1 text-sm" style={{ fontSize: 16 }} />
                <button onClick={() => confirmEdit(p.id)} disabled={isUpdating} className="p-1" style={{ color: 'var(--color-primary)' }} title="Salvar">
                  {isUpdating ? <Loader2 size={14} className="animate-spin" /> : <Check size={14} />}
                </button>
                <button onClick={() => setEditingId(null)} className="p-1" style={{ color: 'var(--color-text-faint)' }} title="Cancelar"><X size={14} /></button>
              </>
            ) : (
              <>
                <span className="text-sm flex-1 truncate" style={{ color: 'var(--color-text)' }}>{p.name}</span>
                <button onClick={() => startEdit(p.id, p.name)} className="p-1" style={{ color: 'var(--color-text-faint)' }} title="Renomear"><Pencil size={14} /></button>
                <button onClick={() => handleDelete(p.id, p.name)} disabled={isDeleting && deletingId === p.id} className="p-1 disabled:opacity-50" style={{ color: 'var(--color-text-faint)' }} title="Excluir carteira">
                  {isDeleting && deletingId === p.id ? <Loader2 size={14} className="animate-spin" /> : <Trash2 size={14} />}
                </button>
              </>
            )}
          </li>
        ))}
        {portfolios.length === 0 && (
          <li className="text-center text-sm py-4" style={{ color: 'var(--color-text-muted)' }}>Nenhuma carteira cadastrada.</li>
        )}
      </ul>
      <div className="flex gap-2">
        <input value={newName} onChange={e => setNewName(e.target.value)} placeholder="Nome da nova carteira" className="input flex-1 text-sm" style={{ fontSize: 16 }} onKeyDown={e => e.key === 'Enter' && handleCreate()} />
        <button onClick={handleCreate} disabled={isCreating || !newName.trim()} className="btn btn-primary px-3 disabled:opacity-50" title="Criar carteira">
          {isCreating ? <Loader2 size={16} className="animate-spin" /> : <Plus size={16} />}
        </button>
      </div>
    </SectionCard>
  )
}

// ── Zona de perigo ───────────────────────────────────────

function DangerZone() {
  const { user } = useAuth()
  const deleteAccount = useDeleteAccount()
  const [open,    setOpen]    = useState(false)
  const [confirm, setConfirm] = useState('')
  const [error,   setError]   = useState<string | null>(null)

  async function handleDelete() {
    if (confirm !== user?.email) {
      setError('O e-mail digitado não confere.')
      return
    }
    try {
      await deleteAccount.mutateAsync()
    } catch {
      setError('Erro ao excluir conta. Tente novamente.')
    }
  }

  return (
    <section className="card p-5 flex flex-col gap-4" style={{ border: '1px solid oklch(from var(--color-error) l c h / 0.3)', background: 'oklch(from var(--color-error) l c h / 0.04)' }}>
      <button onClick={() => setOpen(o => !o)} className="flex items-center justify-between w-full">
        <div className="flex items-center gap-2">
          <AlertTriangle size={15} style={{ color: 'var(--color-error)' }} />
          <h2 className="text-xs font-semibold uppercase tracking-wide" style={{ color: 'var(--color-error)' }}>Zona de perigo</h2>
        </div>
        {open ? <ChevronUp size={14} style={{ color: 'var(--color-error)' }} /> : <ChevronDown size={14} style={{ color: 'var(--color-error)' }} />}
      </button>
      {open && (
        <div className="flex flex-col gap-3">
          <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
            A exclusão da conta é <strong style={{ color: 'var(--color-error)' }}>permanente e irreversível</strong>.
            Todos os seus dados, carteiras e histórico serão apagados.
          </p>
          <FieldGroup label={`Digite seu e-mail (${user?.email}) para confirmar`}>
            <input type="email" className="input" style={{ fontSize: 16 }} placeholder={user?.email} value={confirm} onChange={e => { setConfirm(e.target.value); setError(null) }} />
          </FieldGroup>
          {error && <SaveFeedback msg={error} isError />}
          <button onClick={handleDelete} disabled={confirm !== user?.email || deleteAccount.isPending} className="btn self-start disabled:opacity-40" style={{ background: 'var(--color-error)', color: '#fff', minHeight: 38 }}>
            {deleteAccount.isPending ? <Loader2 size={14} className="animate-spin" /> : 'Excluir minha conta'}
          </button>
        </div>
      )}
    </section>
  )
}

// ── Página principal ───────────────────────────────────────

export default function Configuracoes() {
  const { user } = useAuth()
  const isSuperAdmin = user?.role === 'superadmin'

  return (
    <div className="page-container max-w-2xl pb-24">
      <div className="page-header">
        <div>
          <h1 className="page-title">Configurações</h1>
          <p className="page-subtitle">Gerencie seu perfil e carteiras</p>
        </div>
      </div>
      <SectionCard><ProfileSection /></SectionCard>
      <PasswordSection />
      <CarteirasSection />
      {isSuperAdmin && <AdminPanel />}
      <DangerZone />
    </div>
  )
}
