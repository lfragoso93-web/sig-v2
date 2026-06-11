import { Landmark, TrendingUp, TrendingDown, Minus, Loader2 } from 'lucide-react'
import { usePositions } from '@/hooks/usePortfolio'
import { useAppStore } from '@/store/appStore'
import { formatTreasuryName } from '@/utils/treasury'

// ── helpers ──────────────────────────────────────────────────────────────────

const fmtBRL = (v: number | null | undefined) =>
  v == null ? '—' : v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })

const fmt = (v: number | null | undefined, dec = 2) =>
  v == null ? '—' : v.toLocaleString('pt-BR', { minimumFractionDigits: dec, maximumFractionDigits: dec })

// ── Componente ────────────────────────────────────────────────────────────────

export default function TesouroDiretoPage() {
  const portfolioId = useAppStore(s => s.selectedPortfolioId)
  const { data: groups = [], isLoading } = usePositions(portfolioId)

  const group = groups.find(g => g.asset_type === 'TESOURO_DIRETO')
  const positions = group?.positions ?? []

  // ── loading ────────────────────────────────────────────────────────────────
  if (isLoading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: 'var(--space-16)' }}>
        <Loader2 size={24} style={{ animation: 'spin 1s linear infinite', color: 'var(--color-text-muted)' }} />
        <style>{`@keyframes spin { to { transform: rotate(360deg) } }`}</style>
      </div>
    )
  }

  // ── empty state ────────────────────────────────────────────────────────────
  if (positions.length === 0) {
    return (
      <div style={{
        display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
        gap: 'var(--space-3)', padding: 'var(--space-16) var(--space-8)',
        border: '1px dashed var(--color-border)', borderRadius: 'var(--radius-lg)',
        color: 'var(--color-text-muted)', textAlign: 'center',
      }}>
        <Landmark size={32} style={{ color: 'var(--color-text-faint)' }} />
        <p style={{ margin: 0, fontSize: 'var(--text-sm)', fontWeight: 500 }}>
          Nenhum título cadastrado.
        </p>
        <p style={{ margin: 0, fontSize: 'var(--text-xs)', color: 'var(--color-text-faint)', maxWidth: '36ch' }}>
          Clique em <strong>+ Novo Lançamento</strong> no topo, selecione a aba <strong>Tesouro</strong> e registre sua compra.
        </p>
      </div>
    )
  }

  // ── resumo do grupo ────────────────────────────────────────────────────────
  const totalInvestido = positions.reduce((s, p) => s + p.average_price * p.quantity, 0)
  const totalAtual     = group?.total_value ?? 0
  const resultado      = totalAtual - totalInvestido
  const resultadoPct   = totalInvestido > 0 ? (resultado / totalInvestido) * 100 : 0
  const positivo       = resultado >= 0

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-5)' }}>

      {/* Cards de resumo */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 'var(--space-3)' }}>
        {[
          { label: 'Total Investido',  value: fmtBRL(totalInvestido) },
          { label: 'Valor Atual',      value: fmtBRL(totalAtual) },
          {
            label: 'Resultado',
            value: `${fmtBRL(resultado)} (${fmt(resultadoPct)}%)`,
            color: positivo ? 'var(--color-success)' : 'var(--color-error)',
          },
          { label: 'Títulos',          value: String(positions.length) },
        ].map(card => (
          <div key={card.label} style={{
            background: 'var(--color-surface)',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius-lg)',
            padding: 'var(--space-4)',
          }}>
            <p style={{ margin: '0 0 var(--space-1)', fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>
              {card.label}
            </p>
            <p style={{
              margin: 0, fontSize: 'var(--text-base)', fontWeight: 600,
              color: card.color ?? 'var(--color-text)',
              fontVariantNumeric: 'tabular-nums',
            }}>
              {card.value}
            </p>
          </div>
        ))}
      </div>

      {/* Tabela de posições */}
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 'var(--text-sm)' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--color-border)' }}>
              {['Título', 'Qtd', 'Preço Médio', 'Preço Atual', 'Valor Atual', 'Resultado', '% Cart.'].map(h => (
                <th key={h} style={{
                  padding: 'var(--space-2) var(--space-3)',
                  textAlign: 'left', fontWeight: 600,
                  color: 'var(--color-text-muted)',
                  fontSize: 'var(--text-xs)', whiteSpace: 'nowrap',
                }}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {positions.map(pos => {
              const res     = pos.variation_value
              const resPct  = pos.variation_percent
              const isPos   = res >= 0
              const isZero  = res === 0
              const name    = formatTreasuryName(pos.ticker)

              return (
                <tr key={pos.id} style={{ borderBottom: '1px solid var(--color-divider)' }}>
                  {/* Título */}
                  <td style={{ padding: 'var(--space-2) var(--space-3)', fontWeight: 500, color: 'var(--color-text)' }}>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
                        <Landmark size={13} style={{ color: 'var(--color-text-faint)', flexShrink: 0 }} />
                        <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: 240 }}>
                          {name}
                        </span>
                      </div>
                      <span style={{
                        fontSize: 'var(--text-xs)',
                        color: 'var(--color-text-faint)',
                        paddingLeft: 21,
                        fontFamily: 'monospace',
                        letterSpacing: '0.02em',
                      }}>
                        {pos.ticker}
                      </span>
                    </div>
                  </td>
                  {/* Qtd */}
                  <td style={{ padding: 'var(--space-2) var(--space-3)', fontVariantNumeric: 'tabular-nums', color: 'var(--color-text-muted)' }}>
                    {fmt(pos.quantity, 0)}
                  </td>
                  {/* Preço Médio */}
                  <td style={{ padding: 'var(--space-2) var(--space-3)', fontVariantNumeric: 'tabular-nums' }}>
                    {fmtBRL(pos.average_price)}
                  </td>
                  {/* Preço Atual */}
                  <td style={{ padding: 'var(--space-2) var(--space-3)', fontVariantNumeric: 'tabular-nums', color: 'var(--color-text-muted)' }}>
                    {pos.current_price === pos.average_price ? '—' : fmtBRL(pos.current_price)}
                  </td>
                  {/* Valor Atual */}
                  <td style={{ padding: 'var(--space-2) var(--space-3)', fontWeight: 500, fontVariantNumeric: 'tabular-nums' }}>
                    {fmtBRL(pos.current_value)}
                  </td>
                  {/* Resultado */}
                  <td style={{ padding: 'var(--space-2) var(--space-3)' }}>
                    <span style={{
                      display: 'inline-flex', alignItems: 'center', gap: 'var(--space-1)',
                      fontVariantNumeric: 'tabular-nums',
                      color: isZero
                        ? 'var(--color-text-muted)'
                        : isPos
                          ? 'var(--color-success)'
                          : 'var(--color-error)',
                    }}>
                      {isZero
                        ? <Minus size={12} />
                        : isPos
                          ? <TrendingUp size={12} />
                          : <TrendingDown size={12} />}
                      {isZero ? '—' : `${fmtBRL(res)} (${fmt(resPct)}%)`}
                    </span>
                  </td>
                  {/* % Carteira */}
                  <td style={{ padding: 'var(--space-2) var(--space-3)', color: 'var(--color-text-muted)', fontVariantNumeric: 'tabular-nums' }}>
                    {fmt(pos.portfolio_percent)}%
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      <style>{`@keyframes spin { to { transform: rotate(360deg) } }`}</style>
    </div>
  )
}
