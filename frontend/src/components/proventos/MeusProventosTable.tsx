import { ProventoItem } from '@/services/proventosService'
import { formatBRL, formatQuantity } from '@/utils/format'
import { format, parseISO } from 'date-fns'
import { ptBR } from 'date-fns/locale'

const ASSET_TYPE_LABELS: Record<string, string> = {
  ACAO: 'Ações', ACAO_NACIONAL: 'Ações', FII: 'FII', ETF_NACIONAL: 'ETF',
  TESOURO_DIRETO: 'Tesouro', STOCK: 'Stock', BDR: 'BDR',
  ETF_INTERNACIONAL: 'ETF Int.', CRIPTO: 'Cripto', RENDA_FIXA: 'Renda Fixa',
}

const DIVIDEND_TYPE_LABELS: Record<string, string> = {
  DIVIDENDO: 'Dividendos', JCP: 'JCP', RENDIMENTO: 'Rendimento',
  AMORTIZACAO: 'Amortização', BONIFICACAO: 'Bonificação',
  SUBSCRICAO: 'Subscrição', OUTROS: 'Outros',
}

const NON_CASH_TYPES = new Set(['BONIFICACAO', 'SUBSCRICAO'])

function fmt(dateStr: string | null): string {
  if (!dateStr) return '—'
  try { return format(parseISO(dateStr), 'dd/MM/yyyy', { locale: ptBR }) } catch { return dateStr }
}

function fmtMaybeMoney(value: number | null | undefined): string {
  if (value === null || value === undefined) return '—'
  return formatBRL(value)
}

function isCashEvent(item: ProventoItem): boolean {
  if (typeof item.is_cash === 'boolean') return item.is_cash
  return !NON_CASH_TYPES.has(item.dividend_type)
}

const cellText  = { color: 'var(--color-text)' }
const cellMuted = { color: 'var(--color-text-muted)' }
const cellFaint = { color: 'var(--color-text-faint)' }

function StatusBadge({ status }: { status: string }) {
  const isRecebido = status === 'RECEBIDO'
  return (
    <span
      className="px-2 py-0.5 rounded-full text-[10px] font-semibold"
      style={{
        background: isRecebido
          ? 'oklch(from var(--color-success) l c h / 0.15)'
          : 'oklch(from var(--color-primary) l c h / 0.15)',
        color: isRecebido ? 'var(--color-success)' : 'var(--color-primary)',
      }}
    >
      {isRecebido ? 'Recebido' : 'A receber'}
    </span>
  )
}

function EventKindBadge({ item }: { item: ProventoItem }) {
  const cash = isCashEvent(item)
  return (
    <span
      className="px-1.5 py-0.5 rounded text-[9px] font-semibold"
      style={{
        background: cash
          ? 'oklch(from var(--color-success) l c h / 0.11)'
          : 'oklch(from var(--color-warning) l c h / 0.14)',
        color: cash ? 'var(--color-success)' : 'var(--color-warning)',
      }}
    >
      {cash ? 'Financeiro' : 'Não-cash'}
    </span>
  )
}

function ProventoCard({ item }: { item: ProventoItem }) {
  const typeLabel = DIVIDEND_TYPE_LABELS[item.dividend_type] ?? item.dividend_type
  const cash = isCashEvent(item)
  return (
    <div
      className="rounded-xl p-3 flex flex-col gap-2"
      style={{ background: 'var(--color-surface-offset)', border: '1px solid var(--color-divider)' }}
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <span className="font-bold text-sm" style={cellText}>{item.ticker}</span>
          <span
            className="px-1.5 py-0.5 rounded text-[9px] font-medium"
            style={{ background: 'var(--color-surface-dynamic)', color: 'var(--color-text-muted)' }}
          >
            {ASSET_TYPE_LABELS[item.asset_type] ?? item.asset_type}
          </span>
        </div>
        <StatusBadge status={item.status} />
      </div>

      <div className="flex items-center gap-2">
        <EventKindBadge item={item} />
        <span className="text-[10px]" style={cellFaint}>{typeLabel}</span>
      </div>

      <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-xs">
        <div>
          <div className="text-[10px]" style={cellFaint}>Data Pgto</div>
          <div className="tabular-nums" style={cellMuted}>{fmt(item.payment_date)}</div>
        </div>
        <div>
          <div className="text-[10px]" style={cellFaint}>Data Com</div>
          <div className="tabular-nums" style={cellMuted}>{fmt(item.record_date)}</div>
        </div>
        <div>
          <div className="text-[10px]" style={cellFaint}>Data Ex</div>
          <div className="tabular-nums" style={cellMuted}>{fmt(item.ex_date)}</div>
        </div>
        <div>
          <div className="text-[10px]" style={cellFaint}>{cash ? 'Valor unit.' : 'Fator'}</div>
          <div className="tabular-nums" style={cellText}>{cash ? fmtMaybeMoney(item.value_per_unit) : (item.factor ?? item.complete_factor ?? '—')}</div>
        </div>
        <div>
          <div className="text-[10px]" style={cellFaint}>Quantidade</div>
          <div className="tabular-nums" style={cellText}>{formatQuantity(item.quantity)}</div>
        </div>
        <div>
          <div className="text-[10px]" style={cellFaint}>{cash ? 'Líquido' : 'Total financeiro'}</div>
          <div className="font-semibold tabular-nums" style={{ color: cash ? 'var(--color-success)' : 'var(--color-text-faint)' }}>
            {cash ? formatBRL(item.net_value) : 'Não soma'}
          </div>
        </div>
      </div>
    </div>
  )
}

