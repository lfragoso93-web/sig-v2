import { useState, useCallback } from 'react'
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
import { useIRPFAnos, useIRPFReport } from '@/hooks/useIRPF'
import { formatBRL } from '@/utils/format'
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

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

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

// ---------------------------------------------------------------------------
// Sub-tabelas
// ---------------------------------------------------------------------------

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
            {/* Linha do mês */}
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

            {/* Detalhe expandido */}
            {isOpen && (
              <div className="px-4 pb-4">
                {/* Totais do mês */}
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
                {/* Detalhe das vendas */}
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
      {/* Dividendos Isentos */}
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

      {/* JCP */}
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

// ---------------------------------------------------------------------------
// Página principal
// ---------------------------------------------------------------------------

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

  const [selectedYear, setSelectedYear] = useState<number>(currentYear - 1)
  const [activeTab, setActiveTab] = useState<Tab>('resumo')
  const [downloading, setDownloading] = useState(false)
  const [refreshKey, setRefreshKey] = useState(false)

  const { data: anos, isLoading: loadingAnos } = useIRPFAnos(portfolioId)
  const { data: report, isLoading: loadingReport } = useIRPFReport(portfolioId, selectedYear, refreshKey)

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

  const r = report?.resumo

  return (
    <div className="page-container">

      {/* Cabeçalho */}
      <div className="page-header">
        <div>
          <h1 className="page-title">IRPF</h1>
          <p className="page-subtitle">Relatório fiscal de investimentos para declaração do Imposto de Renda</p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {/* Seletor de ano */}
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
                : <option value={currentYear - 1}>{currentYear - 1}</option>}
            </select>
            <ChevronDown size={13} className="absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none" style={{ color: 'var(--color-text-muted)' }} />
          </div>

          {/* Recalcular */}
          <button
            type="button"
            onClick={() => setRefreshKey(k => !k)}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors"
            style={{
              background: 'var(--color-surface-offset)',
              border: '1px solid var(--color-border)',
              color: 'var(--color-text)',
            }}
            title="Recalcular relatório"
          >
            <RefreshCw size={13} />
            Recalcular
          </button>

          {/* Download PDF */}
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
        </div>
      </div>

      {/* KPI Cards — Resumo Rápido */}
      <div className="kpi-grid">
        {loadingReport ? (
          [...Array(4)].map((_, i) => <SkeletonCard key={i} />)
        ) : r ? (
          <>
            <KpiCard
              label="Bens e Direitos (31/12)"
              value={formatBRL(r.total_bens_direitos)}
              subLabel={`Ano-base ${selectedYear}`}
            />
            <KpiCard
              label="IR a Recolher"
              value={formatBRL(r.ir_a_recolher_total)}
              valueColor={r.ir_a_recolher_total > 0 ? 'text-[var(--color-error)]' : 'text-[var(--color-success)]'}
              subLabel="Swing + Day Trade - Fonte"
            />
            <KpiCard
              label="Dividendos Isentos"
              value={formatBRL(r.total_dividendos_isentos)}
              subLabel="Rendimentos isentos no ano"
            />
            <KpiCard
              label="Prejuízo Acumulado"
              value={formatBRL(Math.abs(r.prejuizo_acumulado))}
              valueColor={r.prejuizo_acumulado < 0 ? 'text-[var(--color-error)]' : 'text-[var(--color-text-muted)]'}
              subLabel="A compensar em meses futuros"
            />
          </>
        ) : null}
      </div>

      {/* Abas */}
      <div className="card overflow-hidden">
        {/* Tab bar */}
        <div
          className="flex border-b overflow-x-auto"
          style={{ borderColor: 'var(--color-divider)' }}
        >
          {TABS.map(({ key, label, icon: Icon }) => {
            const active = activeTab === key
            return (
              <button
                key={key}
                type="button"
                onClick={() => setActiveTab(key)}
                className="flex items-center gap-1.5 px-4 py-3 text-sm font-medium whitespace-nowrap transition-colors border-b-2"
                style={{
                  borderColor: active ? 'var(--color-primary)' : 'transparent',
                  color: active ? 'var(--color-primary)' : 'var(--color-text-muted)',
                }}
              >
                <Icon size={13} />
                {label}
              </button>
            )
          })}
        </div>

        {/* Conteúdo da aba */}
        <div className="p-4">
          {loadingReport ? (
            <div className="flex flex-col gap-2">
              {[...Array(5)].map((_, i) => <div key={i} className="h-10 rounded skeleton" />)}
            </div>
          ) : !report ? (
            <Empty label="Nenhum dado encontrado para este ano. Clique em Recalcular." />
          ) : (
            <>
              {activeTab === 'resumo' && r && (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {[
                    { label: 'Total de Vendas no Ano',          value: r.total_vendas_ano },
                    { label: 'Lucro Tributável Swing Trade',    value: r.lucro_tributavel_swing },
                    { label: 'Lucro Tributável Day Trade',      value: r.lucro_tributavel_day_trade },
                    { label: 'IR Swing Trade Devido',           value: r.ir_swing_trade_devido },
                    { label: 'IR Day Trade Devido',             value: r.ir_day_trade_devido },
                    { label: 'IR Retido na Fonte',              value: r.ir_retido_fonte_total },
                    { label: 'IR a Recolher',                   value: r.ir_a_recolher_total, destaque: true },
                    { label: 'Total Dividendos Isentos',        value: r.total_dividendos_isentos },
                    { label: 'Total JCP Bruto',                 value: r.total_jcp_bruto },
                    { label: 'IR Retido JCP (15%)',             value: r.total_jcp_ir_retido },
                    { label: 'Prejuízo Acumulado',              value: r.prejuizo_acumulado },
                  ].map(({ label, value, destaque }) => (
                    <div
                      key={label}
                      className="flex justify-between items-center rounded-lg px-4 py-3"
                      style={{
                        background: 'var(--color-surface-offset)',
                        border: destaque ? '1px solid var(--color-primary)40' : '1px solid transparent',
                      }}
                    >
                      <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>{label}</span>
                      <span className={clsx('text-sm font-semibold tabular-nums', signCls(value))}>
                        {formatBRL(value)}
                      </span>
                    </div>
                  ))}
                </div>
              )}

              {activeTab === 'bens' && (
                <BensDireitosTable data={report.bens_direitos} />
              )}

              {activeTab === 'ganhos' && (
                <GanhosCapitalTable data={report.ganhos_mensais} />
              )}

              {activeTab === 'rendimentos' && (
                <RendimentosTable dividendos={report.dividendos} jcp={[]} />
              )}

              {activeTab === 'jcp' && (
                <RendimentosTable dividendos={[]} jcp={report.jcp} />
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
