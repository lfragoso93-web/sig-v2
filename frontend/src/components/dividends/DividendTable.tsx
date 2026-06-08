import type { Dividend } from '@/hooks/useDividends'
import { formatBRL, formatDate, assetBadgeClass } from '@/utils/format'

interface Props {
  dividends: Dividend[]
  loading: boolean
}

const TYPE_LABEL: Record<string, string> = {
  dividendo:    'Dividendo',
  jcp:          'JCP',
  rendimento:   'Rendimento',
  amortizacao:  'Amortização',
  outro:        'Outro',
}

export default function DividendTable({ dividends, loading }: Props) {
  return (
    <div className="bg-surface border border-[var(--color-border)] rounded-xl overflow-hidden">
      <div className="px-4 py-3 border-b border-[var(--color-divider)]">
        <h3 className="text-sm font-semibold">Histórico de proventos</h3>
      </div>

      {loading ? (
        <div className="p-5 flex flex-col gap-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="skeleton h-9 w-full rounded" />
          ))}
        </div>
      ) : dividends.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-14 text-center">
          <p className="text-sm font-medium mb-1">Nenhum provento registrado</p>
          <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
            Clique em "Lançar provento" para adicionar.
          </p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="positions-table">
            <thead>
              <tr>
                <th>Pagamento</th>
                <th>Ativo</th>
                <th>Tipo</th>
                <th className="text-right">Qtd</th>
                <th className="text-right">Valor/cota</th>
                <th className="text-right">Total</th>
              </tr>
            </thead>
            <tbody>
              {dividends
                .slice()
                .sort((a, b) => b.payment_date.localeCompare(a.payment_date))
                .map(d => (
                  <tr key={d.id}>
                    <td className="text-sm" style={{ color: 'var(--color-text-muted)' }}>
                      {formatDate(d.payment_date)}
                    </td>
                    <td>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-sm">{d.ticker}</span>
                        <span className={`asset-badge ${assetBadgeClass(d.asset_type)}`}>
                          {d.asset_type}
                        </span>
                      </div>
                    </td>
                    <td>
                      <span
                        className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium"
                        style={{
                          background: 'oklch(from var(--color-gold) l c h / 0.12)',
                          color: 'var(--color-gold)',
                        }}
                      >
                        {TYPE_LABEL[d.type] ?? d.type}
                      </span>
                    </td>
                    <td className="text-right text-sm tabular-nums">{d.quantity}</td>
                    <td className="text-right text-sm tabular-nums">{formatBRL(d.amount)}</td>
                    <td className="text-right text-sm font-semibold tabular-nums"
                      style={{ color: 'var(--color-gold)' }}>
                      {formatBRL(d.amount * d.quantity)}
                    </td>
                  </tr>
                ))}
            </tbody>
            <tfoot>
              <tr style={{ background: 'var(--color-surface-offset)', borderTop: '2px solid var(--color-divider)' }}>
                <td colSpan={5} className="px-3 py-2.5 text-xs font-semibold" style={{ color: 'var(--color-text-muted)' }}>
                  {dividends.length} provento{dividends.length !== 1 ? 's' : ''}
                </td>
                <td className="text-right px-3 py-2.5 text-sm font-bold tabular-nums"
                  style={{ color: 'var(--color-gold)' }}>
                  {formatBRL(dividends.reduce((s, d) => s + d.amount * d.quantity, 0))}
                </td>
              </tr>
            </tfoot>
          </table>
        </div>
      )}
    </div>
  )
}
