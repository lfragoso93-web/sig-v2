import { useState, type FormEvent } from 'react'
import { Clock3, CheckCircle2, PencilLine, RotateCcw } from 'lucide-react'
import {
  useDeleteCorporateFractionSettlement,
  usePendingCorporateFractions,
  usePortfolioCorporateRights,
  useUpsertCorporateFractionSettlement,
} from '@/hooks/usePortfolio'

interface EditingSettlementTarget {
  sourceEventId: string
  ticker: string
  eventLabel: string
  defaultDate: string
  initialAmount: string
}

function parseBrlInput(raw: string): number | null {
  const cleaned = raw.trim().replace(/\s+/g, '')
  if (!cleaned) return null
  const normalized = cleaned.includes(',')
    ? cleaned.replace(/\./g, '').replace(',', '.')
    : cleaned
  const parsed = Number(normalized)
  if (!Number.isFinite(parsed) || parsed < 0) return null
  return Math.round(parsed * 100) / 100
}

function formatBrl(value: number): string {
  return Number(value).toLocaleString('pt-BR', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}

export default function PendingCorporateFractionsPanel({
  portfolioId,
}: {
  portfolioId: number
}) {
  const { data: fractions = [], isLoading, error } =
    usePendingCorporateFractions(portfolioId)
  const rightsQuery = usePortfolioCorporateRights(portfolioId)
  const rights = rightsQuery.data ?? []

  const upsertSettlement = useUpsertCorporateFractionSettlement(portfolioId)
  const deleteSettlement = useDeleteCorporateFractionSettlement(portfolioId)

  const [editing, setEditing] = useState<EditingSettlementTarget | null>(null)
  const [amountInput, setAmountInput] = useState('')
  const [dateInput, setDateInput] = useState('')
  const [notesInput, setNotesInput] = useState('')
  const [formError, setFormError] = useState<string | null>(null)

  if (!isLoading && !error && fractions.length === 0 && rights.length === 0) return null

  const openEditor = (target: EditingSettlementTarget) => {
    setEditing(target)
    setAmountInput(target.initialAmount)
    setDateInput(target.defaultDate)
    setNotesInput('')
    setFormError(null)
  }

  const closeEditor = () => {
    setEditing(null)
    setAmountInput('')
    setDateInput('')
    setNotesInput('')
    setFormError(null)
  }

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    if (!editing) return
    const parsedAmount = parseBrlInput(amountInput)
    if (parsedAmount === null) {
      setFormError('Informe um valor válido em reais (ex.: 15,23).')
      return
    }
    setFormError(null)
    try {
      await upsertSettlement.mutateAsync({
        source_event_id: editing.sourceEventId,
        gross_amount_brl: parsedAmount,
        settlement_date: dateInput.trim() || null,
        notes: notesInput.trim() || null,
      })
      closeEditor()
    } catch {
      setFormError('Não foi possível salvar o valor do leilão de frações.')
    }
  }

  const handleClear = async (sourceEventId: string) => {
    try {
      await deleteSettlement.mutateAsync(sourceEventId)
      if (editing?.sourceEventId === sourceEventId) {
        closeEditor()
      }
    } catch {
      setFormError('Não foi possível remover a liquidação manual.')
    }
  }

  const isBusy = upsertSettlement.isPending || deleteSettlement.isPending

  return (
    <section className="card overflow-hidden" aria-labelledby="corporate-events-calendar-title">
      <div className="section-card-header">
        <div className="flex items-center gap-2">
          <Clock3 size={15} style={{ color: 'var(--color-warning)' }} />
          <span id="corporate-events-calendar-title" className="section-card-title">
            Calendário de Eventos Corporativos
          </span>
        </div>
      </div>
      <div className="p-5 md:p-6">
        {isLoading ? (
          <div className="h-16 skeleton rounded" />
        ) : error ? (
          <p role="alert" className="text-sm" style={{ color: 'var(--color-error)' }}>
            Não foi possível carregar os eventos corporativos e direitos da carteira.
          </p>
        ) : (
          <>
            <p className="text-xs mb-4" style={{ color: 'var(--color-text-muted)' }}>
              Histórico completo de eventos corporativos aplicados aos ativos da carteira e frações — a fração é calculada pela quantidade da sua carteira na data efetiva. Quando liquidada em leilão, exibe o valor creditado; você também pode informar ou ajustar manualmente o valor recebido no extrato da corretora.
            </p>
            {fractions.length > 0 && (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-xs" style={{ color: 'var(--color-text-faint)' }}>
                      <th className="py-2 pr-4 font-medium">Ativo</th>
                      <th className="py-2 pr-4 font-medium">Evento</th>
                      <th className="py-2 pr-4 font-medium">Data</th>
                      <th className="py-2 text-right font-medium">Quantidade / Fator</th>
                      <th className="py-2 pl-4 text-right font-medium">Valor / Status</th>
                      <th className="py-2 pl-4 text-right font-medium">Ação</th>
                    </tr>
                  </thead>
                  <tbody>
                    {fractions.map(fraction => {
                      const hasFraction =
                        fraction.fractional_quantity != null && Number(fraction.fractional_quantity) > 0
                      const isUserConfirmed =
                        fraction.cash_treatment === 'PORTFOLIO_USER_CONFIRMED_AUCTION'

                      return (
                        <tr
                          key={`${fraction.source_event_id}-${fraction.ticker}`}
                          className="border-t"
                          style={{ borderColor: 'var(--color-divider)' }}
                        >
                          <td className="py-3 pr-4 font-semibold">{fraction.ticker}</td>
                          <td className="py-3 pr-4">{fraction.event_type}</td>
                          <td className="py-3 pr-4">
                            {fraction.event_date.split('-').reverse().join('/')}
                          </td>
                          <td className="py-3 text-right tabular-nums">
                            {fraction.fractional_quantity != null
                              ? Number(fraction.fractional_quantity).toLocaleString('pt-BR')
                              : `Fator ${Number(fraction.quantity_factor).toLocaleString('pt-BR')}`}
                          </td>
                          <td className="py-3 pl-4 text-right" style={{ color: 'var(--color-text-muted)' }}>
                            {fraction.settlement_status === 'SETTLED' && fraction.gross_amount_brl != null ? (
                              <div>
                                <span className="font-medium" style={{ color: 'var(--color-success, #16a34a)' }}>
                                  R$ {formatBrl(fraction.gross_amount_brl)} (Leilão liquidado)
                                </span>
                                {fraction.realized_pnl_brl != null && (
                                  <span className="block text-xs" style={{ color: 'var(--color-text-faint)' }}>
                                    Resultado: R$ {formatBrl(fraction.realized_pnl_brl)}
                                  </span>
                                )}
                              </div>
                            ) : fraction.settlement_status === 'PENDING_VALUE' ? (
                              <div>
                                <span>A confirmar</span>
                                <span className="block text-xs" style={{ color: 'var(--color-text-faint)' }}>Aguardando leilão</span>
                              </div>
                            ) : (
                              <span>Aplicado</span>
                            )}
                          </td>
                          <td className="py-3 pl-4 text-right whitespace-nowrap">
                            {fraction.settlement_status === 'PENDING_VALUE' && hasFraction ? (
                              <button
                                type="button"
                                disabled={isBusy}
                                onClick={() =>
                                  openEditor({
                                    sourceEventId: fraction.source_event_id,
                                    ticker: fraction.ticker,
                                    eventLabel: `${fraction.ticker} · ${fraction.event_type}`,
                                    defaultDate: fraction.event_date,
                                    initialAmount: '',
                                  })
                                }
                                className="inline-flex items-center gap-1 rounded px-2.5 py-1 text-xs font-medium border transition-colors hover:opacity-90"
                                style={{
                                  borderColor: 'var(--color-divider)',
                                  color: 'var(--color-text-primary)',
                                }}
                              >
                                <PencilLine size={12} />
                                Informar leilão
                              </button>
                            ) : isUserConfirmed ? (
                              <div className="inline-flex items-center gap-2">
                                <button
                                  type="button"
                                  disabled={isBusy}
                                  onClick={() =>
                                    openEditor({
                                      sourceEventId: fraction.source_event_id,
                                      ticker: fraction.ticker,
                                      eventLabel: `${fraction.ticker} · ${fraction.event_type}`,
                                      defaultDate: fraction.event_date,
                                      initialAmount:
                                        fraction.gross_amount_brl != null
                                          ? formatBrl(fraction.gross_amount_brl)
                                          : '',
                                    })
                                  }
                                  className="inline-flex items-center gap-1 rounded px-2 py-1 text-xs font-medium border"
                                  style={{ borderColor: 'var(--color-divider)' }}
                                >
                                  <PencilLine size={12} />
                                  Editar
                                </button>
                                <button
                                  type="button"
                                  disabled={isBusy}
                                  onClick={() => void handleClear(fraction.source_event_id)}
                                  className="inline-flex items-center gap-1 rounded px-2 py-1 text-xs"
                                  style={{ color: 'var(--color-text-faint)' }}
                                  aria-label={`Remover liquidação de ${fraction.ticker}`}
                                >
                                  <RotateCcw size={12} />
                                  Limpar
                                </button>
                              </div>
                            ) : null}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}

        {editing && (
          <form
            onSubmit={e => void handleSubmit(e)}
            className="mt-4 rounded-lg border p-4 space-y-3"
            style={{
              borderColor: 'var(--color-divider)',
              backgroundColor: 'var(--color-surface-subtle, rgba(148, 163, 184, 0.06))',
            }}
            aria-label={`Liquidação do leilão de frações ${editing.ticker}`}
          >
            <div className="flex items-center justify-between gap-2">
              <h4 className="text-sm font-semibold">
                Informar valor do leilão — {editing.eventLabel}
              </h4>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <div>
                <label
                  htmlFor="auction-gross-amount"
                  className="block text-xs font-medium mb-1"
                  style={{ color: 'var(--color-text-muted)' }}
                >
                  Valor recebido no leilão (R$)
                </label>
                <input
                  id="auction-gross-amount"
                  type="text"
                  inputMode="decimal"
                  required
                  placeholder="Ex.: 15,23"
                  value={amountInput}
                  onChange={e => setAmountInput(e.target.value)}
                  className="input w-full text-sm"
                />
              </div>
              <div>
                <label
                  htmlFor="auction-settlement-date"
                  className="block text-xs font-medium mb-1"
                  style={{ color: 'var(--color-text-muted)' }}
                >
                  Data do crédito
                </label>
                <input
                  id="auction-settlement-date"
                  type="date"
                  value={dateInput}
                  onChange={e => setDateInput(e.target.value)}
                  className="input w-full text-sm"
                />
              </div>
              <div>
                <label
                  htmlFor="auction-settlement-notes"
                  className="block text-xs font-medium mb-1"
                  style={{ color: 'var(--color-text-muted)' }}
                >
                  Observação (opcional)
                </label>
                <input
                  id="auction-settlement-notes"
                  type="text"
                  maxLength={500}
                  placeholder="Ex.: Nota / extrato corretora"
                  value={notesInput}
                  onChange={e => setNotesInput(e.target.value)}
                  className="input w-full text-sm"
                />
              </div>
            </div>
            {formError && (
              <p role="alert" className="text-xs" style={{ color: 'var(--color-error)' }}>
                {formError}
              </p>
            )}
            <div className="flex items-center justify-end gap-2">
              <button
                type="button"
                onClick={closeEditor}
                disabled={isBusy}
                className="px-3 py-1.5 text-xs rounded border"
                style={{ borderColor: 'var(--color-divider)' }}
              >
                Cancelar
              </button>
              <button
                type="submit"
                disabled={isBusy}
                className="btn-primary px-3 py-1.5 text-xs rounded"
              >
                {upsertSettlement.isPending ? 'Salvando...' : 'Salvar liquidação'}
              </button>
            </div>
          </form>
        )}

        {rights.length > 0 && (
          <div className={fractions.length > 0 ? 'mt-6 border-t pt-5' : ''}>
            <h3 className="text-sm font-semibold mb-3">Apuração de bonificação por carteira</h3>
            <p className="text-xs mb-4" style={{ color: 'var(--color-text-muted)' }}>
              Quantidades calculadas pela posição na data-base. O valor das frações é uma estimativa bruta baseada na evidência do emissor; confirme ou ajuste o crédito recebido em conta quando liquidado.
            </p>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs" style={{ color: 'var(--color-text-faint)' }}>
                    <th className="py-2 pr-4 font-medium">Ativo / espécie</th>
                    <th className="py-2 pr-4 font-medium">Data-base</th>
                    <th className="py-2 pr-4 font-medium">Ações usadas em Units</th>
                    <th className="py-2 text-right font-medium">Ações inteiras / fração</th>
                    <th className="py-2 pl-4 text-right font-medium">Estimativa / Creditado</th>
                    <th className="py-2 pl-4 text-right font-medium">Custo atribuído à fração</th>
                    <th className="py-2 pl-4 text-right font-medium">Resultado estimado</th>
                    <th className="py-2 pl-4 text-right font-medium">Ação</th>
                  </tr>
                </thead>
                <tbody>
                  {rights.flatMap(right => right.components.map(component => (
                    <tr key={`${right.event_id}:${component.component}`} className="border-t" style={{ borderColor: 'var(--color-divider)' }}>
                      <td className="py-3 pr-4 font-semibold">{right.ticker} · {component.component}</td>
                      <td className="py-3 pr-4">{right.record_date.split('-').reverse().join('/')}</td>
                      <td className="py-3 pr-4 tabular-nums">{component.component_shares_in_units.toLocaleString('pt-BR')}</td>
                      <td className="py-3 text-right tabular-nums">{component.residual_whole_quantity.toLocaleString('pt-BR')} / {component.fractional_quantity.toLocaleString('pt-BR')}</td>
                      <td className="py-3 pl-4 text-right tabular-nums">R$ {formatBrl(component.gross_amount_brl)}</td>
                      <td className="py-3 pl-4 text-right tabular-nums">R$ {formatBrl(component.fractional_cost_basis_brl)}</td>
                      <td className="py-3 pl-4 text-right tabular-nums">R$ {formatBrl(component.estimated_fractional_result_brl)}</td>
                      <td className="py-3 pl-4" />
                    </tr>
                  )))}
                  {rights.map(right => (
                    <tr key={`${right.event_id}:total`} className="border-t font-semibold" style={{ borderColor: 'var(--color-divider)' }}>
                      <td className="py-3 pr-4">Total {right.ticker}</td>
                      <td className="py-3 pr-4" colSpan={3}>
                        {right.cash_status === 'CONFIRMED' ? (
                          <span className="inline-flex items-center gap-1" style={{ color: 'var(--color-success, #16a34a)' }}>
                            <CheckCircle2 size={13} />
                            Crédito confirmado manualmente
                          </span>
                        ) : right.settlement_status === 'AVAILABLE' ? (
                          'Disponível segundo o emissor; crédito individual não confirmado'
                        ) : (
                          'Data de pagamento futura'
                        )}
                      </td>
                      <td className="py-3 pl-4 text-right tabular-nums">
                        R$ {formatBrl(right.gross_amount_brl)}
                      </td>
                      <td className="py-3 pl-4 text-right tabular-nums">R$ {formatBrl(right.fractional_cost_basis_brl)}</td>
                      <td className="py-3 pl-4 text-right tabular-nums">R$ {formatBrl(right.estimated_fractional_result_brl)}</td>
                      <td className="py-3 pl-4 text-right whitespace-nowrap">
                        <div className="inline-flex items-center gap-2 font-normal">
                          <button
                            type="button"
                            disabled={isBusy}
                            onClick={() =>
                              openEditor({
                                sourceEventId: right.source_event_id,
                                ticker: right.ticker,
                                eventLabel: `${right.ticker} · ${right.event_type}`,
                                defaultDate: right.settlement_date,
                                initialAmount: formatBrl(right.gross_amount_brl),
                              })
                            }
                            className="inline-flex items-center gap-1 rounded px-2.5 py-1 text-xs font-medium border"
                            style={{ borderColor: 'var(--color-divider)' }}
                          >
                            <PencilLine size={12} />
                            {right.cash_status === 'CONFIRMED' ? 'Editar' : 'Confirmar valor'}
                          </button>
                          {right.cash_status === 'CONFIRMED' && (
                            <button
                              type="button"
                              disabled={isBusy}
                              onClick={() => void handleClear(right.source_event_id)}
                              className="inline-flex items-center gap-1 rounded px-2 py-1 text-xs"
                              style={{ color: 'var(--color-text-faint)' }}
                              aria-label={`Remover confirmação de ${right.ticker}`}
                            >
                              <RotateCcw size={12} />
                              Limpar
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </section>
  )
}
