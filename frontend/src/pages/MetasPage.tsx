import { useEffect, useState } from 'react'
import { useAppStore } from '@/store/appStore'
import { useGoals } from '@/hooks/useGoals'
import type { Goal, GoalCreate, GoalUpdate } from '@/services/goalsService'

// ─── helpers ────────────────────────────────────────────────────────────────
function fmtBRL(v: number) {
  return v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
}
function fmtDate(iso: string | null) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('pt-BR')
}
function progressColor(pct: number) {
  if (pct >= 100) return 'var(--color-success)'
  if (pct >= 60)  return 'var(--color-primary)'
  if (pct >= 30)  return 'var(--color-warning)'
  return 'var(--color-danger)'
}

// ─── Modal ──────────────────────────────────────────────────────────────────
interface ModalProps {
  initial?: Goal
  onClose: () => void
  onSave: (data: GoalCreate | GoalUpdate) => Promise<void>
}

function GoalModal({ initial, onClose, onSave }: ModalProps) {
  const [name, setName]               = useState(initial?.name ?? '')
  const [target, setTarget]           = useState(initial?.target_value ?? '')
  const [current, setCurrent]         = useState(initial?.current_value ?? '')
  const [date, setDate]               = useState(
    initial?.target_date ? initial.target_date.slice(0, 10) : ''
  )
  const [desc, setDesc]               = useState(initial?.description ?? '')
  const [saving, setSaving]           = useState(false)
  const [err, setErr]                 = useState('')

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setErr('')
    if (!name.trim()) { setErr('Nome é obrigatório.'); return }
    if (Number(target) <= 0) { setErr('Valor alvo deve ser maior que zero.'); return }
    setSaving(true)
    try {
      await onSave({
        name: name.trim(),
        target_value: Number(target),
        current_value: Number(current) || 0,
        target_date: date ? new Date(date).toISOString() : null,
        description: desc.trim() || null,
      })
      onClose()
    } catch {
      setErr('Erro ao salvar meta.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div
      style={{
        position: 'fixed', inset: 0,
        background: 'rgba(0,0,0,0.6)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        zIndex: 50,
      }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
    >
      <div style={{
        background: 'var(--color-surface)',
        border: '1px solid var(--color-border)',
        borderRadius: 12,
        padding: 28,
        width: '100%',
        maxWidth: 480,
      }}>
        <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 20, color: 'var(--color-text)' }}>
          {initial ? 'Editar Meta' : 'Nova Meta'}
        </h2>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <label style={{ fontSize: 13, color: 'var(--color-muted)' }}>
            Nome *
            <input
              value={name} onChange={e => setName(e.target.value)}
              placeholder="Ex: Reserva de emergência"
              style={inputStyle}
            />
          </label>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <label style={{ fontSize: 13, color: 'var(--color-muted)' }}>
              Valor alvo (R$) *
              <input
                type="number" min="0.01" step="0.01"
                value={target} onChange={e => setTarget(e.target.value)}
                placeholder="50000"
                style={inputStyle}
              />
            </label>
            <label style={{ fontSize: 13, color: 'var(--color-muted)' }}>
              Valor atual (R$)
              <input
                type="number" min="0" step="0.01"
                value={current} onChange={e => setCurrent(e.target.value)}
                placeholder="0"
                style={inputStyle}
              />
            </label>
          </div>

          <label style={{ fontSize: 13, color: 'var(--color-muted)' }}>
            Data alvo
            <input
              type="date"
              value={date} onChange={e => setDate(e.target.value)}
              style={inputStyle}
            />
          </label>

          <label style={{ fontSize: 13, color: 'var(--color-muted)' }}>
            Descrição
            <textarea
              value={desc} onChange={e => setDesc(e.target.value)}
              rows={2}
              placeholder="Detalhe opcional..."
              style={{ ...inputStyle, resize: 'vertical', fontFamily: 'inherit' }}
            />
          </label>

          {err && <p style={{ color: 'var(--color-danger)', fontSize: 13 }}>{err}</p>}

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 4 }}>
            <button type="button" onClick={onClose} style={btnSecondaryStyle}>Cancelar</button>
            <button type="submit" disabled={saving} style={btnPrimaryStyle}>
              {saving ? 'Salvando...' : 'Salvar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ─── Card de meta ────────────────────────────────────────────────────────────
interface CardProps {
  goal: Goal
  onEdit: (g: Goal) => void
  onDelete: (g: Goal) => void
}

function GoalCard({ goal, onEdit, onDelete }: CardProps) {
  const pct = goal.progress_pct
  const color = progressColor(pct)

  return (
    <div style={{
      background: 'var(--color-surface)',
      border: `1px solid ${goal.is_completed ? 'var(--color-success)' : 'var(--color-border)'}`,
      borderRadius: 10,
      padding: '18px 20px',
      display: 'flex',
      flexDirection: 'column',
      gap: 10,
    }}>
      {/* header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 8 }}>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 15, fontWeight: 600, color: 'var(--color-text)' }}>{goal.name}</span>
            {goal.is_completed && (
              <span style={{
                fontSize: 11, fontWeight: 700,
                background: 'var(--color-success)', color: '#fff',
                borderRadius: 99, padding: '2px 8px',
              }}>Concluída ✔</span>
            )}
          </div>
          {goal.description && (
            <p style={{ fontSize: 12, color: 'var(--color-muted)', marginTop: 2 }}>{goal.description}</p>
          )}
        </div>
        <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
          <button onClick={() => onEdit(goal)} style={iconBtnStyle} title="Editar">✏️</button>
          <button onClick={() => onDelete(goal)} style={{ ...iconBtnStyle, color: 'var(--color-danger)' }} title="Excluir">🗑️</button>
        </div>
      </div>

      {/* barra de progresso */}
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
          <span style={{ fontSize: 12, color: 'var(--color-muted)' }}>
            {fmtBRL(goal.current_value)} de {fmtBRL(goal.target_value)}
          </span>
          <span style={{ fontSize: 13, fontWeight: 700, color }}>{pct.toFixed(1)}%</span>
        </div>
        <div style={{
          height: 8, borderRadius: 99,
          background: 'var(--color-border)', overflow: 'hidden',
        }}>
          <div style={{
            height: '100%', borderRadius: 99,
            width: `${Math.min(pct, 100)}%`,
            background: color,
            transition: 'width 0.4s ease',
          }} />
        </div>
      </div>

      {/* data alvo */}
      <div style={{ fontSize: 12, color: 'var(--color-muted)' }}>
        Data alvo: {fmtDate(goal.target_date)}
      </div>
    </div>
  )
}

// ─── Page ────────────────────────────────────────────────────────────────────
export default function MetasPage() {
  const portfolioId = useAppStore((s) => s.selectedPortfolioId)
  const { goals, loading, error, loadGoals, addGoal, editGoal, removeGoal } = useGoals()

  const [showModal, setShowModal] = useState(false)
  const [editing, setEditing]     = useState<Goal | null>(null)
  const [deleting, setDeleting]   = useState<Goal | null>(null)

  useEffect(() => {
    if (portfolioId) loadGoals(portfolioId)
  }, [portfolioId, loadGoals])

  if (!portfolioId) {
    return (
      <div className="p-6">
        <p style={{ color: 'var(--color-muted)', fontSize: 14 }}>Selecione uma carteira para ver as metas.</p>
      </div>
    )
  }

  const pending   = goals.filter(g => !g.is_completed)
  const completed = goals.filter(g => g.is_completed)

  async function handleSave(data: GoalCreate | GoalUpdate) {
    if (editing) {
      await editGoal(portfolioId!, editing.id, data as GoalUpdate)
    } else {
      await addGoal(portfolioId!, data as GoalCreate)
    }
  }

  async function confirmDelete() {
    if (!deleting || !portfolioId) return
    await removeGoal(portfolioId, deleting.id)
    setDeleting(null)
  }

  return (
    <div style={{ padding: '24px 28px', maxWidth: 900 }}>
      {/* header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 24 }}>
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700, color: 'var(--color-text)' }}>Metas Financeiras</h1>
          <p style={{ fontSize: 13, color: 'var(--color-muted)', marginTop: 2 }}>
            {goals.length} {goals.length === 1 ? 'meta' : 'metas'} • {completed.length} concluída{completed.length !== 1 ? 's' : ''}
          </p>
        </div>
        <button
          onClick={() => { setEditing(null); setShowModal(true) }}
          style={btnPrimaryStyle}
        >
          + Nova Meta
        </button>
      </div>

      {/* estados */}
      {loading && <p style={{ color: 'var(--color-muted)', fontSize: 14 }}>Carregando...</p>}
      {error   && <p style={{ color: 'var(--color-danger)', fontSize: 14 }}>{error}</p>}

      {/* metas em andamento */}
      {pending.length > 0 && (
        <section style={{ marginBottom: 32 }}>
          <h2 style={{ fontSize: 14, fontWeight: 600, color: 'var(--color-muted)', marginBottom: 14, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
            Em andamento ({pending.length})
          </h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 14 }}>
            {pending.map(g => (
              <GoalCard
                key={g.id}
                goal={g}
                onEdit={(g) => { setEditing(g); setShowModal(true) }}
                onDelete={setDeleting}
              />
            ))}
          </div>
        </section>
      )}

      {/* metas concluídas */}
      {completed.length > 0 && (
        <section>
          <h2 style={{ fontSize: 14, fontWeight: 600, color: 'var(--color-muted)', marginBottom: 14, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
            Concluídas ({completed.length})
          </h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 14 }}>
            {completed.map(g => (
              <GoalCard
                key={g.id}
                goal={g}
                onEdit={(g) => { setEditing(g); setShowModal(true) }}
                onDelete={setDeleting}
              />
            ))}
          </div>
        </section>
      )}

      {/* estado vazio */}
      {!loading && goals.length === 0 && (
        <div style={{
          textAlign: 'center', padding: '64px 0',
          color: 'var(--color-muted)', fontSize: 14,
        }}>
          <p style={{ fontSize: 32, marginBottom: 12 }}>🎯</p>
          <p style={{ fontWeight: 600, marginBottom: 4 }}>Nenhuma meta cadastrada</p>
          <p>Clique em “+ Nova Meta” para começar.</p>
        </div>
      )}

      {/* modal criar/editar */}
      {showModal && (
        <GoalModal
          initial={editing ?? undefined}
          onClose={() => setShowModal(false)}
          onSave={handleSave}
        />
      )}

      {/* modal confirmar exclusão */}
      {deleting && (
        <div
          style={{
            position: 'fixed', inset: 0,
            background: 'rgba(0,0,0,0.6)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            zIndex: 50,
          }}
        >
          <div style={{
            background: 'var(--color-surface)',
            border: '1px solid var(--color-border)',
            borderRadius: 12, padding: 28,
            maxWidth: 380, width: '100%',
            textAlign: 'center',
          }}>
            <p style={{ fontSize: 15, fontWeight: 600, color: 'var(--color-text)', marginBottom: 8 }}>Excluir meta?</p>
            <p style={{ fontSize: 13, color: 'var(--color-muted)', marginBottom: 20 }}>
              “{deleting.name}” será removida permanentemente.
            </p>
            <div style={{ display: 'flex', gap: 10, justifyContent: 'center' }}>
              <button onClick={() => setDeleting(null)} style={btnSecondaryStyle}>Cancelar</button>
              <button onClick={confirmDelete} style={{ ...btnPrimaryStyle, background: 'var(--color-danger)' }}>Excluir</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// ─── estilos inline reutilizáveis ────────────────────────────────────────────
const inputStyle: React.CSSProperties = {
  display: 'block', width: '100%', marginTop: 4,
  padding: '8px 10px',
  background: 'var(--color-bg)',
  border: '1px solid var(--color-border)',
  borderRadius: 6,
  color: 'var(--color-text)',
  fontSize: 13,
  outline: 'none',
  boxSizing: 'border-box',
}

const btnPrimaryStyle: React.CSSProperties = {
  padding: '8px 18px',
  background: 'var(--color-primary)',
  color: '#fff',
  border: 'none',
  borderRadius: 7,
  fontSize: 13,
  fontWeight: 600,
  cursor: 'pointer',
}

const btnSecondaryStyle: React.CSSProperties = {
  padding: '8px 18px',
  background: 'transparent',
  color: 'var(--color-text)',
  border: '1px solid var(--color-border)',
  borderRadius: 7,
  fontSize: 13,
  fontWeight: 600,
  cursor: 'pointer',
}

const iconBtnStyle: React.CSSProperties = {
  background: 'transparent',
  border: '1px solid var(--color-border)',
  borderRadius: 6,
  padding: '4px 8px',
  cursor: 'pointer',
  fontSize: 14,
  lineHeight: 1,
}
