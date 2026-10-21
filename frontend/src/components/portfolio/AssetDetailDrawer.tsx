import { useMemo, useState } from 'react'
import {
  X,
  TrendingUp,
  DollarSign,
  Zap,
  CalendarDays,
  RefreshCw,
  PieChart,
  BarChart3,
  Sparkles,
  ShieldAlert,
  ShieldCheck,
  Building2,
  Briefcase,
  Layers,
  ArrowUpRight,
  ArrowDownRight,
} from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import {
  useAssetCorporateLifecycle,
  useAssetDetail,
  useAssetEnrichment,
  useAssetPortfolioInsights,
} from '@/hooks/useAssetDetail'
import { useTransactions } from '@/hooks/useTransactions'
import { useDividends } from '@/hooks/useDividends'
import { formatReferenceDate } from '@/utils/portfolioSummary'
import { formatBRL } from '@/utils/format'
import type { PositionGroup } from '@/hooks/usePortfolio'

export interface AssetDetailDrawerProps {
  asset?: PositionGroup['positions'][number] | null
  ticker?: string | null
  portfolioId: number
  onClose: () => void
}

const HISTORY_PERIODS = [
  { label: '1 sem', days: 7 },
  { label: '15 dias', days: 15 },
  { label: '30 dias', days: 30 },
  { label: '90 dias', days: 90 },
  { label: '1 ano', days: 365 },
  { label: 'Max', days: 1825 },
] as const

type ActiveTab = 'overview' | 'portfolio' | 'fundamentals' | 'insights'

function variationForPeriod(
  priceHistory: { date: string; price: number }[],
  days: number,
  currentPrice: number | null | undefined,
) {
  const lastPrice = currentPrice ?? priceHistory[priceHistory.length - 1]?.price
  if (!lastPrice || priceHistory.length === 0) return null

  const target = new Date()
  target.setDate(target.getDate() - days)
  const baseline = priceHistory.find(point => new Date(point.date) >= target) ?? priceHistory[0]
  if (!baseline?.price) return null

  const value = lastPrice - baseline.price
  return {
    value,
    percent: baseline.price > 0 ? (value / baseline.price) * 100 : null,
  }
}

function formatPercent(value: number | null | undefined) {
  if (value == null || !Number.isFinite(value)) return '-'
  return `${value >= 0 ? '+' : ''}${value.toFixed(2).replace('.', ',')}%`
}

function formatNumber(value: number | null | undefined, decimals = 2) {
  if (value == null || !Number.isFinite(value)) return '-'
  return value.toLocaleString('pt-BR', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })
}

