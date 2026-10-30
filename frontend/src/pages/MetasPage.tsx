import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ArrowRight,
  BarChart3,
  Check,
  Edit3,
  Flag,
  HandCoins,
  Loader2,
  PieChart,
  Plus,
  Sliders,
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
import { useClassTargets, ClassTargetRow } from '@/hooks/useClassTargets'
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

    try {
      await onSave({
        portfolio_id: portfolioId,
        goal_type: form.goal_type,
        name: form.name.trim(),
        description: form.description.trim() || undefined,
        target_value: targetValue,
        current_value: isManualCurrent ? currentValue : 0,
        monthly_contribution: monthlyContribution,
        target_date: form.target_date || null,
      })
    } catch (saveError: any) {
      setError(saveError?.response?.data?.detail ?? 'Falha ao salvar a meta.')
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: 'rgba(0, 0, 0, 0.6)', backdropFilter: 'blur(4px)' }}
    >
      <div
        className="w-full max-w-lg rounded-2xl p-6 shadow-2xl"
        style={{
          background: 'var(--color-surface)',
          border: '1px solid var(--color-border)',
        }}
      >
        <div className="flex items-center justify-between pb-4 border-b border-[var(--color-border)]">
          <div className="flex items-center gap-3">
            <div
              className="flex h-10 w-10 items-center justify-center rounded-xl"
              style={{
                backgroundColor: `color-mix(in srgb, ${typeMeta.color} 15%, transparent)`,
                color: typeMeta.color,
              }}
            >
              <TypeIcon size={20} />
            </div>
            <div>
              <h2 className="text-base font-bold text-[var(--color-text)]">
                {editGoal ? 'Editar Meta' : 'Nova Meta'}
              </h2>
              <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                {typeMeta.hint}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1.5 transition-colors hover:bg-[var(--color-surface-offset)]"
            style={{ color: 'var(--color-text-muted)' }}
          >
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="mt-5 flex flex-col gap-4">
          {!editGoal && (
            <div>
              <span className="text-xs font-semibold block mb-2" style={{ color: 'var(--color-text-muted)' }}>
                Tipo da Meta
              </span>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                {(Object.keys(GOAL_TYPE_META) as GoalType[]).map(type => {
                  const meta = GOAL_TYPE_META[type]
                  const Icon = meta.icon
                  const active = form.goal_type === type
                  return (
                    <button
                      key={type}
                      type="button"
                      onClick={() => set('goal_type', type)}
                      className="flex flex-col items-center gap-1.5 rounded-xl p-3 text-center transition-all"
                      style={{
                        background: active
                          ? `color-mix(in srgb, ${meta.color} 12%, var(--color-surface-offset))`
                          : 'var(--color-surface-offset)',
                        border: active
                          ? `1.5px solid ${meta.color}`
                          : '1px solid var(--color-border)',
                        color: active ? meta.color : 'var(--color-text-muted)',
                      }}
                    >
                      <Icon size={18} />
                      <span className="text-xs font-semibold">{meta.label}</span>
                    </button>
                  )
                })}
              </div>
            </div>
          )}

          <Field label="Nome da Meta">
            <input
              type="text"
              className="input text-sm"
              placeholder="Ex: R$ 500k de patrimônio"
              value={form.name}
              onChange={event => set('name', event.target.value)}
              required
            />
          </Field>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <Field
              label={form.goal_type === 'RENTABILIDADE' ? 'Rentabilidade Alvo (%)' : 'Valor Alvo (R$)'}
              hint="Objetivo principal a ser alcançado"
            >
              <input
                type="text"
                className="input text-sm"
                placeholder={form.goal_type === 'RENTABILIDADE' ? 'Ex: 15' : 'Ex: 500000'}
                value={form.target_value}
                onChange={event => set('target_value', event.target.value)}
                required
              />
            </Field>

            {isManualCurrent ? (
              <Field label="Valor Atual (R$)" hint="Atualizado manualmente para metas livres">
                <input
                  type="text"
                  className="input text-sm"
                  placeholder="Ex: 50000"
                  value={form.current_value}
                  onChange={event => set('current_value', event.target.value)}
                  required
                />
              </Field>
            ) : (
              <Field label="Valor Atual" hint="Sincronizado automaticamente com a carteira">
                <input
                  type="text"
                  className="input text-sm opacity-60"
                  value="Automático (tempo real)"
                  disabled
                />
              </Field>
            )}
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <Field
              label="Aporte Mensal Estimado (R$)"
              hint="Usado para projetar a data de conclusão"
            >
              <input
                type="text"
                className="input text-sm"
                placeholder="Ex: 2500"
                value={form.monthly_contribution}
                onChange={event => set('monthly_contribution', event.target.value)}
              />
            </Field>

            <Field label="Data Limite (Opcional)" hint="Prazo desejado para conclusão">
              <input
                type="date"
                className="input text-sm"
                value={form.target_date}
                onChange={event => set('target_date', event.target.value)}
              />
            </Field>
          </div>

          <Field label="Descrição (Opcional)">
            <textarea
              className="input text-sm"
              rows={2}
              placeholder="Notas adicionais sobre a estratégia para atingir esta meta"
              value={form.description}
              onChange={event => set('description', event.target.value)}
            />
          </Field>

          {error && (
            <div className="rounded-lg p-2.5 text-xs font-medium" style={{ background: 'var(--color-error-bg)', color: 'var(--color-error)' }}>
              {error}
            </div>
          )}

          <div className="flex justify-end gap-2 pt-2 border-t border-[var(--color-border)]">
            <button
              type="button"
              onClick={onClose}
              disabled={saving}
              className="btn btn-secondary text-xs"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={saving}
              className="btn btn-primary text-xs flex items-center gap-1.5"
            >
              {saving && <Loader2 size={14} className="animate-spin" />}
              {editGoal ? 'Salvar Alterações' : 'Criar Meta'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function ClassTargetsSection({
  portfolioId: _portfolioId,
  classTargets,
  isLoading,
}: {
  portfolioId: number
  classTargets: ClassTargetRow[]
  isLoading: boolean
}) {
  const hasTargets = classTargets.some(r => Number(r.target_pct) > 0)

  return (
    <section className="card p-5">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4 pb-3 border-b border-[var(--color-border)]">
        <div>
          <div className="flex items-center gap-2">
            <PieChart size={18} className="text-[var(--color-primary)]" />
            <h2 className="text-base font-semibold text-[var(--color-text)]">
              Alocação Alvo por Classe de Ativo
            </h2>
          </div>
          <p className="text-xs text-[var(--color-text-muted)] mt-0.5">
            Metas de distribuição percentual da carteira por categoria de ativo.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link
            to="/carteira/analise"
            className="btn btn-primary text-xs py-1.5 px-3 flex items-center gap-1.5"
          >
            <BarChart3 size={14} />
            Análise & Rebalanceamento
            <ArrowRight size={14} />
          </Link>
          <Link
            to="/carteira/configuracoes"
            className="btn btn-secondary text-xs py-1.5 px-3 flex items-center gap-1.5"
            title="Ajustar percentuais na tela de configurações"
          >
            <Sliders size={14} />
            Configurar
          </Link>
        </div>
      </div>

      {isLoading ? (
        <div className="py-4 text-center text-xs text-[var(--color-text-muted)]">
          Carregando metas de alocação...
        </div>
      ) : !hasTargets ? (
        <div className="py-4 text-center">
          <p className="text-xs text-[var(--color-text-muted)]">
            Nenhuma meta de distribuição configurada para esta carteira.
          </p>
          <p className="text-xs text-[var(--color-text-faint)] mt-1">
            Defina os percentuais por classe para habilitar o cálculo de desvios e sugestões de rebalanceamento.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
          {classTargets.map(target => {
            const current = Number(target.current_pct || 0)
            const targetP = Number(target.target_pct || 0)
            const delta = Number(target.delta_pct || 0)
            return (
              <div
                key={target.asset_type}
                className="p-3 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-offset)] flex flex-col justify-between"
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="font-semibold text-xs text-[var(--color-text)] flex items-center gap-1.5">
                    <span
                      className="w-2.5 h-2.5 rounded-full inline-block"
                      style={{ backgroundColor: target.color || 'var(--color-primary)' }}
                    />
                    {target.label || target.asset_type}
                  </span>
                  <span
                    className={`text-xs font-medium px-1.5 py-0.5 rounded ${
                      Math.abs(delta) < 1
                        ? 'bg-[var(--color-success)]/10 text-[var(--color-success)]'
                        : delta > 0
                        ? 'bg-[var(--color-blue)]/10 text-[var(--color-blue)]'
                        : 'bg-[var(--color-warning)]/10 text-[var(--color-warning)]'
                    }`}
                  >
                    {delta > 0 ? `+${delta.toFixed(1)}%` : `${delta.toFixed(1)}%`}
                  </span>
                </div>
                <div>
                  <div className="flex justify-between text-xs text-[var(--color-text-muted)] mb-1">
                    <span>Atual: <strong>{current.toFixed(1)}%</strong></span>
                    <span>Alvo: <strong>{targetP.toFixed(1)}%</strong></span>
                  </div>
                  <div className="w-full bg-[var(--color-border)] rounded-full h-1.5 overflow-hidden">
                    <div
                      className="h-1.5 rounded-full"
                      style={{
                        width: `${Math.min(targetP > 0 ? (current / targetP) * 100 : 0, 100)}%`,
                        backgroundColor: target.color || 'var(--color-primary)',
                      }}
                    />
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </section>
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
  const meta = GOAL_TYPE_META[goal.goal_type]
  const Icon = meta.icon

  return (
    <article
      className="card flex flex-col justify-between p-5 transition-all hover:border-[var(--color-border-hover)]"
      style={{
        borderLeft: `4px solid ${meta.color}`,
      }}
    >
      <div>
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2">
            <div
              className="flex h-8 w-8 items-center justify-center rounded-lg"
              style={{
                backgroundColor: `color-mix(in srgb, ${meta.color} 12%, transparent)`,
                color: meta.color,
              }}
            >
              <Icon size={16} />
            </div>
            <div>
              <span className="text-xs font-semibold" style={{ color: meta.color }}>
                {meta.label}
              </span>
              <h3 className="text-sm font-bold text-[var(--color-text)] line-clamp-1">
                {goal.name}
              </h3>
            </div>
          </div>

          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => onEdit(goal)}
              className="rounded p-1 text-[var(--color-text-muted)] hover:bg-[var(--color-surface-offset)] hover:text-[var(--color-text)]"
              title="Editar"
            >
              <Edit3 size={14} />
            </button>
            <button
              type="button"
              onClick={() => onDelete(goal.id)}
              disabled={deleting}
              className="rounded p-1 text-[var(--color-text-muted)] hover:bg-[var(--color-surface-offset)] hover:text-[var(--color-error)]"
              title="Excluir"
            >
              {deleting ? <Loader2 size={14} className="animate-spin" /> : <Trash2 size={14} />}
            </button>
          </div>
        </div>

        <div className="mt-4 flex items-baseline justify-between">
          <div>
            <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
              Atual
            </span>
            <p className="text-lg font-bold text-[var(--color-text)]">
              {formatGoalValue(goal.goal_type, goal.current_value)}
            </p>
          </div>
          <div className="text-right">
            <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
              Alvo
            </span>
            <p className="text-sm font-semibold" style={{ color: 'var(--color-text-muted)' }}>
              {formatGoalValue(goal.goal_type, goal.target_value)}
            </p>
          </div>
        </div>

        <div className="mt-3">
          <div className="flex items-center justify-between text-xs mb-1">
            <span style={{ color: 'var(--color-text-muted)' }}>Progresso</span>
            <span className="font-bold" style={{ color: meta.color }}>
              {formatPct(goal.progress_pct)}
            </span>
          </div>
          <div className="w-full bg-[var(--color-border)] rounded-full h-2 overflow-hidden">
            <div
              className="h-2 rounded-full transition-all duration-500"
              style={{
                width: `${Math.min(goal.progress_pct, 100)}%`,
                backgroundColor: meta.color,
              }}
            />
          </div>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-2 rounded-xl p-2.5 text-xs" style={{ background: 'var(--color-surface-offset)' }}>
          <div>
            <span style={{ color: 'var(--color-text-muted)' }}>Prazo Estimado</span>
            <p className="mt-0.5 font-semibold text-[var(--color-text)]">
              {goal.is_completed ? (
                <span className="flex items-center gap-1 text-[var(--color-success)]">
                  <Check size={12} /> Concluída
                </span>
              ) : goal.months_to_goal != null ? (
                `${goal.months_to_goal} meses`
              ) : (
                '-'
              )}
            </p>
          </div>
          <div>
            <span style={{ color: 'var(--color-text-muted)' }}>Previsão / Alvo</span>
            <p className="mt-0.5 font-semibold text-[var(--color-text)]">
              {formatDate(goal.projected_date ?? goal.target_date)}
            </p>
          </div>
        </div>

        {goal.description && (
          <p className="mt-3 line-clamp-2 text-xs" style={{ color: 'var(--color-text-muted)' }}>
            {goal.description}
          </p>
        )}
      </div>
    </article>
  )
}

export default function MetasPage() {
  const selectedPortfolioId = useAppStore(state => state.selectedPortfolioId)
  const { data: goals = [], isLoading, isError } = useGoals(selectedPortfolioId)
  const { data: classTargets = [], isLoading: isLoadingTargets } = useClassTargets(selectedPortfolioId)
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
      <div className="flex items-center justify-end">
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

      <ClassTargetsSection
        portfolioId={selectedPortfolioId}
        classTargets={classTargets}
        isLoading={isLoadingTargets}
      />

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
