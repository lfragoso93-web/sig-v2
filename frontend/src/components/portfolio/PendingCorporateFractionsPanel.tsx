import { Clock3 } from 'lucide-react'
import {
  usePendingCorporateFractions,
  usePortfolioCorporateRights,
} from '@/hooks/usePortfolio'

export default function PendingCorporateFractionsPanel({
  portfolioId,
}: {
  portfolioId: number
}) {
  const { data: fractions = [], isLoading, error } =
    usePendingCorporateFractions(portfolioId)
  const rightsQuery = usePortfolioCorporateRights(portfolioId)
  const rights = rightsQuery.data ?? []

  if (!isLoading && !error && fractions.length === 0 && rights.length === 0) return null

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
              A fração é calculada pela quantidade da sua carteira na data efetiva do
              evento. Ela aparece aqui enquanto a liquidação não for confirmada; sem
              evidência do crédito, não recebe valor estimado.
            </p>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs" style={{ color: 'var(--color-text-faint)' }}>
                    <th className="py-2 pr-4 font-medium">Ativo</th>
                    <th className="py-2 pr-4 font-medium">Evento</th>
                    <th className="py-2 pr-4 font-medium">Data</th>
                    <th className="py-2 text-right font-medium">Quantidade</th>
                    <th className="py-2 pl-4 text-right font-medium">Valor</th>
                  </tr>
                </thead>
                <tbody>
                  {fractions.map(fraction => (
                    <tr
                      key={fraction.source_event_id}
                      className="border-t"
                      style={{ borderColor: 'var(--color-divider)' }}
                    >
                      <td className="py-3 pr-4 font-semibold">{fraction.ticker}</td>
                      <td className="py-3 pr-4">{fraction.event_type}</td>
                      <td className="py-3 pr-4">
                        {fraction.event_date.split('-').reverse().join('/')}
                      </td>
                      <td className="py-3 text-right tabular-nums">
                        {Number(fraction.fractional_quantity).toLocaleString('pt-BR')}
                      </td>
                      <td className="py-3 pl-4 text-right" style={{ color: 'var(--color-text-muted)' }}>
                        A confirmar
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
        {rights.length > 0 && (
          <div className={fractions.length > 0 ? 'mt-6 border-t pt-5' : ''}>
            <h3 className="text-sm font-semibold mb-3">Apuração de bonificação por carteira</h3>
            <p className="text-xs mb-4" style={{ color: 'var(--color-text-muted)' }}>
              Quantidades calculadas pela posição na data-base. O valor das frações é uma estimativa bruta baseada na evidência do emissor; não confirma o crédito individual.
            </p>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs" style={{ color: 'var(--color-text-faint)' }}>
                    <th className="py-2 pr-4 font-medium">Ativo / espécie</th>
                    <th className="py-2 pr-4 font-medium">Data-base</th>
                    <th className="py-2 pr-4 font-medium">Ações usadas em Units</th>
                    <th className="py-2 text-right font-medium">Ações inteiras / fração</th>
                    <th className="py-2 pl-4 text-right font-medium">Estimativa bruta</th>
                    <th className="py-2 pl-4 text-right font-medium">Custo atribuído à fração</th>
                    <th className="py-2 pl-4 text-right font-medium">Resultado estimado</th>
                  </tr>
                </thead>
                <tbody>
                  {rights.flatMap(right => right.components.map(component => (
                    <tr key={`${right.event_id}:${component.component}`} className="border-t" style={{ borderColor: 'var(--color-divider)' }}>
                      <td className="py-3 pr-4 font-semibold">{right.ticker} · {component.component}</td>
                      <td className="py-3 pr-4">{right.record_date.split('-').reverse().join('/')}</td>
                      <td className="py-3 pr-4 tabular-nums">{component.component_shares_in_units.toLocaleString('pt-BR')}</td>
                      <td className="py-3 text-right tabular-nums">{component.residual_whole_quantity.toLocaleString('pt-BR')} / {component.fractional_quantity.toLocaleString('pt-BR')}</td>
                      <td className="py-3 pl-4 text-right tabular-nums">R$ {component.gross_amount_brl.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                      <td className="py-3 pl-4 text-right tabular-nums">R$ {component.fractional_cost_basis_brl.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                      <td className="py-3 pl-4 text-right tabular-nums">R$ {component.estimated_fractional_result_brl.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                    </tr>
                  )))}
                  {rights.map(right => (
                    <tr key={`${right.event_id}:total`} className="border-t font-semibold" style={{ borderColor: 'var(--color-divider)' }}>
                      <td className="py-3 pr-4">Total {right.ticker}</td>
                      <td className="py-3 pr-4" colSpan={3}>
                        {right.settlement_status === 'AVAILABLE'
                          ? 'Disponível segundo o emissor; crédito individual não confirmado'
                          : 'Data de pagamento futura'}
                      </td>
                      <td className="py-3 pl-4 text-right tabular-nums">R$ {right.calculated_gross_amount_brl.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                      <td className="py-3 pl-4 text-right tabular-nums">R$ {right.fractional_cost_basis_brl.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                      <td className="py-3 pl-4 text-right tabular-nums">R$ {right.estimated_fractional_result_brl.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
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
