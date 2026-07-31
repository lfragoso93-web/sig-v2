/**
 * AdminPanel — visível apenas para usuários com role === 'superadmin'
 * Seções:
 *   1. Estatísticas do sistema
 *   2. Gestão de usuários (listar, ativar/desativar, editar role, excluir, resetar senha)
 *   3. Configurações do sistema (chave/valor)
 */
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Users, Settings, BarChart2, Trash2, Power, Plus, Save,
  ChevronDown, ChevronUp, Loader2, Pencil, Check, KeyRound, BookOpen, Database,
  ShieldCheck,
} from 'lucide-react'
import api from '@/services/api'
import PasswordInput from '@/components/ui/PasswordInput'
import AuditLogsPanel from '@/components/admin/AuditLogsPanel'
import BackupPanel from '@/components/admin/BackupPanel'
import CorporateEventReviewPanel from '@/components/admin/CorporateEventReviewPanel'

// ── Types ────────────────────────────────────────────
interface AdminUser {
  id: number
  name: string
  email: string
  role: string
  is_active: boolean
  created_at: string
}

interface SystemConfig {
  key: string
  value: string
  description: string | null
  is_public: boolean
}

interface AdminStats {
  total_users: number
  version: string
  system: string
}

// ── API ─────────────────────────────────────────────
const fetchStats   = () => api.get<AdminStats>('/admin/stats').then(r => r.data)
const fetchUsers   = (page: number, search: string) =>
  api.get('/admin/users', { params: { page, page_size: 10, search: search || undefined } }).then(r => r.data)
const fetchConfigs = () => api.get<SystemConfig[]>('/admin/config').then(r => r.data)

const ROLES = ['user', 'superadmin'] as const

// ── Sub-components ──────────────────────────────────────
function SectionHeader({ icon: Icon, title, open, onToggle }: {
  icon: React.ElementType; title: string; open: boolean; onToggle: () => void
}) {
  return (
    <button onClick={onToggle} className="w-full flex items-center justify-between py-2 text-left">
      <div className="flex items-center gap-2">
        <Icon size={15} style={{ color: 'var(--color-primary)' }} />
        <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--color-text-muted)' }}>
          {title}
        </span>
      </div>
      {open
        ? <ChevronUp  size={14} style={{ color: 'var(--color-text-faint)' }} />
        : <ChevronDown size={14} style={{ color: 'var(--color-text-faint)' }} />}
    </button>
  )
}

function RoleBadge({ role }: { role: string }) {
  const colors: Record<string, { bg: string; color: string; border: string }> = {
    superadmin: { bg: 'oklch(from var(--color-purple, #a855f7) l c h / 0.15)', color: 'var(--color-purple, #a855f7)', border: 'oklch(from var(--color-purple, #a855f7) l c h / 0.4)' },
    admin:      { bg: 'oklch(from var(--color-primary) l c h / 0.15)',         color: 'var(--color-primary)',                border: 'oklch(from var(--color-primary) l c h / 0.4)' },
    user:       { bg: 'oklch(from var(--color-text-faint) l c h / 0.1)',       color: 'var(--color-text-muted)',             border: 'var(--color-border)' },
  }
  const s = colors[role] ?? colors.user
  return (
    <span
      className="text-xs px-2 py-0.5 rounded-full"
      style={{ background: s.bg, color: s.color, border: `1px solid ${s.border}` }}
    >
      {role}
    </span>
  )
}

