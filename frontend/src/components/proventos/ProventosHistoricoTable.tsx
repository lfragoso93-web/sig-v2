import { ProventosHistoricoMes } from '@/services/proventosService'
import { formatBRL } from '@/utils/format'

const MONTHS = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez']

const cellText  = { color: 'var(--color-text)' }
const cellMuted = { color: 'var(--color-text-muted)' }
const cellFaint = { color: 'var(--color-text-faint)' }

export default function ProventosHistoricoTable({ data }: { data: ProventosHistoricoMes[] }) {
  if (!data.length) return (
    <p className="text-xs p-4" style={cellMuted}>Sem dados</p>
  )

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[800px] text-xs" style={{ borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ borderBottom: '1px solid var(--color-divider)' }}>
            <th className="px-3 py-2 text-left font-medium w-12" style={cellMuted}>Ano</th>
            {MONTHS.map(m => (
              <th key={m} className="px-2 py-2 text-right font-medium" style={cellMuted}>{m}</th>
            ))}
            <th className="px-3 py-2 text-right font-medium" style={cellMuted}>Média</th>
            <th className="px-3 py-2 text-right font-medium" style={cellMuted}>Total</th>
          </tr>
        </thead>
        <tbody>
          {data.map((row, rowIdx) => (
            <tr
              key={row.year}
              style={{
                borderBottom: '1px solid oklch(from var(--color-text) l c h / 0.05)',
                background: rowIdx % 2 !== 0 ? 'var(--color-surface-offset)' : 'transparent',
              }}
              onMouseEnter={e => (e.currentTarget.style.background = 'oklch(from var(--color-primary) l c h / 0.04)')}
              onMouseLeave={e => (e.currentTarget.style.background = rowIdx % 2 !== 0 ? 'var(--color-surface-offset)' : 'transparent')}
            >
              <td className="px-3 py-2 font-semibold" style={cellText}>{row.year}</td>
              {row.months.map((val, idx) => (
                <td key={idx} className="px-2 py-2 text-right tabular-nums" style={val && val > 0 ? cellText : cellFaint}>
                  {val != null && val > 0 ? formatBRL(val).replace('R$\u00a0', '') : '—'}
                </td>
              ))}
              <td className="px-3 py-2 text-right tabular-nums font-medium" style={{ color: 'var(--color-primary)' }}>
                {formatBRL(row.media).replace('R$\u00a0', '')}
              </td>
              <td className="px-3 py-2 text-right tabular-nums font-semibold" style={{ color: 'var(--color-success)' }}>
                {formatBRL(row.total)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
