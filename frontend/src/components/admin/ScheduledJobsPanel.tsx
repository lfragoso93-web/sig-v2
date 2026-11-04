import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertTriangle, CheckCircle2, Clock3, Loader2, MinusCircle, XCircle, Play, History } from 'lucide-react'
import { useState } from 'react'
import api from '@/services/api'

interface ScheduledJob {
  id: string
  name: string
  enabled: boolean
  next_run_at: string | null
  last_status: 'never_run' | 'running' | 'succeeded' | 'failed' | string
  last_started_at: string | null
  last_finished_at: string | null
  duration_ms: string | null
  last_error_type: string | null
  lease_ttl_seconds: string | null
  trigger_source: string | null
  triggered_by_user_id: string | null
}
type RunRecord = { status: string; started_at: string; finished_at: string; duration_ms: string; error_type: string; trigger_source: string; triggered_by_user_id: string }

interface SchedulerStatus {
  timezone: string
  status_retention_days: number
  status_store_available: boolean
  jobs: ScheduledJob[]
}

function formatDate(value: string | null) {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '—' : date.toLocaleString('pt-BR')
}

function JobState({ job }: { job: ScheduledJob }) {
  if (!job.enabled) return <span className="inline-flex items-center gap-1 text-xs text-[var(--color-text-muted)]"><MinusCircle size={13} /> Desativado</span>
  if (job.last_status === 'failed') return <span className="inline-flex items-center gap-1 text-xs text-red-400"><XCircle size={13} /> Falhou{job.last_error_type ? ` (${job.last_error_type})` : ''}</span>
  if (job.last_status === 'running' && isStaleRun(job)) return <span className="inline-flex items-center gap-1 text-xs text-red-400"><AlertTriangle size={13} /> Execução pode ter sido interrompida</span>
  if (job.last_status === 'running') return <span className="inline-flex items-center gap-1 text-xs text-amber-400"><Loader2 size={13} className="animate-spin" /> Em execução</span>
  if (job.last_status === 'succeeded') return <span className="inline-flex items-center gap-1 text-xs text-emerald-400"><CheckCircle2 size={13} /> Concluiu</span>
  return <span className="inline-flex items-center gap-1 text-xs text-[var(--color-text-muted)]"><Clock3 size={13} /> Ainda sem execução registrada</span>
}

function isStaleRun(job: ScheduledJob) {
  if (!job.last_started_at || !job.lease_ttl_seconds) return false
  const startedAt = new Date(job.last_started_at).getTime()
  const ttlMs = Number(job.lease_ttl_seconds) * 1000
  return Number.isFinite(startedAt) && Number.isFinite(ttlMs) && Date.now() > startedAt + ttlMs
}

