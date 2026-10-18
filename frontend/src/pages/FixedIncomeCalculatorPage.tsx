import { useId, useMemo, useState } from 'react'
import { Calculator, CircleHelp } from 'lucide-react'
import { calculateFixedIncomeComparison } from '@/utils/fixedIncomeComparison'
import { FixedIncomeProductType, isFixedIncomeProductTaxExempt } from '@/utils/fixedIncomeTaxTreatment'

const currency = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })
const percentage = new Intl.NumberFormat('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
const productTypes: Array<[FixedIncomeProductType, string]> = [
  ['CDB', 'CDB'], ['RDB', 'RDB'], ['LCI', 'LCI'], ['LCA', 'LCA'], ['LC', 'LC'],
  ['LIG', 'LIG'], ['CRI', 'CRI'], ['CRA', 'CRA'], ['DEBENTURE', 'Debênture'],
  ['DEBENTURE_INCENTIVADA', 'Debênture incentivada'],
  ['LETRA_FINANCEIRA', 'Letra Financeira'], ['OUTRO', 'Outro'],
]

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
  suffix: string
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
        <span aria-hidden="true" className="absolute right-3 top-1/2 -translate-y-1/2 text-xs" style={{ color: 'var(--color-text-faint)' }}>
          {suffix}
        </span>
      </span>
      <span id={hintId} className="text-xs" style={{ color: 'var(--color-text-faint)' }}>{hint}</span>
    </label>
  )
}

