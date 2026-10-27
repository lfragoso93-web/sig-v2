import { useState, useCallback, useEffect, useMemo } from 'react'
import {
  FileText,
  Download,
  Wallet,
  TrendingUp,
  Landmark,
  Banknote,
  ChevronDown,
  ChevronRight,
  BadgePercent,
  Calendar,
} from 'lucide-react'
import { useAppStore } from '@/store/appStore'
import {
  useIRPFAnos,
  useIRPFCanonicalAnnualAssessment,
  useIRPFCanonicalAssetsAssessment,
  useIRPFCanonicalCapitalGainsAssessment,
  useIRPFCanonicalIncomeAssessment,
} from '@/hooks/useIRPF'
import { formatBRL } from '@/utils/format'
import { reconcileIRPFYear } from '@/utils/irpfYearSelection'
import KpiCard from '@/components/ui/KpiCard'
import SkeletonCard from '@/components/ui/SkeletonCard'
import EmptyState from '@/components/ui/EmptyState'
import api from '@/services/api'
import type {
  BemDireito,
  GanhoCapitalMensal,
  RendimentoIsento,
  JCPItem,
  IRPFCanonicalMonthlyAssessment,
  VendaMensal,
} from '@/types/irpf'
import clsx from 'clsx'

const MESES = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez']

function mesLabel(mes: string) {
  const [, m] = mes.split('-')
  return MESES[parseInt(m, 10) - 1] ?? mes
}

function signCls(v: number) {
  if (v > 0) return 'text-[var(--color-success)]'
  if (v < 0) return 'text-[var(--color-error)]'
  return 'text-[var(--color-text-muted)]'
}

function Badge({ label, color }: { label: string; color: string }) {
  return (
    <span
      className="px-2 py-0.5 rounded-full text-xs font-medium border"
      style={{ background: `${color}18`, color, borderColor: `${color}38` }}
    >
      {label}
    </span>
  )
}

function IRPFSectionCard({
  icon: Icon,
  title,
  subtitle,
  badge,
  children,
  noBodyPadding = false,
}: {
  icon: React.ElementType
  title: string
  subtitle?: string
  badge?: React.ReactNode
  children: React.ReactNode
  noBodyPadding?: boolean
}) {
  return (
    <section className="card settings-card">
      <div className="settings-card-header">
        <div className="flex items-center gap-3 min-w-0">
          <span className="settings-card-icon" aria-hidden="true">
            <Icon size={15} strokeWidth={2} />
          </span>
          <div className="min-w-0">
            <h2 className="text-sm font-semibold leading-tight" style={{ color: 'var(--color-text)' }}>
              {title}
            </h2>
            {subtitle && (
              <p className="text-xs mt-0.5 leading-snug" style={{ color: 'var(--color-text-muted)' }}>
                {subtitle}
              </p>
            )}
          </div>
        </div>
        {badge && <div className="shrink-0">{badge}</div>}
      </div>
      <div className={noBodyPadding ? 'p-0' : 'settings-card-body'}>
        {children}
      </div>
    </section>
  )
}

