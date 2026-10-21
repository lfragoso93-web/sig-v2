/**
 * BootstrapPanel — Central de Bootstrap por etapas para SuperAdmin (Issue #253)
 *
 * Permite visualizar o status dos 10 estágios canônicos do system-bootstrap.v4,
 * dependências, última execução e disparar execuções completas ou seletivas
 * com confirmação explícita e prevenção contra duplo disparo.
 */
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Play, RefreshCw, CheckCircle2, XCircle, AlertTriangle,
  Clock, ShieldAlert, Layers, Loader2, Info, ChevronDown, ChevronUp,
  Server, ShieldCheck,
} from 'lucide-react'
import api from '@/services/api'

export interface BootstrapStage {
  id: string
  name: string
  description: string
  dependencies: string[]
  provider_dependent: boolean
  destructive: boolean
  status: 'idle' | 'pending' | 'running' | 'success' | 'error'
  detail: string | null
  last_run_at: string | null
  error: string | null
}

export interface BootstrapStatusResponse {
  state: 'not_started' | 'running' | 'ready' | 'failed'
  schema_version: string | null
  started_at: string | null
  finished_at: string | null
  failed_stage: string | null
  detail: string | null
  certified_for_real_data: boolean
  bootstrap_complete: boolean
  ready_for_real_data: boolean
  launch_reserved: boolean
  commit_sha?: string | null
  current_stage?: string | null
  stages: BootstrapStage[]
}

const DEFAULT_COMMIT_SHA = '0000000000000000000000000000000000000000'