// ── Reset password inline form ───────────────────────────
function ResetPasswordForm({ userId, onClose }: { userId: number; onClose: () => void }) {
  const [newPassword, setNewPassword] = useState('')
  const [feedback,    setFeedback]    = useState<{ msg: string; isError: boolean } | null>(null)

  const resetPassword = useMutation({
    mutationFn: () =>
      api.post(`/admin/users/${userId}/reset-password`, { new_password: newPassword }),
    onSuccess: () => {
      setFeedback({ msg: 'Senha redefinida com sucesso.', isError: false })
      setTimeout(onClose, 1500)
    },
    onError: (e: any) => {
      const detail = e?.response?.data?.detail
      setFeedback({
        msg: typeof detail === 'string' ? detail : 'Erro ao redefinir senha.',
        isError: true,
      })
    },
  })

  return (
    <div
      className="rounded-lg p-3 flex flex-col gap-2 mt-1"
      style={{ background: 'var(--color-surface-offset)', border: '1px solid var(--color-border)' }}
    >
      <p className="text-xs font-semibold" style={{ color: 'var(--color-text)' }}>Redefinir senha</p>
      <PasswordInput
        placeholder="Nova senha (mín. 8 caracteres)"
        value={newPassword}
        onChange={e => { setNewPassword(e.target.value); setFeedback(null) }}
        className="input w-full text-xs"
        style={{ fontSize: 16 }}
      />
      {feedback && (
        <p
          className="text-xs px-2 py-1.5 rounded"
          style={{
            color:      feedback.isError ? 'var(--color-error)' : 'var(--color-success)',
            background: feedback.isError
              ? 'oklch(from var(--color-error) l c h / 0.1)'
              : 'oklch(from var(--color-success) l c h / 0.1)',
          }}
        >
          {feedback.msg}
        </p>
      )}
      <div className="flex gap-2 justify-end">
        <button
          onClick={onClose}
          className="text-xs px-3 py-1.5 rounded-lg"
          style={{ color: 'var(--color-text-muted)' }}
        >Cancelar</button>
        <button
          onClick={() => resetPassword.mutate()}
          disabled={newPassword.length < 8 || resetPassword.isPending}
          className="btn btn-primary text-xs px-3 disabled:opacity-50"
          style={{ minHeight: 32 }}
        >
          {resetPassword.isPending
            ? <Loader2 size={12} className="animate-spin" />
            : <Check size={12} />}
          Confirmar
        </button>
      </div>
    </div>
  )
}

// ── Stats section ────────────────────────────────────────
function StatsSection() {
  const { data, isLoading } = useQuery({ queryKey: ['admin-stats'], queryFn: fetchStats })
  if (isLoading) return (
    <div className="py-3 text-center">
      <Loader2 size={16} className="animate-spin mx-auto" style={{ color: 'var(--color-primary)' }} />
    </div>
  )
  if (!data) return null
  return (
    <div className="grid grid-cols-2 gap-2 py-2">
      {[
        { label: 'Usuários', value: data.total_users },
        { label: 'Versão',   value: data.version },
      ].map(({ label, value }) => (
        <div key={label} className="rounded-lg p-3" style={{ background: 'var(--color-surface-offset)', border: '1px solid var(--color-divider)' }}>
          <div className="text-xs mb-1" style={{ color: 'var(--color-text-muted)' }}>{label}</div>
          <div className="text-lg font-bold" style={{ color: 'var(--color-text)' }}>{value}</div>
        </div>
      ))}
    </div>
  )
}

