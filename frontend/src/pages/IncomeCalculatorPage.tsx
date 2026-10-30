import { useId, useMemo, useState } from 'react'
import { CircleHelp, TrendingUp } from 'lucide-react'
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { calculateIncomeProjection } from '@/utils/incomeProjection'

const currency = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })
const percentage = new Intl.NumberFormat('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

function parseInput(value: string): number {
  if (!value.trim()) return Number.NaN
  return Number(value)
}

function Field({
  label,
  hint,
  value,
  onChange,
  min,
  max,
  step,
  suffix,
}: {
  label: string
  hint: string
  value: string
  onChange: (value: string) => void
  min: number
  max: number
  step: number
  suffix?: string
}) {
  const hintId = useId()
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-sm font-medium" style={{ color: 'var(--color-text)' }}>{label}</span>
      <span className="relative">
        <input
          className="input w-full"
          type="number"
          inputMode="decimal"
          min={min}
          max={max}
          step={step}
          value={value}
          onChange={event => onChange(event.target.value)}
          aria-label={label}
          aria-describedby={hintId}
        />
        {suffix && (
          <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs" style={{ color: 'var(--color-text-faint)' }}>
            {suffix}
          </span>
        )}
      </span>
      <span id={hintId} className="text-xs" style={{ color: 'var(--color-text-faint)' }}>{hint}</span>
    </label>
  )
}