export default function MeusProventosTable({ data }: { data: ProventoItem[] }) {
  if (!data.length) return <p className="text-xs p-4" style={cellMuted}>Sem eventos no período.</p>

  return (
    <>
      <div className="flex flex-col gap-2 md:hidden">
        {data.map(item => <ProventoCard key={item.id} item={item} />)}
      </div>

      <div className="hidden md:block overflow-x-auto">
        <table className="w-full min-w-[1160px] text-xs">
          <thead>
            <tr style={{ borderBottom: '1px solid var(--color-divider)' }}>
              {['Ativo','Tipo de Ativo','Status','Tipo','Natureza','Data Com','Data Ex','Data Pgto','Qtd elegível','Valor/Unit.','Valor Total','Líquido'].map(h => (
                <th key={h} className="px-3 py-2 font-medium text-left first:pl-4 last:pr-4" style={cellMuted}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.map(item => {
              const cash = isCashEvent(item)
              return (
                <tr
                  key={item.id}
                  className="transition-colors hover:bg-[var(--color-surface-offset)]"
                  style={{ borderBottom: '1px solid var(--color-divider)' }}
                  title={item.remarks || undefined}
                >
                  <td className="px-3 py-2 pl-4"><span className="font-semibold" style={cellText}>{item.ticker}</span></td>
                  <td className="px-3 py-2">
                    <span
                      className="px-1.5 py-0.5 rounded text-[9px] font-medium"
                      style={{ background: 'var(--color-surface-dynamic)', color: 'var(--color-text-muted)' }}
                    >
                      {ASSET_TYPE_LABELS[item.asset_type] ?? item.asset_type}
                    </span>
                  </td>
                  <td className="px-3 py-2"><StatusBadge status={item.status} /></td>
                  <td className="px-3 py-2" style={cellMuted}>{DIVIDEND_TYPE_LABELS[item.dividend_type] ?? item.dividend_type}</td>
                  <td className="px-3 py-2"><EventKindBadge item={item} /></td>
                  <td className="px-3 py-2 tabular-nums" style={cellMuted}>{fmt(item.record_date)}</td>
                  <td className="px-3 py-2 tabular-nums" style={cellMuted}>{fmt(item.ex_date)}</td>
                  <td className="px-3 py-2 tabular-nums" style={cellMuted}>{fmt(item.payment_date)}</td>
                  <td className="px-3 py-2 tabular-nums text-right" style={cellText}>{formatQuantity(item.quantity)}</td>
                  <td className="px-3 py-2 tabular-nums text-right" style={cellText}>
                    {cash ? fmtMaybeMoney(item.value_per_unit) : (item.factor ?? item.complete_factor ?? '—')}
                  </td>
                  <td className="px-3 py-2 tabular-nums text-right font-medium" style={cash ? cellText : cellFaint}>
                    {cash ? formatBRL(item.total_value) : 'Não soma'}
                  </td>
                  <td className="px-3 py-2 pr-4 tabular-nums text-right font-semibold" style={{ color: cash ? 'var(--color-success)' : 'var(--color-text-faint)' }}>
                    {cash ? formatBRL(item.net_value) : 'Não soma'}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </>
  )
}
