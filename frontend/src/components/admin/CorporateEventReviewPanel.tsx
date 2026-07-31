import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  AlertTriangle,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  FileSearch,
  Loader2,
  RefreshCw,
  Search,
  ShieldCheck,
  XCircle,
} from 'lucide-react'
import Modal from '@/components/ui/Modal'
import { corporateEventReviewService } from '@/services/corporateEventReviewService'
import type {
  CorporateEventReviewDecision,
  CorporateEventReviewItem,
} from '@/types/corporateEventReview'
import type { CorporateEventEvidenceGroup } from '@/types/corporateEventReview'

const PAGE_SIZE = 20

function errorMessage(error: unknown): string {
  if (typeof error === 'object' && error !== null && 'response' in error) {
    const response = (error as { response?: { data?: { detail?: string } } }).response
    if (response?.data?.detail) return response.data.detail
  }
  return 'Não foi possível concluir a operação.'
}

function badgeStyle(status: string) {
  if (status === 'CONFLICT') return { color: '#dc2626', background: '#dc262615' }
  if (status === 'UNRECONCILED') return { color: '#d97706', background: '#d9770615' }
  return { color: 'var(--color-primary)', background: 'var(--color-primary-soft)' }
}

const comparisonLabels: Record<string, string> = {
  event_type: 'Tipo do evento',
  effective_date: 'Data efetiva',
  record_date: 'Data-base',
  ex_date: 'Data ex',
  payment_date: 'Pagamento',
  quantity_factor: 'Fator de quantidade',
  cash_component: 'Componente em dinheiro',
  subscription_price: 'Preço de subscrição',
  destination_cost_allocation: 'Custo destinado',
  quantity_step: 'Passo de liquidação',
  fractional_settlement_price: 'Preço da fração',
  cash_treatment: 'Tratamento do caixa',
  currency: 'Moeda',
  isin_code: 'ISIN de origem',
  destination_isin_code: 'ISIN de destino',
}

