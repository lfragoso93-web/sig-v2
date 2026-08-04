import { useState, useCallback, useEffect } from 'react'
import {
  FileText,
  Download,
  RefreshCw,
  Wallet,
  TrendingUp,
  Landmark,
  Banknote,
  ChevronDown,
  ChevronRight,
  BadgePercent,
} from 'lucide-react'
import { useAppStore } from '@/store/appStore'
import {
  useIRPFAnos,
  useIRPFCanonicalAnnualAssessment,
  useIRPFReport,
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
      className="px-1.5 py-0.5 rounded text-xs font-medium border"
      style={{ background: `${color}20`, color, borderColor: `${color}40` }}
    >
      {label}
    </span>
  )
}

function BensDireitosTable({ data }: { data: BemDireito[] }) {
  if (!data.length) return <Empty label="Nenhum bem ou direito encontrado." />
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b" style={{ borderColor: 'var(--color-divider)' }}>
            {['Código', 'Ticker', 'Tipo', 'Qtd', 'Custo Médio', 'Custo Total', 'Moeda'].map(h => (
              <th key={h} className="text-left px-3 py-2 text-xs font-semibold" style={{ color: 'var(--color-text-muted)' }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((b, i) => (
            <tr
              key={b.ticker}
              className="border-b transition-colors"
              style={{
                borderColor: 'var(--color-divider)',
                background: i % 2 === 0 ? 'transparent' : 'var(--color-surface-offset)',
              }}
            >
              <td className="px-3 py-2 tabular-nums text-xs" style={{ color: 'var(--color-text-muted)' }}>{b.codigo_irpf}</td>
              <td className="px-3 py-2 font-medium">{b.ticker}</td>
              <td className="px-3 py-2 text-xs" style={{ color: 'var(--color-text-muted)' }}>{b.asset_type}</td>
              <td className="px-3 py-2 tabular-nums text-right">{b.quantidade.toLocaleString('pt-BR', { maximumFractionDigits: 4 })}</td>
              <td className="px-3 py-2 tabular-nums text-right">{formatBRL(b.custo_medio)}</td>
              <td className="px-3 py-2 tabular-nums text-right font-semibold">{formatBRL(b.custo_total)}</td>
              <td className="px-3 py-2 text-xs" style={{ color: 'var(--color-text-muted)' }}>{b.moeda}</td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr style={{ borderTop: '2px solid var(--color-divider)' }}>
            <td colSpan={5} className="px-3 py-2 text-xs font-semibold" style={{ color: 'var(--color-text-muted)' }}>Total</td>
            <td className="px-3 py-2 tabular-nums text-right font-bold" style={{ color: 'var(--color-primary)' }}>
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
    <div className="overflow-x-auto mt-2">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b" style={{ borderColor: 'var(--color-divider)' }}>
            {['Data', 'Ticker', 'Tipo', 'Qtd', 'Preço Venda', 'Custo Médio', 'Lucro/Prejuízo', 'DT?', 'Isento?'].map(h => (
              <th key={h} className="text-left px-2 py-1 font-semibold" style={{ color: 'var(--color-text-muted)' }}>{h}</th>
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
                background: i % 2 === 0 ? 'var(--color-surface-offset)' : 'transparent',
              }}
            >
              <td className="px-2 py-1 tabular-nums">{v.data}</td>
              <td className="px-2 py-1 font-medium">{v.ticker}</td>
              <td className="px-2 py-1" style={{ color: 'var(--color-text-muted)' }}>{v.asset_type}</td>
              <td className="px-2 py-1 tabular-nums text-right">{v.quantidade.toLocaleString('pt-BR', { maximumFractionDigits: 4 })}</td>
              <td className="px-2 py-1 tabular-nums text-right">{formatBRL(v.preco_venda)}</td>
              <td className="px-2 py-1 tabular-nums text-right">{formatBRL(v.custo_aquisicao)}</td>
              <td className={clsx('px-2 py-1 tabular-nums text-right font-semibold', signCls(v.lucro_bruto))}>
                {formatBRL(v.lucro_bruto)}
              </td>
              <td className="px-2 py-1 text-center">{v.is_day_trade ? <Badge label="DT" color="var(--color-error)" /> : '—'}</td>
              <td className="px-2 py-1 text-center">{v.is_isento ? <Badge label="Isento" color="var(--color-success)" /> : '—'}</td>
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
    <div className="flex flex-col gap-2">
      {data.map(gm => {
        const isOpen = expanded.has(gm.mes)
        const temIR = gm.ir_a_recolher > 0
        return (
          <div key={gm.mes} className="rounded-lg overflow-hidden" style={{ border: '1px solid var(--color-divider)' }}>
            <button
              type="button"
              onClick={() => toggle(gm.mes)}
              className="w-full flex items-center gap-3 px-4 py-3 text-left transition-colors"
              style={{ background: 'var(--color-surface-offset)' }}
            >
              {isOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
              <span className="font-semibold text-sm w-10">{mesLabel(gm.mes)}</span>
              <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>Vendas: {formatBRL(gm.total_vendas)}</span>
              <span className={clsx('text-xs ml-2', signCls(gm.lucro_bruto))}>Lucro: {formatBRL(gm.lucro_bruto)}</span>
              <span className="text-xs ml-2" style={{ color: 'var(--color-text-muted)' }}>Base: {formatBRL(gm.base_calculo)}</span>
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
              <div className="px-4 pb-4">
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 py-3">
                  {[
                    { label: 'IR Swing Trade', value: gm.ir_devido_swing },
                    { label: 'IR Day Trade', value: gm.ir_devido_day_trade },
                    { label: 'IR Retido Fonte', value: gm.ir_retido_fonte },
                    { label: 'IR a Recolher', value: gm.ir_a_recolher, highlight: true },
                  ].map(({ label, value, highlight }) => (
                    <div key={label} className="rounded-lg p-3" style={{ background: 'var(--color-surface-dynamic)' }}>
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

function RendimentosTable({
  dividendos,
  jcp,
}: {
  dividendos: RendimentoIsento[]
  jcp: JCPItem[]
}) {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h3 className="text-sm font-semibold mb-2" style={{ color: 'var(--color-text)' }}>Dividendos Isentos</h3>
        {dividendos.length === 0 ? (
          <Empty label="Nenhum dividendo recebido no ano." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b" style={{ borderColor: 'var(--color-divider)' }}>
                  {['Ticker', 'Tipo', 'Total Recebido', 'Nº Pagamentos'].map(h => (
                    <th key={h} className="text-left px-3 py-2 text-xs font-semibold" style={{ color: 'var(--color-text-muted)' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {dividendos.map((d, i) => (
                  <tr
                    key={d.ticker}
                    className="border-b"
                    style={{
                      borderColor: 'var(--color-divider)',
                      background: i % 2 === 0 ? 'transparent' : 'var(--color-surface-offset)',
                    }}
                  >
                    <td className="px-3 py-2 font-medium">{d.ticker}</td>
                    <td className="px-3 py-2 text-xs" style={{ color: 'var(--color-text-muted)' }}>{d.asset_type}</td>
                    <td className="px-3 py-2 tabular-nums text-right font-semibold" style={{ color: 'var(--color-success)' }}>{formatBRL(d.total_recebido)}</td>
                    <td className="px-3 py-2 tabular-nums text-right">{d.quantidade_pgtos}</td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr style={{ borderTop: '2px solid var(--color-divider)' }}>
                  <td colSpan={2} className="px-3 py-2 text-xs font-semibold" style={{ color: 'var(--color-text-muted)' }}>Total</td>
                  <td className="px-3 py-2 tabular-nums text-right font-bold" style={{ color: 'var(--color-success)' }}>
                    {formatBRL(dividendos.reduce((s, d) => s + d.total_recebido, 0))}
                  </td>
                  <td />
                </tr>
              </tfoot>
            </table>
          </div>
        )}
      </div>

      <div>
        <h3 className="text-sm font-semibold mb-2" style={{ color: 'var(--color-text)' }}>JCP — Juros sobre Capital Próprio</h3>
        {jcp.length === 0 ? (
          <Empty label="Nenhum JCP recebido no ano." />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b" style={{ borderColor: 'var(--color-divider)' }}>
                  {['Ticker', 'Total Bruto', 'IR Retido (15%)', 'Total Líquido'].map(h => (
                    <th key={h} className="text-left px-3 py-2 text-xs font-semibold" style={{ color: 'var(--color-text-muted)' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {jcp.map((j, i) => (
                  <tr
                    key={j.ticker}
                    className="border-b"
                    style={{
                      borderColor: 'var(--color-divider)',
                      background: i % 2 === 0 ? 'transparent' : 'var(--color-surface-offset)',
                    }}
                  >
                    <td className="px-3 py-2 font-medium">{j.ticker}</td>
                    <td className="px-3 py-2 tabular-nums text-right">{formatBRL(j.total_bruto)}</td>
                    <td className="px-3 py-2 tabular-nums text-right" style={{ color: 'var(--color-error)' }}>-{formatBRL(j.ir_retido)}</td>
                    <td className="px-3 py-2 tabular-nums text-right font-semibold">{formatBRL(j.total_liquido)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

function Empty({ label }: { label: string }) {
  return (
    <div className="py-8 text-center text-sm" style={{ color: 'var(--color-text-muted)' }}>{label}</div>
  )
}

const TABS = [
  { key: 'resumo',       label: 'Resumo',          icon: FileText },
  { key: 'bens',         label: 'Bens e Direitos', icon: Wallet },
  { key: 'ganhos',       label: 'Ganhos de Capital', icon: TrendingUp },
  { key: 'rendimentos',  label: 'Rendimentos',     icon: Banknote },
  { key: 'jcp',          label: 'JCP',             icon: BadgePercent },
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
  const [refreshKey, setRefreshKey] = useState(false)

  const { data: anos, isLoading: loadingAnos } = useIRPFAnos(portfolioId)

  useEffect(() => {
    setSelectedYear(current => reconcileIRPFYear(current, anos, fallbackYear))
    setActiveTab('resumo')
    setRefreshKey(false)
  }, [portfolioId, anos, fallbackYear])

  const { data: report, isLoading: loadingReport } = useIRPFReport(portfolioId, selectedYear, refreshKey)
  const {
    data: canonicalAssessment,
    isLoading: loadingCanonicalAssessment,
  } = useIRPFCanonicalAnnualAssessment(portfolioId, selectedYear)

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

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1 className="page-title">IRPF</h1>
          <p className="page-subtitle">Relatório fiscal de investimentos para declaração do Imposto de Renda</p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <div className="relative">
            <select
              value={selectedYear}
              onChange={e => setSelectedYear(Number(e.target.value))}
              className="appearance-none pl-3 pr-8 py-2 rounded-lg text-sm font-medium cursor-pointer"
              style={{
                background: 'var(--color-surface-offset)',
                border: '1px solid var(--color-border)',
                color: 'var(--color-text)',
              }}
              disabled={loadingAnos}
            >
              {anos && anos.length > 0
                ? anos.map(y => <option key={y} value={y}>{y}</option>)
                : <option value={fallbackYear}>{fallbackYear}</option>}
            </select>
            <ChevronDown size={13} className="absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none" style={{ color: 'var(--color-text-muted)' }} />
          </div>

          <button
            type="button"
            onClick={() => setRefreshKey(k => !k)}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors"
            style={{
              background: 'var(--color-surface-offset)',
              border: '1px solid var(--color-border)',
              color: 'var(--color-text)',
            }}
            title="Recalcular dados complementares do relatório legado"
          >
            <RefreshCw size={13} />
            Recalcular complementos
          </button>

          <button
            type="button"
            onClick={handleDownloadPDF}
            disabled={downloading || !report}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-semibold transition-colors"
            style={{
              background: downloading ? 'var(--color-surface-dynamic)' : 'var(--color-primary)',
              color: downloading ? 'var(--color-text-muted)' : 'white',
              opacity: (!report || downloading) ? 0.7 : 1,
            }}
          >
            <Download size={13} />
            {downloading ? 'Gerando...' : 'Exportar PDF'}
          </button>

          <button
            type="button"
            onClick={handleDownloadCSV}
            disabled={downloadingCSV || !report}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-semibold transition-colors"
            style={{
              background: downloadingCSV ? 'var(--color-surface-dynamic)' : 'var(--color-primary)',
              color: downloadingCSV ? 'var(--color-text-muted)' : 'white',
              opacity: (!report || downloadingCSV) ? 0.7 : 1,
            }}
          >
            <Download size={13} />
            {downloadingCSV ? 'Gerando...' : 'Exportar CSV'}
          </button>
        </div>
      </div>

      <div className="kpi-grid">
        {loadingCanonicalAssessment ? (
          [...Array(4)].map((_, i) => <SkeletonCard key={i} />)
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

      <div className="card overflow-hidden">
        <div
          className="flex border-b overflow-x-auto"
          style={{ borderColor: 'var(--color-divider)' }}
        >
          {TABS.map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              type="button"
              onClick={() => setActiveTab(key)}
              className={clsx(
                'flex items-center gap-2 px-4 py-3 text-sm font-medium whitespace-nowrap transition-colors',
                activeTab === key ? 'border-b-2' : '',
              )}
              style={{
                borderColor: activeTab === key ? 'var(--color-primary)' : 'transparent',
                color: activeTab === key ? 'var(--color-primary)' : 'var(--color-text-muted)',
              }}
            >
              <Icon size={14} />
              {label}
            </button>
          ))}
        </div>

        <div className="p-4">
          {activeTab === 'resumo' && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <div>
                <h2 className="text-sm font-semibold mb-3">Bens e Direitos</h2>
                {loadingReport ? <SkeletonCard /> : <BensDireitosTable data={report?.bens_direitos ?? []} />}
              </div>
              <div>
                <h2 className="text-sm font-semibold mb-3">Rendimentos</h2>
                {loadingReport ? (
                  <SkeletonCard />
                ) : (
                  <RendimentosTable
                    dividendos={report?.rendimentos_isentos ?? []}
                    jcp={report?.jcp ?? []}
                  />
                )}
              </div>
            </div>
          )}

          {activeTab === 'bens' && <BensDireitosTable data={report?.bens_direitos ?? []} />}
          {activeTab === 'ganhos' && <GanhosCapitalTable data={report?.ganhos_capital ?? []} />}
          {activeTab === 'rendimentos' && (
            <RendimentosTable
              dividendos={report?.rendimentos_isentos ?? []}
              jcp={[]}
            />
          )}
          {activeTab === 'jcp' && (
            <RendimentosTable
              dividendos={[]}
              jcp={report?.jcp ?? []}
            />
          )}
        </div>
      </div>
    </div>
  )
}