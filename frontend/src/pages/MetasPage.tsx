import { useState } from 'react'
import { useAppStore } from '@/store/appStore'
import {
  useGoals, useCreateGoal, useUpdateGoal, useDeleteGoal,
  GoalType, Goal, GoalCreate,
} from '@/hooks/useGoals'
import { format, parseISO } from 'date-fns'
import { ptBR } from 'date-fns/locale'

// ---- helpers ---------------------------------------------------------------

const GOAL_TYPE_LABELS: Record<GoalType, { label: string; icon: string; hint: string }> = {
  PATRIMONIO:    { label: 'Patrimônio',    icon: '🏦', hint: 'Atingir um valor total de patrimônio na carteira' },
  PROVENTOS:     { label: 'Proventos',     icon: '💰', hint: 'Atingir uma renda mensal de proventos (dividendos + JCP)' },
  RENTABILIDADE: { label: 'Rentabilidade', icon: '📈', hint: 'Atingir um percentual de retorno acumulado' },
  LIVRE:         { label: 'Livre',         icon: '🎯', hint: 'Meta personalizada com valor atual informado por você' },
}

function fmtBRL(v: number) {
  return v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
}

function fmtPct(v: number) {
  return v.toLocaleString('pt-BR', { minimumFractionDigits: 2 }) + '%'
}

function fmtDate(iso: string | null) {
  if (!iso) return '—'
  try { return format(parseISO(iso), 'MMM/yyyy', { locale: ptBR }) } catch { return iso }
}

function fmtValue(type: GoalType, v: number) {
  if (type === 'RENTABILIDADE') return fmtPct(v)
  if (type === 'PROVENTOS')    return fmtBRL(v) + '/mês'
  return fmtBRL(v)
}

function progressColor(pct: number) {
  if (pct >= 100) return 'bg-green-500'
  if (pct >= 60)  return 'bg-blue-500'
  if (pct >= 30)  return 'bg-yellow-500'
  return 'bg-red-500'
}

// ---- Modal form ------------------------------------------------------------

const EMPTY_FORM = {
  goal_type: 'PATRIMONIO' as GoalType,
  name: '',
  description: '',
  target_value: '',
  current_value: '',
  monthly_contribution: '',
  target_date: '',
}

type FormState = typeof EMPTY_FORM