// ── Users section ────────────────────────────────────────
function UsersSection() {
  const qc = useQueryClient()
  const [page,            setPage]            = useState(1)
  const [search,          setSearch]          = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [editingUser,     setEditingUser]     = useState<number | null>(null)
  const [userForm,        setUserForm]        = useState({ name: '', email: '', role: 'user' })
  const [userFeedback,    setUserFeedback]    = useState<{ userId: number; msg: string; isError: boolean } | null>(null)
  // Controla qual usuário está com o form de reset aberto (null = nenhum)
  const [resettingId,     setResettingId]     = useState<number | null>(null)

  const handleSearch = (v: string) => {
    setSearch(v)
    clearTimeout((window as any)._adminSearchTimer)
    ;(window as any)._adminSearchTimer = setTimeout(() => { setDebouncedSearch(v); setPage(1) }, 400)
  }

  const { data, isLoading } = useQuery({
    queryKey: ['admin-users', page, debouncedSearch],
    queryFn:  () => fetchUsers(page, debouncedSearch),
  })

  const toggleActive = useMutation({
    mutationFn: (id: number) => api.put(`/admin/users/${id}/toggle-active`),
    onSuccess:  () => qc.invalidateQueries({ queryKey: ['admin-users'] }),
  })

  const updateUser = useMutation({
    mutationFn: ({ id, name, email, role }: { id: number; name: string; email: string; role: string }) =>
      api.put(`/admin/users/${id}`, { name, email, role }),
    onSuccess: (_res, vars) => {
      qc.invalidateQueries({ queryKey: ['admin-users'] })
      setUserFeedback({ userId: vars.id, msg: 'Usuário atualizado.', isError: false })
      setEditingUser(null)
    },
    onError: (e: any, vars) => {
      const detail = e?.response?.data?.detail
      setUserFeedback({
        userId: vars.id,
        msg: typeof detail === 'string' ? detail : 'Erro ao atualizar usuário.',
        isError: true,
      })
    },
  })

  const deleteUser = useMutation({
    mutationFn: (id: number) => api.delete(`/admin/users/${id}`),
    onSuccess:  () => qc.invalidateQueries({ queryKey: ['admin-users'] }),
  })

  // Criar usuário
  const [showCreate, setShowCreate] = useState(false)
  const [newUser,    setNewUser]    = useState({ name: '', email: '', password: '', role: 'user' })
  const createUser = useMutation({
    mutationFn: () => api.post(`/admin/users?role=${newUser.role}`, {
      name: newUser.name, email: newUser.email, password: newUser.password,
    }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admin-users'] })
      qc.invalidateQueries({ queryKey: ['admin-stats'] })
      setShowCreate(false)
      setNewUser({ name: '', email: '', password: '', role: 'user' })
    },
  })

  const users: AdminUser[] = data?.items ?? []
  const totalPages: number = data?.total_pages ?? 1

  function startEditUser(u: AdminUser) {
    setEditingUser(u.id)
    setUserForm({ name: u.name ?? '', email: u.email ?? '', role: u.role ?? 'user' })
    setUserFeedback(null)
  }

  return (
    <div className="flex flex-col gap-3 py-2">

      {/* Busca + criar */}
      <div className="flex gap-2">
        <input
          value={search}
          onChange={e => handleSearch(e.target.value)}
          placeholder="Buscar usuário..."
          className="input flex-1 text-xs"
          style={{ fontSize: 16 }}
        />
        <button
          onClick={() => setShowCreate(v => !v)}
          className="btn btn-primary px-3"
          title="Criar usuário"
          style={{ minHeight: 38 }}
        >
          <Plus size={14} />
        </button>
      </div>

      {/* Form criar usuário */}
      {showCreate && (
        <div
          className="rounded-lg p-3 flex flex-col gap-2"
          style={{ background: 'var(--color-surface-offset)', border: '1px solid var(--color-border)' }}
        >
          <p className="text-xs font-semibold" style={{ color: 'var(--color-text)' }}>Novo usuário</p>
          <input
            type="text"
            placeholder="Nome"
            value={newUser.name}
            onChange={e => setNewUser(v => ({ ...v, name: e.target.value }))}
            className="input w-full text-xs"
            style={{ fontSize: 16 }}
          />
          <input
            type="email"
            placeholder="E-mail"
            value={newUser.email}
            onChange={e => setNewUser(v => ({ ...v, email: e.target.value }))}
            className="input w-full text-xs"
            style={{ fontSize: 16 }}
          />
          <PasswordInput
            placeholder="Senha"
            value={newUser.password}
            onChange={e => setNewUser(v => ({ ...v, password: e.target.value }))}
            className="input w-full text-xs"
            style={{ fontSize: 16 }}
          />
          <select
            value={newUser.role}
            onChange={e => setNewUser(v => ({ ...v, role: e.target.value }))}
            className="input w-full text-xs"
            style={{ fontSize: 16 }}
          >
            {ROLES.map(r => <option key={r} value={r}>{r}</option>)}
          </select>
          <div className="flex gap-2 justify-end">
            <button
              onClick={() => setShowCreate(false)}
              className="text-xs px-3 py-1.5 rounded-lg"
              style={{ color: 'var(--color-text-muted)' }}
            >Cancelar</button>
            <button
              onClick={() => createUser.mutate()}
              disabled={createUser.isPending || !newUser.email || !newUser.password}
              className="btn btn-primary text-xs px-3 disabled:opacity-50"
              style={{ minHeight: 32 }}
            >
              {createUser.isPending ? <Loader2 size={12} className="animate-spin" /> : <Plus size={12} />}
              Criar
            </button>
          </div>
        </div>
      )}

      {/* Lista de usuários */}
      {isLoading ? (
        <div className="py-4 text-center">
          <Loader2 size={16} className="animate-spin mx-auto" style={{ color: 'var(--color-primary)' }} />
        </div>
      ) : (
        <ul className="flex flex-col gap-1.5">
          {users.map(u => (
            <li key={u.id} className="flex flex-col gap-0">
              <div
                className="rounded-lg px-3 py-2 flex items-center justify-between gap-2"
                style={{
                  background:  'var(--color-surface-offset)',
                  border:      '1px solid var(--color-divider)',
                  opacity:     u.is_active ? 1 : 0.5,
                  borderBottomLeftRadius:  resettingId === u.id ? 0 : undefined,
                  borderBottomRightRadius: resettingId === u.id ? 0 : undefined,
                }}
              >
                <div className="min-w-0 flex-1">
                  {editingUser === u.id && (
                    <div className="flex flex-col gap-1.5 mb-2">
                      <input
                        value={userForm.name}
                        onChange={e => setUserForm(v => ({ ...v, name: e.target.value }))}
                        className="input text-xs py-1 px-2"
                        style={{ fontSize: 13 }}
                        placeholder="Nome"
                        autoFocus
                      />
                      <input
                        type="email"
                        value={userForm.email}
                        onChange={e => setUserForm(v => ({ ...v, email: e.target.value }))}
                        className="input text-xs py-1 px-2"
                        style={{ fontSize: 13 }}
                        placeholder="E-mail"
                      />
                      <select
                        value={userForm.role}
                        onChange={e => setUserForm(v => ({ ...v, role: e.target.value }))}
                        className="input text-xs py-1 px-2"
                        style={{ fontSize: 13 }}
                      >
                        {ROLES.map(r => <option key={r} value={r}>{r}</option>)}
                      </select>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => updateUser.mutate({ id: u.id, ...userForm })}
                          disabled={updateUser.isPending || !userForm.name.trim() || !userForm.email.trim()}
                          className="btn btn-primary text-xs px-2 py-1 disabled:opacity-50"
                          style={{ minHeight: 28 }}
                        >
                          {updateUser.isPending ? <Loader2 size={12} className="animate-spin" /> : <Check size={12} />}
                          Salvar
                        </button>
                        <button
                          onClick={() => setEditingUser(null)}
                          className="text-xs px-2 py-1 rounded"
                          style={{ color: 'var(--color-text-muted)' }}
                        >
                          Cancelar
                        </button>
                      </div>
                    </div>
                  )}
                  <div
                    className="flex items-center gap-2 flex-wrap"
                    style={{ display: editingUser === u.id ? 'none' : undefined }}
                  >
                    <span className="text-xs font-medium truncate" style={{ color: 'var(--color-text)' }}>
                      {u.name || u.email}
                    </span>

                    <RoleBadge role={u.role} />

                    {!u.is_active && (
                      <span className="text-xs italic" style={{ color: 'var(--color-text-faint)' }}>inativo</span>
                    )}
                  </div>
                  {userFeedback?.userId === u.id && (
                    <div
                      className="text-xs mt-1"
                      style={{ color: userFeedback.isError ? 'var(--color-error)' : 'var(--color-success)' }}
                    >
                      {userFeedback.msg}
                    </div>
                  )}
                  <div
                    className="text-xs truncate"
                    style={{ color: 'var(--color-text-faint)', display: editingUser === u.id ? 'none' : undefined }}
                  >
                    {u.email}
                  </div>
                </div>

                <div className="flex items-center gap-1 shrink-0">
                  <button
                    onClick={() => startEditUser(u)}
                    title="Editar usuário"
                    className="p-1.5 rounded"
                    style={{ color: editingUser === u.id ? 'var(--color-primary)' : 'var(--color-text-faint)' }}
                  >
                    <Pencil size={13} />
                  </button>
                  {/* Botão reset de senha */}
                  <button
                    onClick={() => setResettingId(id => id === u.id ? null : u.id)}
                    title="Redefinir senha"
                    className="p-1.5 rounded"
                    style={{ color: resettingId === u.id ? 'var(--color-primary)' : 'var(--color-text-faint)' }}
                  >
                    <KeyRound size={13} />
                  </button>
                  <button
                    onClick={() => {
                      if (!confirm(`${u.is_active ? 'Desativar' : 'Ativar'} usuário "${u.name || u.email}"?`)) return
                      toggleActive.mutate(u.id)
                    }}
                    title={u.is_active ? 'Desativar' : 'Ativar'}
                    className="p-1.5 rounded"
                    style={{ color: 'var(--color-text-faint)' }}
                  >
                    <Power size={13} />
                  </button>
                  <button
                    onClick={() => {
                      if (!confirm(`Excluir permanentemente "${u.name || u.email}"?`)) return
                      deleteUser.mutate(u.id)
                    }}
                    title="Excluir usuário"
                    className="p-1.5 rounded"
                    style={{ color: 'var(--color-text-faint)' }}
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
              </div>

              {/* Form reset senha — expande inline abaixo do card do usuário */}
              {resettingId === u.id && (
                <div style={{ borderTop: 'none' }}>
                  <ResetPasswordForm
                    userId={u.id}
                    onClose={() => setResettingId(null)}
                  />
                </div>
              )}
            </li>
          ))}
          {users.length === 0 && (
            <li className="text-center text-xs py-4" style={{ color: 'var(--color-text-muted)' }}>
              Nenhum usuário encontrado.
            </li>
          )}
        </ul>
      )}

      {/* Paginação */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <button
            disabled={page <= 1}
            onClick={() => setPage(p => p - 1)}
            className="text-xs disabled:opacity-30"
            style={{ color: 'var(--color-text-muted)' }}
          >← Anterior</button>
          <span className="text-xs" style={{ color: 'var(--color-text-faint)' }}>{page} / {totalPages}</span>
          <button
            disabled={page >= totalPages}
            onClick={() => setPage(p => p + 1)}
            className="text-xs disabled:opacity-30"
            style={{ color: 'var(--color-text-muted)' }}
          >Próxima →</button>
        </div>
      )}
    </div>
  )
}

