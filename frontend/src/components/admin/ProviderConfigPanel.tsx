import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Server,
  Globe,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  Clock,
  KeyRound,
  RotateCcw,
  Loader2,
  Play,
  Pencil,
  X,
  ExternalLink,
} from 'lucide-react'
import api from '@/services/api'

export interface ProviderConfig {
  provider_id: string
  display_name: string
  description: string
  capabilities: string[]
  is_enabled: boolean
  priority: number
  base_url: string | null
  effective_base_url: string | null
  timeout_seconds: number
  rate_limit_per_minute: number | null
  custom_headers: Record<string, unknown> | null
  status: string
  last_health_check_at: string | null
  last_error_message: string | null
  requires_auth: boolean
  has_api_key_configured: boolean
  api_key_masked: string | null
  is_official_authority: boolean
  is_customized: boolean
  doc_url: string | null
}

export interface ProviderTestResult {
  provider_id: string
  success: boolean
  status: string
  latency_ms: number
  message: string
  tested_at: string
}

const CAPABILITY_LABELS: Record<string, string> = {
  quotes_intraday: 'Cotações Intradiárias',
  quotes_historical: 'Histórico de Preços',
  dividends: 'Proventos',
  corporate_events: 'Eventos Corporativos',
  fundamentals: 'Indicadores Fundamentalistas',
  benchmark_rates: 'Taxas de Benchmark',
  treasury_bonds: 'Títulos Públicos',
  fx_rates: 'Câmbio / FX',
}