function GoalModal({
  open, onClose, onSave, portfolioId, editGoal,
}: {
  open: boolean
  onClose: () => void
  onSave: (d: GoalCreate) => void
  portfolioId: number
  editGoal?: Goal | null
}) {
  const [form, setForm] = useState<FormState>(
    editGoal
      ? {
          goal_type: editGoal.goal_type,
          name: editGoal.name,
          description: editGoal.description ?? '',
          target_value: String(editGoal.target_value),
          current_value: String(editGoal.current_value),
          monthly_contribution: editGoal.monthly_contribution != null
            ? String(editGoal.monthly_contribution) : '',
          target_date: editGoal.target_date
            ? editGoal.target_date.slice(0, 10) : '',
        }
      : EMPTY_FORM
  )

  if (!open) return null

  const type = form.goal_type
  const isAuto = type !== 'LIVRE'
  const meta = GOAL_TYPE_LABELS[type]

  const set = (k: keyof FormState, v: string) =>
    setForm(prev => ({ ...prev, [k]: v }))

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const payload: GoalCreate = {
      portfolio_id:         portfolioId,
      goal_type:            form.goal_type,
      name:                 form.name.trim(),
      target_value:         parseFloat(form.target_value),
      current_value:        form.current_value ? parseFloat(form.current_value) : 0,
      monthly_contribution: form.monthly_contribution
        ? parseFloat(form.monthly_contribution) : undefined,
      target_date:          form.target_date || null,
      description:          form.description || undefined,
    }
    onSave(payload)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-base-200 rounded-2xl shadow-2xl w-full max-w-lg p-6 relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 btn btn-sm btn-ghost"
        >✕</button>

        <h2 className="text-xl font-bold mb-4">
          {editGoal ? 'Editar Meta' : 'Nova Meta'}
        </h2>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">

          {/* Tipo */}
          <div>
            <label className="label"><span className="label-text font-semibold">Tipo de meta</span></label>
            <div className="grid grid-cols-2 gap-2">
              {(Object.keys(GOAL_TYPE_LABELS) as GoalType[]).map(t => (
                <button
                  key={t}
                  type="button"
                  onClick={() => set('goal_type', t)}
                  className={`btn btn-sm ${
                    form.goal_type === t ? 'btn-primary' : 'btn-outline'
                  } justify-start gap-2`}
                >
                  <span>{GOAL_TYPE_LABELS[t].icon}</span>
                  {GOAL_TYPE_LABELS[t].label}
                </button>
              ))}
            </div>
            <p className="text-xs text-base-content/50 mt-1">{meta.hint}</p>
          </div>

          {/* Nome */}
          <div>
            <label className="label"><span className="label-text">Nome</span></label>
            <input
              required
              className="input input-bordered w-full"
              placeholder={`Ex: ${meta.label} de R$ 1.000.000`}
              value={form.name}
              onChange={e => set('name', e.target.value)}
            />
          </div>

          {/* Valor alvo */}
          <div>
            <label className="label">
              <span className="label-text">
                {type === 'RENTABILIDADE' ? 'Rentabilidade alvo (%)' :
                 type === 'PROVENTOS' ? 'Renda mensal alvo (R$)' :
                 'Valor alvo (R$)'}
              </span>
            </label>
            <input
              required
              type="number"
              min={0}
              step="any"
              className="input input-bordered w-full"
              placeholder={type === 'RENTABILIDADE' ? '50' : '1000000'}
              value={form.target_value}
              onChange={e => set('target_value', e.target.value)}
            />
          </div>

          {/* Valor atual — somente LIVRE */}
          {!isAuto && (
            <div>
              <label className="label"><span className="label-text">Valor atual (R$)</span></label>
              <input
                type="number"
                min={0}
                step="any"
                className="input input-bordered w-full"
                placeholder="0"
                value={form.current_value}
                onChange={e => set('current_value', e.target.value)}
              />
            </div>
          )}

          {/* Para tipos auto: aviso de preenchimento automático */}
          {isAuto && (
            <div className="alert alert-info py-2 text-sm">
              <span>
                ℹ️ O valor atual será preenchido automaticamente com base nos dados reais da sua carteira.
              </span>
            </div>
          )}

          {/* Aporte mensal projetado */}
          <div>
            <label className="label">
              <span className="label-text">Aporte mensal projetado (R$)</span>
              <span className="label-text-alt text-base-content/50">Usado para calcular a data estimada</span>
            </label>
            <input
              type="number"
              min={0}
              step="any"
              className="input input-bordered w-full"
              placeholder="Ex: 2000"
              value={form.monthly_contribution}
              onChange={e => set('monthly_contribution', e.target.value)}
            />
          </div>

          {/* Data alvo manual (opcional) */}
          <div>
            <label className="label">
              <span className="label-text">Data alvo (opcional)</span>
              <span className="label-text-alt text-base-content/50">Deixe vazio para calcular automaticamente</span>
            </label>
            <input
              type="date"
              className="input input-bordered w-full"
              value={form.target_date}
              onChange={e => set('target_date', e.target.value)}
            />
          </div>

          {/* Descrição */}
          <div>
            <label className="label"><span className="label-text">Descrição (opcional)</span></label>
            <textarea
              className="textarea textarea-bordered w-full"
              rows={2}
              placeholder="Observações..."
              value={form.description}
              onChange={e => set('description', e.target.value)}
            />
          </div>

          <div className="flex gap-2 justify-end mt-2">
            <button type="button" onClick={onClose} className="btn btn-ghost">Cancelar</button>
            <button type="submit" className="btn btn-primary">Salvar</button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ---- Card de meta ----------------------------------------------------------

function GoalCard({
  goal, onEdit, onDelete,
}: {
  goal: Goal
  onEdit: (g: Goal) => void
  onDelete: (id: number) => void
}) {
  const meta = GOAL_TYPE_LABELS[goal.goal_type as GoalType] ?? GOAL_TYPE_LABELS.LIVRE
  const barColor = progressColor(goal.progress_pct)

  return (
    <div className="card bg-base-200 shadow border border-base-300">
      <div className="card-body p-4">
        {/* Header */}
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="text-2xl">{meta.icon}</span>
            <div>
              <p className="font-bold text-base leading-tight">{goal.name}</p>
              <span className="badge badge-sm badge-outline mt-0.5">{meta.label}</span>
            </div>
          </div>
          <div className="flex gap-1">
            <button
              className="btn btn-xs btn-ghost"
              onClick={() => onEdit(goal)}
            >✏️</button>
            <button
              className="btn btn-xs btn-ghost text-error"
              onClick={() => onDelete(goal.id)}
            >🗑️</button>
          </div>
        </div>

        {/* Progresso */}
        <div className="mt-3">
          <div className="flex justify-between text-sm mb-1">
            <span className="text-base-content/60">Progresso</span>
            <span className="font-semibold">{goal.progress_pct.toFixed(1)}%</span>
          </div>
          <div className="w-full bg-base-300 rounded-full h-2">
            <div
              className={`h-2 rounded-full transition-all ${barColor}`}
              style={{ width: `${Math.min(goal.progress_pct, 100)}%` }}
            />
          </div>
        </div>

        {/* Valores */}
        <div className="grid grid-cols-2 gap-2 mt-3 text-sm">
          <div>
            <p className="text-base-content/50 text-xs">Atual</p>
            <p className="font-semibold">{fmtValue(goal.goal_type as GoalType, goal.current_value)}</p>
          </div>
          <div>
            <p className="text-base-content/50 text-xs">Alvo</p>
            <p className="font-semibold">{fmtValue(goal.goal_type as GoalType, goal.target_value)}</p>
          </div>

          {/* Data projetada */}
          <div>
            <p className="text-base-content/50 text-xs">Data projetada</p>
            <p className="font-semibold">
              {goal.projected_date
                ? fmtDate(goal.projected_date)
                : goal.target_date
                  ? fmtDate(goal.target_date)
                  : '—'}
            </p>
          </div>

          {/* Meses restantes */}
          <div>
            <p className="text-base-content/50 text-xs">Meses restantes</p>
            <p className="font-semibold">
              {goal.is_completed
                ? <span className="text-green-500">✅ Concluído</span>
                : goal.months_to_goal != null
                  ? `${goal.months_to_goal} meses`
                  : '—'}
            </p>
          </div>
        </div>

        {/* Aporte mensal */}
        {goal.monthly_contribution != null && (
          <p className="text-xs text-base-content/50 mt-2">
            Aporte projetado: {fmtBRL(goal.monthly_contribution)}/mês
          </p>
        )}

        {goal.is_completed && (
          <div className="badge badge-success badge-sm mt-2 w-full justify-center">
            ✅ Meta atingida!
          </div>
        )}
      </div>
    </div>
  )
}

// ---- Página principal ------------------------------------------------------

export default function MetasPage() {
  const selectedPortfolioId = useAppStore(s => s.selectedPortfolioId)
  const { data: goals = [], isLoading } = useGoals(selectedPortfolioId)
  const createGoal = useCreateGoal()
  const updateGoal = useUpdateGoal()
  const deleteGoal = useDeleteGoal()

  const [modalOpen, setModalOpen] = useState(false)
  const [editGoal, setEditGoal]   = useState<Goal | null>(null)

  function openCreate() {
    setEditGoal(null)
    setModalOpen(true)
  }

  function openEdit(g: Goal) {
    setEditGoal(g)
    setModalOpen(true)
  }

  async function handleSave(data: GoalCreate) {
    if (editGoal) {
      await updateGoal.mutateAsync({
        portfolioId: selectedPortfolioId!,
        id: editGoal.id,
        data,
      })
    } else {
      await createGoal.mutateAsync(data)
    }
    setModalOpen(false)
  }

  async function handleDelete(id: number) {
    if (!confirm('Remover esta meta?')) return
    await deleteGoal.mutateAsync({ portfolioId: selectedPortfolioId!, id })
  }

  const active    = goals.filter(g => !g.is_completed)
  const completed = goals.filter(g => g.is_completed)

  return (
    <div className="p-4 md:p-6 max-w-5xl mx-auto">
      {/* Cabeçalho */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Metas Financeiras</h1>
          <p className="text-base-content/50 text-sm mt-0.5">
            Acompanhe patrimônio, proventos, rentabilidade e metas personalizadas
          </p>
        </div>
        <button className="btn btn-primary" onClick={openCreate}>
          + Nova Meta
        </button>
      </div>

      {isLoading && (
        <div className="flex justify-center py-12">
          <span className="loading loading-spinner loading-lg" />
        </div>
      )}

      {!isLoading && goals.length === 0 && (
        <div className="text-center py-16">
          <p className="text-5xl mb-4">🎯</p>
          <p className="text-lg font-semibold">Nenhuma meta criada ainda</p>
          <p className="text-base-content/50 text-sm mt-1">
            Crie sua primeira meta e acompanhe quando você vai atingí-la.
          </p>
          <button className="btn btn-primary mt-4" onClick={openCreate}>
            Criar primeira meta
          </button>
        </div>
      )}

      {/* Metas ativas */}
      {active.length > 0 && (
        <>
          <h2 className="text-sm font-semibold text-base-content/50 uppercase tracking-wider mb-3">
            Em andamento ({active.length})
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
            {active.map(g => (
              <GoalCard key={g.id} goal={g} onEdit={openEdit} onDelete={handleDelete} />
            ))}
          </div>
        </>
      )}

      {/* Metas concluídas */}
      {completed.length > 0 && (
        <>
          <h2 className="text-sm font-semibold text-base-content/50 uppercase tracking-wider mb-3">
            Concluídas ({completed.length})
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {completed.map(g => (
              <GoalCard key={g.id} goal={g} onEdit={openEdit} onDelete={handleDelete} />
            ))}
          </div>
        </>
      )}

      {/* Modal */}
      {selectedPortfolioId && (
        <GoalModal
          open={modalOpen}
          onClose={() => setModalOpen(false)}
          onSave={handleSave}
          portfolioId={selectedPortfolioId}
          editGoal={editGoal}
        />
      )}
    </div>
  )
}
