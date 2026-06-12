/**
 * AdminPanel — visível apenas para usuários com role === 'superadmin'
 * Secções:
 *   1. Estatísticas do sistema
 *   2. Gestão de usuários (listar, ativar/desativar, excluir)
 *   3. Configurações do sistema (chave/valor)
 */
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Users, Settings, BarChart2, Trash2, Power, Plus, Save, ChevronDown, ChevronUp, Loader2 } from 'lucide-react'
import api from '@/services/api'

// ── Types ──────────────────────────────────────────────────────────────────────────
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

// ── API calls ───────────────────────────────────────────────────────────────────────
const fetchStats        = () => api.get<AdminStats>('/admin/stats').then(r => r.data)
const fetchUsers        = (page: number, search: string) =>
  api.get('/admin/users', { params: { page, page_size: 10, search: search || undefined } }).then(r => r.data)
const fetchConfigs      = () => api.get<SystemConfig[]>('/admin/config').then(r => r.data)

// ── Sub-components ─────────────────────────────────────────────────────────────────────
function SectionHeader({ icon: Icon, title, open, onToggle }: {
  icon: React.ElementType; title: string; open: boolean; onToggle: () => void
}) {
  return (
    <button
      onClick={onToggle}
      className="w-full flex items-center justify-between py-2 text-left group"
    >
      <div className="flex items-center gap-2">
        <Icon size={15} className="text-teal-400" />
        <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">{title}</span>
      </div>
      {open ? <ChevronUp size={14} className="text-gray-500" /> : <ChevronDown size={14} className="text-gray-500" />}
    </button>
  )
}

