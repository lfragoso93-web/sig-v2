import { useEffect, useMemo, useState } from 'react'
import {
  Calendar,
  Check,
  Edit3,
  Flag,
  HandCoins,
  Loader2,
  Plus,
  Target,
  Trash2,
  TrendingUp,
  Wallet,
  X,
} from 'lucide-react'
import { format, parseISO } from 'date-fns'
import { ptBR } from 'date-fns/locale'
import { useAppStore } from '@/store/appStore'
import {
  useGoals,
  useCreateGoal,
  useUpdateGoal,
  useDeleteGoal,
  GoalType,
  Goal,
  GoalCreate,
} from '@/hooks/useGoals'
import EmptyState from '@/components/ui/EmptyState'
import SkeletonCard from '@/components/ui/SkeletonCard'

type GoalMeta = {
  label: string
  hint: string
  icon: typeof Wallet
  color: string
}

const GOAL_TYPE_META: Record<GoalType, GoalMeta> = {
  PATRIMONIO: {
    label: 'Patrimônio',
    hint: 'Valor total desejado para a carteira selecionada.',
    icon: Wallet,
    color: 'var(--color-primary)',
  },
  PROVENTOS: {
    label: 'Proventos',
    hint: 'Renda mensal líquida desejada com dividendos, JCP e rendimentos.',
    icon: HandCoins,
    color: 'var(--color-success)',
  },
  RENTABILIDADE: {
    label: 'Rentabilidade',
    hint: 'Percentual acumulado de retorno que você quer atingir.',
    icon: TrendingUp,
    color: 'var(--color-blue)',
  },
  LIVRE: {
    label: 'Livre',
    hint: 'Meta personalizada com valor atual informado manualmente.',
    icon: Target,
    color: 'var(--color-purple)',
  },
}

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

function formatBRL(value: number) {
  return value.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
}

function formatPct(value: number) {
  return `${value.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%`
}

function formatDate(value: string | null) {
  if (!value) return '-'
  try {
    return format(parseISO(value), 'MMM/yyyy', { locale: ptBR })
  } catch {
    return value
  }
}

function formatGoalValue(type: GoalType, value: number) {
  if (type === 'RENTABILIDADE') return formatPct(value)
  if (type === 'PROVENTOS') return `${formatBRL(value)}/mês`
  return formatBRL(value)
}

function parseNumber(value: string) {
  const normalized = value.replace(/\./g, '').replace(',', '.')
  const parsed = Number(normalized)
  return Number.isFinite(parsed) ? parsed : NaN
}

function formFromGoal(goal: Goal | null): FormState {
  if (!goal) return { ...EMPTY_FORM }
  return {
    goal_type: goal.goal_type,
    name: goal.name,
    description: goal.description ?? '',
    target_value: String(goal.target_value),
    current_value: String(goal.current_value),
    monthly_contribution:
      goal.monthly_contribution != null ? String(goal.monthly_contribution) : '',
    target_date: goal.target_date ? goal.target_date.slice(0, 10) : '',
  }
}

function Field({
  label,
  hint,
  children,
}: {
  label: string
  hint?: string
  children: React.ReactNode
}) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-xs font-semibold" style={{ color: 'var(--color-text-muted)' }}>
        {label}
      </span>
      {children}
      {hint && <span className="text-xs" style={{ color: 'var(--color-text-faint)' }}>{hint}</span>}
    </label>
  )
}