export default function ScheduledJobsPanel() {
  const queryClient = useQueryClient()
  const [historyJobId, setHistoryJobId] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const { data, isLoading, isError } = useQuery<SchedulerStatus>({
    queryKey: ['admin-scheduler-status'],
    queryFn: () => api.get('/admin/scheduler/status').then(response => response.data),
    refetchInterval: 60_000,
  })
  const historyQuery = useQuery<{ job_id: string; runs: RunRecord[] }>({
    queryKey: ['admin-scheduler-history', historyJobId],
    queryFn: () => api.get('/admin/scheduler/' + historyJobId + '/history', { params: { limit: 30 } }).then(response => response.data),
    enabled: historyJobId !== null,
  })
  const runMutation = useMutation({
    mutationFn: (jobId: string) => api.post('/admin/scheduler/' + jobId + '/run'),
    onSuccess: (_result, jobId) => {
      setNotice('Execução manual solicitada. O estado será atualizado em instantes.')
      setHistoryJobId(jobId)
      window.setTimeout(() => queryClient.invalidateQueries({ queryKey: ['admin-scheduler-status'] }), 1500)
    },
    onError: () => setNotice('Não foi possível iniciar. Verifique se o job já está executando e consulte o histórico.'),
  })

  if (isLoading) return <div className="py-4 text-center"><Loader2 size={18} className="animate-spin mx-auto" /></div>
  if (isError || !data) return <p className="text-sm text-red-400">Não foi possível consultar o estado do scheduler.</p>

  const hasFailure = data.jobs.some(job => job.enabled && (
    job.last_status === 'failed' || (job.last_status === 'running' && isStaleRun(job))
  ))
  return (
    <div className="space-y-3">
      {hasFailure && (
        <div role="alert" className="flex items-center gap-2 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">
          <AlertTriangle size={16} /> Há tarefa agendada com falha ou execução interrompida provável.
        </div>
      )}
      {!data.status_store_available && (
        <div role="alert" className="flex items-center gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-300">
          <AlertTriangle size={16} /> O Redis está indisponível; os últimos resultados das tarefas não podem ser consultados.
        </div>
      )}
      <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
        Horário: {data.timezone}. O resultado mais recente fica disponível por {data.status_retention_days} dias. Execução registrada indica conclusão técnica, não valida a qualidade dos dados de origem.
      </p>
      {notice && <p role="status" className="text-xs" style={{ color: 'var(--color-text-muted)' }}>{notice}</p>}
      <div className="overflow-x-auto">
        <table className="w-full min-w-[760px] text-left text-xs">
          <thead><tr style={{ color: 'var(--color-text-muted)' }}>
            <th className="px-2 py-2">Tarefa</th><th className="px-2 py-2">Estado</th><th className="px-2 py-2">Última execução</th><th className="px-2 py-2">Próxima</th><th className="px-2 py-2">Duração</th><th className="px-2 py-2">Ações</th>
          </tr></thead>
          <tbody>{data.jobs.map(job => <tr key={job.id} className="border-t" style={{ borderColor: 'var(--color-divider)' }}>
            <td className="px-2 py-2 font-medium" style={{ color: 'var(--color-text)' }}>{job.name}</td>
            <td className="px-2 py-2"><JobState job={job} /></td>
            <td className="px-2 py-2" style={{ color: 'var(--color-text-muted)' }}>{formatDate(job.last_finished_at)}</td>
            <td className="px-2 py-2" style={{ color: 'var(--color-text-muted)' }}>{job.enabled ? formatDate(job.next_run_at) : '—'}</td>
            <td className="px-2 py-2 tabular-nums" style={{ color: 'var(--color-text-muted)' }}>{job.duration_ms ? `${job.duration_ms} ms` : '—'}{job.trigger_source === 'manual' ? <span className="ml-1">(manual)</span> : null}</td>
            <td className="px-2 py-2"><div className="flex gap-2">
              <button type="button" disabled={!job.enabled || runMutation.isPending || job.last_status === 'running'} title="Executar agora" aria-label={`Executar ${job.name} agora`} className="rounded border p-1.5 disabled:opacity-40" style={{ borderColor: 'var(--color-border)' }} onClick={() => { if (window.confirm(`Executar agora: ${job.name}?`)) runMutation.mutate(job.id) }}><Play size={14} /></button>
              <button type="button" title="Ver histórico" aria-label={`Ver histórico de ${job.name}`} className="rounded border p-1.5" style={{ borderColor: 'var(--color-border)' }} onClick={() => setHistoryJobId(current => current === job.id ? null : job.id)}><History size={14} /></button>
            </div></td>
          </tr>)}</tbody>
        </table>
      </div>
      {historyJobId && <section className="rounded-lg border p-3" style={{ borderColor: 'var(--color-divider)' }}>
        <div className="mb-2 flex items-center justify-between"><h3 className="text-sm font-semibold">Histórico: {data.jobs.find(job => job.id === historyJobId)?.name}</h3><button type="button" className="text-xs underline" onClick={() => setHistoryJobId(null)}>Fechar</button></div>
        {historyQuery.isLoading ? <p className="text-xs">Carregando histórico…</p> : !historyQuery.data?.runs.length ? <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>Nenhuma execução registrada.</p> : <div className="space-y-2">{historyQuery.data.runs.map((run, index) => <div key={index} className="flex flex-wrap gap-x-3 text-xs" style={{ color: 'var(--color-text-muted)' }}><span>{run.status === 'succeeded' ? 'Concluiu' : 'Falhou'}</span><span>{formatDate(run.started_at)}</span><span>{run.duration_ms} ms</span><span>{run.trigger_source === 'manual' ? (run.triggered_by_user_id ? 'Manual · usuário #' + run.triggered_by_user_id : 'Manual') : 'Agendada'}</span>{run.error_type && <span className="text-red-400">Erro: {run.error_type}</span>}</div>)}</div>}
      </section>}
    </div>
  )
}