export default function ProviderConfigPanel() {
  const queryClient = useQueryClient()
  const [editingProvider, setEditingProvider] = useState<ProviderConfig | null>(null)
  const [testResults, setTestResults] = useState<Record<string, ProviderTestResult>>({})
  const [testingId, setTestingId] = useState<string | null>(null)
  const [feedback, setFeedback] = useState<{ msg: string; isError: boolean } | null>(null)

  // Edit form state
  const [editPriority, setEditPriority] = useState(10)
  const [editTimeout, setEditTimeout] = useState(30)
  const [editBaseUrl, setEditBaseUrl] = useState('')
  const [editRateLimit, setEditRateLimit] = useState<string>('')
  const [editApiKey, setEditApiKey] = useState('')

  const { data: providers = [], isLoading, refetch } = useQuery<ProviderConfig[]>({
    queryKey: ['admin_providers'],
    queryFn: () => api.get<ProviderConfig[]>('/admin/providers').then(r => r.data),
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Record<string, unknown> }) =>
      api.put(`/admin/providers/${id}`, data).then(r => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin_providers'] })
      setFeedback({ msg: 'Configurações do provedor atualizadas com sucesso.', isError: false })
      setEditingProvider(null)
      setTimeout(() => setFeedback(null), 3000)
    },
    onError: (err: any) => {
      const detail = err?.response?.data?.detail
      setFeedback({
        msg: typeof detail === 'string' ? detail : 'Erro ao atualizar provedor.',
        isError: true,
      })
    },
  })

  const resetMutation = useMutation({
    mutationFn: (id: string) => api.post(`/admin/providers/${id}/reset`).then(r => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin_providers'] })
      setFeedback({ msg: 'Provedor restaurado para as configurações padrão do sistema.', isError: false })
      setTimeout(() => setFeedback(null), 3000)
    },
    onError: (err: any) => {
      const detail = err?.response?.data?.detail
      setFeedback({
        msg: typeof detail === 'string' ? detail : 'Erro ao restaurar provedor.',
        isError: true,
      })
    },
  })

  const handleStartEdit = (p: ProviderConfig) => {
    setEditingProvider(p)
    setEditPriority(p.priority)
    setEditTimeout(p.timeout_seconds)
    setEditBaseUrl(p.base_url ?? '')
    setEditRateLimit(p.rate_limit_per_minute?.toString() ?? '')
    setEditApiKey('')
    setFeedback(null)
  }

  const handleSaveEdit = () => {
    if (!editingProvider) return
    const payload: Record<string, unknown> = {
      priority: editPriority,
      timeout_seconds: editTimeout,
      base_url: editBaseUrl.trim() || null,
      rate_limit_per_minute: editRateLimit.trim() ? parseInt(editRateLimit, 10) : null,
    }
    if (editApiKey.trim()) {
      payload.new_api_key = editApiKey.trim()
    }
    updateMutation.mutate({ id: editingProvider.provider_id, data: payload })
  }

  const handleToggleEnable = (p: ProviderConfig) => {
    updateMutation.mutate({
      id: p.provider_id,
      data: { is_enabled: !p.is_enabled },
    })
  }

  const handleTestConnection = async (id: string) => {
    setTestingId(id)
    try {
      const res = await api.post<ProviderTestResult>(`/admin/providers/${id}/test`)
      setTestResults(prev => ({ ...prev, [id]: res.data }))
      refetch()
    } catch (err: any) {
      const detail = err?.response?.data?.detail ?? 'Falha ao executar teste de conexão.'
      setTestResults(prev => ({
        ...prev,
        [id]: {
          provider_id: id,
          success: false,
          status: 'PROVIDER_ERROR',
          latency_ms: 0,
          message: typeof detail === 'string' ? detail : 'Erro de rede',
          tested_at: new Date().toISOString(),
        },
      }))
    } finally {
      setTestingId(null)
    }
  }

  if (isLoading) {
    return (
      <div className="flex flex-col gap-3 py-4">
        {[1, 2, 3].map(i => (
          <div key={i} className="skeleton h-28 w-full rounded-xl" />
        ))}
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Banner / Info */}
      <div
        className="rounded-lg p-3 text-xs leading-relaxed flex items-start gap-2.5"
        style={{
          background: 'oklch(from var(--color-primary) l c h / 0.08)',
          border: '1px solid oklch(from var(--color-primary) l c h / 0.2)',
          color: 'var(--color-text)',
        }}
      >
        <Server size={16} className="text-primary shrink-0 mt-0.5" />
        <div>
          <span className="font-semibold text-primary">Arquitetura de Provedores Configuráveis</span>
          <p className="text-muted mt-0.5">
            Configurações persistidas para sincronizadores e workers de mercado sem alterar variáveis de ambiente.
            O <em>read path</em> financeiro permanece estritamente DB-first. Todas as alterações são registradas em logs de auditoria.
          </p>
        </div>
      </div>

      {feedback && (
        <div
          className="p-3 rounded-lg text-xs font-medium"
          style={{
            background: feedback.isError
              ? 'oklch(from var(--color-notification) l c h / 0.15)'
              : 'oklch(from var(--color-success) l c h / 0.15)',
            color: feedback.isError ? 'var(--color-notification)' : 'var(--color-success)',
            border: `1px solid ${
              feedback.isError
                ? 'oklch(from var(--color-notification) l c h / 0.3)'
                : 'oklch(from var(--color-success) l c h / 0.3)'
            }`,
          }}
        >
          {feedback.msg}
        </div>
      )}

      {/* Lista de Provedores */}
      <div className="flex flex-col gap-3">
        {providers.map(p => {
          const testRes = testResults[p.provider_id]
          const isTesting = testingId === p.provider_id
          const isOk = p.status === 'OK'

          return (
            <div
              key={p.provider_id}
              className="rounded-xl p-4 flex flex-col gap-3 transition-all"
              style={{
                background: 'var(--color-surface)',
                border: '1px solid var(--color-border)',
                opacity: p.is_enabled ? 1 : 0.65,
              }}
            >
              {/* Top Row: Title, Badges & Toggles */}
              <div className="flex items-start justify-between flex-wrap gap-2">
                <div className="flex items-center gap-2.5">
                  <div
                    className="w-8 h-8 rounded-lg flex items-center justify-center font-bold text-xs"
                    style={{
                      background: 'var(--color-surface-offset)',
                      color: 'var(--color-primary)',
                      border: '1px solid var(--color-divider)',
                    }}
                  >
                    <Globe size={16} />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-sm">{p.display_name}</span>
                      <span className="text-[10px] font-mono text-muted bg-surface-offset px-1.5 py-0.5 rounded border border-divider">
                        {p.provider_id}
                      </span>
                      {p.is_official_authority && (
                        <span
                          className="text-[10px] px-2 py-0.5 rounded-full font-medium flex items-center gap-1"
                          style={{
                            background: 'oklch(from var(--color-success) l c h / 0.12)',
                            color: 'var(--color-success)',
                          }}
                        >
                          <ShieldCheck size={11} /> Autoridade Oficial
                        </span>
                      )}
                      {p.is_customized && (
                        <span
                          className="text-[10px] px-2 py-0.5 rounded-full font-medium"
                          style={{
                            background: 'oklch(from var(--color-primary) l c h / 0.12)',
                            color: 'var(--color-primary)',
                          }}
                        >
                          Personalizado
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-muted mt-0.5">{p.description}</p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <span
                    className="text-[11px] px-2.5 py-1 rounded-full font-semibold flex items-center gap-1"
                    style={{
                      background: isOk
                        ? 'oklch(from var(--color-success) l c h / 0.15)'
                        : 'oklch(from var(--color-notification) l c h / 0.15)',
                      color: isOk ? 'var(--color-success)' : 'var(--color-notification)',
                    }}
                  >
                    {isOk ? <CheckCircle2 size={12} /> : <AlertTriangle size={12} />}
                    {p.status}
                  </span>

                  <button
                    type="button"
                    onClick={() => handleToggleEnable(p)}
                    className="btn btn-secondary text-xs py-1 px-2.5"
                    title={p.is_enabled ? 'Desativar provedor' : 'Ativar provedor'}
                  >
                    {p.is_enabled ? 'Ativo' : 'Inativo'}
                  </button>
                </div>
              </div>

              {/* Capabilities Badges */}
              <div className="flex items-center gap-1.5 flex-wrap">
                <span className="text-[10px] text-muted mr-1">Capacidades:</span>
                {p.capabilities.map(cap => (
                  <span
                    key={cap}
                    className="text-[10px] px-2 py-0.5 rounded font-medium"
                    style={{
                      background: 'var(--color-surface-offset)',
                      border: '1px solid var(--color-divider)',
                      color: 'var(--color-text)',
                    }}
                  >
                    {CAPABILITY_LABELS[cap] ?? cap}
                  </span>
                ))}
              </div>

              {/* Metrics & Parameters Grid */}
              <div
                className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 text-xs"
                style={{ borderTop: '1px solid var(--color-divider)' }}
              >
                <div>
                  <span className="text-[10px] text-muted block">Prioridade</span>
                  <span className="font-semibold tabular-nums">#{p.priority}</span>
                </div>

                <div>
                  <span className="text-[10px] text-muted block">Timeout</span>
                  <span className="font-semibold tabular-nums">{p.timeout_seconds}s</span>
                </div>

                <div>
                  <span className="text-[10px] text-muted block">Limite / Minuto</span>
                  <span className="font-semibold tabular-nums">
                    {p.rate_limit_per_minute ? `${p.rate_limit_per_minute} req/min` : 'Padrão'}
                  </span>
                </div>

                <div>
                  <span className="text-[10px] text-muted block">Chave de API</span>
                  {p.requires_auth ? (
                    <span className="font-mono text-[11px] flex items-center gap-1">
                      <KeyRound size={12} className="text-primary" />
                      {p.api_key_masked ?? 'Não configurada'}
                    </span>
                  ) : (
                    <span className="text-muted text-[11px]">Pública (sem auth)</span>
                  )}
                </div>
              </div>

              {/* Endpoint Reference */}
              {p.effective_base_url && (
                <div className="flex items-center justify-between text-[11px] text-muted pt-1">
                  <span className="truncate">
                    Endpoint: <code className="text-primary">{p.effective_base_url}</code>
                  </span>
                  {p.doc_url && (
                    <a
                      href={p.doc_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-1 text-primary hover:underline shrink-0"
                    >
                      Documentação <ExternalLink size={10} />
                    </a>
                  )}
                </div>
              )}

              {/* Probe Test Results Banner */}
              {testRes && (
                <div
                  className="rounded-lg p-2.5 text-xs flex items-center justify-between flex-wrap gap-2"
                  style={{
                    background: testRes.success
                      ? 'oklch(from var(--color-success) l c h / 0.08)'
                      : 'oklch(from var(--color-notification) l c h / 0.08)',
                    border: `1px solid ${
                      testRes.success
                        ? 'oklch(from var(--color-success) l c h / 0.2)'
                        : 'oklch(from var(--color-notification) l c h / 0.2)'
                    }`,
                  }}
                >
                  <div className="flex items-center gap-1.5">
                    {testRes.success ? (
                      <CheckCircle2 size={14} style={{ color: 'var(--color-success)' }} />
                    ) : (
                      <AlertTriangle size={14} style={{ color: 'var(--color-notification)' }} />
                    )}
                    <span>{testRes.message}</span>
                  </div>
                  <span className="font-mono text-[10px] text-muted">
                    Latência: <strong>{testRes.latency_ms}ms</strong> · Status: {testRes.status}
                  </span>
                </div>
              )}

              {/* Action Buttons Footer */}
              <div className="flex items-center justify-between pt-2 flex-wrap gap-2" style={{ borderTop: '1px solid var(--color-divider)' }}>
                <div className="flex items-center gap-2 text-[10px] text-muted">
                  <Clock size={12} />
                  <span>
                    Último teste:{' '}
                    {p.last_health_check_at
                      ? new Date(p.last_health_check_at).toLocaleString('pt-BR')
                      : 'Nunca realizado'}
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => handleTestConnection(p.provider_id)}
                    disabled={isTesting}
                    className="btn btn-secondary text-xs py-1 px-2.5 flex items-center gap-1.5"
                    title="Realizar teste de conectividade e latência"
                  >
                    {isTesting ? (
                      <>
                        <Loader2 size={12} className="animate-spin" /> Testando…
                      </>
                    ) : (
                      <>
                        <Play size={12} /> Testar Conexão
                      </>
                    )}
                  </button>

                  <button
                    type="button"
                    onClick={() => handleStartEdit(p)}
                    className="btn btn-secondary text-xs py-1 px-2.5 flex items-center gap-1.5"
                  >
                    <Pencil size={12} /> Configurar
                  </button>

                  {p.is_customized && (
                    <button
                      type="button"
                      onClick={() => resetMutation.mutate(p.provider_id)}
                      disabled={resetMutation.isPending}
                      className="btn btn-secondary text-xs py-1 px-2 flex items-center gap-1 text-muted hover:text-danger"
                      title="Restaurar parâmetros padrão do sistema"
                    >
                      <RotateCcw size={12} /> Restaurar Padrão
                    </button>
                  )}
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {/* Edit Modal */}
      {editingProvider && (
        <div
          role="dialog"
          aria-modal="true"
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          style={{ background: 'rgba(0,0,0,0.65)', backdropFilter: 'blur(3px)' }}
        >
          <div
            className="card p-5 w-full max-w-md flex flex-col gap-4 shadow-xl"
            style={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)' }}
          >
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold">Configurar {editingProvider.display_name}</h3>
                <span className="text-[11px] text-muted">Edição dinâmica de parâmetros</span>
              </div>
              <button
                type="button"
                onClick={() => setEditingProvider(null)}
                className="text-muted hover:text-text p-1 rounded"
              >
                <X size={16} />
              </button>
            </div>

            <div className="flex flex-col gap-3 text-xs">
              <div>
                <label className="block text-[11px] text-muted mb-1">Prioridade (1 a 100 — menor número tem precedência)</label>
                <input
                  type="number"
                  min="1"
                  max="100"
                  value={editPriority}
                  onChange={e => setEditPriority(parseInt(e.target.value, 10) || 1)}
                  className="input w-full py-1 px-2 text-xs"
                />
              </div>

              <div>
                <label className="block text-[11px] text-muted mb-1">Timeout de Requisição (segundos)</label>
                <input
                  type="number"
                  min="1"
                  max="300"
                  value={editTimeout}
                  onChange={e => setEditTimeout(parseInt(e.target.value, 10) || 1)}
                  className="input w-full py-1 px-2 text-xs"
                />
              </div>

              <div>
                <label className="block text-[11px] text-muted mb-1">URL Base Personalizada (opcional)</label>
                <input
                  type="text"
                  placeholder={editingProvider.effective_base_url ?? 'https://...'}
                  value={editBaseUrl}
                  onChange={e => setEditBaseUrl(e.target.value)}
                  className="input w-full py-1 px-2 text-xs font-mono"
                />
              </div>

              <div>
                <label className="block text-[11px] text-muted mb-1">Limite de Requisições por Minuto (opcional)</label>
                <input
                  type="number"
                  min="1"
                  placeholder="Ex: 300 (deixe vazio para ilimitado)"
                  value={editRateLimit}
                  onChange={e => setEditRateLimit(e.target.value)}
                  className="input w-full py-1 px-2 text-xs"
                />
              </div>

              {editingProvider.requires_auth && (
                <div>
                  <label className="block text-[11px] text-muted mb-1">
                    Nova Chave de API / Token (deixe em branco para manter a atual)
                  </label>
                  <input
                    type="password"
                    placeholder={editingProvider.api_key_masked ?? 'Insira a nova chave'}
                    value={editApiKey}
                    onChange={e => setEditApiKey(e.target.value)}
                    className="input w-full py-1 px-2 text-xs font-mono"
                  />
                  <p className="text-[10px] text-muted mt-1">
                    A chave será criptografada com a chave mestra do sistema antes de ser gravada no banco.
                  </p>
                </div>
              )}
            </div>

            <div className="flex justify-end gap-2 pt-2" style={{ borderTop: '1px solid var(--color-divider)' }}>
              <button
                type="button"
                onClick={() => setEditingProvider(null)}
                className="btn btn-secondary text-xs py-1 px-3"
              >
                Cancelar
              </button>
              <button
                type="button"
                onClick={handleSaveEdit}
                disabled={updateMutation.isPending}
                className="btn btn-primary text-xs py-1 px-3 flex items-center gap-1.5"
              >
                {updateMutation.isPending && <Loader2 size={12} className="animate-spin" />}
                Salvar Alterações
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