function GoalModal({
  open,
  onClose,
  onSave,
  portfolioId,
  editGoal,
  saving,
}: {
  open: boolean
  onClose: () => void
  onSave: (data: GoalCreate) => Promise<void>
  portfolioId: number
  editGoal?: Goal | null
  saving: boolean
}) {
  const [form, setForm] = useState<FormState>(() => formFromGoal(editGoal ?? null))
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (open) {
      setForm(formFromGoal(editGoal ?? null))
      setError(null)
    }
  }, [editGoal, open])

  if (!open) return null

  const typeMeta = GOAL_TYPE_META[form.goal_type]
  const TypeIcon = typeMeta.icon
  const isManualCurrent = form.goal_type === 'LIVRE'

  const set = (key: keyof FormState, value: string) => {
    setForm(previous => ({ ...previous, [key]: value }))
    setError(null)
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()

    const targetValue = parseNumber(form.target_value)
    const currentValue = form.current_value ? parseNumber(form.current_value) : 0
    const monthlyContribution = form.monthly_contribution
      ? parseNumber(form.monthly_contribution)
      : undefined

    if (!form.name.trim()) {
      setError('Informe um nome para a meta.')
      return
    }
    if (!Number.isFinite(targetValue) || targetValue <= 0) {
      setError('Informe um valor alvo maior que zero.')
      return
    }
    if (isManualCurrent && (!Number.isFinite(currentValue) || currentValue < 0)) {
      setError('Informe um valor atual válido para a meta livre.')
      return
    }
    if (monthlyContribution !== undefined && (!Number.isFinite(monthlyContribution) || monthlyContribution < 0)) {
      setError('Informe um aporte mensal válido.')
      return
    }

    await onSave({
      portfolio_id: portfolioId,
      goal_type: form.goal_type,
      name: form.name.trim(),
      target_value: targetValue,
      current_value: isManualCurrent ? currentValue : 0,
      monthly_contribution: monthlyContribution,
      target_date: form.target_date || null,
      description: form.description.trim() || undefined,
    })
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <button
        type="button"
        aria-label="Fechar"
        className="absolute inset-0 bg-black/60"
        onClick={onClose}
      />
      <section
        role="dialog"
        aria-modal="true"
        aria-label={editGoal ? 'Editar meta' : 'Nova meta'}
        className="relative w-full max-w-2xl overflow-hidden rounded-lg border shadow-2xl"
        style={{
          background: 'var(--color-surface)',
          borderColor: 'var(--color-border)',
          color: 'var(--color-text)',
        }}
      >
        <div className="flex items-start justify-between gap-4 border-b px-5 py-4" style={{ borderColor: 'var(--color-divider)' }}>
          <div className="flex items-start gap-3">
            <span
              className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg"
              style={{ background: `${typeMeta.color}1f`, color: typeMeta.color }}
            >
              <TypeIcon size={18} />
            </span>
            <div>
              <h2 className="text-base font-semibold">{editGoal ? 'Editar meta' : 'Nova meta'}</h2>
              <p className="mt-0.5 text-sm" style={{ color: 'var(--color-text-muted)' }}>
                {typeMeta.hint}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="flex h-8 w-8 items-center justify-center rounded-lg transition-colors"
            style={{ color: 'var(--color-text-muted)' }}
          >
            <X size={17} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="max-h-[78vh] overflow-y-auto px-5 py-5">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {(Object.keys(GOAL_TYPE_META) as GoalType[]).map(goalType => {
              const meta = GOAL_TYPE_META[goalType]
              const Icon = meta.icon
              const active = form.goal_type === goalType
              return (
                <button
                  key={goalType}
                  type="button"
                  onClick={() => set('goal_type', goalType)}
                  className="flex min-h-16 items-center gap-3 rounded-lg border px-3 py-3 text-left transition-colors"
                  style={{
                    background: active ? `${meta.color}14` : 'var(--color-surface-offset)',
                    borderColor: active ? `${meta.color}73` : 'var(--color-border)',
                    color: active ? meta.color : 'var(--color-text)',
                  }}
                >
                  <Icon size={18} />
                  <span>
                    <span className="block text-sm font-semibold">{meta.label}</span>
                    <span className="block text-xs" style={{ color: 'var(--color-text-muted)' }}>
                      {meta.hint}
                    </span>
                  </span>
                </button>
              )
            })}
          </div>

          <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-2">
            <div className="md:col-span-2">
              <Field label="Nome da meta">
                <input
                  required
                  className="input w-full"
                  value={form.name}
                  onChange={event => set('name', event.target.value)}
                  placeholder="Ex: Patrimônio de R$ 1.000.000"
                />
              </Field>
            </div>

            <Field
              label={
                form.goal_type === 'RENTABILIDADE'
                  ? 'Rentabilidade alvo (%)'
                  : form.goal_type === 'PROVENTOS'
                    ? 'Renda mensal alvo (R$)'
                    : 'Valor alvo (R$)'
              }
            >
              <input
                required
                inputMode="decimal"
                className="input w-full"
                value={form.target_value}
                onChange={event => set('target_value', event.target.value)}
                placeholder={form.goal_type === 'RENTABILIDADE' ? '15' : '1000000'}
              />
            </Field>

            <Field
              label="Valor atual"
              hint={isManualCurrent ? 'Obrigatório para metas livres.' : 'Calculado automaticamente pela carteira.'}
            >
              <input
                inputMode="decimal"
                className="input w-full disabled:opacity-60"
                value={form.current_value}
                onChange={event => set('current_value', event.target.value)}
                placeholder={isManualCurrent ? '0' : 'Automático'}
                disabled={!isManualCurrent}
              />
            </Field>

            <Field label="Aporte mensal projetado (R$)" hint="Usado apenas para estimar a data de conclusão.">
              <input
                inputMode="decimal"
                className="input w-full"
                value={form.monthly_contribution}
                onChange={event => set('monthly_contribution', event.target.value)}
                placeholder="2000"
              />
            </Field>

            <Field label="Data alvo" hint="Opcional.">
              <input
                type="date"
                className="input w-full"
                value={form.target_date}
                onChange={event => set('target_date', event.target.value)}
              />
            </Field>

            <div className="md:col-span-2">
              <Field label="Descrição">
                <textarea
                  className="input min-h-24 w-full resize-y py-3"
                  value={form.description}
                  onChange={event => set('description', event.target.value)}
                  placeholder="Observações, motivação ou critério de acompanhamento."
                />
              </Field>
            </div>
          </div>

          {error && (
            <div
              role="alert"
              className="mt-4 rounded-lg border px-3 py-2 text-sm"
              style={{
                background: 'rgba(239, 68, 68, 0.08)',
                borderColor: 'rgba(239, 68, 68, 0.35)',
                color: 'var(--color-error)',
              }}
            >
              {error}
            </div>
          )}

          <div className="mt-5 flex justify-end gap-2 border-t pt-4" style={{ borderColor: 'var(--color-divider)' }}>
            <button type="button" onClick={onClose} className="btn">
              Cancelar
            </button>
            <button type="submit" disabled={saving} className="btn btn-primary disabled:opacity-60">
              {saving ? <Loader2 size={16} className="animate-spin" /> : <Check size={16} />}
              Salvar meta
            </button>
          </div>
        </form>
      </section>
    </div>
  )
}