export default function FixedIncomeCalculatorPage() {
  const firstTaxHintId = useId()
  const secondTaxHintId = useId()
  const [principal, setPrincipal] = useState('10000')
  const [days, setDays] = useState('365')
  const [firstProductType, setFirstProductType] = useState<FixedIncomeProductType>('CDB')
  const [firstRate, setFirstRate] = useState('12')
  const [secondProductType, setSecondProductType] = useState<FixedIncomeProductType>('LCI')
  const [secondRate, setSecondRate] = useState('10')

  const result = useMemo(() => {
    try {
      return {
        value: calculateFixedIncomeComparison({
          principal: parseInput(principal),
          daysToMaturity: parseInput(days),
          firstProductType,
          firstAnnualEffectiveRatePercent: parseInput(firstRate),
          secondProductType,
          secondAnnualEffectiveRatePercent: parseInput(secondRate),
        }),
        error: null,
      }
    } catch (error) {
      return { value: null, error: error instanceof Error ? error.message : 'Revise os valores informados.' }
    }
  }, [days, firstProductType, firstRate, principal, secondProductType, secondRate])

  const comparison = result.value

  return (
    <div className="page-container">
      <header className="page-header">
        <div>
          <h1 className="page-title">Simulador de Renda Fixa</h1>
          <p className="page-subtitle">
            Compare dois títulos. O tratamento de IR é definido automaticamente pelo tipo de produto.
          </p>
        </div>
        <div className="flex items-center gap-2 rounded-lg px-3 py-2 text-xs" style={{ background: 'var(--color-surface-2)', color: 'var(--color-text-muted)' }}>
          <Calculator size={15} aria-hidden="true" />
          Simulação independente da carteira
        </div>
      </header>

      <section className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(280px,0.8fr)_minmax(0,1.5fr)]" aria-label="Premissas e comparação">
        <div className="card flex flex-col gap-5 p-4 sm:p-5">
          <div>
            <h2 className="section-card-title">Premissas</h2>
            <p className="mt-1 text-xs" style={{ color: 'var(--color-text-muted)' }}>
              Informe taxas efetivas anuais. O simulador não busca taxas de mercado.
            </p>
          </div>
          <Field
            label="Valor aplicado"
            hint="Mesmo principal nos dois cenários."
            value={principal}
            onChange={setPrincipal}
            min={0.01}
            max={1_000_000_000}
            step={0.01}
            suffix="R$"
          />
          <Field
            label="Prazo até o vencimento"
            hint="Mínimo de 30 dias; o cálculo não estima IOF."
            value={days}
            onChange={setDays}
            min={30}
            max={36_500}
            step={1}
            suffix="dias"
          />
          <label className="flex flex-col gap-1.5">
            <span className="text-sm font-medium" style={{ color: 'var(--color-text)' }}>Tipo do primeiro título</span>
            <select aria-describedby={firstTaxHintId} className="input w-full" value={firstProductType} onChange={event => setFirstProductType(event.target.value as FixedIncomeProductType)}>
              {productTypes.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select>
            <span id={firstTaxHintId} className="text-xs" style={{ color: 'var(--color-text-faint)' }}>
              Tratamento automático: {isFixedIncomeProductTaxExempt(firstProductType) ? 'isento de IR, conforme enquadramento legal' : 'tributável pela tabela regressiva'}.
            </span>
          </label>
          <Field
            label="Taxa anual do primeiro título"
            hint="Use a taxa efetiva anual bruta da oferta."
            value={firstRate}
            onChange={setFirstRate}
            min={-99.99}
            max={1000}
            step={0.01}
            suffix="% a.a."
          />
          <label className="flex flex-col gap-1.5">
            <span className="text-sm font-medium" style={{ color: 'var(--color-text)' }}>Tipo do segundo título</span>
            <select aria-describedby={secondTaxHintId} className="input w-full" value={secondProductType} onChange={event => setSecondProductType(event.target.value as FixedIncomeProductType)}>
              {productTypes.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select>
            <span id={secondTaxHintId} className="text-xs" style={{ color: 'var(--color-text-faint)' }}>
              Tratamento automático: {isFixedIncomeProductTaxExempt(secondProductType) ? 'isento de IR, conforme enquadramento legal' : 'tributável pela tabela regressiva'}.
            </span>
          </label>
          <Field
            label="Taxa anual do segundo título"
            hint="Use a taxa efetiva anual bruta da oferta."
            value={secondRate}
            onChange={setSecondRate}
            min={-99.99}
            max={1000}
            step={0.01}
            suffix="% a.a."
          />
          {result.error && (
            <p role="alert" className="text-sm" style={{ color: 'var(--color-error)' }}>{result.error}</p>
          )}
        </div>

        <div className="card min-w-0 p-4 sm:p-5">
          <div className="mb-4">
            <h2 className="section-card-title">Resultado estimado</h2>
            <p className="mt-1 text-xs" style={{ color: 'var(--color-text-muted)' }}>
              IR estimado pela faixa de prazo da aplicação: {comparison ? `${comparison.daysToMaturity} dias` : '—'}.
            </p>
          </div>

          {comparison ? (
            <>
              <div className="table-scroll" role="region" aria-label="Tabela de comparação dos títulos; use as setas para rolar horizontalmente" tabIndex={0}>
                <table className="min-w-[560px]">
                  <thead>
                    <tr>
                      <th scope="col" className="px-3 py-3 text-left text-xs font-semibold">Item</th>
                      <th scope="col" className="px-3 py-3 text-right text-xs font-semibold">{comparison.first.productType}</th>
                      <th scope="col" className="px-3 py-3 text-right text-xs font-semibold">{comparison.second.productType}</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr style={{ borderTop: '1px solid var(--color-divider)' }}>
                      <th scope="row" className="px-3 py-3 text-left text-sm font-medium">Valor bruto no vencimento</th>
                      <td className="px-3 py-3 text-right text-sm tabular-nums">{currency.format(comparison.first.grossMaturityValue)}</td>
                      <td className="px-3 py-3 text-right text-sm tabular-nums">{currency.format(comparison.second.grossMaturityValue)}</td>
                    </tr>
                    <tr style={{ borderTop: '1px solid var(--color-divider)' }}>
                      <th scope="row" className="px-3 py-3 text-left text-sm font-medium">Rendimento bruto</th>
                      <td className="px-3 py-3 text-right text-sm tabular-nums">{currency.format(comparison.first.grossReturn)}</td>
                      <td className="px-3 py-3 text-right text-sm tabular-nums">{currency.format(comparison.second.grossReturn)}</td>
                    </tr>
                    <tr style={{ borderTop: '1px solid var(--color-divider)' }}>
                      <th scope="row" className="px-3 py-3 text-left text-sm font-medium">Alíquota estimada de IR</th>
                      <td className="px-3 py-3 text-right text-sm tabular-nums">{percentage.format(comparison.first.incomeTaxRate * 100)}%</td>
                      <td className="px-3 py-3 text-right text-sm tabular-nums">{percentage.format(comparison.second.incomeTaxRate * 100)}%</td>
                    </tr>
                    <tr style={{ borderTop: '1px solid var(--color-divider)' }}>
                      <th scope="row" className="px-3 py-3 text-left text-sm font-medium">IR estimado</th>
                      <td className="px-3 py-3 text-right text-sm tabular-nums">{currency.format(comparison.first.incomeTax)}</td>
                      <td className="px-3 py-3 text-right text-sm tabular-nums">{currency.format(comparison.second.incomeTax)}</td>
                    </tr>
                    <tr style={{ borderTop: '1px solid var(--color-divider)' }}>
                      <th scope="row" className="px-3 py-3 text-left text-sm font-semibold">Valor líquido no vencimento</th>
                      <td className="px-3 py-3 text-right text-sm font-semibold tabular-nums">{currency.format(comparison.first.netMaturityValue)}</td>
                      <td className="px-3 py-3 text-right text-sm font-semibold tabular-nums">{currency.format(comparison.second.netMaturityValue)}</td>
                    </tr>
                    <tr style={{ borderTop: '1px solid var(--color-divider)' }}>
                      <th scope="row" className="px-3 py-3 text-left text-sm font-medium">Rentabilidade líquida efetiva anual</th>
                      <td className="px-3 py-3 text-right text-sm tabular-nums">{percentage.format(comparison.first.netEffectiveAnnualRatePercent)}%</td>
                      <td className="px-3 py-3 text-right text-sm tabular-nums">{percentage.format(comparison.second.netEffectiveAnnualRatePercent)}%</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div className="mt-4 rounded-lg p-4" style={{ background: 'var(--color-surface-2)' }}>
                <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                  Para igualar o valor líquido do segundo título, o primeiro precisaria render aproximadamente
                  {' '}
                  <strong style={{ color: 'var(--color-text)' }}>
                    {percentage.format(comparison.firstEquivalentRateForSecondScenario)}% a.a.
                  </strong>
                  {' '}brutos.
                </p>
              </div>
            </>
          ) : (
            <div className="flex min-h-64 items-center justify-center text-sm" style={{ color: 'var(--color-text-muted)' }}>
              Corrija as premissas para calcular a comparação.
            </div>
          )}
        </div>
      </section>

      <p className="sr-only" role="status" aria-live="polite" aria-atomic="true">
        {comparison
          ? `Comparação atualizada. Valor líquido no vencimento: ${comparison.first.productType}, ${currency.format(comparison.first.netMaturityValue)}; ${comparison.second.productType}, ${currency.format(comparison.second.netMaturityValue)}.`
          : result.error ?? 'A comparação ainda não está disponível.'}
      </p>

      <aside className="card flex items-start gap-3 p-4" aria-label="Limites e premissas tributárias">
        <CircleHelp size={17} className="mt-0.5 shrink-0" style={{ color: 'var(--color-text-muted)' }} aria-hidden="true" />
        <p className="text-xs leading-relaxed" style={{ color: 'var(--color-text-muted)' }}>
          Simulação matemática para pessoa física residente no Brasil, com taxa anual efetiva constante, principal único e resgate no vencimento. A regra automática usa o tipo informado e pressupõe que a emissão e o titular atendam aos requisitos legais, especialmente para títulos isentos. Prazo mínimo de 30 dias exclui a estimativa de IOF. Não considera taxas, cupons, come-cotas, marcação a mercado, risco do emissor ou oscilação de indexadores; não consulta mercado, não altera a carteira e não substitui a informação da instituição financeira ou orientação fiscal.
        </p>
      </aside>
    </div>
  )
}
