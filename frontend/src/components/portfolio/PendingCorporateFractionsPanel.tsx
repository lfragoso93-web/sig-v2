import { Clock3 } from 'lucide-react'
import { usePendingCorporateFractions } from '@/hooks/usePortfolio'

export default function PendingCorporateFractionsPanel({
  portfolioId,
}: {
  portfolioId: number
}) {
  const { data: fractions = [], isLoading, error } =
    usePendingCorporateFractions(portfolioId)

  if (!isLoading && !error && fractions.length === 0) return null

  return (
    <section className="card overflow-hidden" aria-labelledby="pending-fractions-title">
      <div className="section-card-header">
        <div className="flex items-center gap-2">
          <Clock3 size={15} style={{ color: 'var(--color-warning)' }} />
          <span id="pending-fractions-title" className="section-card-title">
            Frações pendentes de liquidação
          </span>
        </div>
      </div>
      <div className="p-5 md:p-6">
        {isLoading ? (
          <div className="h-16 skeleton rounded" />
        ) : error ? (
          <p role="alert" className="text-sm" style={{ color: 'var(--color-error)' }}>
            Não foi possível carregar as frações pendentes.
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
      </div>
    </section>
  )
}
