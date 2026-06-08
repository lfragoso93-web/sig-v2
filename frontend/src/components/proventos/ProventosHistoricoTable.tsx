import clsx from 'clsx'
import { ProventosHistoricoMes } from '@/services/proventosService'
import { formatBRL } from '@/utils/format'

const MONTHS = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez']

export default function ProventosHistoricoTable({ data }: { data: ProventosHistoricoMes[] }) {
  if (!data.length) return <p className="text-xs text-muted p-4">Sem dados</p>

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[800px] text-xs">
        <thead>
          <tr className="border-b border-light-border dark:border-dark-border">
            <th className="px-3 py-2 text-left font-medium text-muted w-12">Ano</th>
            {MONTHS.map(m => (
              <th key={m} className="px-2 py-2 text-right font-medium text-muted">{m}</th>
            ))}
            <th className="px-3 py-2 text-right font-medium text-muted">Média</th>
            <th className="px-3 py-2 text-right font-medium text-muted">Total</th>
          </tr>
        </thead>
        <tbody>
          {data.map(row => (
            <tr key={row.year} className="border-b border-light-border/30 dark:border-dark-border/30 hover:bg-light-100 dark:hover:bg-dark-700 transition-colors">
              <td className="px-3 py-2 font-semibold text-gray-700 dark:text-gray-300">{row.year}</td>
              {row.months.map((val, idx) => (
                <td key={idx} className={clsx(
                  'px-2 py-2 text-right tabular-nums',
                  val && val > 0 ? 'text-gray-800 dark:text-gray-200' : 'text-muted'
                )}>
                  {val != null && val > 0 ? formatBRL(val).replace('R$\u00a0', '') : '—'}
                </td>
              ))}
              <td className="px-3 py-2 text-right tabular-nums font-medium text-brand-primary">
                {formatBRL(row.media).replace('R$\u00a0', '')}
              </td>
              <td className="px-3 py-2 text-right tabular-nums font-semibold text-gray-800 dark:text-gray-200">
                {formatBRL(row.total)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
