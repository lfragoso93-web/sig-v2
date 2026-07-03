import { X, TrendingUp, DollarSign, Zap } from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { useAssetDetail } from '@/hooks/useAssetDetail'
import { useTransactions } from '@/hooks/useTransactions'
import { useDividends } from '@/hooks/useDividends'
import { formatBRL } from '@/utils/format'
import type { PositionGroup } from '@/hooks/usePortfolio'

interface AssetDetailDrawerProps {
  asset: PositionGroup['positions'][number] | null
  portfolioId: number
  onClose: () => void
}

export default function AssetDetailDrawer({ asset, portfolioId, onClose }: AssetDetailDrawerProps) {
  if (!asset) return null

  const { data: assetDetail, isLoading: loadingDetail } = useAssetDetail(asset.ticker, 90)
  const { data: txData } = useTransactions(portfolioId, { ticker: asset.ticker })
  const { data: dividends } = useDividends(portfolioId)

  const transactions = txData?.items ?? []
  const assetDividends = (dividends ?? []).filter(d => d.ticker === asset.ticker)

  const priceHistory = assetDetail?.price_history ?? []
  const chartData = priceHistory.map(p => ({
    date: new Date(p.date).toLocaleDateString('pt-BR', { month: '2-digit', day: '2-digit' }),
    price: p.price,
  }))

  const avgPrice = transactions.length > 0
    ? transactions.reduce((sum, tx) => sum + (tx.price * (tx.operation === 'buy' ? 1 : -1)), 0) / 
      transactions.filter(tx => tx.operation === 'buy').length
    : 0

  const totalDividends = assetDividends.reduce((sum, d) => sum + d.amount, 0)

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      right: 0,
      width: '100%',
      maxWidth: 480,
      height: '100vh',
      background: 'var(--color-surface)',
      borderLeft: '1px solid var(--color-divider)',
      boxShadow: 'var(--shadow-xl)',
      zIndex: 50,
      display: 'flex',
      flexDirection: 'column',
      animation: 'slideIn 0.3s ease-out',
    }}>
      <style>{`
        @keyframes slideIn {
          from {
            transform: translateX(100%);
            opacity: 0;
          }
          to {
            transform: translateX(0);
            opacity: 1;
          }
        }
      `}</style>

      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '1rem',
        borderBottom: '1px solid var(--color-divider)',
        flexShrink: 0,
      }}>
        <div>
          <h2 style={{ fontSize: 'var(--text-lg)', fontWeight: 700, color: 'var(--color-text)', margin: 0 }}>
            {asset.ticker}
          </h2>
          <p style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', margin: '2px 0 0' }}>
            {asset.asset_label || asset.asset_type}
          </p>
        </div>
        <button
          onClick={onClose}
          style={{
            background: 'transparent',
            border: 'none',
            cursor: 'pointer',
            padding: 6,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'var(--color-text-muted)',
            borderRadius: 'var(--radius-md)',
          }}
          onMouseEnter={e => (e.currentTarget.style.background = 'var(--color-surface-offset)')}
          onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
        >
          <X size={20} />
        </button>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '1rem' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {/* Preço atual */}
          {assetDetail && (
            <div style={{
              background: 'var(--color-surface-offset)',
              padding: '1rem',
              borderRadius: 'var(--radius-lg)',
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '0.5rem' }}>
                <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>Preço Atual</span>
                <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>
                  Histórico: 90d
                </span>
              </div>
              <div style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--color-text)' }}>
                {assetDetail.current_price ? formatBRL(assetDetail.current_price) : '—'}
              </div>
              {assetDetail.last_price_updated_at && (
                <div style={{ fontSize: '0.65rem', color: 'var(--color-text-faint)', marginTop: '0.5rem' }}>
                  Atualizado em {new Date(assetDetail.last_price_updated_at).toLocaleDateString('pt-BR')}
                </div>
              )}
            </div>
          )}

          {/* Gráfico de preços */}
          {loadingDetail ? (
            <div style={{ height: 200, background: 'var(--color-surface-offset)', borderRadius: 'var(--radius-lg)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <span style={{ color: 'var(--color-text-muted)', fontSize: 'var(--text-xs)' }}>Carregando...</span>
            </div>
          ) : chartData.length > 0 ? (
            <div style={{ background: 'var(--color-surface-offset)', padding: '1rem', borderRadius: 'var(--radius-lg)' }}>
              <h3 style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--color-text)', margin: '0 0 1rem' }}>
                Histórico de Preços
              </h3>
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={chartData}>
                  <CartesianGrid stroke="var(--color-divider)" vertical={false} />
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 11, fill: 'var(--color-text-muted)' }}
                    interval={Math.floor(chartData.length / 5)}
                  />
                  <YAxis
                    tick={{ fontSize: 11, fill: 'var(--color-text-muted)' }}
                    width={50}
                  />
                  <Tooltip
                    contentStyle={{
                      background: 'var(--color-surface)',
                      border: '1px solid var(--color-divider)',
                      borderRadius: 'var(--radius-md)',
                    }}
                    formatter={(value: any) => formatBRL(value)}
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

          {/* Métricas KPI */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
            <div style={{
              background: 'var(--color-surface-offset)',
              padding: '0.75rem',
              borderRadius: 'var(--radius-md)',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: '0.5rem' }}>
                <DollarSign size={14} style={{ color: 'var(--color-primary)' }} />
                <span style={{ fontSize: '0.65rem', color: 'var(--color-text-muted)' }}>Preço Médio</span>
              </div>
              <div style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--color-text)' }}>
                {avgPrice > 0 ? formatBRL(avgPrice) : '—'}
              </div>
            </div>

            <div style={{
              background: 'var(--color-surface-offset)',
              padding: '0.75rem',
              borderRadius: 'var(--radius-md)',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: '0.5rem' }}>
                <Zap size={14} style={{ color: 'var(--color-primary)' }} />
                <span style={{ fontSize: '0.65rem', color: 'var(--color-text-muted)' }}>Dividendos (Total)</span>
              </div>
              <div style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--color-text)' }}>
                {totalDividends > 0 ? formatBRL(totalDividends) : '—'}
              </div>
            </div>
          </div>

          {/* Transações */}
          {transactions.length > 0 && (
            <div style={{
              background: 'var(--color-surface-offset)',
              padding: '1rem',
              borderRadius: 'var(--radius-lg)',
            }}>
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

          {/* Dividendos */}
          {assetDividends.length > 0 && (
            <div style={{
              background: 'var(--color-surface-offset)',
              padding: '1rem',
              borderRadius: 'var(--radius-lg)',
            }}>
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
                        {new Date(div.payment_date).toLocaleDateString('pt-BR')}
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
        </div>
      </div>
    </div>
  )
}
