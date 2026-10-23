import { useState } from 'react'
import { PieChart, Plus, Trash2, Loader2, Save, Check } from 'lucide-react'
import { useAppStore } from '@/store/appStore'
import {
  useClassTargets,
  useUpsertClassTarget,
  useBulkUpsertClassTargets,
  useDeleteClassTarget,
} from '@/hooks/useClassTargets'

const ASSET_TYPES: { value: string; label: string }[] = [
  { value: 'ACAO',               label: 'Ações'              },
  { value: 'FII',                label: 'FIIs'               },
  { value: 'BDR',                label: 'BDRs'               },
  { value: 'ETF_NACIONAL',       label: 'ETF Nacional'       },
  { value: 'ETF_INTERNACIONAL',  label: 'ETF Internacional'  },
  { value: 'STOCK',              label: "Stock / Int'l"      },
  { value: 'TESOURO_DIRETO',     label: 'Tesouro Direto'     },
  { value: 'RENDA_FIXA',         label: 'Renda Fixa'         },
  { value: 'CRIPTO',             label: 'Cripto'             },
]

function parsePercentage(raw: string): number {
  const normalized = String(raw ?? '').trim().replace(',', '.')
  return normalized === '' ? NaN : Number(normalized)
}

function extractApiError(error: unknown, fallback: string): string {
  if (error && typeof error === 'object' && 'response' in error) {
    const response = (error as { response?: { data?: { detail?: unknown } } }).response
    const detail = response?.data?.detail
    if (typeof detail === 'string' && detail.trim()) {
      return detail
    }
  }
  return fallback
}

function pctColor(total: number) {
  if (total > 100.01) return 'var(--color-error)'
  if (Math.abs(total - 100) <= 0.01) return 'var(--color-success)'
  return 'var(--color-warning)'
}