export default function AssetDetailDrawer({
  asset,
  ticker,
  portfolioId,
  onClose,
}: AssetDetailDrawerProps) {
  const activeTicker = asset?.ticker ?? ticker
  if (!activeTicker) return null

  const [activeTab, setActiveTab] = useState<ActiveTab>('overview')
  const [historyDays, setHistoryDays] = useState(90)

  const { data: assetDetail, isLoading: loadingDetail } = useAssetDetail(activeTicker, historyDays)
  const { data: variationDetail } = useAssetDetail(activeTicker, 365)
  const { data: txData } = useTransactions(portfolioId, { ticker: activeTicker })
  const { data: corporateLifecycle = [] } = useAssetCorporateLifecycle(portfolioId, activeTicker)
  const { data: dividends } = useDividends(portfolioId)
  const { data: enrichment } = useAssetEnrichment(activeTicker, asset?.asset_type)
  const { data: portfolioInsight } = useAssetPortfolioInsights(portfolioId, activeTicker)

  const transactions = txData?.items ?? []
  const assetDividends = (dividends ?? []).filter(d => d.ticker === activeTicker)
  const priceHistory = assetDetail?.price_history ?? []
  const chartData = priceHistory.map(p => ({
    date: new Date(p.date).toLocaleDateString('pt-BR', { month: '2-digit', day: '2-digit' }),
    price: p.price,
  }))

  const avgPrice = asset?.average_price ?? portfolioInsight?.position.average_price ?? 0
  const totalDividends =
    asset?.proventos ??
    portfolioInsight?.position.dividends_received ??
    assetDividends.reduce((sum, d) => sum + d.amount, 0)

  const variationHistory = variationDetail?.price_history ?? priceHistory
  const weekVariation = useMemo(
    () => variationForPeriod(variationHistory, 7, assetDetail?.current_price),
    [variationHistory, assetDetail?.current_price],
  )
  const quarterVariation = useMemo(
    () => variationForPeriod(variationHistory, 90, assetDetail?.current_price),
    [variationHistory, assetDetail?.current_price],
  )
  const historyLabel =
    HISTORY_PERIODS.find(period => period.days === historyDays)?.label ?? `${historyDays}d`

  const position = portfolioInsight?.position
  const aiInsights = portfolioInsight?.ai_insights
  const fii = enrichment?.fii_indicators
  const stock = enrichment?.stock_fundamentals

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={`Detalhes do ativo ${activeTicker}`}
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.65)',
        backdropFilter: 'blur(4px)',
        zIndex: 50,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '1rem',
      }}
      onClick={e => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <div
        style={{
          width: '100%',
          maxWidth: 880,
          maxHeight: '92vh',
          background: 'var(--color-surface)',
          border: '1px solid var(--color-divider)',
          borderRadius: 'var(--radius-xl, 1rem)',
          boxShadow: 'var(--shadow-2xl, 0 25px 50px -12px rgba(0, 0, 0, 0.25))',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          animation: 'fadeInScale 0.25s ease-out',
        }}
      >
        <style>{`
          @keyframes fadeInScale {
            from {
              opacity: 0;
              transform: scale(0.96);
            }
            to {
              opacity: 1;
              transform: scale(1);
            }
          }
        `}</style>

        {/* Header Centralizado */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '1.25rem 1.5rem',
            borderBottom: '1px solid var(--color-divider)',
            background: 'var(--color-surface-offset, rgba(255, 255, 255, 0.02))',
            flexShrink: 0,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            {asset?.logo_url ? (
              <img
                src={asset.logo_url}
                alt={activeTicker}
                style={{ width: 44, height: 44, borderRadius: '50%', objectFit: 'contain' }}
              />
            ) : (
              <div
                style={{
                  width: 44,
                  height: 44,
                  borderRadius: '50%',
                  background: 'var(--color-primary-light, rgba(37, 99, 235, 0.1))',
                  color: 'var(--color-primary)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontWeight: 700,
                  fontSize: '1rem',
                }}
              >
                {activeTicker.slice(0, 2)}
              </div>
            )}
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <h2
                  style={{
                    fontSize: 'var(--text-lg, 1.25rem)',
                    fontWeight: 700,
                    color: 'var(--color-text)',
                    margin: 0,
                  }}
                >
                  {activeTicker}
                </h2>
                <span
                  style={{
                    fontSize: '0.7rem',
                    fontWeight: 600,
                    padding: '2px 8px',
                    borderRadius: 999,
                    background: 'var(--color-surface-offset)',
                    color: 'var(--color-text-muted)',
                    border: '1px solid var(--color-divider)',
                  }}
                >
                  {asset?.asset_label ?? assetDetail?.asset_type ?? 'Ativo'}
                </span>
                {enrichment?.coverage_status && (
                  <span
                    style={{
                      fontSize: '0.65rem',
                      fontWeight: 600,
                      padding: '2px 6px',
                      borderRadius: 4,
                      background:
                        enrichment.coverage_status === 'FULL'
                          ? 'rgba(34, 197, 94, 0.15)'
                          : 'rgba(234, 179, 8, 0.15)',
                      color:
                        enrichment.coverage_status === 'FULL'
                          ? 'var(--color-success)'
                          : 'var(--color-warning)',
                    }}
                  >
                    {enrichment.coverage_status}
                  </span>
                )}
              </div>
              <div style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)', marginTop: 2 }}>
                {assetDetail?.name ?? asset?.asset_label ?? 'Informações do Ativo'}
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
            {assetDetail?.current_price != null && (
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--color-text)' }}>
                  {formatBRL(assetDetail.current_price)}
                </div>
                <div
                  style={{
                    fontSize: '0.75rem',
                    fontWeight: 600,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'flex-end',
                    gap: 2,
                    color: (weekVariation?.value ?? 0) >= 0 ? 'var(--color-success)' : 'var(--color-danger)',
                  }}
                >
                  {(weekVariation?.value ?? 0) >= 0 ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
                  {formatPercent(weekVariation?.percent)} (7d)
                </div>
              </div>
            )}
            <button
              onClick={onClose}
              aria-label="Fechar janela"
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--color-text-muted)',
                cursor: 'pointer',
                padding: '0.5rem',
                borderRadius: 'var(--radius-md)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <X size={20} />
            </button>
          </div>
        </div>

        {/* Tab Navigation */}
        <div
          style={{
            display: 'flex',
            gap: '0.5rem',
            padding: '0.5rem 1.5rem',
            borderBottom: '1px solid var(--color-divider)',
            background: 'var(--color-surface)',
            flexShrink: 0,
            overflowX: 'auto',
          }}
        >
          <button
            onClick={() => setActiveTab('overview')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              padding: '0.5rem 0.85rem',
              borderRadius: 'var(--radius-md)',
              fontSize: '0.85rem',
              fontWeight: 600,
              cursor: 'pointer',
              border: 'none',
              background: activeTab === 'overview' ? 'var(--color-primary)' : 'transparent',
              color: activeTab === 'overview' ? '#fff' : 'var(--color-text-muted)',
            }}
          >
            <BarChart3 size={15} />
            Visão Geral & Preço
          </button>

          <button
            onClick={() => setActiveTab('portfolio')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              padding: '0.5rem 0.85rem',
              borderRadius: 'var(--radius-md)',
              fontSize: '0.85rem',
              fontWeight: 600,
              cursor: 'pointer',
              border: 'none',
              background: activeTab === 'portfolio' ? 'var(--color-primary)' : 'transparent',
              color: activeTab === 'portfolio' ? '#fff' : 'var(--color-text-muted)',
            }}
          >
            <PieChart size={15} />
            Na Minha Carteira
          </button>

          <button
            onClick={() => setActiveTab('fundamentals')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              padding: '0.5rem 0.85rem',
              borderRadius: 'var(--radius-md)',
              fontSize: '0.85rem',
              fontWeight: 600,
              cursor: 'pointer',
              border: 'none',
              background: activeTab === 'fundamentals' ? 'var(--color-primary)' : 'transparent',
              color: activeTab === 'fundamentals' ? '#fff' : 'var(--color-text-muted)',
            }}
          >
            <Building2 size={15} />
            Fundamentos & Imóveis
          </button>

          <button
            onClick={() => setActiveTab('insights')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              padding: '0.5rem 0.85rem',
              borderRadius: 'var(--radius-md)',
              fontSize: '0.85rem',
              fontWeight: 600,
              cursor: 'pointer',
              border: 'none',
              background: activeTab === 'insights' ? 'var(--color-primary)' : 'transparent',
              color: activeTab === 'insights' ? '#fff' : 'var(--color-text-muted)',
            }}
          >
            <Sparkles size={15} />
            Insights com IA
          </button>
        </div>

        {/* Corpo com Scroll */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '1.25rem 1.5rem' }}>
          {/* TAB 1: VISÃO GERAL & PREÇO */}
          {activeTab === 'overview' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
              {chartData.length > 0 ? (
                <div
                  style={{
                    background: 'var(--color-surface-offset)',
                    padding: '1rem',
                    borderRadius: 'var(--radius-lg)',
                    border: '1px solid var(--color-divider)',
                  }}
                >
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      marginBottom: '0.75rem',
                    }}
                  >
                    <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
                      Evolução de Preço ({historyLabel})
                    </span>
                    <select
                      value={historyDays}
                      onChange={e => setHistoryDays(Number(e.target.value))}
                      style={{
                        background: 'var(--color-surface)',
                        color: 'var(--color-text)',
                        border: '1px solid var(--color-divider)',
                        borderRadius: 'var(--radius-md)',
                        fontSize: '0.75rem',
                        padding: '0.25rem 0.5rem',
                        cursor: 'pointer',
                      }}
                    >
                      {HISTORY_PERIODS.map(period => (
                        <option key={period.days} value={period.days}>
                          {period.label}
                        </option>
                      ))}
                    </select>
                  </div>
                  <ResponsiveContainer width="100%" height={220}>
                    <LineChart data={chartData}>
                      <CartesianGrid stroke="var(--color-divider)" vertical={false} />
                      <XAxis
                        dataKey="date"
                        tick={{ fontSize: 11, fill: 'var(--color-text-muted)' }}
                        interval={Math.floor(chartData.length / 5)}
                      />
                      <YAxis tick={{ fontSize: 11, fill: 'var(--color-text-muted)' }} width={55} />
                      <Tooltip
                        contentStyle={{
                          background: 'var(--color-surface)',
                          border: '1px solid var(--color-divider)',
                          borderRadius: 'var(--radius-md)',
                        }}
                        formatter={(value: unknown) => formatBRL(Number(value))}
                      />
                      <Line
                        type="monotone"
                        dataKey="price"
                        stroke="var(--color-primary)"
                        dot={false}
                        isAnimationActive={false}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              ) : null}

              {/* Grid 4 KPIs Rápidos */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '0.75rem' }}>
                <div style={{ background: 'var(--color-surface-offset)', padding: '0.85rem', borderRadius: 'var(--radius-md)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: '0.5rem' }}>
                    <DollarSign size={14} style={{ color: 'var(--color-primary)' }} />
                    <span style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>Preço Médio</span>
                  </div>
                  <div style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--color-text)' }}>
                    {avgPrice > 0 ? formatBRL(avgPrice) : '-'}
                  </div>
                </div>

                <div style={{ background: 'var(--color-surface-offset)', padding: '0.85rem', borderRadius: 'var(--radius-md)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: '0.5rem' }}>
                    <Zap size={14} style={{ color: 'var(--color-primary)' }} />
                    <span style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>Proventos (Total)</span>
                  </div>
                  <div style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--color-text)' }}>
                    {formatBRL(totalDividends)}
                  </div>
                </div>

                <div style={{ background: 'var(--color-surface-offset)', padding: '0.85rem', borderRadius: 'var(--radius-md)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: '0.5rem' }}>
                    <CalendarDays size={14} style={{ color: 'var(--color-primary)' }} />
                    <span style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>Variação 7 dias</span>
                  </div>
                  <div
                    style={{
                      fontSize: '1rem',
                      fontWeight: 600,
                      color: (weekVariation?.value ?? 0) >= 0 ? 'var(--color-success)' : 'var(--color-danger)',
                    }}
                  >
                    {formatPercent(weekVariation?.percent)}
                  </div>
                </div>

                <div style={{ background: 'var(--color-surface-offset)', padding: '0.85rem', borderRadius: 'var(--radius-md)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: '0.5rem' }}>
                    <TrendingUp size={14} style={{ color: 'var(--color-primary)' }} />
                    <span style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>Variação 90 dias</span>
                  </div>
                  <div
                    style={{
                      fontSize: '1rem',
                      fontWeight: 600,
                      color: (quarterVariation?.value ?? 0) >= 0 ? 'var(--color-success)' : 'var(--color-danger)',
                    }}
                  >
                    {formatPercent(quarterVariation?.percent)}
                  </div>
                </div>
              </div>

              {/* Eventos Corporativos (se houver) */}
              {corporateLifecycle.length > 0 && (
                <div style={{ background: 'var(--color-surface-offset)', padding: '1rem', borderRadius: 'var(--radius-lg)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: '0.75rem' }}>
                    <RefreshCw size={14} style={{ color: 'var(--color-primary)' }} />
                    <h3 style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--color-text)', margin: 0 }}>
                      Eventos corporativos ({corporateLifecycle.length})
                    </h3>
                  </div>
                  <div style={{ maxHeight: 240, overflowY: 'auto' }}>
                    {corporateLifecycle.map((event, index) => (
                      <div
                        key={event.source_event_id}
                        style={{
                          padding: '0.65rem 0',
                          borderBottom: index < corporateLifecycle.length - 1 ? '1px solid var(--color-divider)' : 'none',
                          fontSize: 'var(--text-xs)',
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.75rem' }}>
                          <div style={{ fontWeight: 600, color: 'var(--color-text)' }}>
                            {event.event_type} · fator {Number(event.quantity_factor).toLocaleString('pt-BR')}
                          </div>
                          <div style={{ color: 'var(--color-text-muted)', whiteSpace: 'nowrap' }}>
                            {event.event_date.split('-').reverse().join('/')}
                          </div>
                        </div>
                        {event.message && (
                          <div style={{ color: 'var(--color-text-muted)', marginTop: 4 }}>
                            {event.message}
                          </div>
                        )}
                        {event.fractional_quantity != null && (
                          <div style={{ color: 'var(--color-text)', marginTop: 4 }}>
                            {event.settlement_status === 'PENDING_VALUE'
                              ? `Fração pendente: ${Number(event.fractional_quantity).toLocaleString('pt-BR')}`
                              : `Fração vendida: ${Number(event.fractional_quantity).toLocaleString('pt-BR')}`}
                            {event.gross_amount_brl != null && ` · Valor creditado: ${formatBRL(Number(event.gross_amount_brl))}`}
                          </div>
                        )}
                        {event.realized_pnl_brl != null && (
                          <div style={{ color: 'var(--color-text-muted)', marginTop: 2 }}>
                            Resultado realizado: {formatBRL(Number(event.realized_pnl_brl))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Proventos */}
              {assetDividends.length > 0 && (
                <div style={{ background: 'var(--color-surface-offset)', padding: '1rem', borderRadius: 'var(--radius-lg)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: '0.75rem' }}>
                    <Zap size={14} style={{ color: 'var(--color-primary)' }} />
                    <h3 style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--color-text)', margin: 0 }}>
                      Proventos ({assetDividends.length})
                    </h3>
                  </div>
                  <div style={{ maxHeight: 200, overflowY: 'auto' }}>
                    {assetDividends.map((div, i) => (
                      <div
                        key={i}
                        style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                          padding: '0.5rem 0',
                          borderBottom: i < assetDividends.length - 1 ? '1px solid var(--color-divider)' : 'none',
                          fontSize: 'var(--text-xs)',
                        }}
                      >
                        <div>
                          <div style={{ fontWeight: 600, color: 'var(--color-text)', marginBottom: 2 }}>
                            {div.type}
                          </div>
                          <div style={{ color: 'var(--color-text-muted)' }}>
                            {formatReferenceDate(div.payment_date) ?? '-'}
                          </div>
                        </div>
                        <div style={{ fontWeight: 600, color: 'var(--color-success)', textAlign: 'right' }}>
                          {formatBRL(div.amount)}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Transações */}
              {transactions.length > 0 && (
                <div style={{ background: 'var(--color-surface-offset)', padding: '1rem', borderRadius: 'var(--radius-lg)' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: '0.75rem' }}>
                    <TrendingUp size={14} style={{ color: 'var(--color-primary)' }} />
                    <h3 style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--color-text)', margin: 0 }}>
                      Transações ({transactions.length})
                    </h3>
                  </div>
                  <div style={{ maxHeight: 200, overflowY: 'auto' }}>
                    {transactions.map((tx, i) => (
                      <div
                        key={i}
                        style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                          padding: '0.5rem 0',
                          borderBottom: i < transactions.length - 1 ? '1px solid var(--color-divider)' : 'none',
                          fontSize: 'var(--text-xs)',
                        }}
                      >
                        <div>
                          <div style={{ fontWeight: 600, color: 'var(--color-text)', marginBottom: 2 }}>
                            {tx.operation.toUpperCase()} {tx.quantity} @ {formatBRL(tx.price)}
                          </div>
                          <div style={{ color: 'var(--color-text-muted)' }}>
                            {new Date(tx.date).toLocaleDateString('pt-BR')}
                          </div>
                        </div>
                        <div style={{ fontWeight: 600, color: 'var(--color-text)', textAlign: 'right' }}>
                          {formatBRL(tx.quantity * tx.price)}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* TAB 2: NA MINHA CARTEIRA */}
          {activeTab === 'portfolio' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
              {position && position.is_held ? (
                <>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '0.75rem' }}>
                    <div style={{ background: 'var(--color-surface-offset)', padding: '1rem', borderRadius: 'var(--radius-md)' }}>
                      <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>Posição em Custódia</span>
                      <div style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--color-text)', marginTop: 4 }}>
                        {formatNumber(position.quantity)} cotas
                      </div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginTop: 2 }}>
                        PM: {formatBRL(position.average_price)}
                      </div>
                    </div>

                    <div style={{ background: 'var(--color-surface-offset)', padding: '1rem', borderRadius: 'var(--radius-md)' }}>
                      <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>Total Investido vs Atual</span>
                      <div style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--color-text)', marginTop: 4 }}>
                        {formatBRL(position.current_value)}
                      </div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', marginTop: 2 }}>
                        Custo: {formatBRL(position.invested_value)}
                      </div>
                    </div>

                    <div style={{ background: 'var(--color-surface-offset)', padding: '1rem', borderRadius: 'var(--radius-md)' }}>
                      <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>Ganho de Capital</span>
                      <div
                        style={{
                          fontSize: '1.25rem',
                          fontWeight: 700,
                          marginTop: 4,
                          color: position.capital_gain_value >= 0 ? 'var(--color-success)' : 'var(--color-danger)',
                        }}
                      >
                        {formatBRL(position.capital_gain_value)}
                      </div>
                      <div
                        style={{
                          fontSize: '0.75rem',
                          fontWeight: 600,
                          marginTop: 2,
                          color: position.capital_gain_percent >= 0 ? 'var(--color-success)' : 'var(--color-danger)',
                        }}
                      >
                        {formatPercent(position.capital_gain_percent)}
                      </div>
                    </div>

                    <div style={{ background: 'var(--color-surface-offset)', padding: '1rem', borderRadius: 'var(--radius-md)' }}>
                      <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>Retorno Total (c/ Proventos)</span>
                      <div
                        style={{
                          fontSize: '1.25rem',
                          fontWeight: 700,
                          marginTop: 4,
                          color: position.total_return_value >= 0 ? 'var(--color-success)' : 'var(--color-danger)',
                        }}
                      >
                        {formatBRL(position.total_return_value)}
                      </div>
                      <div
                        style={{
                          fontSize: '0.75rem',
                          fontWeight: 600,
                          marginTop: 2,
                          color: position.total_return_percent >= 0 ? 'var(--color-success)' : 'var(--color-danger)',
                        }}
                      >
                        {formatPercent(position.total_return_percent)} (+{formatBRL(position.dividends_received)})
                      </div>
                    </div>
                  </div>

                  {/* Barra de Pesos e Alocação */}
                  <div style={{ background: 'var(--color-surface-offset)', padding: '1.25rem', borderRadius: 'var(--radius-lg)' }}>
                    <h3 style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--color-text)', margin: '0 0 1rem 0' }}>
                      Alocação e Pesos na Carteira
                    </h3>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem' }}>
                      <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: 4 }}>
                          <span style={{ color: 'var(--color-text-muted)' }}>Peso no Portfólio Global</span>
                          <span style={{ fontWeight: 600, color: 'var(--color-text)' }}>{formatPercent(position.portfolio_weight_percent)}</span>
                        </div>
                        <div style={{ height: 8, background: 'var(--color-divider)', borderRadius: 999, overflow: 'hidden' }}>
                          <div style={{ width: `${Math.min(position.portfolio_weight_percent, 100)}%`, height: '100%', background: 'var(--color-primary)' }} />
                        </div>
                      </div>

                      <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: 4 }}>
                          <span style={{ color: 'var(--color-text-muted)' }}>Peso na Classe ({position.class_label})</span>
                          <span style={{ fontWeight: 600, color: 'var(--color-text)' }}>{formatPercent(position.class_weight_percent)}</span>
                        </div>
                        <div style={{ height: 8, background: 'var(--color-divider)', borderRadius: 999, overflow: 'hidden' }}>
                          <div style={{ width: `${Math.min(position.class_weight_percent, 100)}%`, height: '100%', background: 'var(--color-success)' }} />
                        </div>
                      </div>

                      <div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: 4 }}>
                          <span style={{ color: 'var(--color-text-muted)' }}>Yield on Cost (YoC)</span>
                          <span style={{ fontWeight: 600, color: 'var(--color-success)' }}>
                            {position.yield_on_cost_percent != null ? `${position.yield_on_cost_percent.toFixed(2).replace('.', ',')}%` : '-'}
                          </span>
                        </div>
                        <span style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>
                          Retorno anualizado sobre o preço médio pago
                        </span>
                      </div>
                    </div>
                  </div>
                </>
              ) : (
                <div style={{ textAlign: 'center', padding: '3rem 1rem', color: 'var(--color-text-muted)' }}>
                  <Briefcase size={36} style={{ margin: '0 auto 1rem auto', opacity: 0.5 }} />
                  <p style={{ fontWeight: 600, color: 'var(--color-text)', margin: 0 }}>
                    Você ainda não possui cotas de {activeTicker} nesta carteira.
                  </p>
                  <p style={{ fontSize: '0.8rem', marginTop: 4 }}>
                    Ao registrar transações de compra deste ativo, esta aba passará a exibir o acompanhamento
                    detalhado de preço médio, ganho de capital e proventos recebidos.
                  </p>
                </div>
              )}
            </div>
          )}

          {/* TAB 3: FUNDAMENTOS & IMÓVEIS */}
          {activeTab === 'fundamentals' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
              {fii ? (
                <>
                  <div style={{ background: 'var(--color-surface-offset)', padding: '1.25rem', borderRadius: 'var(--radius-lg)' }}>
                    <h3 style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--color-text)', margin: '0 0 1rem 0' }}>
                      Indicadores Financeiros de FII
                    </h3>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '0.75rem' }}>
                      <div style={{ padding: '0.5rem', background: 'var(--color-surface)', borderRadius: 6 }}>
                        <span style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>P/VP</span>
                        <div style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--color-text)' }}>
                          {fii.pvp != null ? formatNumber(fii.pvp) : '-'}
                        </div>
                      </div>
                      <div style={{ padding: '0.5rem', background: 'var(--color-surface)', borderRadius: 6 }}>
                        <span style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>Dividend Yield</span>
                        <div style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--color-success)' }}>
                          {fii.dividend_yield != null ? `${formatNumber(fii.dividend_yield)}%` : '-'}
                        </div>
                      </div>
                      <div style={{ padding: '0.5rem', background: 'var(--color-surface)', borderRadius: 6 }}>
                        <span style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>Patrimônio Líquido</span>
                        <div style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--color-text)' }}>
                          {fii.net_worth != null ? formatBRL(fii.net_worth) : '-'}
                        </div>
                      </div>
                      <div style={{ padding: '0.5rem', background: 'var(--color-surface)', borderRadius: 6 }}>
                        <span style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>Cotistas</span>
                        <div style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--color-text)' }}>
                          {fii.share_holders != null ? fii.share_holders.toLocaleString('pt-BR') : '-'}
                        </div>
                      </div>
                    </div>
                  </div>

                  <div style={{ background: 'var(--color-surface-offset)', padding: '1.25rem', borderRadius: 'var(--radius-lg)' }}>
                    <h3 style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--color-text)', margin: '0 0 1rem 0' }}>
                      Operações, Imóveis e Vacância
                    </h3>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '0.75rem' }}>
                      <div style={{ padding: '0.5rem', background: 'var(--color-surface)', borderRadius: 6 }}>
                        <span style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>Vacância Física</span>
                        <div style={{ fontSize: '1.1rem', fontWeight: 700, color: (fii.physical_vacancy ?? 0) > 10 ? 'var(--color-warning)' : 'var(--color-text)' }}>
                          {fii.physical_vacancy != null ? `${formatNumber(fii.physical_vacancy)}%` : '-'}
                        </div>
                      </div>
                      <div style={{ padding: '0.5rem', background: 'var(--color-surface)', borderRadius: 6 }}>
                        <span style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>Vacância Financeira</span>
                        <div style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--color-text)' }}>
                          {fii.financial_vacancy != null ? `${formatNumber(fii.financial_vacancy)}%` : '-'}
                        </div>
                      </div>
                      <div style={{ padding: '0.5rem', background: 'var(--color-surface)', borderRadius: 6 }}>
                        <span style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>Imóveis / Propriedades</span>
                        <div style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--color-text)' }}>
                          {fii.properties_count != null ? fii.properties_count : '-'}
                        </div>
                      </div>
                      <div style={{ padding: '0.5rem', background: 'var(--color-surface)', borderRadius: 6 }}>
                        <span style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>Segmento</span>
                        <div style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--color-text)' }}>
                          {fii.segment ?? '-'}
                        </div>
                      </div>
                    </div>
                  </div>
                </>
              ) : stock ? (
                <>
                  <div style={{ background: 'var(--color-surface-offset)', padding: '1.25rem', borderRadius: 'var(--radius-lg)' }}>
                    <h3 style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--color-text)', margin: '0 0 1rem 0' }}>
                      Métricas de Valuation da Ação
                    </h3>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '0.75rem' }}>
                      <div style={{ padding: '0.5rem', background: 'var(--color-surface)', borderRadius: 6 }}>
                        <span style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>P/L (Preço / Lucro)</span>
                        <div style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--color-text)' }}>
                          {stock.pe != null ? formatNumber(stock.pe) : '-'}
                        </div>
                      </div>
                      <div style={{ padding: '0.5rem', background: 'var(--color-surface)', borderRadius: 6 }}>
                        <span style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>P/VP</span>
                        <div style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--color-text)' }}>
                          {stock.pb != null ? formatNumber(stock.pb) : '-'}
                        </div>
                      </div>
                      <div style={{ padding: '0.5rem', background: 'var(--color-surface)', borderRadius: 6 }}>
                        <span style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>Dividend Yield</span>
                        <div style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--color-success)' }}>
                          {stock.dividend_yield != null ? `${formatNumber(stock.dividend_yield)}%` : '-'}
                        </div>
                      </div>
                      <div style={{ padding: '0.5rem', background: 'var(--color-surface)', borderRadius: 6 }}>
                        <span style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>LPA (Lucro p/ Ação)</span>
                        <div style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--color-text)' }}>
                          {stock.eps != null ? formatBRL(stock.eps) : '-'}
                        </div>
                      </div>
                    </div>
                  </div>

                  <div style={{ background: 'var(--color-surface-offset)', padding: '1.25rem', borderRadius: 'var(--radius-lg)' }}>
                    <h3 style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--color-text)', margin: '0 0 1rem 0' }}>
                      Rentabilidade, Margens e Balanço
                    </h3>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '0.75rem' }}>
                      <div style={{ padding: '0.5rem', background: 'var(--color-surface)', borderRadius: 6 }}>
                        <span style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>ROE</span>
                        <div style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--color-text)' }}>
                          {stock.roe != null ? `${formatNumber(stock.roe)}%` : '-'}
                        </div>
                      </div>
                      <div style={{ padding: '0.5rem', background: 'var(--color-surface)', borderRadius: 6 }}>
                        <span style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>Margem Líquida</span>
                        <div style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--color-text)' }}>
                          {stock.net_margin != null ? `${formatNumber(stock.net_margin)}%` : '-'}
                        </div>
                      </div>
                      <div style={{ padding: '0.5rem', background: 'var(--color-surface)', borderRadius: 6 }}>
                        <span style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>EBITDA</span>
                        <div style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--color-text)' }}>
                          {stock.ebitda != null ? formatBRL(stock.ebitda) : '-'}
                        </div>
                      </div>
                      <div style={{ padding: '0.5rem', background: 'var(--color-surface)', borderRadius: 6 }}>
                        <span style={{ fontSize: '0.7rem', color: 'var(--color-text-muted)' }}>Valor de Mercado</span>
                        <div style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--color-text)' }}>
                          {stock.market_cap != null ? formatBRL(stock.market_cap) : '-'}
                        </div>
                      </div>
                    </div>
                  </div>
                </>
              ) : (
                <div style={{ textAlign: 'center', padding: '3rem 1rem', color: 'var(--color-text-muted)' }}>
                  <Layers size={36} style={{ margin: '0 auto 1rem auto', opacity: 0.5 }} />
                  <p style={{ fontWeight: 600, color: 'var(--color-text)', margin: 0 }}>
                    Métricas fundamentalistas em processo de enriquecimento.
                  </p>
                  <p style={{ fontSize: '0.8rem', marginTop: 4 }}>
                    Os indicadores para {activeTicker} serão atualizados automaticamente através do nosso serviço de
                    cobertura integrada de mercado.
                  </p>
                </div>
              )}
            </div>
          )}

          {/* TAB 4: INSIGHTS COM IA */}
          {activeTab === 'insights' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
              {aiInsights ? (
                <>
                  {/* Card Principal de Resumo Explicável de IA */}
                  <div
                    style={{
                      background: 'linear-gradient(135deg, rgba(37, 99, 235, 0.12) 0%, rgba(147, 51, 234, 0.12) 100%)',
                      border: '1px solid rgba(147, 51, 234, 0.25)',
                      padding: '1.25rem',
                      borderRadius: 'var(--radius-lg)',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: '0.75rem' }}>
                      <Sparkles size={18} style={{ color: '#a855f7' }} />
                      <h3 style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--color-text)', margin: 0 }}>
                        Diagnóstico Estratégico com IA
                      </h3>
                    </div>
                    <p style={{ fontSize: '0.85rem', color: 'var(--color-text)', lineHeight: 1.6, margin: 0 }}>
                      {aiInsights.explainable_summary}
                    </p>
                  </div>

                  {/* 3 Blocos de Análise Inteligente */}
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1rem' }}>
                    {/* Concentração & Risco */}
                    <div
                      style={{
                        background: 'var(--color-surface-offset)',
                        padding: '1.25rem',
                        borderRadius: 'var(--radius-lg)',
                        border: '1px solid var(--color-divider)',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                          {aiInsights.concentration_level === 'HIGH' || aiInsights.concentration_level === 'WARNING' ? (
                            <ShieldAlert size={16} style={{ color: 'var(--color-warning)' }} />
                          ) : (
                            <ShieldCheck size={16} style={{ color: 'var(--color-success)' }} />
                          )}
                          <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--color-text)' }}>
                            Concentração & Risco
                          </span>
                        </div>
                        <span
                          style={{
                            fontSize: '0.7rem',
                            fontWeight: 700,
                            padding: '2px 8px',
                            borderRadius: 999,
                            background:
                              aiInsights.concentration_level === 'HIGH'
                                ? 'rgba(239, 68, 68, 0.15)'
                                : aiInsights.concentration_level === 'WARNING'
                                ? 'rgba(234, 179, 8, 0.15)'
                                : 'rgba(34, 197, 94, 0.15)',
                            color:
                              aiInsights.concentration_level === 'HIGH'
                                ? 'var(--color-danger)'
                                : aiInsights.concentration_level === 'WARNING'
                                ? 'var(--color-warning)'
                                : 'var(--color-success)',
                          }}
                        >
                          {aiInsights.concentration_level}
                        </span>
                      </div>
                      <p style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)', lineHeight: 1.5, margin: 0 }}>
                        {aiInsights.concentration_message}
                      </p>
                    </div>

                    {/* Geração de Renda */}
                    <div
                      style={{
                        background: 'var(--color-surface-offset)',
                        padding: '1.25rem',
                        borderRadius: 'var(--radius-lg)',
                        border: '1px solid var(--color-divider)',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: '0.75rem' }}>
                        <Zap size={16} style={{ color: 'var(--color-primary)' }} />
                        <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--color-text)' }}>
                          Geração de Renda & YoC
                        </span>
                      </div>
                      <p style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)', lineHeight: 1.5, margin: 0 }}>
                        {aiInsights.income_assessment}
                      </p>
                    </div>

                    {/* Rebalanceamento */}
                    <div
                      style={{
                        background: 'var(--color-surface-offset)',
                        padding: '1.25rem',
                        borderRadius: 'var(--radius-lg)',
                        border: '1px solid var(--color-divider)',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: '0.75rem' }}>
                        <PieChart size={16} style={{ color: 'var(--color-success)' }} />
                        <span style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--color-text)' }}>
                          Aderência ao Rebalanceamento
                        </span>
                      </div>
                      <p style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)', lineHeight: 1.5, margin: 0 }}>
                        {aiInsights.rebalancing_guidance}
                      </p>
                    </div>
                  </div>
                </>
              ) : (
                <div style={{ textAlign: 'center', padding: '3rem 1rem', color: 'var(--color-text-muted)' }}>
                  <Sparkles size={36} style={{ margin: '0 auto 1rem auto', opacity: 0.5 }} />
                  <p style={{ fontWeight: 600, color: 'var(--color-text)', margin: 0 }}>
                    Carregando insights com IA para {activeTicker}...
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