function BensDireitosTable({ data }: { data: BemDireito[] }) {
  if (!data.length) return <Empty label="Nenhum bem ou direito encontrado." />
  return (
    <div className="table-responsive">
      <table className="table-dense">
        <thead>
          <tr>
            {['Código', 'Ativo', 'Tipo', 'Qtd', 'Custo Médio', 'Custo Total', 'Moeda'].map((h, idx) => (
              <th
                key={h}
                style={{
                  textAlign: idx >= 3 && idx <= 5 ? 'right' : idx === 6 ? 'center' : 'left',
                }}
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((b, i) => (
            <tr
              key={b.ticker}
              style={{
                background: i % 2 === 0 ? 'transparent' : 'oklch(from var(--color-text) l c h / 0.015)',
              }}
            >
              <td className="tabular-nums text-xs" style={{ color: 'var(--color-text-muted)', width: '5.5rem' }}>{b.codigo_irpf}</td>
              <td>
                <div className="font-medium" style={{ color: 'var(--color-text)' }}>{b.nome || b.ticker}</div>
                {b.nome && b.nome !== b.ticker && (
                  <div className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                    {b.ticker}
                  </div>
                )}
              </td>
              <td className="text-xs" style={{ color: 'var(--color-text-muted)' }}>{b.asset_type}</td>
              <td className="tabular-nums" style={{ textAlign: 'right' }}>{b.quantidade.toLocaleString('pt-BR', { maximumFractionDigits: 4 })}</td>
              <td className="tabular-nums" style={{ textAlign: 'right' }}>{formatBRL(b.custo_medio)}</td>
              <td className="tabular-nums font-semibold" style={{ textAlign: 'right' }}>{formatBRL(b.custo_total)}</td>
              <td className="text-xs" style={{ color: 'var(--color-text-muted)', textAlign: 'center', width: '5rem' }}>{b.moeda}</td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr style={{ borderTop: '2px solid var(--color-divider)', background: 'oklch(from var(--color-text) l c h / 0.02)' }}>
            <td colSpan={5} className="text-xs font-semibold" style={{ color: 'var(--color-text-muted)', padding: '0.75rem 1rem' }}>Total em Custódia</td>
            <td className="tabular-nums font-bold" style={{ color: 'var(--color-primary)', textAlign: 'right', padding: '0.75rem 1rem' }}>
              {formatBRL(data.reduce((s, b) => s + b.custo_total, 0))}
            </td>
            <td />
          </tr>
        </tfoot>
      </table>
    </div>
  )
}

function VendasDetalhe({ vendas }: { vendas: VendaMensal[] }) {
  return (
    <div className="overflow-x-auto mt-2 rounded-lg border" style={{ borderColor: 'var(--color-divider)' }}>
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b" style={{ borderColor: 'var(--color-divider)', background: 'var(--color-surface-offset)' }}>
            {['Data', 'Ticker', 'Tipo', 'Qtd', 'Preço Venda', 'Custo Médio', 'Lucro/Prejuízo', 'DT?', 'Isento?'].map(h => (
              <th key={h} className="text-left px-2.5 py-2 font-semibold" style={{ color: 'var(--color-text-muted)' }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {vendas.map((v, i) => (
            <tr
              key={`${v.ticker}-${v.data}-${i}`}
              className="border-b"
              style={{
                borderColor: 'var(--color-divider)',
                background: i % 2 === 0 ? 'transparent' : 'var(--color-surface-offset)',
              }}
            >
              <td className="px-2.5 py-1.5 tabular-nums">{v.data}</td>
              <td className="px-2.5 py-1.5 font-medium">{v.ticker}</td>
              <td className="px-2.5 py-1.5" style={{ color: 'var(--color-text-muted)' }}>{v.asset_type}</td>
              <td className="px-2.5 py-1.5 tabular-nums text-right">{v.quantidade.toLocaleString('pt-BR', { maximumFractionDigits: 4 })}</td>
              <td className="px-2.5 py-1.5 tabular-nums text-right">{formatBRL(v.preco_venda)}</td>
              <td className="px-2.5 py-1.5 tabular-nums text-right">{formatBRL(v.custo_aquisicao)}</td>
              <td className={clsx('px-2.5 py-1.5 tabular-nums text-right font-semibold', signCls(v.lucro_bruto))}>
                {formatBRL(v.lucro_bruto)}
              </td>
              <td className="px-2.5 py-1.5 text-center">{v.is_day_trade ? <Badge label="DT" color="var(--color-error)" /> : '—'}</td>
              <td className="px-2.5 py-1.5 text-center">{v.is_isento ? <Badge label="Isento" color="var(--color-success)" /> : '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function GanhosCapitalTable({ data }: { data: GanhoCapitalMensal[] }) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set())

  const toggle = (mes: string) =>
    setExpanded(prev => {
      const next = new Set(prev)
      if (next.has(mes)) {
        next.delete(mes)
      } else {
        next.add(mes)
      }
      return next
    })

  if (!data.length) return <Empty label="Nenhuma venda no ano." />

  return (
    <div className="flex flex-col gap-2.5">
      {data.map(gm => {
        const isOpen = expanded.has(gm.mes)
        const temIR = gm.ir_a_recolher > 0
        return (
          <div
            key={gm.mes}
            className="rounded-lg overflow-hidden"
            style={{
              border: '1px solid oklch(from var(--color-text) l c h / 0.08)',
              background: 'var(--color-surface)',
            }}
          >
            <button
              type="button"
              onClick={() => toggle(gm.mes)}
              className="w-full flex items-center flex-wrap gap-3 px-4 py-3 text-left transition-colors"
              style={{ background: 'var(--color-surface-offset)' }}
            >
              {isOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
              <span className="font-semibold text-sm w-10">{mesLabel(gm.mes)}</span>
              <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>Vendas: {formatBRL(gm.total_vendas)}</span>
              <span className={clsx('text-xs ml-1 font-medium', signCls(gm.lucro_bruto))}>Lucro: {formatBRL(gm.lucro_bruto)}</span>
              <span className="text-xs ml-1" style={{ color: 'var(--color-text-muted)' }}>Base: {formatBRL(gm.base_calculo)}</span>
              {gm.isencao_aplicada > 0 && <Badge label={`Isenção ${formatBRL(gm.isencao_aplicada)}`} color="var(--color-success)" />}
              {gm.lucro_day_trade !== 0 && <Badge label={`DT ${formatBRL(gm.lucro_day_trade)}`} color="var(--color-error)" />}
              <span className="ml-auto">
                {temIR ? (
                  <Badge label={`DARF ${formatBRL(gm.ir_a_recolher)}`} color="var(--color-warning, #f59e0b)" />
                ) : (
                  <span className="text-xs" style={{ color: 'var(--color-text-faint)' }}>Sem IR</span>
                )}
              </span>
            </button>

            {isOpen && (
              <div className="p-4 flex flex-col gap-3">
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  {[
                    { label: 'IR Swing Trade', value: gm.ir_devido_swing },
                    { label: 'IR Day Trade', value: gm.ir_devido_day_trade },
                    { label: 'IR Retido Fonte', value: gm.ir_retido_fonte },
                    { label: 'IR a Recolher', value: gm.ir_a_recolher, highlight: true },
                  ].map(({ label, value, highlight }) => (
                    <div
                      key={label}
                      className="rounded-lg p-3"
                      style={{
                        background: 'var(--color-surface-offset)',
                        border: '1px solid oklch(from var(--color-text) l c h / 0.07)',
                      }}
                    >
                      <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>{label}</p>
                      <p className={clsx('text-sm font-semibold tabular-nums mt-0.5', highlight ? signCls(value) : '')}>{formatBRL(value)}</p>
                    </div>
                  ))}
                </div>
                <VendasDetalhe vendas={gm.vendas} />
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

function DividendosOnlyTable({ dividendos }: { dividendos: RendimentoIsento[] }) {
  if (dividendos.length === 0) {
    return <Empty label="Nenhum dividendo recebido no ano." />
  }
  return (
    <div className="table-responsive">
      <table className="table-dense">
        <thead>
          <tr>
            {['Ticker', 'Tipo', 'Total Recebido', 'Nº Pagamentos'].map((h, idx) => (
              <th
                key={h}
                style={{ textAlign: idx >= 2 ? 'right' : 'left' }}
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {dividendos.map((d, i) => (
            <tr
              key={d.ticker}
              style={{
                background: i % 2 === 0 ? 'transparent' : 'oklch(from var(--color-text) l c h / 0.015)',
              }}
            >
              <td className="font-medium">{d.ticker}</td>
              <td className="text-xs" style={{ color: 'var(--color-text-muted)' }}>{d.asset_type}</td>
              <td className="tabular-nums font-semibold" style={{ color: 'var(--color-success)', textAlign: 'right' }}>{formatBRL(d.total_recebido)}</td>
              <td className="tabular-nums" style={{ textAlign: 'right' }}>{d.quantidade_pgtos}</td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr style={{ borderTop: '2px solid var(--color-divider)', background: 'oklch(from var(--color-text) l c h / 0.02)' }}>
            <td colSpan={2} className="text-xs font-semibold" style={{ color: 'var(--color-text-muted)', padding: '0.75rem 1rem' }}>Total Isento</td>
            <td className="tabular-nums font-bold" style={{ color: 'var(--color-success)', textAlign: 'right', padding: '0.75rem 1rem' }}>
              {formatBRL(dividendos.reduce((s, d) => s + d.total_recebido, 0))}
            </td>
            <td />
          </tr>
        </tfoot>
      </table>
    </div>
  )
}

function JCPOnlyTable({ jcp }: { jcp: JCPItem[] }) {
  if (jcp.length === 0) {
    return <Empty label="Nenhum JCP recebido no ano." />
  }
  return (
    <div className="table-responsive">
      <table className="table-dense">
        <thead>
          <tr>
            {['Ticker', 'Total Bruto', 'IR Retido (15%)', 'Total Líquido'].map((h, idx) => (
              <th
                key={h}
                style={{ textAlign: idx >= 1 ? 'right' : 'left' }}
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {jcp.map((j, i) => (
            <tr
              key={j.ticker}
              style={{
                background: i % 2 === 0 ? 'transparent' : 'oklch(from var(--color-text) l c h / 0.015)',
              }}
            >
              <td className="font-medium">{j.ticker}</td>
              <td className="tabular-nums" style={{ textAlign: 'right' }}>{formatBRL(j.total_bruto)}</td>
              <td className="tabular-nums" style={{ color: 'var(--color-error)', textAlign: 'right' }}>-{formatBRL(j.ir_retido)}</td>
              <td className="tabular-nums font-semibold" style={{ textAlign: 'right' }}>{formatBRL(j.total_liquido)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function RendimentosTable({
  dividendos,
  jcp,
  mode = 'both',
}: {
  dividendos: RendimentoIsento[]
  jcp: JCPItem[]
  mode?: 'both' | 'dividendos' | 'jcp'
}) {
  return (
    <div className="settings-stack">
      {(mode === 'both' || mode === 'dividendos') && (
        <IRPFSectionCard
          icon={Banknote}
          title="Dividendos Isentos"
          subtitle="Proventos isentos de Imposto de Renda creditados no ano-base"
          badge={
            dividendos.length > 0 ? (
              <span className="badge badge-green tabular-nums">
                {formatBRL(dividendos.reduce((s, d) => s + d.total_recebido, 0))}
              </span>
            ) : undefined
          }
          noBodyPadding={dividendos.length > 0}
        >
          <DividendosOnlyTable dividendos={dividendos} />
        </IRPFSectionCard>
      )}

      {(mode === 'both' || mode === 'jcp') && (
        <IRPFSectionCard
          icon={BadgePercent}
          title="JCP — Juros sobre Capital Próprio"
          subtitle="Rendimentos sujeitos à tributação exclusiva na fonte (alíquota de 15%)"
          badge={
            jcp.length > 0 ? (
              <span className="badge badge-primary tabular-nums">
                {formatBRL(jcp.reduce((s, j) => s + j.total_liquido, 0))}
              </span>
            ) : undefined
          }
          noBodyPadding={jcp.length > 0}
        >
          <JCPOnlyTable jcp={jcp} />
        </IRPFSectionCard>
      )}
    </div>
  )
}

function DARFMonthlyTable({
  data,
  paidMonths,
  onTogglePaid,
}: {
  data: IRPFCanonicalMonthlyAssessment[]
  paidMonths: Set<string>
  onTogglePaid: (month: string) => void
}) {
  if (!data.length) return <Empty label="Nenhuma apuração mensal encontrada." />

  return (
    <div className="table-responsive">
      <table className="table-dense">
        <thead>
          <tr>
            {['Mês', 'IR Swing', 'IR Day Trade', 'IRRF', 'Imposto Líquido', 'DARF do Mês', 'Saldo Acumulado', 'Pagamento'].map((h, idx) => (
              <th
                key={h}
                style={{ textAlign: idx >= 1 ? 'right' : 'left' }}
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((month, i) => {
            const swingTax = Number(month.swing_gross_tax_due_brl)
            const dayTradeTax = Number(month.day_trade_gross_tax_due_brl)
            const withholding = Number(month.swing_withholding_brl) + Number(month.day_trade_withholding_brl)
            const netTax = Number(month.total_net_tax_due_brl)
            const paymentDue = Number(month.payment_due_brl)
            const accumulated = Number(month.closing_accumulated_tax_brl)
            const isPaid = paidMonths.has(month.competence_month)

            return (
              <tr
                key={month.competence_month}
                style={{
                  background: i % 2 === 0 ? 'transparent' : 'oklch(from var(--color-text) l c h / 0.015)',
                }}
              >
                <td className="font-medium">{mesLabel(month.competence_month)}</td>
                <td className="tabular-nums" style={{ textAlign: 'right' }}>{formatBRL(swingTax)}</td>
                <td className="tabular-nums" style={{ textAlign: 'right' }}>{formatBRL(dayTradeTax)}</td>
                <td className="tabular-nums" style={{ color: withholding > 0 ? 'var(--color-success)' : 'var(--color-text-muted)', textAlign: 'right' }}>
                  {formatBRL(withholding)}
                </td>
                <td className="tabular-nums" style={{ textAlign: 'right' }}>{formatBRL(netTax)}</td>
                <td className={clsx('tabular-nums font-semibold', paymentDue > 0 ? 'text-[var(--color-error)]' : 'text-[var(--color-text-muted)]')} style={{ textAlign: 'right' }}>
                  {formatBRL(paymentDue)}
                </td>
                <td className="tabular-nums" style={{ color: accumulated > 0 ? 'var(--color-warning, #f59e0b)' : 'var(--color-text-muted)', textAlign: 'right' }}>
                  {formatBRL(accumulated)}
                </td>
                <td style={{ textAlign: 'right' }}>
                  {paymentDue > 0 ? (
                    <button
                      type="button"
                      onClick={() => onTogglePaid(month.competence_month)}
                      className="rounded-md border px-2.5 py-1 text-xs font-semibold transition-colors"
                      style={{
                        background: isPaid ? 'rgba(34, 197, 94, 0.12)' : 'var(--color-surface-dynamic)',
                        borderColor: isPaid ? 'rgba(34, 197, 94, 0.45)' : 'var(--color-border)',
                        color: isPaid ? 'var(--color-success)' : 'var(--color-text)',
                      }}
                    >
                      {isPaid ? 'Pago' : 'Marcar pago'}
                    </button>
                  ) : (
                    <span className="text-xs" style={{ color: 'var(--color-text-faint)' }}>-</span>
                  )}
                </td>
              </tr>
            )
          })}
        </tbody>
        <tfoot>
          <tr style={{ borderTop: '2px solid var(--color-divider)', background: 'oklch(from var(--color-text) l c h / 0.02)' }}>
            <td className="text-xs font-semibold" style={{ color: 'var(--color-text-muted)', padding: '0.75rem 1rem' }}>Total no Ano</td>
            <td colSpan={4} />
            <td className="tabular-nums font-bold" style={{ color: 'var(--color-error)', textAlign: 'right', padding: '0.75rem 1rem' }}>
              {formatBRL(data.reduce((sum, month) => sum + Number(month.payment_due_brl), 0))}
            </td>
            <td colSpan={2} />
          </tr>
        </tfoot>
      </table>
    </div>
  )
}

function Empty({ label }: { label: string }) {
  return (
    <div className="py-6 text-center text-xs" style={{ color: 'var(--color-text-muted)' }}>{label}</div>
  )
}

function ErrorNotice({ label }: { label: string }) {
  return (
    <div
      className="rounded-lg border px-3.5 py-2.5 text-xs"
      style={{
        background: 'rgba(239, 68, 68, 0.08)',
        borderColor: 'rgba(239, 68, 68, 0.35)',
        color: 'var(--color-error)',
      }}
    >
      {label}
    </div>
  )
}

const TABS = [
  { key: 'resumo',       label: 'Resumo',            icon: FileText },
  { key: 'bens',         label: 'Bens e Direitos',   icon: Wallet },
  { key: 'ganhos',       label: 'Ganhos de Capital', icon: TrendingUp },
  { key: 'darf',         label: 'DARF Mensal',       icon: Landmark },
  { key: 'rendimentos',  label: 'Rendimentos',       icon: Banknote },
  { key: 'jcp',          label: 'JCP',               icon: BadgePercent },
] as const

type Tab = typeof TABS[number]['key']

export default function IRPFPage() {
  const portfolioId = useAppStore(s => s.selectedPortfolioId)
  const currentYear = new Date().getFullYear()
  const fallbackYear = currentYear - 1

  const [selectedYear, setSelectedYear] = useState<number>(fallbackYear)
  const [activeTab, setActiveTab] = useState<Tab>('resumo')
  const [downloading, setDownloading] = useState(false)
  const [downloadingCSV, setDownloadingCSV] = useState(false)
  const [paidDARFMonths, setPaidDARFMonths] = useState<Set<string>>(new Set())

  const paidDARFStorageKey = useMemo(
    () => portfolioId && selectedYear ? `sgi.irpf.darf.paid.${portfolioId}.${selectedYear}` : null,
    [portfolioId, selectedYear],
  )

  const { data: anos, isLoading: loadingAnos } = useIRPFAnos(portfolioId)

  useEffect(() => {
    setSelectedYear(current => reconcileIRPFYear(current, anos, fallbackYear))
    setActiveTab('resumo')
  }, [portfolioId, anos, fallbackYear])

  useEffect(() => {
    if (!paidDARFStorageKey) {
      setPaidDARFMonths(new Set())
      return
    }

    try {
      const stored = window.localStorage.getItem(paidDARFStorageKey)
      const months = stored ? JSON.parse(stored) : []
      setPaidDARFMonths(new Set(Array.isArray(months) ? months : []))
    } catch {
      setPaidDARFMonths(new Set())
    }
  }, [paidDARFStorageKey])

  const togglePaidDARFMonth = useCallback((month: string) => {
    if (!paidDARFStorageKey) return

    setPaidDARFMonths(previous => {
      const next = new Set(previous)
      if (next.has(month)) {
        next.delete(month)
      } else {
        next.add(month)
      }
      window.localStorage.setItem(paidDARFStorageKey, JSON.stringify([...next].sort()))
      return next
    })
  }, [paidDARFStorageKey])

  const {
    data: canonicalAssessment,
    isLoading: loadingCanonicalAssessment,
    isError: isCanonicalAssessmentError,
  } = useIRPFCanonicalAnnualAssessment(portfolioId, selectedYear)
  const {
    data: canonicalAssets,
    isLoading: loadingCanonicalAssets,
    isError: isCanonicalAssetsError,
  } = useIRPFCanonicalAssetsAssessment(portfolioId, selectedYear)
  const {
    data: canonicalCapitalGains,
    isLoading: loadingCanonicalCapitalGains,
    isError: isCanonicalCapitalGainsError,
  } = useIRPFCanonicalCapitalGainsAssessment(portfolioId, selectedYear)
  const {
    data: canonicalIncome,
    isLoading: loadingCanonicalIncome,
    isError: isCanonicalIncomeError,
  } = useIRPFCanonicalIncomeAssessment(portfolioId, selectedYear)

  const handleDownloadPDF = useCallback(async () => {
    if (!portfolioId || !selectedYear) return
    setDownloading(true)
    try {
      const res = await api.get(
        `/portfolios/${portfolioId}/irpf/${selectedYear}/pdf`,
        { responseType: 'blob' },
      )
      const url = URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }))
      const a = document.createElement('a')
      a.href = url
      a.download = `irpf_${selectedYear}_carteira${portfolioId}.pdf`
      a.click()
      URL.revokeObjectURL(url)
    } finally {
      setDownloading(false)
    }
  }, [portfolioId, selectedYear])

  const handleDownloadCSV = useCallback(async () => {
    if (!portfolioId || !selectedYear) return
    setDownloadingCSV(true)
    try {
      const res = await api.get(
        `/portfolios/${portfolioId}/irpf/${selectedYear}/csv`,
        { responseType: 'blob' },
      )
      const url = URL.createObjectURL(new Blob([res.data], { type: 'text/csv' }))
      const a = document.createElement('a')
      a.href = url
      a.download = `irpf_${selectedYear}_carteira${portfolioId}.csv`
      a.click()
      URL.revokeObjectURL(url)
    } finally {
      setDownloadingCSV(false)
    }
  }, [portfolioId, selectedYear])

  if (!portfolioId) {
    return (
      <div className="p-6">
        <EmptyState
          icon={Landmark}
          title="Nenhuma carteira selecionada"
          description="Selecione uma carteira no menu superior para visualizar o IRPF."
        />
      </div>
    )
  }

  const canonicalGrossTax = Number(canonicalAssessment?.total_gross_tax_due_brl ?? 0)
  const canonicalWithholding = Number(canonicalAssessment?.total_withholding_brl ?? 0)
  const canonicalPaymentDue = Number(canonicalAssessment?.total_payment_due_brl ?? 0)
  const canonicalDayTradeLoss = Number(
    canonicalAssessment?.closing_day_trade_loss_carryforward_brl ?? 0,
  )
  const bensDireitos = canonicalAssets?.items ?? []
  const ganhosCapital = canonicalCapitalGains?.months ?? []
  const darfMonthly = canonicalAssessment?.monthly ?? []
  const dividendos = canonicalIncome?.dividends ?? []
  const jcp = canonicalIncome?.jcp ?? []

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1 className="page-title">IRPF</h1>
          <p className="page-subtitle">Relatório fiscal consolidado de investimentos para declaração anual</p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {/* Caixa de seleção de Ano-base moderna */}
          <div
            className="inline-flex items-center rounded-lg px-2.5 gap-2"
            style={{
              height: '2.15rem',
              background: 'var(--color-surface-2)',
              border: '1px solid oklch(from var(--color-text) l c h / 0.12)',
              boxShadow: 'var(--shadow-xs)',
            }}
          >
            <Calendar size={13} style={{ color: 'var(--color-primary)', flexShrink: 0 }} />
            <span className="text-xs font-medium" style={{ color: 'var(--color-text-muted)' }}>
              Ano-base
            </span>
            <div className="relative flex items-center">
              <select
                aria-label="Selecionar ano-base do IRPF"
                value={selectedYear}
                onChange={e => setSelectedYear(Number(e.target.value))}
                className="appearance-none pl-1.5 pr-5 py-0.5 text-xs font-semibold tabular-nums cursor-pointer bg-transparent focus:outline-none"
                style={{ color: 'var(--color-text)', backgroundColor: 'var(--color-surface, #1e293b)' }}
                disabled={loadingAnos}
              >
                {anos && anos.length > 0
                  ? anos.map(y => (
                      <option
                        key={y}
                        value={y}
                        style={{
                          backgroundColor: 'var(--color-surface, #1e293b)',
                          color: 'var(--color-text, #f8fafc)',
                        }}
                      >
                        {y}
                      </option>
                    ))
                  : (
                      <option
                        value={fallbackYear}
                        style={{
                          backgroundColor: 'var(--color-surface, #1e293b)',
                          color: 'var(--color-text, #f8fafc)',
                        }}
                      >
                        {fallbackYear}
                      </option>
                    )}
              </select>
              <ChevronDown
                size={12}
                className="absolute right-0.5 top-1/2 -translate-y-1/2 pointer-events-none"
                style={{ color: 'var(--color-text-muted)' }}
              />
            </div>
          </div>

          <button
            type="button"
            onClick={handleDownloadPDF}
            disabled={downloading}
            className="btn btn-primary"
          >
            <Download size={13} />
            {downloading ? 'Gerando...' : 'Exportar PDF'}
          </button>

          <button
            type="button"
            onClick={handleDownloadCSV}
            disabled={downloadingCSV}
            className="btn btn-secondary"
          >
            <Download size={13} />
            {downloadingCSV ? 'Gerando...' : 'Exportar CSV'}
          </button>
        </div>
      </div>

      {/* KPIs Fiscais Anuais */}
      <div className="kpi-grid">
        {loadingCanonicalAssessment ? (
          [...Array(4)].map((_, i) => <SkeletonCard key={i} />)
        ) : isCanonicalAssessmentError ? (
          <div className="col-span-full">
            <ErrorNotice label="Não foi possível carregar a apuração anual de IRPF." />
          </div>
        ) : canonicalAssessment ? (
          <>
            <KpiCard
              label="Imposto Bruto Canônico"
              value={formatBRL(canonicalGrossTax)}
              subLabel={`Ano-base ${selectedYear}`}
            />
            <KpiCard
              label="IRRF Compensado"
              value={formatBRL(canonicalWithholding)}
              subLabel="Swing + Day Trade"
            />
            <KpiCard
              label="DARF Liberada"
              value={formatBRL(canonicalPaymentDue)}
              valueColor={canonicalPaymentDue > 0 ? 'text-[var(--color-error)]' : 'text-[var(--color-success)]'}
              subLabel="Após IRRF e mínimo de R$ 10"
            />
            <KpiCard
              label="Prejuízo Day Trade"
              value={formatBRL(canonicalDayTradeLoss)}
              valueColor={canonicalDayTradeLoss > 0 ? 'text-[var(--color-error)]' : 'text-[var(--color-text-muted)]'}
              subLabel="Saldo canônico a compensar"
            />
          </>
        ) : null}
      </div>

      {/* Topbar de Navegação das Seções do IRPF */}
      <div
        role="tablist"
        aria-label="Seções do relatório de IRPF"
        className="settings-tabs w-full sm:w-auto"
        style={{
          background: 'var(--color-surface)',
          border: '1px solid oklch(from var(--color-text) l c h / 0.08)',
          boxShadow: 'var(--shadow-xs)',
        }}
      >
        {TABS.map(({ key, label, icon: Icon }) => {
          const isActive = activeTab === key
          return (
            <button
              key={key}
              type="button"
              role="tab"
              aria-selected={isActive}
              onClick={() => setActiveTab(key)}
              className="settings-tab"
              style={{
                background: isActive ? 'oklch(from var(--color-primary) l c h / 0.12)' : 'transparent',
                color: isActive ? 'var(--color-primary)' : 'var(--color-text-muted)',
                border: isActive ? '1px solid oklch(from var(--color-primary) l c h / 0.22)' : '1px solid transparent',
                fontWeight: isActive ? 600 : 500,
              }}
            >
              <Icon size={13} />
              <span>{label}</span>
            </button>
          )
        })}
      </div>

      {/* Conteúdo Carregado Abaixo em Cards Independentes */}
      <div className="settings-stack">
        {activeTab === 'resumo' && (
          <>
            <IRPFSectionCard
              icon={Wallet}
              title="Bens e Direitos"
              subtitle={`Posições custodiadas no encerramento do ano-base ${selectedYear} pelo custo de aquisição`}
              badge={
                bensDireitos.length > 0 ? (
                  <span className="badge badge-primary tabular-nums">
                    {bensDireitos.length} {bensDireitos.length === 1 ? 'item' : 'itens'}
                  </span>
                ) : undefined
              }
              noBodyPadding={bensDireitos.length > 0 && !loadingCanonicalAssets && !isCanonicalAssetsError}
            >
              {loadingCanonicalAssets ? (
                <SkeletonCard />
              ) : isCanonicalAssetsError ? (
                <ErrorNotice label="Não foi possível carregar Bens e Direitos." />
              ) : (
                <BensDireitosTable data={bensDireitos} />
              )}
            </IRPFSectionCard>

            {loadingCanonicalIncome ? (
              <SkeletonCard />
            ) : isCanonicalIncomeError ? (
              <ErrorNotice label="Não foi possível carregar Rendimentos." />
            ) : (
              <RendimentosTable dividendos={dividendos} jcp={jcp} mode="both" />
            )}
          </>
        )}

        {activeTab === 'bens' && (
          <IRPFSectionCard
            icon={Wallet}
            title="Bens e Direitos"
            subtitle={`Relação detalhada de ativos em custódia em 31/12/${selectedYear}`}
            badge={
              bensDireitos.length > 0 ? (
                <span className="badge badge-primary tabular-nums">
                  {bensDireitos.length} {bensDireitos.length === 1 ? 'ativo' : 'ativos'}
                </span>
              ) : undefined
            }
            noBodyPadding={bensDireitos.length > 0 && !isCanonicalAssetsError}
          >
            {isCanonicalAssetsError
              ? <ErrorNotice label="Não foi possível carregar Bens e Direitos." />
              : <BensDireitosTable data={bensDireitos} />}
          </IRPFSectionCard>
        )}

        {activeTab === 'ganhos' && (
          <IRPFSectionCard
            icon={TrendingUp}
            title="Ganhos de Capital"
            subtitle="Apuração mensal de alienações, isenções legais e imposto devido em Swing Trade e Day Trade"
          >
            {loadingCanonicalCapitalGains
              ? <SkeletonCard />
              : isCanonicalCapitalGainsError
                ? <ErrorNotice label="Não foi possível carregar Ganhos de Capital." />
                : <GanhosCapitalTable data={ganhosCapital} />}
          </IRPFSectionCard>
        )}

        {activeTab === 'darf' && (
          <IRPFSectionCard
            icon={Landmark}
            title="DARF Mensal"
            subtitle="Controle de recolhimento mensal após compensação de IRRF e aplicação do limite mínimo de R$ 10,00"
            noBodyPadding={darfMonthly.length > 0 && !loadingCanonicalAssessment && !isCanonicalAssessmentError}
          >
            {loadingCanonicalAssessment
              ? <SkeletonCard />
              : isCanonicalAssessmentError
                ? <ErrorNotice label="Não foi possível carregar DARF mensal." />
                : (
                  <DARFMonthlyTable
                    data={darfMonthly}
                    paidMonths={paidDARFMonths}
                    onTogglePaid={togglePaidDARFMonth}
                  />
                )}
          </IRPFSectionCard>
        )}

        {activeTab === 'rendimentos' && (
          isCanonicalIncomeError
            ? <ErrorNotice label="Não foi possível carregar Rendimentos." />
            : <RendimentosTable dividendos={dividendos} jcp={[]} mode="dividendos" />
        )}

        {activeTab === 'jcp' && (
          isCanonicalIncomeError
            ? <ErrorNotice label="Não foi possível carregar JCP." />
            : <RendimentosTable dividendos={[]} jcp={jcp} mode="jcp" />
        )}
      </div>
    </div>
  )
}