export default function BootstrapPanel() {
  const queryClient = useQueryClient()
  const [selectedStageForModal, setSelectedStageForModal] = useState<BootstrapStage | null>(null)
  const [isFullBootstrapModalOpen, setIsFullBootstrapModalOpen] = useState(false)
  const [commitShaInput, setCommitShaInput] = useState('')
  const [expandedDetails, setExpandedDetails] = useState<Record<string, boolean>>({})
  const [feedback, setFeedback] = useState<{ msg: string; isError: boolean } | null>(null)

  const { data: statusData, isLoading, isFetching } = useQuery<BootstrapStatusResponse>({
    queryKey: ['admin-bootstrap-status'],
    queryFn: () => api.get('/admin/bootstrap/status').then(r => r.data),
    refetchInterval: (query) => {
      const data = query.state.data as BootstrapStatusResponse | undefined
      // Polling a cada 2.5s se estiver executando ou reservado
      if (data?.state === 'running' || data?.launch_reserved) {
        return 2500
      }
      return 15000
    },
  })

  const triggerMutation = useMutation({
    mutationFn: (variables: { commitSha: string; stages?: string[] }) =>
      api.post('/admin/bootstrap', {
        commit_sha: variables.commitSha,
        stages: variables.stages,
      }).then(r => r.data),
    onSuccess: (data) => {
      setFeedback({
        msg: data.detail || 'Execução de bootstrap agendada com sucesso.',
        isError: false,
      })
      setIsFullBootstrapModalOpen(false)
      setSelectedStageForModal(null)
      queryClient.invalidateQueries({ queryKey: ['admin-bootstrap-status'] })
    },
    onError: (err: any) => {
      const detail = err.response?.data?.detail || err.message || 'Erro ao disparar bootstrap.'
      setFeedback({ msg: detail, isError: true })
    },
  })

  const isRunning = statusData?.state === 'running' || statusData?.launch_reserved

  const toggleDetail = (id: string) => {
    setExpandedDetails(prev => ({ ...prev, [id]: !prev[id] }))
  }

  const handleOpenFullBootstrap = () => {
    setCommitShaInput(statusData?.commit_sha || DEFAULT_COMMIT_SHA)
    setIsFullBootstrapModalOpen(true)
  }

  const handleOpenStageBootstrap = (stage: BootstrapStage) => {
    setCommitShaInput(statusData?.commit_sha || DEFAULT_COMMIT_SHA)
    setSelectedStageForModal(stage)
  }

  const handleConfirmTrigger = (stages?: string[]) => {
    const sha = commitShaInput.trim() || DEFAULT_COMMIT_SHA
    triggerMutation.mutate({ commitSha: sha, stages })
  }

  const getStatusBadge = (status: BootstrapStage['status']) => {
    switch (status) {
      case 'success':
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
            <CheckCircle2 size={11} /> Concluído
          </span>
        )
      case 'running':
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-full bg-blue-500/15 text-blue-400 border border-blue-500/30">
            <Loader2 size={11} className="animate-spin" /> Executando
          </span>
        )
      case 'error':
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-full bg-red-500/15 text-red-400 border border-red-500/30">
            <XCircle size={11} /> Falha
          </span>
        )
      case 'pending':
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-400 border border-amber-500/30">
            <Clock size={11} /> Na Fila
          </span>
        )
      default:
        return (
          <span className="inline-flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-full bg-zinc-500/15 text-zinc-400 border border-zinc-500/30">
            Idle
          </span>
        )
    }
  }

  const getGlobalStateBadge = (state?: string) => {
    switch (state) {
      case 'ready':
        return (
          <span className="inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
            <CheckCircle2 size={13} /> Sistema Pronto
          </span>
        )
      case 'running':
        return (
          <span className="inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-full bg-blue-500/15 text-blue-400 border border-blue-500/30 animate-pulse">
            <Loader2 size={13} className="animate-spin" /> Bootstrap em Execução
          </span>
        )
      case 'failed':
        return (
          <span className="inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-full bg-red-500/15 text-red-400 border border-red-500/30">
            <XCircle size={13} /> Falha no Bootstrap
          </span>
        )
      default:
        return (
          <span className="inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-full bg-zinc-500/15 text-zinc-400 border border-zinc-500/30">
            <Clock size={13} /> Não Iniciado
          </span>
        )
    }
  }

  return (
    <div className="flex flex-col gap-4 text-sm" style={{ color: 'var(--color-text)' }}>
      {/* Feedback Banner */}
      {feedback && (
        <div
          className={`flex items-center justify-between p-3 rounded-lg border text-xs ${
            feedback.isError
              ? 'bg-red-500/10 border-red-500/30 text-red-400'
              : 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
          }`}
        >
          <div className="flex items-center gap-2">
            {feedback.isError ? <AlertTriangle size={14} /> : <CheckCircle2 size={14} />}
            <span>{feedback.msg}</span>
          </div>
          <button
            onClick={() => setFeedback(null)}
            className="text-xs hover:underline opacity-80"
          >
            Fechar
          </button>
        </div>
      )}

      {/* Global Status Banner Card */}
      <div
        className="rounded-lg p-4 border flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4"
        style={{
          background: 'oklch(from var(--color-surface) l c h / 0.7)',
          borderColor: 'var(--color-border)',
        }}
      >
        <div className="flex flex-col gap-1.5">
          <div className="flex items-center gap-2.5 flex-wrap">
            <span className="font-semibold text-sm">Status Global:</span>
            {getGlobalStateBadge(statusData?.state)}
            {statusData?.ready_for_real_data ? (
              <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                <ShieldCheck size={12} /> Certificado para Dados Reais
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-amber-500/15 text-amber-400 border border-amber-500/30">
                <ShieldAlert size={12} /> Certificação Real Pendente
              </span>
            )}
            <span className="text-xs text-zinc-400 font-mono">
              v: {statusData?.schema_version || 'system-bootstrap.v4'}
            </span>
          </div>

          <p className="text-xs text-zinc-400">
            {statusData?.detail || 'Gerenciamento dos estágios canônicos de bootstrap.'}
            {statusData?.current_stage && (
              <span className="text-blue-400 font-medium ml-1">
                (Executando estágio: <code className="bg-blue-950/40 px-1 py-0.5 rounded">{statusData.current_stage}</code>)
              </span>
            )}
          </p>
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto">
          <button
            onClick={() => queryClient.invalidateQueries({ queryKey: ['admin-bootstrap-status'] })}
            disabled={isFetching}
            className="p-2 rounded-lg border border-zinc-700 hover:bg-zinc-800 text-zinc-300 disabled:opacity-50 transition-colors"
            title="Atualizar Status"
          >
            <RefreshCw size={14} className={isFetching ? 'animate-spin' : ''} />
          </button>
          <button
            onClick={handleOpenFullBootstrap}
            disabled={isRunning || triggerMutation.isPending}
            className="flex-1 sm:flex-initial flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-xs font-semibold text-white bg-blue-600 hover:bg-blue-500 disabled:opacity-50 transition-colors shadow-sm"
          >
            {isRunning ? (
              <>
                <Loader2 size={13} className="animate-spin" />
                Execução em Curso...
              </>
            ) : (
              <>
                <Play size={13} />
                Executar Bootstrap Completo
              </>
            )}
          </button>
        </div>
      </div>

      {/* Stages List */}
      <div className="flex flex-col gap-2.5">
        <div className="flex items-center justify-between text-xs text-zinc-400 font-medium px-1">
          <span>Estágios Canônicos ({statusData?.stages?.length || 10})</span>
          <span>Ações Operacionais</span>
        </div>

        {isLoading ? (
          <div className="p-8 flex items-center justify-center gap-2 text-zinc-400">
            <Loader2 size={16} className="animate-spin" />
            <span>Carregando estágios do bootstrap...</span>
          </div>
        ) : (
          statusData?.stages?.map((stage, idx) => {
            const isDetailOpen = !!expandedDetails[stage.id]
            const isCurrent = statusData.current_stage === stage.id

            return (
              <div
                key={stage.id}
                className={`rounded-lg border p-3 flex flex-col gap-2 transition-all ${
                  isCurrent
                    ? 'border-blue-500/60 bg-blue-950/20 ring-1 ring-blue-500/30'
                    : 'border-zinc-800 bg-zinc-900/40 hover:border-zinc-700'
                }`}
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <div className="flex items-start sm:items-center gap-2.5">
                    <span className="text-xs font-mono font-semibold text-zinc-400 w-5">
                      #{idx + 1}
                    </span>
                    <div className="flex flex-col">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-semibold text-xs text-zinc-100">
                          {stage.name}
                        </span>
                        <code className="text-[10px] font-mono text-zinc-400 bg-zinc-800/80 px-1.5 py-0.5 rounded">
                          {stage.id}
                        </code>
                        {getStatusBadge(stage.status)}
                        {stage.provider_dependent && (
                          <span
                            className="inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded bg-blue-950/40 text-blue-300 border border-blue-800/40"
                            title="Esta etapa consulta provedores de dados configurados"
                          >
                            <Server size={10} /> Provedor
                          </span>
                        )}
                        {stage.destructive && (
                          <span
                            className="inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded bg-amber-950/40 text-amber-300 border border-amber-800/40"
                            title="Reconstrói séries históricas no banco de dados"
                          >
                            <Layers size={10} /> Rebuild
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-zinc-400 mt-0.5">
                        {stage.description}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 self-end sm:self-center">
                    {stage.detail && (
                      <button
                        onClick={() => toggleDetail(stage.id)}
                        className="flex items-center gap-1 text-[11px] text-zinc-400 hover:text-zinc-200 px-2 py-1 rounded bg-zinc-800/60 hover:bg-zinc-800 transition-colors"
                      >
                        <span>Detalhes</span>
                        {isDetailOpen ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                      </button>
                    )}
                    <button
                      onClick={() => handleOpenStageBootstrap(stage)}
                      disabled={isRunning || triggerMutation.isPending}
                      className="flex items-center gap-1 text-xs font-medium px-2.5 py-1 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-200 disabled:opacity-40 transition-colors border border-zinc-700/60"
                      title={`Executar apenas o estágio ${stage.name}`}
                    >
                      <Play size={11} /> Executar Etapa
                    </button>
                  </div>
                </div>

                {/* Dependencies pills */}
                {stage.dependencies && stage.dependencies.length > 0 && (
                  <div className="flex items-center gap-1.5 text-[11px] text-zinc-400 pt-1 border-t border-zinc-800/60">
                    <span className="text-zinc-400">Dependências:</span>
                    {stage.dependencies.map(dep => (
                      <span
                        key={dep}
                        className="font-mono text-[10px] bg-zinc-800/80 text-zinc-300 px-1.5 py-0.2 rounded border border-zinc-700/50"
                      >
                        {dep}
                      </span>
                    ))}
                  </div>
                )}

                {/* Details Accordion */}
                {isDetailOpen && stage.detail && (
                  <div className="mt-1 p-2.5 rounded bg-zinc-950 border border-zinc-800 text-[11px] font-mono text-zinc-300 flex flex-col gap-1 whitespace-pre-wrap break-all">
                    <div className="flex items-center justify-between text-zinc-400 text-[10px] pb-1 border-b border-zinc-800/50">
                      <span>Última execução: {stage.last_run_at ? new Date(stage.last_run_at).toLocaleString('pt-BR') : 'N/A'}</span>
                      {stage.error && <span className="text-red-400 font-semibold">ERRO</span>}
                    </div>
                    <div>{stage.detail}</div>
                  </div>
                )}
              </div>
            )
          })
        )}
      </div>

      {/* Confirmation Modal — Full Bootstrap */}
      {isFullBootstrapModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div className="rounded-xl border border-zinc-700 bg-zinc-900 p-5 max-w-md w-full shadow-2xl flex flex-col gap-4">
            <div className="flex items-center gap-3 text-amber-400">
              <AlertTriangle size={20} />
              <h3 className="font-semibold text-base text-zinc-100">
                Confirmar Bootstrap Completo
              </h3>
            </div>

            <p className="text-xs text-zinc-300 leading-relaxed">
              Esta ação executará <strong>todos os 10 estágios canônicos</strong> do <code>system-bootstrap.v4</code> em sequência estrita, consultando provedores de mercado e reconciliando catálogos globais.
            </p>

            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-medium text-zinc-300">
                Commit SHA da stable-15jun (40 dígitos hexadecimais):
              </label>
              <input
                type="text"
                value={commitShaInput}
                onChange={e => setCommitShaInput(e.target.value)}
                placeholder="Ex: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
                className="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-zinc-700 text-xs font-mono text-zinc-100 focus:outline-none focus:border-blue-500"
              />
              <span className="text-[10px] text-zinc-400">
                O SHA audita formalmente a execução e identifica o snapshot de código nos gates de governança.
              </span>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-zinc-800">
              <button
                onClick={() => setIsFullBootstrapModalOpen(false)}
                disabled={triggerMutation.isPending}
                className="px-3 py-1.5 rounded-lg text-xs font-medium text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 transition-colors"
              >
                Cancelar
              </button>
              <button
                onClick={() => handleConfirmTrigger()}
                disabled={triggerMutation.isPending || !commitShaInput.trim()}
                className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-xs font-semibold text-white bg-blue-600 hover:bg-blue-500 disabled:opacity-50 transition-colors"
              >
                {triggerMutation.isPending ? <Loader2 size={13} className="animate-spin" /> : <Play size={13} />}
                Confirmar e Iniciar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Confirmation Modal — Stage Selective Bootstrap */}
      {selectedStageForModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div className="rounded-xl border border-zinc-700 bg-zinc-900 p-5 max-w-md w-full shadow-2xl flex flex-col gap-4">
            <div className="flex items-center gap-3 text-blue-400">
              <Info size={20} />
              <h3 className="font-semibold text-base text-zinc-100">
                Executar Etapa: {selectedStageForModal.name}
              </h3>
            </div>

            <p className="text-xs text-zinc-300 leading-relaxed">
              Você está prestes a disparar isoladamente o estágio <code>{selectedStageForModal.id}</code> ({selectedStageForModal.description}).
            </p>

            {selectedStageForModal.dependencies && selectedStageForModal.dependencies.length > 0 && (
              <div className="p-2.5 rounded bg-zinc-950 border border-zinc-800 text-xs text-zinc-400">
                <span className="font-semibold text-zinc-300">Atenção às dependências:</span>{' '}
                Esta etapa assume que as etapas <code>{selectedStageForModal.dependencies.join(', ')}</code> já foram previamente concluídas.
              </div>
            )}

            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-medium text-zinc-300">
                Commit SHA da stable-15jun:
              </label>
              <input
                type="text"
                value={commitShaInput}
                onChange={e => setCommitShaInput(e.target.value)}
                placeholder="Ex: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
                className="w-full px-3 py-2 rounded-lg bg-zinc-950 border border-zinc-700 text-xs font-mono text-zinc-100 focus:outline-none focus:border-blue-500"
              />
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-zinc-800">
              <button
                onClick={() => setSelectedStageForModal(null)}
                disabled={triggerMutation.isPending}
                className="px-3 py-1.5 rounded-lg text-xs font-medium text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 transition-colors"
              >
                Cancelar
              </button>
              <button
                onClick={() => handleConfirmTrigger([selectedStageForModal.id])}
                disabled={triggerMutation.isPending || !commitShaInput.trim()}
                className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-xs font-semibold text-white bg-blue-600 hover:bg-blue-500 disabled:opacity-50 transition-colors"
              >
                {triggerMutation.isPending ? <Loader2 size={13} className="animate-spin" /> : <Play size={13} />}
                Confirmar Execução
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