function RoleBadge({ role }: { role: string }) {
  const map: Record<string, string> = {
    superadmin: 'bg-purple-900/60 text-purple-300 border border-purple-700',
    admin:      'bg-blue-900/60 text-blue-300 border border-blue-700',
    user:       'bg-gray-800 text-gray-400 border border-gray-700',
  }
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full ${map[role] ?? map.user}`}>
      {role}
    </span>
  )
}

// ── Stats section ───────────────────────────────────────────────────────────────────────
function StatsSection() {
  const { data, isLoading } = useQuery({ queryKey: ['admin-stats'], queryFn: fetchStats })
  if (isLoading) return <div className="py-3 text-center"><Loader2 size={16} className="animate-spin text-teal-400 mx-auto" /></div>
  if (!data) return null
  return (
    <div className="grid grid-cols-2 gap-2 py-2">
      <div className="bg-gray-800 rounded-lg p-3">
        <div className="text-xs text-gray-400 mb-1">Usuários</div>
        <div className="text-lg font-bold text-white">{data.total_users}</div>
      </div>
      <div className="bg-gray-800 rounded-lg p-3">
        <div className="text-xs text-gray-400 mb-1">Versão</div>
        <div className="text-lg font-bold text-white">{data.version}</div>
      </div>
    </div>
  )
}

// ── Users section ───────────────────────────────────────────────────────────────────────
function UsersSection() {
  const qc = useQueryClient()
  const [page, setPage]   = useState(1)
  const [search, setSearch] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')

  // Debounce simples sem lib
  const handleSearch = (v: string) => {
    setSearch(v)
    clearTimeout((window as any)._adminSearchTimer)
    ;(window as any)._adminSearchTimer = setTimeout(() => { setDebouncedSearch(v); setPage(1) }, 400)
  }

  const { data, isLoading } = useQuery({
    queryKey: ['admin-users', page, debouncedSearch],
    queryFn: () => fetchUsers(page, debouncedSearch),
  })

  const toggleActive = useMutation({
    mutationFn: (id: number) => api.put(`/admin/users/${id}/toggle-active`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-users'] }),
  })

  const deleteUser = useMutation({
    mutationFn: (id: number) => api.delete(`/admin/users/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-users'] }),
  })

  // Criar usuário
  const [showCreate, setShowCreate] = useState(false)
  const [newUser, setNewUser] = useState({ name: '', email: '', password: '', role: 'user' })
  const createUser = useMutation({
    mutationFn: () => api.post(`/admin/users?role=${newUser.role}`, {
      name: newUser.name, email: newUser.email, password: newUser.password
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

  return (
    <div className="space-y-3 py-2">
      {/* Busca + criar */}
      <div className="flex gap-2">
        <input
          value={search}
          onChange={e => handleSearch(e.target.value)}
          placeholder="Buscar usuário..."
          className="flex-1 bg-gray-800 text-white text-xs rounded-lg px-3 py-2 border border-gray-700 focus:outline-none focus:border-teal-500"
        />
        <button
          onClick={() => setShowCreate(v => !v)}
          className="bg-teal-700 hover:bg-teal-600 text-white px-3 py-2 rounded-lg transition flex items-center gap-1"
          title="Criar usuário"
        >
          <Plus size={14} />
        </button>
      </div>

      {/* Form criar usuário */}
      {showCreate && (
        <div className="bg-gray-800 rounded-lg p-3 space-y-2 border border-gray-700">
          <p className="text-xs font-semibold text-gray-300">Novo usuário</p>
          {(['name', 'email', 'password'] as const).map(f => (
            <input
              key={f}
              type={f === 'password' ? 'password' : 'text'}
              placeholder={f === 'name' ? 'Nome' : f === 'email' ? 'E-mail' : 'Senha'}
              value={newUser[f]}
              onChange={e => setNewUser(v => ({ ...v, [f]: e.target.value }))}
              className="w-full bg-gray-900 text-white text-xs rounded-lg px-3 py-2 border border-gray-700 focus:outline-none focus:border-teal-500"
            />
          ))}
          <select
            value={newUser.role}
            onChange={e => setNewUser(v => ({ ...v, role: e.target.value }))}
            className="w-full bg-gray-900 text-white text-xs rounded-lg px-3 py-2 border border-gray-700 focus:outline-none focus:border-teal-500"
          >
            <option value="user">user</option>
            <option value="admin">admin</option>
            <option value="superadmin">superadmin</option>
          </select>
          <div className="flex gap-2 justify-end">
            <button onClick={() => setShowCreate(false)} className="text-xs text-gray-400 hover:text-white px-3 py-1.5 rounded-lg transition">Cancelar</button>
            <button
              onClick={() => createUser.mutate()}
              disabled={createUser.isPending || !newUser.email || !newUser.password}
              className="bg-teal-600 hover:bg-teal-500 disabled:opacity-50 text-white text-xs px-3 py-1.5 rounded-lg transition flex items-center gap-1"
            >
              {createUser.isPending ? <Loader2 size={12} className="animate-spin" /> : <Plus size={12} />}
              Criar
            </button>
          </div>
        </div>
      )}

      {/* Lista de usuários */}
      {isLoading ? (
        <div className="py-4 text-center"><Loader2 size={16} className="animate-spin text-teal-400 mx-auto" /></div>
      ) : (
        <ul className="space-y-1.5">
          {users.map(u => (
            <li key={u.id} className={`flex items-center justify-between bg-gray-800 rounded-lg px-3 py-2 gap-2 ${!u.is_active ? 'opacity-50' : ''}`}>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-white text-xs font-medium truncate">{u.name || u.email}</span>
                  <RoleBadge role={u.role} />
                  {!u.is_active && <span className="text-xs text-gray-500 italic">inativo</span>}
                </div>
                <div className="text-gray-500 text-xs truncate">{u.email}</div>
              </div>
              <div className="flex items-center gap-1 shrink-0">
                <button
                  onClick={() => {
                    if (!confirm(`${u.is_active ? 'Desativar' : 'Ativar'} usuário "${u.name || u.email}"?`)) return
                    toggleActive.mutate(u.id)
                  }}
                  title={u.is_active ? 'Desativar' : 'Ativar'}
                  className={`p-1.5 rounded transition ${u.is_active ? 'text-gray-500 hover:text-yellow-400' : 'text-gray-600 hover:text-teal-400'}`}
                >
                  <Power size={13} />
                </button>
                <button
                  onClick={() => {
                    if (!confirm(`Excluir permanentemente "${u.name || u.email}"? Todas as carteiras e dados serão removidos.`)) return
                    deleteUser.mutate(u.id)
                  }}
                  title="Excluir usuário"
                  className="p-1.5 rounded text-gray-500 hover:text-red-400 transition"
                >
                  <Trash2 size={13} />
                </button>
              </div>
            </li>
          ))}
          {users.length === 0 && (
            <li className="text-center text-gray-500 text-xs py-4">Nenhum usuário encontrado.</li>
          )}
        </ul>
      )}

      {/* Paginação */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between pt-1">
          <button
            disabled={page <= 1}
            onClick={() => setPage(p => p - 1)}
            className="text-xs text-gray-400 hover:text-white disabled:opacity-30 px-2 py-1 rounded transition"
          >← Anterior</button>
          <span className="text-xs text-gray-500">{page} / {totalPages}</span>
          <button
            disabled={page >= totalPages}
            onClick={() => setPage(p => p + 1)}
            className="text-xs text-gray-400 hover:text-white disabled:opacity-30 px-2 py-1 rounded transition"
          >Próxima →</button>
        </div>
      )}
    </div>
  )
}

// ── Configs section ────────────────────────────────────────────────────────────────────
function ConfigsSection() {
  const qc = useQueryClient()
  const { data: configs = [], isLoading } = useQuery<SystemConfig[]>({
    queryKey: ['admin-configs'],
    queryFn: fetchConfigs,
  })

  // Estado local de edição — {key: newValue}
  const [edits, setEdits] = useState<Record<string, string>>({})
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

  if (isLoading) return <div className="py-3 text-center"><Loader2 size={16} className="animate-spin text-teal-400 mx-auto" /></div>

  return (
    <div className="space-y-2 py-2">
      {configs.length === 0 && (
        <p className="text-xs text-gray-500 text-center py-4">Nenhuma configuração cadastrada.</p>
      )}
      {configs.map(c => (
        <div key={c.key} className="bg-gray-800 rounded-lg p-3 space-y-1.5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono text-teal-400">{c.key}</span>
            {c.is_public && <span className="text-xs text-gray-500 border border-gray-700 px-1.5 py-0.5 rounded">pública</span>}
          </div>
          {c.description && <p className="text-xs text-gray-500">{c.description}</p>}
          <div className="flex gap-2">
            <input
              value={edits[c.key] ?? c.value}
              onChange={e => handleEdit(c.key, e.target.value)}
              className="flex-1 bg-gray-900 text-white text-xs rounded px-2 py-1.5 border border-gray-700 focus:outline-none focus:border-teal-500 font-mono"
            />
            {edits[c.key] !== undefined && edits[c.key] !== c.value && (
              <button
                onClick={() => handleSave(c.key)}
                disabled={saving === c.key}
                title="Salvar"
                className="bg-teal-700 hover:bg-teal-600 text-white px-2 rounded transition"
              >
                {saving === c.key ? <Loader2 size={12} className="animate-spin" /> : <Save size={12} />}
              </button>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}

// ── Main export ──────────────────────────────────────────────────────────────────────────────
export default function AdminPanel() {
  const [openStats,   setOpenStats]   = useState(true)
  const [openUsers,   setOpenUsers]   = useState(true)
  const [openConfigs, setOpenConfigs] = useState(false)

  return (
    <section className="bg-gray-900 rounded-xl p-4 space-y-1 border border-purple-900/40">
      {/* Header */}
      <div className="flex items-center gap-2 mb-3">
        <span className="w-2 h-2 rounded-full bg-purple-400"></span>
        <h2 className="text-sm font-semibold text-purple-300 uppercase tracking-wide">Painel Admin</h2>
      </div>

      {/* Estatísticas */}
      <div className="border-b border-gray-800 pb-1">
        <SectionHeader icon={BarChart2} title="Estatísticas" open={openStats} onToggle={() => setOpenStats(v => !v)} />
        {openStats && <StatsSection />}
      </div>

      {/* Usuários */}
      <div className="border-b border-gray-800 pb-1">
        <SectionHeader icon={Users} title="Usuários" open={openUsers} onToggle={() => setOpenUsers(v => !v)} />
        {openUsers && <UsersSection />}
      </div>

      {/* Configurações do sistema */}
      <div>
        <SectionHeader icon={Settings} title="Configurações do sistema" open={openConfigs} onToggle={() => setOpenConfigs(v => !v)} />
        {openConfigs && <ConfigsSection />}
      </div>
    </section>
  )
}
