/**
 * AdminPanel — visível apenas para usuários com role === 'superadmin'
 * Seções independentes em cards separados para organização visual limpa:
 *   1. Estatísticas do sistema
 *   2. Gestão de usuários
 *   3. Configurações do sistema e Backup
 *   4. Provedores de Mercado
 *   5. Central de Bootstrap
 *   6. Audit Logs
 */
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Users, Settings, BarChart2, Trash2, Power, Plus, Save,
  ChevronDown, ChevronUp, Loader2, Pencil, Check, KeyRound, BookOpen, Database, Server, Zap, Mail, Send, AlertTriangle, CheckCircle2,
} from 'lucide-react'
import api from '@/services/api'
import PasswordInput from '@/components/ui/PasswordInput'
import AuditLogsPanel from '@/components/admin/AuditLogsPanel'
import BackupPanel from '@/components/admin/BackupPanel'
import ProviderConfigPanel from '@/components/admin/ProviderConfigPanel'
import BootstrapPanel from '@/components/admin/BootstrapPanel'
import { isStrongPassword } from '@/utils/passwordPolicy'

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

interface SmtpStatus {
  configured: boolean
  mode: 'live' | 'simulation'
  host: string
  port: number
  use_tls: boolean
  smtp_user_masked: string | null
  from_email: string
  from_name: string
}

interface SmtpTestResult {
  ok: boolean
  simulated: boolean
  to_email: string
  host: string
  port: number
  duration_ms: number
  message: string
  error: string | null
}

// ── API ─────────────────────────────────────────────
const fetchStats      = () => api.get<AdminStats>('/admin/stats').then(r => r.data)
const fetchUsers      = (page: number, search: string) =>
  api.get('/admin/users', { params: { page, page_size: 10, search: search || undefined } }).then(r => r.data)
const fetchConfigs    = () => api.get<SystemConfig[]>('/admin/config').then(r => r.data)
const fetchSmtpStatus = () => api.get<SmtpStatus>('/admin/smtp/status').then(r => r.data)

const ROLES = ['user', 'superadmin'] as const