export default function IncomeCalculatorPage() {
  const [initialContribution, setInitialContribution] = useState('0')
  const [monthlyContribution, setMonthlyContribution] = useState('0')
  const [annualRate, setAnnualRate] = useState('0')
  const [months, setMonths] = useState('120')

  const result = useMemo(() => {
    try {
      return {
        value: calculateIncomeProjection({
          initialContribution: parseInput(initialContribution),
          monthlyContribution: parseInput(monthlyContribution),
          annualEffectiveRatePercent: parseInput(annualRate),
          months: parseInput(months),
        }),
        error: null,
      }
    } catch (error) {
      return { value: null, error: error instanceof Error ? error.message : 'Revise os valores informados.' }
    }
  }, [annualRate, initialContribution, monthlyContribution, months])

  const yearlyPoints = result.value?.points.filter(point => point.month === 0 || point.month % 12 === 0) ?? []
  const projection = result.value

  return (
    <div className="page-container">
      <section className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(280px,0.8fr)_minmax(0,1.5fr)]" aria-label="Premissas e projeção">
        <div className="card flex flex-col gap-5 p-4 sm:p-5">
          <div>
            <h2 className="section-card-title">Premissas</h2>
            <p className="mt-1 text-xs" style={{ color: 'var(--color-text-muted)' }}>
              Informe valores e taxa efetiva anual. Não há taxa sugerida.
            </p>
          </div>
          <Field
            label="Aporte inicial"
            hint="Valor aplicado no início do período."
            value={initialContribution}
            onChange={setInitialContribution}
            min={0}
            max={1_000_000_000}
            step={0.01}
            suffix="R$"
          />
          <Field
            label="Aporte mensal"
            hint="Considerado no fim de cada mês."
            value={monthlyContribution}
            onChange={setMonthlyContribution}
            min={0}
            max={1_000_000_000}
            step={0.01}
            suffix="R$"
          />
          <Field
            label="Taxa efetiva anual"
            hint="Taxa constante informada pelo usuário; pode ser zero ou negativa acima de -100%."
            value={annualRate}
            onChange={setAnnualRate}
            min={-99.99}
            max={1000}
            step={0.01}
            suffix="% a.a."
          />
          <Field
            label="Prazo"
            hint="De 1 a 600 meses."
            value={months}
            onChange={setMonths}
            min={1}
            max={600}
            step={1}
            suffix="meses"
          />
          {result.error && (
            <p role="alert" className="text-sm" style={{ color: 'var(--color-error)' }}>{result.error}</p>
          )}
        </div>

        <div className="card min-w-0 p-4 sm:p-5">
          <div className="mb-4 flex flex-wrap items-start justify-between gap-2">
            <div>
              <h2 className="section-card-title">Patrimônio projetado</h2>
              <p className="mt-1 text-xs" style={{ color: 'var(--color-text-muted)' }}>
                Taxa mensal equivalente: {projection ? `${percentage.format(projection.monthlyEffectiveRate * 100)}% a.m.` : '—'}
              </p>
            </div>
            <TrendingUp size={17} style={{ color: 'var(--color-primary)' }} aria-hidden="true" />
          </div>

          {projection ? (
            <>
              <div className="mb-3 grid grid-cols-1 gap-3 sm:grid-cols-3">
                <div className="rounded-lg p-3" style={{ background: 'var(--color-surface-2)' }}>
                  <p className="kpi-label">Total aportado</p>
                  <p className="mt-1 text-base font-semibold tabular-nums">{currency.format(projection.totalInvested)}</p>
                </div>
                <div className="rounded-lg p-3" style={{ background: 'var(--color-surface-2)' }}>
                  <p className="kpi-label">Rendimento projetado</p>
                  <p className="mt-1 text-base font-semibold tabular-nums">{currency.format(projection.projectedReturn)}</p>
                </div>
                <div className="rounded-lg p-3" style={{ background: 'var(--color-surface-2)' }}>
                  <p className="kpi-label">Saldo final</p>
                  <p className="mt-1 text-base font-semibold tabular-nums" style={{ color: 'var(--color-primary)' }}>{currency.format(projection.projectedBalance)}</p>
                </div>
              </div>
              <div className="h-64 min-w-0" role="img" aria-label="Gráfico de patrimônio e total aportado ao longo do prazo">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={projection.points} margin={{ top: 8, right: 6, left: 4, bottom: 0 }}>
                    <defs>
                      <linearGradient id="incomeProjectionFill" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="var(--color-primary)" stopOpacity={0.28} />
                        <stop offset="95%" stopColor="var(--color-primary)" stopOpacity={0.02} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid stroke="var(--color-divider)" strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="month" tickLine={false} axisLine={false} tick={{ fill: 'var(--color-text-faint)', fontSize: 11 }} tickFormatter={value => `${value}m`} />
                    <YAxis width={72} tickLine={false} axisLine={false} tick={{ fill: 'var(--color-text-faint)', fontSize: 10 }} tickFormatter={value => currency.format(Number(value))} />
                    <Tooltip
                      formatter={(value, name) => [currency.format(Number(value)), name === 'projectedBalance' ? 'Patrimônio' : 'Total aportado']}
                      labelFormatter={label => `Mês ${label}`}
                      contentStyle={{ background: 'var(--color-surface-2)', border: '1px solid var(--color-border)', borderRadius: 'var(--radius-md)', color: 'var(--color-text)' }}
                    />
                    <Area type="monotone" dataKey="invested" name="Total aportado" stroke="var(--color-text-muted)" strokeDasharray="4 4" fill="transparent" strokeWidth={1.5} />
                    <Area type="monotone" dataKey="projectedBalance" name="Patrimônio" stroke="var(--color-primary)" fill="url(#incomeProjectionFill)" strokeWidth={2} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </>
          ) : (
            <div className="flex min-h-64 items-center justify-center text-sm" style={{ color: 'var(--color-text-muted)' }}>
              Corrija as premissas para calcular a projeção.
            </div>
          )}
        </div>
      </section>

      <p className="sr-only" role="status" aria-live="polite" aria-atomic="true">
        {projection
          ? `Projeção atualizada. Total aportado: ${currency.format(projection.totalInvested)}. Rendimento projetado: ${currency.format(projection.projectedReturn)}. Saldo final: ${currency.format(projection.projectedBalance)}.`
          : result.error ?? 'A projeção ainda não está disponível.'}
      </p>

      {projection && (
        <section className="card overflow-hidden" aria-labelledby="projection-table-title">
          <div className="section-card-header">
            <h2 id="projection-table-title" className="section-card-title">Evolução anual</h2>
          </div>
          <div className="table-scroll" role="region" aria-label="Tabela de evolução anual; use as setas para rolar horizontalmente" tabIndex={0}>
            <table className="min-w-[520px]">
              <thead>
                <tr>
                  <th scope="col" className="px-4 py-3 text-left text-xs font-semibold">Período</th>
                  <th scope="col" className="px-4 py-3 text-right text-xs font-semibold">Total aportado</th>
                  <th scope="col" className="px-4 py-3 text-right text-xs font-semibold">Rendimento</th>
                  <th scope="col" className="px-4 py-3 text-right text-xs font-semibold">Patrimônio projetado</th>
                </tr>
              </thead>
              <tbody>
                {yearlyPoints.map(point => (
                  <tr key={point.month} style={{ borderTop: '1px solid var(--color-divider)' }}>
                    <th scope="row" className="px-4 py-3 text-left text-sm font-medium">{point.month === 0 ? 'Início' : `${point.month} meses`}</th>
                    <td className="px-4 py-3 text-right text-sm tabular-nums">{currency.format(point.invested)}</td>
                    <td className="px-4 py-3 text-right text-sm tabular-nums">{currency.format(point.projectedReturn)}</td>
                    <td className="px-4 py-3 text-right text-sm font-medium tabular-nums">{currency.format(point.projectedBalance)}</td>
                  </tr>
                ))}
                {projection.points[projection.points.length - 1].month % 12 !== 0 && (
                  <tr style={{ borderTop: '1px solid var(--color-divider)' }}>
                    <th scope="row" className="px-4 py-3 text-left text-sm font-medium">{months} meses</th>
                    <td className="px-4 py-3 text-right text-sm tabular-nums">{currency.format(projection.totalInvested)}</td>
                    <td className="px-4 py-3 text-right text-sm tabular-nums">{currency.format(projection.projectedReturn)}</td>
                    <td className="px-4 py-3 text-right text-sm font-medium tabular-nums">{currency.format(projection.projectedBalance)}</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      )}

      <aside className="card flex items-start gap-3 p-4" aria-label="Limites da simulação">
        <CircleHelp size={17} className="mt-0.5 shrink-0" style={{ color: 'var(--color-text-muted)' }} aria-hidden="true" />
        <p className="text-xs leading-relaxed" style={{ color: 'var(--color-text-muted)' }}>
          Simulação matemática com taxa constante e capitalização mensal equivalente. A taxa informada é efetiva anual; os aportes mensais entram no fim de cada mês. O cálculo não considera impostos, inflação, tarifas, variação de retorno ou datas específicas e não altera dados da carteira.
        </p>
      </aside>
    </div>
  )
}