function EvidenceModal({
  event,
  evidence,
  loading,
  error,
  onClose,
}: {
  event: CorporateEventReviewItem
  evidence: CorporateEventEvidenceGroup | undefined
  loading: boolean
  error: boolean
  onClose: () => void
}) {
  const [sourceQuantity, setSourceQuantity] = useState('')
  const [totalCost, setTotalCost] = useState('')
  const projection = useMutation({
    mutationFn: () => corporateEventReviewService.projectionPlan(
      event.id,
      sourceQuantity,
      totalCost,
    ),
  })
  const validProjectionInputs = Number(sourceQuantity) >= 0
    && sourceQuantity.trim() !== ''
    && Number(totalCost) >= 0
    && totalCost.trim() !== ''

  return (
    <Modal open onClose={onClose} title={`Evidências de ${event.ticker}`} size="xl">
      {loading ? (
        <div className="flex justify-center p-8"><Loader2 className="animate-spin" /></div>
      ) : error || !evidence ? (
        <div className="rounded-lg p-4 text-sm" style={{ background: '#dc262612', color: '#b91c1c' }}>
          Não foi possível carregar as evidências deste evento.
        </div>
      ) : (
        <div className="flex flex-col gap-5">
          <div
            className="rounded-lg p-3 text-sm flex gap-2"
            style={{
              background: evidence.terms_complete ? '#16a34a12' : '#dc262612',
              color: evidence.terms_complete ? '#15803d' : '#b91c1c',
            }}
          >
            {evidence.terms_complete ? <CheckCircle2 size={18} /> : <AlertTriangle size={18} />}
            <span>
              Efeito: <strong>{evidence.economic_effect}</strong>.{' '}
              {evidence.terms_complete
                ? evidence.automatic_application_supported
                  ? 'Termos completos e tipo suportado pelo projetor automático.'
                  : 'Termos completos, mas a aplicação permanece manual.'
                : `Aprovação bloqueada; faltam: ${evidence.missing_terms.join(', ')}.`}
            </span>
          </div>
          <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>
            Compare os campos econômicos antes de decidir. Linhas destacadas divergem entre as fontes.
          </p>
          {evidence.destination_resolution_status && (
            <div className="grid grid-cols-2 gap-3 rounded-lg p-3 text-sm" style={{ border: '1px solid var(--color-border)' }}>
              <span style={{ color: 'var(--color-text-muted)' }}>Resolução do destino</span>
              <strong>{evidence.destination_resolution_status}</strong>
              <span style={{ color: 'var(--color-text-muted)' }}>Ativo resolvido</span>
              <strong>{evidence.destination_ticker ?? '—'}{evidence.destination_asset_id ? ` · #${evidence.destination_asset_id}` : ''}</strong>
              {!!evidence.destination_candidate_ids.length && evidence.destination_resolution_status !== 'RESOLVED' && (
                <><span style={{ color: 'var(--color-text-muted)' }}>Candidatos</span><strong>{evidence.destination_candidate_ids.join(', ')}</strong></>
              )}
            </div>
          )}
          {evidence.economic_effect === 'DESTINATION_ASSET_EXCHANGE' && (
            <div className="rounded-lg p-4 flex flex-col gap-3" style={{ border: '1px solid var(--color-border)' }}>
              <h3 className="font-semibold">Simulador econômico</h3>
              <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                A simulação é somente leitura e não altera posições, custos ou caixa.
              </p>
              <div className="grid gap-3 sm:grid-cols-2">
                <label className="flex flex-col gap-1 text-sm">Quantidade na origem
                  <input className="input" type="number" min="0" step="any" value={sourceQuantity} onChange={item => setSourceQuantity(item.target.value)} />
                </label>
                <label className="flex flex-col gap-1 text-sm">Custo total atual
                  <input className="input" type="number" min="0" step="any" value={totalCost} onChange={item => setTotalCost(item.target.value)} />
                </label>
              </div>
              <button className="btn btn-secondary self-start" disabled={!validProjectionInputs || projection.isPending} onClick={() => projection.mutate()}>
                {projection.isPending && <Loader2 size={15} className="animate-spin" />} Simular projeção
              </button>
              {projection.isError && <div className="text-sm" style={{ color: '#b91c1c' }}>{errorMessage(projection.error)}</div>}
              {projection.data && (
                <div className="grid grid-cols-2 gap-3 rounded-lg p-3 text-sm" style={{ background: 'var(--color-surface-offset)' }}>
                  <span>Quantidade final na origem</span><strong>{projection.data.source_quantity_after}</strong>
                  <span>Quantidade recebida</span><strong>{projection.data.destination_quantity_delta}</strong>
                  <span>Fração liquidada</span><strong>{projection.data.destination_fractional_quantity}</strong>
                  <span>Custo na origem</span><strong>{projection.data.allocated_source_cost ?? '—'}</strong>
                  <span>Custo no destino</span><strong>{projection.data.allocated_destination_cost ?? '—'}</strong>
                  <span>Caixa total</span><strong>{projection.data.cash_component_total}</strong>
                  <span>Estado do plano</span><strong style={{ color: projection.data.executable ? '#15803d' : '#b91c1c' }}>{projection.data.executable ? 'Completo' : 'Bloqueado'}</strong>
                  {!!projection.data.blocking_reasons.length && <><span>Bloqueios</span><strong>{projection.data.blocking_reasons.join(', ')}</strong></>}
                </div>
              )}
            </div>
          )}
          <div className="overflow-x-auto rounded-lg" style={{ border: '1px solid var(--color-border)' }}>
            <table className="w-full text-sm">
              <thead style={{ background: 'var(--color-surface-offset)' }}>
                <tr className="text-left">
                  <th className="p-3">Campo</th>
                  {evidence.evidences.map(item => (
                    <th className="p-3" key={item.id}>
                      {item.source_provider}<div className="text-xs font-normal">#{item.id}</div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {evidence.comparisons.map(comparison => (
                  <tr
                    key={comparison.field}
                    style={{
                      borderTop: '1px solid var(--color-divider)',
                      background: comparison.divergent ? '#d9770610' : undefined,
                    }}
                  >
                    <td className="p-3 font-medium">
                      {comparisonLabels[comparison.field] ?? comparison.field}
                      {comparison.divergent && <span className="ml-2 text-xs" style={{ color: '#d97706' }}>divergente</span>}
                    </td>
                    {evidence.evidences.map(item => (
                      <td className="p-3 tabular-nums" key={item.id}>{comparison.values[String(item.id)] ?? '—'}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            {evidence.evidences.map(item => (
              <details key={item.id} className="rounded-lg p-3" style={{ border: '1px solid var(--color-border)' }}>
                <summary className="cursor-pointer font-medium">Payload bruto · {item.source_provider} #{item.id}</summary>
                <pre className="mt-3 max-h-72 overflow-auto whitespace-pre-wrap break-all rounded p-3 text-xs" style={{ background: 'var(--color-surface-offset)' }}>
                  {JSON.stringify(item.raw_metadata, null, 2)}
                </pre>
              </details>
            ))}
          </div>
          <div className="flex justify-end"><button className="btn btn-secondary" onClick={onClose}>Fechar</button></div>
        </div>
      )}
    </Modal>
  )
}

function ReviewModal({
  event,
  decision,
  pending,
  onClose,
  onConfirm,
}: {
  event: CorporateEventReviewItem
  decision: CorporateEventReviewDecision
  pending: boolean
  onClose: () => void
  onConfirm: (note: string) => void
}) {
  const [note, setNote] = useState('')
  const valid = note.trim().length >= 10
  const approving = decision === 'APPROVE'

  return (
    <Modal
      open
      onClose={pending ? () => undefined : onClose}
      title={approving ? `Aprovar ${event.ticker}` : `Rejeitar ${event.ticker}`}
      size="md"
    >
      <div className="flex flex-col gap-4">
        {event.reconciliation_status === 'CONFLICT' && approving && (
          <div className="rounded-lg p-3 text-sm flex gap-2" style={{ background: '#dc262612', color: '#b91c1c' }}>
            <AlertTriangle size={18} className="shrink-0" />
            <span>Esta evidência será escolhida como canônica e as concorrentes do mesmo grupo serão rejeitadas.</span>
          </div>
        )}
        <div className="grid grid-cols-2 gap-3 text-sm">
          <span style={{ color: 'var(--color-text-muted)' }}>Evento</span><strong>{event.event_type}</strong>
          <span style={{ color: 'var(--color-text-muted)' }}>Data efetiva</span><strong>{new Date(`${event.effective_date}T12:00:00`).toLocaleDateString('pt-BR')}</strong>
          <span style={{ color: 'var(--color-text-muted)' }}>Fator</span><strong>{event.quantity_factor}</strong>
          <span style={{ color: 'var(--color-text-muted)' }}>Fonte</span><strong>{event.source_provider}</strong>
        </div>
        <label className="flex flex-col gap-2 text-sm font-medium">
          Justificativa obrigatória
          <textarea
            value={note}
            onChange={event => setNote(event.target.value)}
            rows={5}
            maxLength={2000}
            autoFocus
            placeholder="Descreva a evidência verificada e o motivo da decisão."
            className="input resize-y"
            aria-label="Justificativa da revisão"
          />
          <span className="text-xs font-normal" style={{ color: valid ? 'var(--color-text-muted)' : '#d97706' }}>
            {note.trim().length}/2000 caracteres · mínimo 10
          </span>
        </label>
        <div className="flex justify-end gap-2">
          <button className="btn btn-secondary" onClick={onClose} disabled={pending}>Cancelar</button>
          <button
            className={approving ? 'btn btn-primary' : 'btn'}
            style={approving ? undefined : { background: '#dc2626', color: 'white' }}
            disabled={!valid || pending}
            onClick={() => onConfirm(note.trim())}
          >
            {pending && <Loader2 size={15} className="animate-spin" />}
            Confirmar {approving ? 'aprovação' : 'rejeição'}
          </button>
        </div>
      </div>
    </Modal>
  )
}

export default function CorporateEventReviewPanel() {
  const queryClient = useQueryClient()
  const [page, setPage] = useState(1)
  const [tickerInput, setTickerInput] = useState('')
  const [ticker, setTicker] = useState('')
  const [reconciliation, setReconciliation] = useState('')
  const [selection, setSelection] = useState<{
    event: CorporateEventReviewItem
    decision: CorporateEventReviewDecision
  } | null>(null)
  const [evidenceEvent, setEvidenceEvent] = useState<CorporateEventReviewItem | null>(null)
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  const filters = useMemo(() => ({
    page,
    page_size: PAGE_SIZE,
    ticker: ticker || undefined,
    reconciliation_status: reconciliation || undefined,
  }), [page, ticker, reconciliation])

  const query = useQuery({
    queryKey: ['corporate-event-reviews', filters],
    queryFn: () => corporateEventReviewService.list(filters),
  })
  const evidenceQuery = useQuery({
    queryKey: ['corporate-event-evidence', evidenceEvent?.id],
    queryFn: () => corporateEventReviewService.evidence(evidenceEvent!.id),
    enabled: evidenceEvent !== null,
  })
  const mutation = useMutation({
    mutationFn: ({ eventId, decision, note }: { eventId: number; decision: CorporateEventReviewDecision; note: string }) =>
      corporateEventReviewService.review(eventId, decision, note),
    onSuccess: reviewed => {
      setSelection(null)
      setFeedback({ type: 'success', text: `Evento ${reviewed.ticker} revisado com sucesso.` })
      queryClient.invalidateQueries({ queryKey: ['corporate-event-reviews'] })
      queryClient.invalidateQueries({ queryKey: ['auditLogs'] })
    },
    onError: error => setFeedback({ type: 'error', text: errorMessage(error) }),
  })

  const totalPages = Math.max(1, Math.ceil((query.data?.total ?? 0) / PAGE_SIZE))

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end gap-3">
        <label className="flex flex-col gap-1 text-xs font-medium">
          Ticker
          <div className="flex gap-2">
            <div className="relative">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: 'var(--color-text-faint)' }} />
              <input
                className="input pl-9 uppercase"
                value={tickerInput}
                onChange={event => setTickerInput(event.target.value)}
                onKeyDown={event => {
                  if (event.key === 'Enter') {
                    setTicker(tickerInput.trim().toUpperCase())
                    setPage(1)
                  }
                }}
                placeholder="PETR4"
              />
            </div>
            <button
              className="btn btn-secondary"
              onClick={() => {
                setTicker(tickerInput.trim().toUpperCase())
                setPage(1)
              }}
            >Buscar</button>
          </div>
        </label>
        <label className="flex flex-col gap-1 text-xs font-medium">
          Reconciliação
          <select
            className="input"
            value={reconciliation}
            onChange={event => {
              setReconciliation(event.target.value)
              setPage(1)
            }}
          >
            <option value="">Todas pendentes</option>
            <option value="CONFLICT">Conflitos</option>
            <option value="UNRECONCILED">Fonte única</option>
            <option value="REVIEW_REQUIRED">Tipo complexo</option>
          </select>
        </label>
        <button className="btn btn-secondary" onClick={() => query.refetch()} disabled={query.isFetching}>
          <RefreshCw size={15} className={query.isFetching ? 'animate-spin' : ''} /> Atualizar
        </button>
      </div>

      {feedback && (
        <div
          role="status"
          className="rounded-lg p-3 text-sm flex items-center gap-2"
          style={{ background: feedback.type === 'success' ? '#16a34a12' : '#dc262612', color: feedback.type === 'success' ? '#15803d' : '#b91c1c' }}
        >
          {feedback.type === 'success' ? <CheckCircle2 size={17} /> : <XCircle size={17} />}
          {feedback.text}
        </div>
      )}

      {query.isLoading ? (
        <div className="flex justify-center p-8"><Loader2 className="animate-spin" /></div>
      ) : query.isError ? (
        <div className="rounded-lg p-4 text-sm" style={{ background: '#dc262612', color: '#b91c1c' }}>
          Não foi possível carregar a fila de revisão.
        </div>
      ) : !query.data?.items.length ? (
        <div className="rounded-lg p-8 text-center" style={{ border: '1px dashed var(--color-border)' }}>
          <ShieldCheck size={28} className="mx-auto mb-2" style={{ color: 'var(--color-primary)' }} />
          <p className="font-medium">Nenhum evento aguarda revisão</p>
          <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>A fila está reconciliada para os filtros selecionados.</p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg" style={{ border: '1px solid var(--color-border)' }}>
          <table className="w-full text-sm">
            <thead style={{ background: 'var(--color-surface-offset)' }}>
              <tr className="text-left">
                <th className="p-3">Ativo / evento</th>
                <th className="p-3">Data / fator</th>
                <th className="p-3">Fonte</th>
                <th className="p-3">Estado</th>
                <th className="p-3">Motivo</th>
                <th className="p-3 text-right">Decisão</th>
              </tr>
            </thead>
            <tbody>
              {query.data.items.map(event => (
                <tr key={event.id} style={{ borderTop: '1px solid var(--color-divider)' }}>
                  <td className="p-3"><strong>{event.ticker}</strong><div className="text-xs" style={{ color: 'var(--color-text-muted)' }}>{event.event_type} · #{event.id}</div></td>
                  <td className="p-3 tabular-nums">{new Date(`${event.effective_date}T12:00:00`).toLocaleDateString('pt-BR')}<div className="text-xs" style={{ color: 'var(--color-text-muted)' }}>× {event.quantity_factor}</div></td>
                  <td className="p-3">{event.source_provider}<div className="text-xs max-w-40 truncate" title={event.source_event_id ?? ''} style={{ color: 'var(--color-text-muted)' }}>{event.source_event_id ?? 'sem ID'}</div></td>
                  <td className="p-3"><span className="rounded-full px-2 py-1 text-xs font-semibold" style={badgeStyle(event.reconciliation_status)}>{event.reconciliation_status}</span></td>
                  <td className="p-3 max-w-xs text-xs" style={{ color: 'var(--color-text-muted)' }}>{event.review_reason ?? 'Revisão manual necessária'}</td>
                  <td className="p-3"><div className="flex justify-end gap-2"><button className="btn btn-secondary" onClick={() => setEvidenceEvent(event)}><FileSearch size={15} /> Evidências</button><button className="btn btn-secondary" onClick={() => setSelection({ event, decision: 'REJECT' })}><XCircle size={15} /> Rejeitar</button><button className="btn btn-primary" onClick={() => setSelection({ event, decision: 'APPROVE' })}><CheckCircle2 size={15} /> Aprovar</button></div></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="flex items-center justify-between text-sm">
        <span style={{ color: 'var(--color-text-muted)' }}>{query.data?.total ?? 0} evento(s) pendente(s)</span>
        <div className="flex items-center gap-2">
          <button className="btn btn-secondary" aria-label="Página anterior" disabled={page <= 1} onClick={() => setPage(value => value - 1)}><ChevronLeft size={15} /></button>
          <span>Página {page} de {totalPages}</span>
          <button className="btn btn-secondary" aria-label="Próxima página" disabled={page >= totalPages} onClick={() => setPage(value => value + 1)}><ChevronRight size={15} /></button>
        </div>
      </div>

      {selection && (
        <ReviewModal
          event={selection.event}
          decision={selection.decision}
          pending={mutation.isPending}
          onClose={() => setSelection(null)}
          onConfirm={note => mutation.mutate({ eventId: selection.event.id, decision: selection.decision, note })}
        />
      )}
      {evidenceEvent && (
        <EvidenceModal
          event={evidenceEvent}
          evidence={evidenceQuery.data}
          loading={evidenceQuery.isLoading}
          error={evidenceQuery.isError}
          onClose={() => setEvidenceEvent(null)}
        />
      )}
    </div>
  )
}
