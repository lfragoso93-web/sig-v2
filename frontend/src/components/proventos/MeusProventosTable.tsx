import clsx from 'clsx'
import { ProventoItem } from '@/services/proventosService'
import { formatBRL, formatQuantity } from '@/utils/format'
import { format, parseISO } from 'date-fns'
import { ptBR } from 'date-fns/locale'

const ASSET_TYPE_LABELS: Record<string, string> = {
  ACAO_NACIONAL: 'Ações',
  FII: 'FII',
  ETF_NACIONAL: 'ETF',
  TESOURO_DIRETO: 'Tesouro',
  STOCK: 'Stock',
  ETF_INTERNACIONAL: 'ETF Int.',
  CRIPTO: 'Cripto',
  RENDA_FIXA: 'Renda Fixa',
}

const DIVIDEND_TYPE_LABELS: Record<string, string> = {
  DIVIDENDO: 'Dividendos',
  JCP: 'JCP',
  RENDIMENTO: 'Rendimento',
  AMORTIZACAO: 'Amortização',
  BONIFICACAO: 'Bonificação',
  OUTROS: 'Outros',
}

function fmt(dateStr: string | null): string {
  if (!dateStr) return '—'
  try { return format(parseISO(dateStr), 'dd/MM/yyyy', { locale: ptBR }) } catch { return dateStr }
}

export default function MeusProventosTable({ data }: { data: ProventoItem[] }) {
  if (!data.length) return <p className="text-xs text-muted p-4">Sem proventos no período.</p>

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[900px]">
        <thead>
          <tr className="border-b border-light-border dark:border-dark-border">
            {['Ativo','Tipo de Ativo','Status','Tipo Pgto','Data Com','Data Pgto','Quantidade','Valor/Unit.','Valor Total','Líquido'].map(h => (
              <th key={h} className="px-3 py-2 text-xs font-medium text-muted text-left first:pl-4 last:pr-4">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map(item => (
            <tr key={item.id} className="border-b border-light-border/30 dark:border-dark-border/30 hover:bg-light-100 dark:hover:bg-dark-700 transition-colors">
              <td className="px-3 py-2 pl-4">
                <span className="text-xs font-semibold text-gray-800 dark:text-gray-200">{item.ticker}</span>
              </td>
              <td className="px-3 py-2">
                <span className="badge-gray">{ASSET_TYPE_LABELS[item.asset_type] ?? item.asset_type}</span>
              </td>
              <td className="px-3 py-2">
                <span className={clsx('badge', item.status === 'RECEBIDO' ? 'badge-green' : 'badge-blue')}>
                  {item.status === 'RECEBIDO' ? 'Recebido' : 'A Receber'}
                </span>
              </td>
              <td className="px-3 py-2 text-xs text-gray-700 dark:text-gray-300">
                {DIVIDEND_TYPE_LABELS[item.dividend_type] ?? item.dividend_type}
              </td>
              <td className="px-3 py-2 text-xs tabular-nums text-muted">{fmt(item.ex_date)}</td>
              <td className="px-3 py-2 text-xs tabular-nums text-muted">{fmt(item.payment_date)}</td>
              <td className="px-3 py-2 text-xs tabular-nums text-right">{formatQuantity(item.quantity)}</td>
              <td className="px-3 py-2 text-xs tabular-nums text-right">{formatBRL(item.value_per_unit)}</td>
              <td className="px-3 py-2 text-xs tabular-nums text-right font-medium text-gray-800 dark:text-gray-200">{formatBRL(item.total_value)}</td>
              <td className="px-3 py-2 pr-4 text-xs tabular-nums text-right font-medium text-positive">{formatBRL(item.net_value)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
