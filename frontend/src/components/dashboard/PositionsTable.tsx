import type { Position } from '@/hooks/usePerformance'
import { formatBRL, formatPct, assetBadgeClass } from '@/utils/format'

interface Props {
  positions?: Position[]
}

export default function PositionsTable({ positions }: Props) {
  // guard: nunca crash se positions vier undefined ou null
  if (!positions || positions.length === 0) {
    return (
      <div className="bg-surface border border-[var(--color-border)] rounded-xl p-8 text-center">
        <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>
          Nenhuma posição. Registre sua primeira transação.
        </p>
      </div>
    )
  }

  return (
    <div className="bg-surface border border-[var(--color-border)] rounded-xl overflow-hidden">
      <div className="px-4 py-3 border-b border-[var(--color-divider)]">
        <h3 className="text-sm font-semibold">Posições</h3>
      </div>
      <div className="overflow-x-auto">
        <table className="positions-table">
          <thead>
            <tr>
              <th>Ativo</th>
              <th className="text-right">Qtd</th>
              <th className="text-right">P. Médio</th>
              <th className="text-right">P. Atual</th>
              <th className="text-right">Total</th>
              <th className="text-right">Result.</th>
            </tr>
          </thead>
          <tbody>
            {positions.map((p) => {
              const pos = p.gain >= 0
              return (
                <tr key={p.asset_id ?? p.ticker}>
                  <td>
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-sm">{p.ticker}</span>
                      <span className={`asset-badge ${assetBadgeClass(p.asset_type ?? '')}`}>
                        {p.asset_type}
                      </span>
                    </div>
                    <p className="text-xs mt-0.5" style={{ color: 'var(--color-text-muted)' }}>{p.name}</p>
                  </td>
                  <td className="text-right text-sm">{p.quantity}</td>
                  <td className="text-right text-sm">{formatBRL(p.avg_price)}</td>
                  <td className="text-right text-sm">{formatBRL(p.current_price)}</td>
                  <td className="text-right text-sm font-medium">{formatBRL(p.current_value)}</td>
                  <td className="text-right">
                    <span
                      className="text-sm font-semibold"
                      style={{ color: pos ? 'var(--color-success)' : 'var(--color-notification)' }}
                    >
                      {formatPct(p.gain_pct)}
                    </span>
                    <p className="text-xs" style={{ color: pos ? 'var(--color-success)' : 'var(--color-notification)' }}>
                      {pos ? '+' : ''}{formatBRL(p.gain)}
                    </p>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