// ── Configs section ──────────────────────────────────────
function ConfigsSection() {
  const qc = useQueryClient()
  const { data: configs = [], isLoading } = useQuery<SystemConfig[]>({
    queryKey: ['admin-configs'],
    queryFn:  fetchConfigs,
  })

  const [edits,  setEdits]  = useState<Record<string, string>>({})
  const [saving, setSaving] = useState<string | null>(null)

  const handleEdit = (key: string, val: string) =>
    setEdits(prev => ({ ...prev, [key]: val }))

  const handleSave = async (key: string) => {
    if (edits[key] === undefined) return
    setSaving(key)
    try {
      await api.put(`/admin/config/${key}`, { value: edits[key] })
      qc.invalidateQueries({ queryKey: ['admin-configs'] })
      setEdits(prev => { const n = { ...prev }; delete n[key]; return n })
    } finally {
      setSaving(null)
    }
  }

  if (isLoading) return (
    <div className="py-3 text-center">
      <Loader2 size={16} className="animate-spin mx-auto" style={{ color: 'var(--color-primary)' }} />
    </div>
  )

  return (
    <div className="flex flex-col gap-4 py-2">
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-2 pt-1">
          <Settings size={14} style={{ color: 'var(--color-primary)' }} />
          <span className="text-xs font-semibold uppercase tracking-wide" style={{ color: 'var(--color-text-muted)' }}>
            Variáveis do sistema
          </span>
        </div>
      {configs.length === 0 && (
        <p className="text-xs text-center py-4" style={{ color: 'var(--color-text-muted)' }}>
          Nenhuma configuração cadastrada.
        </p>
      )}
      {configs.map(c => (
        <div
          key={c.key}
          className="rounded-lg p-3 flex flex-col gap-1.5"
          style={{ background: 'var(--color-surface-offset)', border: '1px solid var(--color-divider)' }}
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono" style={{ color: 'var(--color-primary)' }}>{c.key}</span>
            {c.is_public && (
              <span
                className="text-xs px-1.5 py-0.5 rounded"
                style={{ color: 'var(--color-text-faint)', border: '1px solid var(--color-border)' }}
              >pública</span>
            )}
          </div>
          {c.description && (
            <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>{c.description}</p>
          )}
          <div className="flex gap-2">
            <input
              value={edits[c.key] ?? c.value}
              onChange={e => handleEdit(c.key, e.target.value)}
              className="input flex-1 text-xs font-mono"
              style={{ fontSize: 13 }}
            />
            {edits[c.key] !== undefined && edits[c.key] !== c.value && (
              <button
                onClick={() => handleSave(c.key)}
                disabled={saving === c.key}
                title="Salvar"
                className="btn btn-primary px-2"
                style={{ minHeight: 34 }}
              >
                {saving === c.key
                  ? <Loader2 size={12} className="animate-spin" />
                  : <Save size={12} />}
              </button>
            )}
          </div>
        </div>
      ))}

      </div>

      <div className="flex flex-col gap-2 pt-2" style={{ borderTop: '1px solid var(--color-divider)' }}>
        <div className="flex items-center gap-2 pt-1">
          <Database size={14} style={{ color: 'var(--color-primary)' }} />
          <span className="text-xs font-semibold uppercase tracking-wide" style={{ color: 'var(--color-text-muted)' }}>
            Backup e restauração
          </span>
        </div>
        <BackupPanel />
      </div>
    </div>
  )
}