export default function DistribuicaoCarteira() {
  const portfolioId = useAppStore(s => s.selectedPortfolioId)

  const { data: targets = [], isLoading } = useClassTargets(portfolioId)
  const upsert = useUpsertClassTarget(portfolioId)
  const bulkUpsert = useBulkUpsertClassTargets(portfolioId)
  const remove = useDeleteClassTarget(portfolioId)

  const [draft, setDraft] = useState<Record<string, string>>({})
  const [newType, setNewType] = useState('')
  const [newPct,  setNewPct]  = useState('')
  const [feedback, setFeedback] = useState<{ msg: string; isError: boolean } | null>(null)
  const [savingType, setSavingType] = useState<string | null>(null)
  const [deletingType, setDeletingType] = useState<string | null>(null)

  const totalSaved = targets.reduce((s, t) => s + t.target_pct, 0)
  const totalEffective = targets.reduce((sum, t) => {
    const raw = draft[t.asset_type]
    if (raw === undefined) return sum + t.target_pct
    const parsed = parsePercentage(raw)
    return sum + (Number.isFinite(parsed) ? parsed : 0)
  }, 0)

  const dirtyEntries = Object.entries(draft).filter(([assetType, raw]) => {
    const existing = targets.find(t => t.asset_type === assetType)
    if (!existing) return true
    const parsed = parsePercentage(raw)
    return !Number.isFinite(parsed) || Math.abs(parsed - existing.target_pct) > 0.001
  })
  const hasDirtyChanges = dirtyEntries.length > 0

  const savedTypes = new Set(targets.map(t => t.asset_type))
  const availableTypes = ASSET_TYPES.filter(t => !savedTypes.has(t.value))

  function localPct(asset_type: string, fallback: number) {
    return draft[asset_type] !== undefined ? draft[asset_type] : String(fallback)
  }

  async function handleSave(asset_type: string) {
    const raw = draft[asset_type]
    if (raw === undefined) return
    const pct = parsePercentage(raw)
    if (!Number.isFinite(pct) || pct < 0 || pct > 100) {
      setFeedback({ msg: 'O percentual de cada classe deve estar entre 0% e 100%.', isError: true })
      return
    }
    setFeedback(null)
    setSavingType(asset_type)
    try {
      await upsert.mutateAsync({ asset_type, target_pct: pct })
      setDraft(d => { const c = { ...d }; delete c[asset_type]; return c })
      setFeedback({ msg: 'Meta salva com sucesso.', isError: false })
    } catch (err) {
      setFeedback({ msg: extractApiError(err, 'Erro ao salvar meta.'), isError: true })
    } finally {
      setSavingType(null)
    }
  }

  async function handleSaveAll() {
    if (!dirtyEntries.length) return
    const payload: { asset_type: string; target_pct: number }[] = []
    for (const [asset_type, raw] of dirtyEntries) {
      const pct = parsePercentage(raw)
      const label = ASSET_TYPES.find(a => a.value === asset_type)?.label ?? asset_type
      if (!Number.isFinite(pct) || pct < 0 || pct > 100) {
        setFeedback({ msg: `Valor inválido em ${label}: informe um percentual entre 0% e 100%.`, isError: true })
        return
      }
      payload.push({ asset_type, target_pct: pct })
    }

    setFeedback(null)
    setSavingType('__ALL__')
    try {
      await bulkUpsert.mutateAsync(payload)
      setDraft({})
      setFeedback({ msg: 'Todas as metas alteradas foram salvas.', isError: false })
    } catch (err) {
      setFeedback({ msg: extractApiError(err, 'Erro ao salvar metas.'), isError: true })
    } finally {
      setSavingType(null)
    }
  }

  async function handleDelete(asset_type: string) {
    setFeedback(null)
    setDeletingType(asset_type)
    try {
      await remove.mutateAsync(asset_type)
      setDraft(d => { const c = { ...d }; delete c[asset_type]; return c })
      setFeedback({ msg: 'Meta removida.', isError: false })
    } catch (err) {
      const status = (err as { response?: { status?: number } })?.response?.status
      if (status === 404) {
        setDraft(d => { const c = { ...d }; delete c[asset_type]; return c })
        setFeedback({ msg: 'Esta classe ainda não possuía meta salva.', isError: false })
      } else {
        setFeedback({ msg: extractApiError(err, 'Erro ao remover meta.'), isError: true })
      }
    } finally {
      setDeletingType(null)
    }
  }

  async function handleAdd() {
    if (!newType || !newPct) return
    const pct = parsePercentage(newPct)
    if (!Number.isFinite(pct) || pct < 0 || pct > 100) {
      setFeedback({ msg: 'O percentual deve estar entre 0% e 100%.', isError: true })
      return
    }
    setFeedback(null)
    try {
      await upsert.mutateAsync({ asset_type: newType, target_pct: pct })
      setNewType('')
      setNewPct('')
      setFeedback({ msg: 'Meta adicionada com sucesso.', isError: false })
    } catch (err) {
      setFeedback({ msg: extractApiError(err, 'Erro ao adicionar meta.'), isError: true })
    }
  }

  if (!portfolioId) {
    return (
      <div className="settings-card-body">
        <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>
          Selecione uma carteira para configurar metas de alocação.
        </p>
      </div>
    )
  }

  const badgeColor = pctColor(totalEffective)

  return (
    <>
      <div className="settings-card-header">
        <div className="flex items-center gap-3 min-w-0">
          <span className="settings-card-icon" aria-hidden="true">
            <PieChart size={16} strokeWidth={2} />
          </span>
          <div className="min-w-0">
            <h2 className="text-sm font-semibold leading-tight" style={{ color: 'var(--color-text)' }}>
              Metas de alocação por classe
            </h2>
            <p className="text-xs mt-0.5 leading-snug" style={{ color: 'var(--color-text-muted)' }}>
              Defina o percentual ideal de cada classe para orientar aportes e rebalanceamento
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {hasDirtyChanges && (
            <button
              type="button"
              onClick={handleSaveAll}
              disabled={savingType !== null}
              className="btn btn-primary text-xs px-3 py-1.5 flex items-center gap-1.5 disabled:opacity-50"
              title="Salvar todas as metas alteradas"
            >
              {savingType === '__ALL__' ? (
                <Loader2 size={13} className="animate-spin" />
              ) : (
                <Check size={13} />
              )}
              <span>Salvar alterações ({dirtyEntries.length})</span>
            </button>
          )}
          <span
            className="text-xs font-semibold tabular-nums px-2.5 py-1 rounded-full shrink-0"
            style={{
              color: badgeColor,
              background: `oklch(from ${badgeColor} l c h / 0.12)`,
            }}
            title={hasDirtyChanges ? `Salvo: ${totalSaved.toFixed(1)}% · Em edição: ${totalEffective.toFixed(1)}%` : undefined}
          >
            {totalEffective.toFixed(1)}% alocado{hasDirtyChanges ? ' *' : ''}
          </span>
        </div>
      </div>

      <div className="settings-card-body">
        {isLoading ? (
          <div className="flex items-center gap-2 py-2" style={{ color: 'var(--color-text-muted)' }}>
            <Loader2 size={14} className="animate-spin" />
            <span className="text-xs">Carregando metas…</span>
          </div>
        ) : targets.length === 0 ? (
          <p className="text-sm py-2" style={{ color: 'var(--color-text-muted)' }}>
            Nenhuma meta configurada. Adicione abaixo.
          </p>
        ) : (
          <ul className="flex flex-col gap-2">
            {targets.map(t => {
              const label = ASSET_TYPES.find(a => a.value === t.asset_type)?.label ?? t.label ?? t.asset_type
              const rawDraft = draft[t.asset_type]
              const isDirty = rawDraft !== undefined && Math.abs(parsePercentage(rawDraft) - t.target_pct) > 0.001
              return (
                <li
                  key={t.asset_type}
                  className="settings-list-row"
                  style={{
                    background: 'var(--color-surface-offset)',
                    border: isDirty
                      ? '1px solid oklch(from var(--color-primary) l c h / 0.45)'
                      : '1px solid oklch(from var(--color-text) l c h / 0.08)',
                  }}
                >
                  <span className="text-sm font-medium flex-1 truncate" style={{ color: 'var(--color-text)' }}>
                    {label}
                  </span>
                  <div className="flex items-center gap-2 shrink-0">
                    <input
                      type="number"
                      min={0}
                      max={100}
                      step={0.1}
                      value={localPct(t.asset_type, t.target_pct)}
                      onChange={e => setDraft(d => ({ ...d, [t.asset_type]: e.target.value }))}
                      onKeyDown={e => {
                        if (e.key === 'Enter' && isDirty) {
                          e.preventDefault()
                          void handleSave(t.asset_type)
                        }
                      }}
                      className="input text-right tabular-nums"
                      style={{ width: 76 }}
                    />
                    <span className="text-xs font-medium" style={{ color: 'var(--color-text-muted)' }}>%</span>
                    {isDirty && (
                      <button
                        type="button"
                        onClick={() => handleSave(t.asset_type)}
                        disabled={savingType !== null}
                        className="settings-icon-button disabled:opacity-50"
                        style={{ color: 'var(--color-primary)' }}
                        title="Salvar esta classe (Enter)"
                      >
                        {savingType === t.asset_type ? (
                          <Loader2 size={14} className="animate-spin" />
                        ) : (
                          <Save size={14} />
                        )}
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={() => handleDelete(t.asset_type)}
                      disabled={deletingType === t.asset_type || savingType !== null}
                      className="settings-icon-button disabled:opacity-50"
                      style={{ color: 'var(--color-text-muted)' }}
                      title="Remover meta"
                    >
                      {deletingType === t.asset_type ? (
                        <Loader2 size={14} className="animate-spin" />
                      ) : (
                        <Trash2 size={14} />
                      )}
                    </button>
                  </div>
                </li>
              )
            })}
          </ul>
        )}

        {availableTypes.length > 0 && (
          <div
            className="pt-3 mt-1 flex flex-col gap-2"
            style={{ borderTop: '1px solid oklch(from var(--color-text) l c h / 0.07)' }}
          >
            <span className="text-xs font-medium" style={{ color: 'var(--color-text-muted)' }}>
              Adicionar nova classe
            </span>
            <div className="flex items-center gap-2 flex-wrap sm:flex-nowrap">
              <select
                value={newType}
                onChange={e => setNewType(e.target.value)}
                className="select-modern flex-1 min-w-[180px]"
              >
                <option value="">Selecionar classe…</option>
                {availableTypes.map(t => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
              <input
                type="number"
                min={0}
                max={100}
                step={0.1}
                placeholder="%"
                value={newPct}
                onChange={e => setNewPct(e.target.value)}
                className="input text-right tabular-nums"
                style={{ width: 84 }}
              />
              <button
                onClick={handleAdd}
                disabled={!newType || !newPct || upsert.isPending}
                className="btn btn-primary px-3.5 disabled:opacity-50"
                title="Adicionar meta"
              >
                {upsert.isPending ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />}
                <span>Adicionar</span>
              </button>
            </div>
          </div>
        )}

        {feedback && (
          <p
            className="text-xs px-3 py-2 rounded-lg"
            style={{
              color: feedback.isError ? 'var(--color-error)' : 'var(--color-success)',
              background: feedback.isError
                ? 'oklch(from var(--color-error) l c h / 0.1)'
                : 'oklch(from var(--color-success) l c h / 0.1)',
            }}
          >
            {feedback.msg}
          </p>
        )}
      </div>
    </>
  )
}
