import { useState } from 'react'
import { PieChart, Plus, Trash2, Loader2, Save } from 'lucide-react'
import { useAppStore } from '@/store/appStore'
import { useClassTargets, useUpsertClassTarget, useDeleteClassTarget } from '@/hooks/useClassTargets'

const ASSET_TYPES: { value: string; label: string }[] = [
  { value: 'ACAO',               label: 'Ações'              },
  { value: 'FII',                label: 'FIIs'               },
  { value: 'ETF_NACIONAL',       label: 'ETF Nacional'       },
  { value: 'ETF_INTERNACIONAL',  label: 'ETF Internacional'  },
  { value: 'STOCK',              label: "Stock / Int'l"      },
  { value: 'TESOURO_DIRETO',     label: 'Tesouro Direto'     },
  { value: 'RENDA_FIXA',         label: 'Renda Fixa'         },
  { value: 'CRIPTO',             label: 'Cripto'             },
]

function pctColor(total: number) {
  if (total > 100) return 'var(--color-error)'
  if (total === 100) return 'var(--color-success)'
  return 'var(--color-warning)'
}

export default function DistribuicaoCarteira() {
  const portfolioId = useAppStore(s => s.selectedPortfolioId)

  const { data: targets = [], isLoading } = useClassTargets(portfolioId)
  const upsert = useUpsertClassTarget(portfolioId)
  const remove = useDeleteClassTarget(portfolioId)

  // local draft: asset_type -> pct string
  const [draft, setDraft] = useState<Record<string, string>>({})
  const [newType, setNewType] = useState('')
  const [newPct,  setNewPct]  = useState('')
  const [feedback, setFeedback] = useState<{ msg: string; isError: boolean } | null>(null)
  const [savingType, setSavingType] = useState<string | null>(null)
  const [deletingType, setDeletingType] = useState<string | null>(null)

  const totalSaved = targets.reduce((s, t) => s + t.target_pct, 0)
  const savedTypes = new Set(targets.map(t => t.asset_type))
  const availableTypes = ASSET_TYPES.filter(t => !savedTypes.has(t.value))

  function localPct(asset_type: string, fallback: number) {
    return draft[asset_type] !== undefined ? draft[asset_type] : String(fallback)
  }

  async function handleSave(asset_type: string) {
    const raw = draft[asset_type]
    if (raw === undefined) return
    const pct = parseFloat(raw)
    if (isNaN(pct) || pct < 0 || pct > 100) {
      setFeedback({ msg: 'Percentual deve ser entre 0 e 100.', isError: true })
      return
    }
    setFeedback(null)
    setSavingType(asset_type)
    try {
      await upsert.mutateAsync({ asset_type, target_pct: pct })
      setDraft(d => { const c = { ...d }; delete c[asset_type]; return c })
      setFeedback({ msg: 'Meta salva.', isError: false })
    } catch {
      setFeedback({ msg: 'Erro ao salvar meta.', isError: true })
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
    } catch {
      setFeedback({ msg: 'Erro ao remover meta.', isError: true })
    } finally {
      setDeletingType(null)
    }
  }

  async function handleAdd() {
    if (!newType || !newPct) return
    const pct = parseFloat(newPct)
    if (isNaN(pct) || pct < 0 || pct > 100) {
      setFeedback({ msg: 'Percentual deve ser entre 0 e 100.', isError: true })
      return
    }
    setFeedback(null)
    try {
      await upsert.mutateAsync({ asset_type: newType, target_pct: pct })
      setNewType('')
      setNewPct('')
      setFeedback({ msg: 'Meta adicionada.', isError: false })
    } catch {
      setFeedback({ msg: 'Erro ao adicionar meta.', isError: true })
    }
  }

  if (!portfolioId) {
    return (
      <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>
        Selecione uma carteira para configurar metas de alocação.
      </p>
    )
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Cabeçalho com total */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <PieChart size={15} style={{ color: 'var(--color-primary)' }} />
          <h2 className="text-xs font-semibold uppercase tracking-wide" style={{ color: 'var(--color-text-muted)' }}>
            Metas de alocação
          </h2>
        </div>
        <span
          className="text-xs font-semibold tabular-nums px-2 py-0.5 rounded-full"
          style={{
            color: pctColor(totalSaved),
            background: `oklch(from ${pctColor(totalSaved)} l c h / 0.1)`,
          }}
        >
          {totalSaved.toFixed(1)}% alocado
        </span>
      </div>

      {/* Lista de metas salvas */}
      {isLoading ? (
        <div className="flex items-center gap-2" style={{ color: 'var(--color-text-muted)' }}>
          <Loader2 size={14} className="animate-spin" />
          <span className="text-xs">Carregando metas…</span>
        </div>
      ) : targets.length === 0 ? (
        <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>
          Nenhuma meta configurada. Adicione abaixo.
        </p>
      ) : (
        <ul className="flex flex-col gap-2">
          {targets.map(t => {
            const label = ASSET_TYPES.find(a => a.value === t.asset_type)?.label ?? t.asset_type
            const isDirty = draft[t.asset_type] !== undefined
            return (
              <li
                key={t.asset_type}
                className="flex items-center gap-3 rounded-lg px-3 py-2"
                style={{ background: 'var(--color-surface-offset)', border: '1px solid var(--color-divider)' }}
              >
                <span className="text-sm flex-1 truncate" style={{ color: 'var(--color-text)' }}>{label}</span>
                <input
                  type="number"
                  min={0}
                  max={100}
                  step={0.1}
                  value={localPct(t.asset_type, t.target_pct)}
                  onChange={e => setDraft(d => ({ ...d, [t.asset_type]: e.target.value }))}
                  className="input text-right tabular-nums"
                  style={{ width: 72, fontSize: 14 }}
                />
                <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>%</span>
                {isDirty && (
                  <button
                    onClick={() => handleSave(t.asset_type)}
                    disabled={savingType === t.asset_type}
                    className="p-1 disabled:opacity-50"
                    style={{ color: 'var(--color-primary)' }}
                    title="Salvar"
                  >
                    {savingType === t.asset_type
                      ? <Loader2 size={14} className="animate-spin" />
                      : <Save size={14} />}
                  </button>
                )}
                <button
                  onClick={() => handleDelete(t.asset_type)}
                  disabled={deletingType === t.asset_type}
                  className="p-1 disabled:opacity-50"
                  style={{ color: 'var(--color-text-faint)' }}
                  title="Remover meta"
                >
                  {deletingType === t.asset_type
                    ? <Loader2 size={14} className="animate-spin" />
                    : <Trash2 size={14} />}
                </button>
              </li>
            )
          })}
        </ul>
      )}

      {/* Adicionar nova meta */}
      {availableTypes.length > 0 && (
        <div className="flex gap-2">
          <select
            value={newType}
            onChange={e => setNewType(e.target.value)}
            className="input flex-1 text-sm"
            style={{ fontSize: 14 }}
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
            style={{ width: 72, fontSize: 14 }}
          />
          <button
            onClick={handleAdd}
            disabled={!newType || !newPct || upsert.isPending}
            className="btn btn-primary px-3 disabled:opacity-50"
            title="Adicionar meta"
          >
            {upsert.isPending ? <Loader2 size={16} className="animate-spin" /> : <Plus size={16} />}
          </button>
        </div>
      )}

      {/* Feedback */}
      {feedback && (
        <p
          className="text-xs px-3 py-2 rounded-lg"
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
    </div>
  )
}