function GoalCard({
  goal,
  onEdit,
  onDelete,
  deleting,
}: {
  goal: Goal
  onEdit: (goal: Goal) => void
  onDelete: (id: number) => void
  deleting: boolean
}) {
  const type = goal.goal_type as GoalType
  const meta = GOAL_TYPE_META[type] ?? GOAL_TYPE_META.LIVRE
  const Icon = meta.icon
  const progress = Math.min(Math.max(goal.progress_pct, 0), 100)
  const remaining = Math.max(goal.target_value - goal.current_value, 0)

  return (
    <article className="card p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-start gap-3">
          <span
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg"
            style={{ background: `${meta.color}1f`, color: meta.color }}
          >
            <Icon size={19} />
          </span>
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold" style={{ color: 'var(--color-text)' }}>
              {goal.name}
            </p>
            <p className="mt-0.5 text-xs" style={{ color: 'var(--color-text-muted)' }}>
              {meta.label}
            </p>
          </div>
        </div>
        <div className="flex shrink-0 gap-1">
          <button
            type="button"
            onClick={() => onEdit(goal)}
            className="flex h-8 w-8 items-center justify-center rounded-lg transition-colors"
            style={{ color: 'var(--color-text-muted)' }}
            title="Editar meta"
          >
            <Edit3 size={15} />
          </button>
          <button
            type="button"
            onClick={() => onDelete(goal.id)}
            disabled={deleting}
            className="flex h-8 w-8 items-center justify-center rounded-lg transition-colors disabled:opacity-50"
            style={{ color: 'var(--color-error)' }}
            title="Excluir meta"
          >
            {deleting ? <Loader2 size={15} className="animate-spin" /> : <Trash2 size={15} />}
          </button>
        </div>
      </div>

      <div className="mt-4">
        <div className="mb-1 flex justify-between text-xs" style={{ color: 'var(--color-text-muted)' }}>
          <span>Progresso</span>
          <span className="font-semibold" style={{ color: 'var(--color-text)' }}>
            {progress.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%
          </span>
        </div>
        <div className="h-2 overflow-hidden rounded-full" style={{ background: 'var(--color-surface-offset)' }}>
          <div
            className="h-full rounded-full transition-all"
            style={{ width: `${progress}%`, background: meta.color }}
          />
        </div>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
        <div>
          <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>Atual</p>
          <p className="mt-0.5 font-semibold tabular-nums">{formatGoalValue(type, goal.current_value)}</p>
        </div>
        <div>
          <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>Alvo</p>
          <p className="mt-0.5 font-semibold tabular-nums">{formatGoalValue(type, goal.target_value)}</p>
        </div>
        <div>
          <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>Falta</p>
          <p className="mt-0.5 font-semibold tabular-nums">{formatGoalValue(type, remaining)}</p>
        </div>
        <div>
          <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>Previsão</p>
          <p className="mt-0.5 font-semibold">{formatDate(goal.projected_date ?? goal.target_date)}</p>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-2 text-xs" style={{ color: 'var(--color-text-muted)' }}>
        {goal.monthly_contribution != null && (
          <span className="inline-flex items-center gap-1 rounded-full border px-2 py-1" style={{ borderColor: 'var(--color-border)' }}>
            <Calendar size={12} />
            {formatBRL(goal.monthly_contribution)}/mês
          </span>
        )}
        {goal.is_completed && (
          <span className="inline-flex items-center gap-1 rounded-full px-2 py-1" style={{ background: 'rgba(34, 197, 94, 0.12)', color: 'var(--color-success)' }}>
            <Check size={12} />
            Concluída
          </span>
        )}
      </div>

      {goal.description && (
        <p className="mt-3 line-clamp-2 text-xs" style={{ color: 'var(--color-text-muted)' }}>
          {goal.description}
        </p>
      )}
    </article>
  )
}

export default function MetasPage() {
  const selectedPortfolioId = useAppStore(state => state.selectedPortfolioId)
  const { data: goals = [], isLoading, isError } = useGoals(selectedPortfolioId)
  const createGoal = useCreateGoal()
  const updateGoal = useUpdateGoal()
  const deleteGoal = useDeleteGoal()
  const [modalOpen, setModalOpen] = useState(false)
  const [editGoal, setEditGoal] = useState<Goal | null>(null)
  const [deletingId, setDeletingId] = useState<number | null>(null)

  const activeGoals = useMemo(() => goals.filter(goal => !goal.is_completed), [goals])
  const completedGoals = useMemo(() => goals.filter(goal => goal.is_completed), [goals])
  const averageProgress = goals.length
    ? goals.reduce((sum, goal) => sum + goal.progress_pct, 0) / goals.length
    : 0
  const saving = createGoal.isPending || updateGoal.isPending

  function openCreate() {
    setEditGoal(null)
    setModalOpen(true)
  }

  function openEdit(goal: Goal) {
    setEditGoal(goal)
    setModalOpen(true)
  }

  async function handleSave(data: GoalCreate) {
    if (!selectedPortfolioId) return

    if (editGoal) {
      const { portfolio_id: _portfolioId, goal_type: _goalType, ...updateData } = data
      await updateGoal.mutateAsync({
        portfolioId: selectedPortfolioId,
        id: editGoal.id,
        data: updateData,
      })
    } else {
      await createGoal.mutateAsync(data)
    }
    setModalOpen(false)
  }

  async function handleDelete(id: number) {
    if (!selectedPortfolioId || !confirm('Remover esta meta?')) return
    setDeletingId(id)
    try {
      await deleteGoal.mutateAsync({ portfolioId: selectedPortfolioId, id })
    } finally {
      setDeletingId(null)
    }
  }

  if (!selectedPortfolioId) {
    return (
      <div className="page-container">
        <EmptyState
          icon={Flag}
          title="Nenhuma carteira selecionada"
          description="Selecione uma carteira no menu superior para criar e acompanhar metas."
        />
      </div>
    )
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1 className="page-title">Metas</h1>
          <p className="page-subtitle">Acompanhe objetivos de patrimônio, renda, rentabilidade e metas livres.</p>
        </div>
        <button type="button" onClick={openCreate} className="btn btn-primary">
          <Plus size={16} />
          Nova meta
        </button>
      </div>

      <div className="kpi-grid">
        <div className="card p-4">
          <p className="kpi-label">Metas ativas</p>
          <p className="kpi-value">{activeGoals.length}</p>
        </div>
        <div className="card p-4">
          <p className="kpi-label">Concluídas</p>
          <p className="kpi-value">{completedGoals.length}</p>
        </div>
        <div className="card p-4">
          <p className="kpi-label">Progresso médio</p>
          <p className="kpi-value">{formatPct(averageProgress)}</p>
        </div>
        <div className="card p-4">
          <p className="kpi-label">Total</p>
          <p className="kpi-value">{goals.length}</p>
        </div>
      </div>

      {isError && (
        <div className="card p-4 text-sm" style={{ color: 'var(--color-error)' }}>
          Não foi possível carregar as metas desta carteira.
        </div>
      )}

      {isLoading ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {[...Array(6)].map((_, index) => <SkeletonCard key={index} />)}
        </div>
      ) : goals.length === 0 ? (
        <div className="card p-8">
          <EmptyState
            icon={Target}
            title="Nenhuma meta criada"
            description="Crie metas concretas para acompanhar avanço, prazo e valor restante por carteira."
            action={{ label: '+ Nova meta', onClick: openCreate }}
          />
        </div>
      ) : (
        <div className="flex flex-col gap-6">
          {activeGoals.length > 0 && (
            <section>
              <div className="section-card-header px-0">
                <span className="section-card-title">Em andamento ({activeGoals.length})</span>
              </div>
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
                {activeGoals.map(goal => (
                  <GoalCard
                    key={goal.id}
                    goal={goal}
                    onEdit={openEdit}
                    onDelete={handleDelete}
                    deleting={deletingId === goal.id}
                  />
                ))}
              </div>
            </section>
          )}

          {completedGoals.length > 0 && (
            <section>
              <div className="section-card-header px-0">
                <span className="section-card-title">Concluídas ({completedGoals.length})</span>
              </div>
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
                {completedGoals.map(goal => (
                  <GoalCard
                    key={goal.id}
                    goal={goal}
                    onEdit={openEdit}
                    onDelete={handleDelete}
                    deleting={deletingId === goal.id}
                  />
                ))}
              </div>
            </section>
          )}
        </div>
      )}

      <GoalModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onSave={handleSave}
        portfolioId={selectedPortfolioId}
        editGoal={editGoal}
        saving={saving}
      />
    </div>
  )
}