// ── Sub-components ──────────────────────────────────────
function AdminSectionCard({
  icon: Icon,
  title,
  subtitle,
  open,
  onToggle,
  children,
}: {
  icon: React.ElementType
  title: string
  subtitle: string
  open: boolean
  onToggle: () => void
  children: React.ReactNode
}) {
  return (
    <section className="card settings-card">
      <button
        type="button"
        onClick={onToggle}
        className="settings-card-header-interactive"
        style={{
          borderBottom: open ? '1px solid oklch(from var(--color-text) l c h / 0.07)' : 'none',
        }}
      >
        <div className="flex items-center gap-3 min-w-0">
          <span className="settings-card-icon" aria-hidden="true">
            <Icon size={15} strokeWidth={2} />
          </span>
          <div className="min-w-0">
            <h3 className="text-sm font-semibold leading-tight" style={{ color: 'var(--color-text)' }}>
              {title}
            </h3>
            <p className="text-xs mt-0.5 leading-snug" style={{ color: 'var(--color-text-muted)' }}>
              {subtitle}
            </p>
          </div>
        </div>
        {open
          ? <ChevronUp size={15} style={{ color: 'var(--color-text-muted)', flexShrink: 0 }} />
          : <ChevronDown size={15} style={{ color: 'var(--color-text-muted)', flexShrink: 0 }} />}
      </button>
      {open && <div className="settings-card-body">{children}</div>}
    </section>
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
        placeholder="Nova senha (min. 10 caracteres)"
        value={newPassword}
        onChange={e => { setNewPassword(e.target.value); setFeedback(null) }}
        className="input w-full text-xs"
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
          disabled={!isStrongPassword(newPassword) || resetPassword.isPending}
          className="btn btn-primary text-xs px-3 disabled:opacity-50"
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
    <div className="grid grid-cols-2 gap-3">
      {[
        { label: 'Usuários Cadastrados', value: data.total_users },
        { label: 'Versão do Sistema',   value: data.version },
      ].map(({ label, value }) => (
        <div key={label} className="rounded-lg p-3.5" style={{ background: 'var(--color-surface-offset)', border: '1px solid var(--color-divider)' }}>
          <div className="text-xs mb-1" style={{ color: 'var(--color-text-muted)' }}>{label}</div>
          <div className="text-base font-bold tabular-nums" style={{ color: 'var(--color-text)' }}>{value}</div>
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
    <div className="flex flex-col gap-3">
      <div className="flex gap-2">
        <input
          value={search}
          onChange={e => handleSearch(e.target.value)}
          placeholder="Buscar usuário..."
          className="input flex-1 text-xs"
        />
        <button
          onClick={() => setShowCreate(v => !v)}
          className="btn btn-primary px-3"
          title="Criar usuário"
        >
          <Plus size={14} />
        </button>
      </div>

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
          />
          <input
            type="email"
            placeholder="E-mail"
            value={newUser.email}
            onChange={e => setNewUser(v => ({ ...v, email: e.target.value }))}
            className="input w-full text-xs"
          />
          <PasswordInput
            placeholder="Senha forte (min. 10 caracteres)"
            value={newUser.password}
            onChange={e => setNewUser(v => ({ ...v, password: e.target.value }))}
            className="input w-full text-xs"
          />
          <select
            value={newUser.role}
            onChange={e => setNewUser(v => ({ ...v, role: e.target.value }))}
            className="select-modern w-full"
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
              disabled={createUser.isPending || !newUser.email || !isStrongPassword(newUser.password)}
              className="btn btn-primary text-xs px-3 disabled:opacity-50"
            >
              {createUser.isPending ? <Loader2 size={12} className="animate-spin" /> : <Plus size={12} />}
              Criar
            </button>
          </div>
        </div>
      )}

      {isLoading ? (
        <div className="py-4 text-center">
          <Loader2 size={16} className="animate-spin mx-auto" style={{ color: 'var(--color-primary)' }} />
        </div>
      ) : (
        <ul className="flex flex-col gap-2">
          {users.map(u => (
            <li key={u.id} className="flex flex-col gap-0">
              <div
                className="rounded-lg px-3.5 py-2.5 flex items-center justify-between gap-2"
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
                        placeholder="Nome"
                        autoFocus
                      />
                      <input
                        type="email"
                        value={userForm.email}
                        onChange={e => setUserForm(v => ({ ...v, email: e.target.value }))}
                        className="input text-xs py-1 px-2"
                        placeholder="E-mail"
                      />
                      <select
                        value={userForm.role}
                        onChange={e => setUserForm(v => ({ ...v, role: e.target.value }))}
                        className="select-modern w-full"
                      >
                        {ROLES.map(r => <option key={r} value={r}>{r}</option>)}
                      </select>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => updateUser.mutate({ id: u.id, ...userForm })}
                          disabled={updateUser.isPending || !userForm.name.trim() || !userForm.email.trim()}
                          className="btn btn-primary text-xs px-2 py-1 disabled:opacity-50"
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
                    className="settings-icon-button"
                    style={{ color: editingUser === u.id ? 'var(--color-primary)' : 'var(--color-text-muted)' }}
                  >
                    <Pencil size={13} />
                  </button>
                  <button
                    onClick={() => setResettingId(id => id === u.id ? null : u.id)}
                    title="Redefinir senha"
                    className="settings-icon-button"
                    style={{ color: resettingId === u.id ? 'var(--color-primary)' : 'var(--color-text-muted)' }}
                  >
                    <KeyRound size={13} />
                  </button>
                  <button
                    onClick={() => {
                      if (!confirm(`${u.is_active ? 'Desativar' : 'Ativar'} usuário "${u.name || u.email}"?`)) return
                      toggleActive.mutate(u.id)
                    }}
                    title={u.is_active ? 'Desativar' : 'Ativar'}
                    className="settings-icon-button"
                    style={{ color: 'var(--color-text-muted)' }}
                  >
                    <Power size={13} />
                  </button>
                  <button
                    onClick={() => {
                      if (!confirm(`Excluir permanentemente "${u.name || u.email}"?`)) return
                      deleteUser.mutate(u.id)
                    }}
                    title="Excluir usuário"
                    className="settings-icon-button"
                    style={{ color: 'var(--color-text-muted)' }}
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
              </div>

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

// ── SMTP Diagnostic & Test section ───────────────────────
function SmtpTestSection() {
  const { data: smtpStatus, isLoading } = useQuery<SmtpStatus>({
    queryKey: ['admin-smtp-status'],
    queryFn:  fetchSmtpStatus,
  })
  const [toEmail,    setToEmail]    = useState('')
  const [testResult, setTestResult] = useState<SmtpTestResult | null>(null)
  const [reqError,   setReqError]   = useState<string | null>(null)
  const [divResult,  setDivResult]  = useState<string | null>(null)

  const testSmtp = useMutation({
    mutationFn: (email: string) =>
      api.post<SmtpTestResult>('/admin/smtp/test', { to_email: email }).then(r => r.data),
    onSuccess: (res) => {
      setTestResult(res)
      setReqError(null)
    },
    onError: (err: any) => {
      const detail = err?.response?.data?.detail
      setTestResult(null)
      setReqError(typeof detail === 'string' ? detail : 'Informe um e-mail válido para realizar o teste.')
    },
  })

  const notifyDividends = useMutation({
    mutationFn: () =>
      api.post<{
        payment_date: string
        users_checked: number
        users_with_payments: number
        emails_sent: number
        skipped_already_sent: number
        errors: number
      }>('/admin/smtp/notify-dividends?force=true').then(r => r.data),
    onSuccess: (res) => {
      setDivResult(
        `Verificação concluída (${res.payment_date}): ${res.users_checked} usuários verificados, ` +
        `${res.users_with_payments} com proventos hoje, ${res.emails_sent} e-mail(s) enviado(s).`,
      )
    },
    onError: () => {
      setDivResult('Erro ao executar verificação de proventos do dia.')
    },
  })

  if (isLoading) {
    return (
      <div className="py-2 text-center">
        <Loader2 size={14} className="animate-spin mx-auto" style={{ color: 'var(--color-primary)' }} />
      </div>
    )
  }

  return (
    <div
      className="rounded-lg p-3.5 flex flex-col gap-3"
      style={{ background: 'var(--color-surface-offset)', border: '1px solid var(--color-divider)' }}
    >
      {smtpStatus && (
        <div className="flex flex-col gap-2">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <span className="text-xs font-medium" style={{ color: 'var(--color-text)' }}>
              Status do servidor SMTP
            </span>
            <span
              className="text-xs px-2 py-0.5 rounded-full font-semibold"
              style={{
                background: smtpStatus.configured
                  ? 'oklch(from var(--color-success) l c h / 0.14)'
                  : 'oklch(from var(--color-warning, #f59e0b) l c h / 0.14)',
                color: smtpStatus.configured
                  ? 'var(--color-success)'
                  : 'var(--color-warning, #f59e0b)',
                border: `1px solid ${
                  smtpStatus.configured
                    ? 'oklch(from var(--color-success) l c h / 0.35)'
                    : 'oklch(from var(--color-warning, #f59e0b) l c h / 0.35)'
                }`,
              }}
            >
              {smtpStatus.configured ? 'Ativo (Disparo Real)' : 'Modo Simulação (Sem credenciais)'}
            </span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs">
            <div className="rounded px-2.5 py-1.5" style={{ background: 'var(--color-surface)', border: '1px solid var(--color-divider)' }}>
              <div style={{ color: 'var(--color-text-faint)' }}>Host / Porta</div>
              <div className="font-mono truncate" style={{ color: 'var(--color-text)' }}>
                {smtpStatus.host}:{smtpStatus.port} {smtpStatus.use_tls ? '(TLS)' : ''}
              </div>
            </div>
            <div className="rounded px-2.5 py-1.5" style={{ background: 'var(--color-surface)', border: '1px solid var(--color-divider)' }}>
              <div style={{ color: 'var(--color-text-faint)' }}>Usuário SMTP</div>
              <div className="font-mono truncate" style={{ color: 'var(--color-text)' }}>
                {smtpStatus.smtp_user_masked ?? 'Não configurado'}
              </div>
            </div>
            <div className="rounded px-2.5 py-1.5" style={{ background: 'var(--color-surface)', border: '1px solid var(--color-divider)' }}>
              <div style={{ color: 'var(--color-text-faint)' }}>Remetente</div>
              <div className="truncate" style={{ color: 'var(--color-text)' }} title={`${smtpStatus.from_name} <${smtpStatus.from_email}>`}>
                {smtpStatus.from_name} &lt;{smtpStatus.from_email}&gt;
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="flex flex-col sm:flex-row gap-2">
        <input
          type="email"
          placeholder="Digite o e-mail de destino para o teste..."
          value={toEmail}
          onChange={e => { setToEmail(e.target.value); setReqError(null) }}
          onKeyDown={e => {
            if (e.key === 'Enter' && toEmail.trim()) {
              e.preventDefault()
              testSmtp.mutate(toEmail.trim())
            }
          }}
          className="input flex-1 text-xs"
        />
        <button
          type="button"
          onClick={() => testSmtp.mutate(toEmail.trim())}
          disabled={testSmtp.isPending || !toEmail.trim()}
          className="btn btn-primary text-xs px-3 py-1.5 flex items-center justify-center gap-1.5 shrink-0 disabled:opacity-50"
        >
          {testSmtp.isPending ? <Loader2 size={13} className="animate-spin" /> : <Send size={13} />}
          Enviar e-mail de teste
        </button>
      </div>

      <div
        className="rounded-lg p-2.5 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs"
        style={{ background: 'var(--color-surface)', border: '1px solid var(--color-divider)' }}
      >
        <div className="min-w-0">
          <div className="font-semibold" style={{ color: 'var(--color-text)' }}>
            Gatilhos automáticos ativos
          </div>
          <div style={{ color: 'var(--color-text-muted)' }}>
            Boas-vindas · Reset e alteração de senha · Status e exclusão de conta · Proventos do dia (08:30)
          </div>
        </div>
        <button
          type="button"
          onClick={() => notifyDividends.mutate()}
          disabled={notifyDividends.isPending}
          className="text-xs px-2.5 py-1.5 rounded-lg font-medium shrink-0 inline-flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
          style={{
            background: 'var(--color-surface-offset)',
            border: '1px solid var(--color-border)',
            color: 'var(--color-text)',
          }}
        >
          {notifyDividends.isPending ? <Loader2 size={12} className="animate-spin" /> : <Mail size={12} />}
          Disparar proventos de hoje
        </button>
      </div>

      {divResult && (
        <div
          className="rounded-lg px-3 py-2 text-xs"
          style={{
            background: 'oklch(from var(--color-primary) l c h / 0.1)',
            border: '1px solid oklch(from var(--color-primary) l c h / 0.25)',
            color: 'var(--color-text)',
          }}
        >
          {divResult}
        </div>
      )}

      {reqError && (
        <div
          className="rounded-lg px-3 py-2 text-xs flex items-start gap-2"
          style={{
            background: 'oklch(from var(--color-error) l c h / 0.1)',
            border: '1px solid oklch(from var(--color-error) l c h / 0.3)',
            color: 'var(--color-error)',
          }}
        >
          <AlertTriangle size={14} className="shrink-0 mt-0.5" />
          <span>{reqError}</span>
        </div>
      )}

      {testResult && (
        <div
          className="rounded-lg px-3 py-2.5 text-xs flex flex-col gap-1"
          style={{
            background: testResult.ok
              ? 'oklch(from var(--color-success) l c h / 0.1)'
              : 'oklch(from var(--color-error) l c h / 0.1)',
            border: `1px solid ${
              testResult.ok
                ? 'oklch(from var(--color-success) l c h / 0.3)'
                : 'oklch(from var(--color-error) l c h / 0.3)'
            }`,
            color: testResult.ok ? 'var(--color-success)' : 'var(--color-error)',
          }}
        >
          <div className="flex items-center gap-1.5 font-semibold">
            {testResult.ok ? <CheckCircle2 size={14} /> : <AlertTriangle size={14} />}
            <span>{testResult.message}</span>
          </div>
          {testResult.error && (
            <div className="font-mono text-[11px] opacity-90 break-all pl-5">
              Detalhe técnico: {testResult.error}
            </div>
          )}
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
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-2.5">
        <div className="flex items-center gap-2">
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
              />
              {edits[c.key] !== undefined && edits[c.key] !== c.value && (
                <button
                  onClick={() => handleSave(c.key)}
                  disabled={saving === c.key}
                  title="Salvar"
                  className="btn btn-primary px-2.5"
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

      <div className="flex flex-col gap-2.5 pt-3" style={{ borderTop: '1px solid var(--color-divider)' }}>
        <div className="flex items-center gap-2">
          <Mail size={14} style={{ color: 'var(--color-primary)' }} />
          <span className="text-xs font-semibold uppercase tracking-wide" style={{ color: 'var(--color-text-muted)' }}>
            Diagnóstico e Teste de E-mail (SMTP)
          </span>
        </div>
        <SmtpTestSection />
      </div>

      <div className="flex flex-col gap-2.5 pt-3" style={{ borderTop: '1px solid var(--color-divider)' }}>
        <div className="flex items-center gap-2">
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
  const [openStats,     setOpenStats]     = useState(true)
  const [openUsers,     setOpenUsers]     = useState(true)
  const [openConfigs,   setOpenConfigs]   = useState(false)
  const [openProviders, setOpenProviders] = useState(false)
  const [openBootstrap, setOpenBootstrap] = useState(false)
  const [openAudit,     setOpenAudit]     = useState(false)

  return (
    <div className="settings-stack">
      <AdminSectionCard
        icon={BarChart2}
        title="Estatísticas do Sistema"
        subtitle="Visão geral de usuários ativos e versão em execução"
        open={openStats}
        onToggle={() => setOpenStats(v => !v)}
      >
        <StatsSection />
      </AdminSectionCard>

      <AdminSectionCard
        icon={Users}
        title="Gestão de Usuários"
        subtitle="Controle de contas, permissões de acesso e redefinição de senhas"
        open={openUsers}
        onToggle={() => setOpenUsers(v => !v)}
      >
        <UsersSection />
      </AdminSectionCard>

      <AdminSectionCard
        icon={Settings}
        title="Configurações do Sistema e Backup"
        subtitle="Parâmetros operacionais globais e cópias de segurança do banco"
        open={openConfigs}
        onToggle={() => setOpenConfigs(v => !v)}
      >
        <ConfigsSection />
      </AdminSectionCard>

      <AdminSectionCard
        icon={Server}
        title="Provedores de Mercado"
        subtitle="Credenciais, prioridade e status dos provedores de cotações e eventos"
        open={openProviders}
        onToggle={() => setOpenProviders(v => !v)}
      >
        <ProviderConfigPanel />
      </AdminSectionCard>

      <AdminSectionCard
        icon={Zap}
        title="Central de Bootstrap"
        subtitle="Sincronização inicial de catálogo, cotações históricas e dividendos"
        open={openBootstrap}
        onToggle={() => setOpenBootstrap(v => !v)}
      >
        <BootstrapPanel />
      </AdminSectionCard>

      <AdminSectionCard
        icon={BookOpen}
        title="Audit Logs"
        subtitle="Trilha de auditoria administrativa e eventos críticos do sistema"
        open={openAudit}
        onToggle={() => setOpenAudit(v => !v)}
      >
        <AuditLogsPanel />
      </AdminSectionCard>
    </div>
  )
}