export default function AdminPanel() {
  const [openStats,   setOpenStats]   = useState(true)
  const [openUsers,   setOpenUsers]   = useState(true)
  const [openConfigs, setOpenConfigs] = useState(false)
  const [openAudit,   setOpenAudit]   = useState(false)
  const [openCorporateEvents, setOpenCorporateEvents] = useState(false)

  return (
    <section
      className="rounded-xl p-4 flex flex-col gap-1"
      style={{
        background: 'var(--color-surface)',
        border:     '1px solid oklch(from var(--color-primary) l c h / 0.3)',
      }}
    >
      {/* Header */}
      <div className="flex items-center gap-2 mb-2">
        <span
          className="w-2 h-2 rounded-full"
          style={{ background: 'var(--color-primary)' }}
        />
        <h2
          className="text-sm font-semibold uppercase tracking-wide"
          style={{ color: 'var(--color-primary)' }}
        >
          Painel Admin
        </h2>
      </div>

      {/* Estatísticas */}
      <div style={{ borderBottom: '1px solid var(--color-divider)', paddingBottom: 4 }}>
        <SectionHeader icon={BarChart2} title="Estatísticas" open={openStats}   onToggle={() => setOpenStats(v => !v)} />
        {openStats   && <StatsSection />}
      </div>

      {/* Usuários */}
      <div style={{ borderBottom: '1px solid var(--color-divider)', paddingBottom: 4 }}>
        <SectionHeader icon={Users}    title="Usuários"     open={openUsers}   onToggle={() => setOpenUsers(v => !v)} />
        {openUsers   && <UsersSection />}
      </div>

      {/* Configurações do sistema */}
      <div>
        <SectionHeader icon={Settings} title="Config. do sistema" open={openConfigs} onToggle={() => setOpenConfigs(v => !v)} />
        {openConfigs && <ConfigsSection />}
      </div>

      {/* Audit Logs */}
      <div style={{ borderTop: '1px solid var(--color-divider)', paddingTop: 4 }}>
        <SectionHeader
          icon={ShieldCheck}
          title="Revisão de eventos corporativos"
          open={openCorporateEvents}
          onToggle={() => setOpenCorporateEvents(value => !value)}
        />
        {openCorporateEvents && (
          <div className="mt-4 pt-4" style={{ borderTop: '1px solid var(--color-divider)' }}>
            <CorporateEventReviewPanel />
          </div>
        )}
      </div>

      {/* Audit Logs */}
      <div style={{ borderTop: '1px solid var(--color-divider)', paddingTop: 4 }}>
        <SectionHeader icon={BookOpen} title="Audit Logs" open={openAudit} onToggle={() => setOpenAudit(v => !v)} />
        {openAudit && (
          <div className="mt-4 pt-4" style={{ borderTop: '1px solid var(--color-divider)' }}>
            <AuditLogsPanel />
          </div>
        )}
      </div>
    </section>
  )
}
