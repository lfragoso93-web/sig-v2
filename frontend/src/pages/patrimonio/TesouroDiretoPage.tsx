import { useState } from 'react'
import { Landmark, TrendingUp, TrendingDown, Minus, Loader2, Pencil, Trash2, X, Check } from 'lucide-react'
import { usePositions } from '@/hooks/usePortfolio'
import { useAppStore } from '@/store/appStore'
import { useTreasuryMutations, TreasuryUpdatePayload } from '@/hooks/useTreasuryMutations'
import { formatTreasuryName } from '@/utils/treasury'

// ── helpers ───────────────────────────────────────────────────────────────────

const fmtBRL = (v: number | null | undefined) =>
  v == null ? '—' : v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })

const fmt = (v: number | null | undefined, dec = 2) =>
  v == null ? '—' : v.toLocaleString('pt-BR', { minimumFractionDigits: dec, maximumFractionDigits: dec })

// ── Tipos locais ─────────────────────────────────────────────────────────────────

interface EditForm {
  invested_value: string
  purchase_date: string
  maturity_date: string
  is_active: boolean
}

// ── Modal de edição ────────────────────────────────────────────────────────────────

interface EditModalProps {
  pos: any
  onClose: () => void
  onSave: (id: number, data: TreasuryUpdatePayload) => Promise<void>
  saving: boolean
}

function EditModal({ pos, onClose, onSave, saving }: EditModalProps) {
  const [form, setForm] = useState<EditForm>({
    invested_value: String(pos.average_price ?? ''),
    purchase_date: pos.purchase_date ?? '',
    maturity_date: pos.maturity_date ?? '',
    is_active: pos.is_active !== false,
  })

  const labelStyle = {
    display: 'block',
    fontSize: 'var(--text-xs)',
    color: 'var(--color-text-muted)',
    marginBottom: 'var(--space-1)',
    fontWeight: 500,
  } as React.CSSProperties

  const inputStyle = {
    width: '100%',
    padding: 'var(--space-2) var(--space-3)',
    borderRadius: 'var(--radius-md)',
    border: '1px solid var(--color-border)',
    background: 'var(--color-surface-2)',
    color: 'var(--color-text)',
    fontSize: 'var(--text-sm)',
  } as React.CSSProperties

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const payload: TreasuryUpdatePayload = {
      invested_value: parseFloat(form.invested_value.replace(',', '.')),
      purchase_date: form.purchase_date || undefined,
      maturity_date: form.maturity_date || null,
      is_active: form.is_active,
    }
    onSave(pos.id, payload)
  }

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 50,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'oklch(0 0 0 / 0.5)',
    }}>
      <div style={{
        background: 'var(--color-surface)',
        border: '1px solid var(--color-border)',
        borderRadius: 'var(--radius-xl)',
        padding: 'var(--space-6)',
        width: '100%', maxWidth: 420,
        display: 'flex', flexDirection: 'column', gap: 'var(--space-4)',
        boxShadow: 'var(--shadow-lg)',
      }}>
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <p style={{ margin: 0, fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--color-text)' }}>
              Editar Título
            </p>
            <p style={{ margin: 0, fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>
              {formatTreasuryName(pos.ticker)}
            </p>
          </div>
          <button
            onClick={onClose}
            style={{ color: 'var(--color-text-muted)', padding: 'var(--space-1)', borderRadius: 'var(--radius-sm)' }}
          >
            <X size={16} />
          </button>
        </div>

        {/* Formulário */}
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>

          <div>
            <label style={labelStyle}>Valor Investido (R$)</label>
            <input
              type="number" step="0.01" required
              value={form.invested_value}
              onChange={e => setForm(f => ({ ...f, invested_value: e.target.value }))}
              style={inputStyle}
            />
          </div>

          <div>
            <label style={labelStyle}>Data de Compra</label>
            <input
              type="date"
              value={form.purchase_date}
              onChange={e => setForm(f => ({ ...f, purchase_date: e.target.value }))}
              style={inputStyle}
            />
          </div>

          <div>
            <label style={labelStyle}>Data de Vencimento (opcional)</label>
            <input
              type="date"
              value={form.maturity_date}
              onChange={e => setForm(f => ({ ...f, maturity_date: e.target.value }))}
              style={inputStyle}
            />
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
            <input
              type="checkbox" id="is_active"
              checked={form.is_active}
              onChange={e => setForm(f => ({ ...f, is_active: e.target.checked }))}
              style={{ width: 15, height: 15 }}
            />
            <label htmlFor="is_active" style={{ fontSize: 'var(--text-sm)', color: 'var(--color-text)', cursor: 'pointer' }}>
              Título ainda ativo (não resgatado)
            </label>
          </div>

          {/* Rodapé */}
          <div style={{ display: 'flex', gap: 'var(--space-2)', justifyContent: 'flex-end', paddingTop: 'var(--space-2)' }}>
            <button
              type="button"
              onClick={onClose}
              style={{
                padding: 'var(--space-2) var(--space-4)',
                borderRadius: 'var(--radius-md)',
                fontSize: 'var(--text-sm)',
                border: '1px solid var(--color-border)',
                background: 'var(--color-surface-2)',
                color: 'var(--color-text-muted)',
                cursor: 'pointer',
              }}
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={saving}
              style={{
                padding: 'var(--space-2) var(--space-4)',
                borderRadius: 'var(--radius-md)',
                fontSize: 'var(--text-sm)',
                background: 'var(--color-primary)',
                color: '#fff',
                cursor: saving ? 'not-allowed' : 'pointer',
                opacity: saving ? 0.6 : 1,
                display: 'flex', alignItems: 'center', gap: 'var(--space-1)',
              }}
            >
              {saving
                ? <Loader2 size={13} style={{ animation: 'spin 1s linear infinite' }} />
                : <Check size={13} />}
              Salvar
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ── Componente principal ─────────────────────────────────────────────────────────────────

export default function TesouroDiretoPage() {
  const portfolioId = useAppStore(s => s.selectedPortfolioId)
  const { data: groups = [], isLoading } = usePositions(portfolioId)
  const { update, remove } = useTreasuryMutations(portfolioId ?? 0)

  const [editTarget, setEditTarget] = useState<any | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<any | null>(null)
  const [deleteConfirming, setDeleteConfirming] = useState(false)

  const group = groups.find(g => g.asset_type === 'TESOURO_DIRETO')
  const positions = group?.positions ?? []

  // ── loading ─────────────────────────────────────────────────────────────────
  if (isLoading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: 'var(--space-16)' }}>
        <Loader2 size={24} style={{ animation: 'spin 1s linear infinite', color: 'var(--color-text-muted)' }} />
        <style>{`@keyframes spin { to { transform: rotate(360deg) } }`}</style>
      </div>
    )
  }

  // ── empty state ─────────────────────────────────────────────────────────────────
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

  // ── totais ──────────────────────────────────────────────────────────────────────
  const totalInvestido = positions.reduce((s, p) => s + p.average_price * p.quantity, 0)
  const totalAtual     = group?.total_value ?? 0
  const resultado      = totalAtual - totalInvestido
  const resultadoPct   = totalInvestido > 0 ? (resultado / totalInvestido) * 100 : 0
  const positivo       = resultado >= 0

  // ── handlers ─────────────────────────────────────────────────────────────────
  const handleSave = async (id: number, data: TreasuryUpdatePayload) => {
    await update.mutateAsync({ id, data })
    setEditTarget(null)
  }

  const handleDelete = async () => {
    if (!deleteTarget) return
    setDeleteConfirming(true)
    try {
      await remove.mutateAsync(deleteTarget.id)
      setDeleteTarget(null)
    } finally {
      setDeleteConfirming(false)
    }
  }

  // ── render ────────────────────────────────────────────────────────────────────
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-5)' }}>

      {/* Cards de resumo */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 'var(--space-3)' }}>
        {[
          { label: 'Total Investido', value: fmtBRL(totalInvestido) },
          { label: 'Valor Atual',     value: fmtBRL(totalAtual) },
          {
            label: 'Resultado',
            value: `${fmtBRL(resultado)} (${fmt(resultadoPct)}%)`,
            color: positivo ? 'var(--color-success)' : 'var(--color-error)',
          },
          { label: 'Títulos', value: String(positions.length) },
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

      {/* Tabela */}
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 'var(--text-sm)' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--color-border)' }}>
              {['Título', 'Qtd', 'Preço Médio', 'Preço Atual', 'Valor Atual', 'Resultado', '% Cart.', ''].map(h => (
                <th key={h} style={{
                  padding: 'var(--space-2) var(--space-3)',
                  textAlign: h === '' ? 'right' : 'left',
                  fontWeight: 600,
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
                <tr
                  key={pos.id}
                  style={{ borderBottom: '1px solid var(--color-divider)', transition: 'background 150ms' }}
                  onMouseEnter={e => (e.currentTarget.style.background = 'var(--color-surface-offset)')}
                  onMouseLeave={e => (e.currentTarget.style.background = '')}
                >
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
                        fontSize: 'var(--text-xs)', color: 'var(--color-text-faint)',
                        paddingLeft: 21, fontFamily: 'monospace', letterSpacing: '0.02em',
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
                      color: isZero ? 'var(--color-text-muted)' : isPos ? 'var(--color-success)' : 'var(--color-error)',
                    }}>
                      {isZero ? <Minus size={12} /> : isPos ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
                      {isZero ? '—' : `${fmtBRL(res)} (${fmt(resPct)}%)`}
                    </span>
                  </td>
                  {/* % Cart. */}
                  <td style={{ padding: 'var(--space-2) var(--space-3)', color: 'var(--color-text-muted)', fontVariantNumeric: 'tabular-nums' }}>
                    {fmt(pos.portfolio_percent)}%
                  </td>
                  {/* Ações */}
                  <td style={{ padding: 'var(--space-2) var(--space-3)', textAlign: 'right', whiteSpace: 'nowrap' }}>
                    <button
                      onClick={() => setEditTarget(pos)}
                      title="Editar"
                      style={{
                        padding: 'var(--space-1)',
                        borderRadius: 'var(--radius-sm)',
                        color: 'var(--color-text-muted)',
                        marginRight: 'var(--space-1)',
                        transition: 'color 150ms',
                      }}
                      onMouseEnter={e => (e.currentTarget.style.color = 'var(--color-primary)')}
                      onMouseLeave={e => (e.currentTarget.style.color = 'var(--color-text-muted)')}
                    >
                      <Pencil size={14} />
                    </button>
                    <button
                      onClick={() => setDeleteTarget(pos)}
                      title="Excluir"
                      style={{
                        padding: 'var(--space-1)',
                        borderRadius: 'var(--radius-sm)',
                        color: 'var(--color-text-muted)',
                        transition: 'color 150ms',
                      }}
                      onMouseEnter={e => (e.currentTarget.style.color = 'var(--color-error)')}
                      onMouseLeave={e => (e.currentTarget.style.color = 'var(--color-text-muted)')}
                    >
                      <Trash2 size={14} />
                    </button>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* Modal de edição */}
      {editTarget && (
        <EditModal
          pos={editTarget}
          onClose={() => setEditTarget(null)}
          onSave={handleSave}
          saving={update.isPending}
        />
      )}

      {/* Confirmação de exclusão */}
      {deleteTarget && (
        <div style={{
          position: 'fixed', inset: 0, zIndex: 50,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          background: 'oklch(0 0 0 / 0.5)',
        }}>
          <div style={{
            background: 'var(--color-surface)',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius-xl)',
            padding: 'var(--space-6)',
            width: '100%', maxWidth: 360,
            display: 'flex', flexDirection: 'column', gap: 'var(--space-4)',
            boxShadow: 'var(--shadow-lg)',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
              <div style={{
                width: 36, height: 36, borderRadius: 'var(--radius-full)',
                background: 'var(--color-error-highlight)',
                display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
              }}>
                <Trash2 size={16} style={{ color: 'var(--color-error)' }} />
              </div>
              <div>
                <p style={{ margin: 0, fontWeight: 600, fontSize: 'var(--text-sm)', color: 'var(--color-text)' }}>
                  Excluir título?
                </p>
                <p style={{ margin: 0, fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>
                  {formatTreasuryName(deleteTarget.ticker)}
                </p>
              </div>
            </div>
            <p style={{ margin: 0, fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>
              Esta ação não pode ser desfeita. O registro será permanentemente removido.
            </p>
            <div style={{ display: 'flex', gap: 'var(--space-2)', justifyContent: 'flex-end' }}>
              <button
                onClick={() => setDeleteTarget(null)}
                disabled={deleteConfirming}
                style={{
                  padding: 'var(--space-2) var(--space-4)',
                  borderRadius: 'var(--radius-md)',
                  fontSize: 'var(--text-sm)',
                  border: '1px solid var(--color-border)',
                  background: 'var(--color-surface-2)',
                  color: 'var(--color-text-muted)',
                  cursor: 'pointer',
                }}
              >
                Cancelar
              </button>
              <button
                onClick={handleDelete}
                disabled={deleteConfirming}
                style={{
                  padding: 'var(--space-2) var(--space-4)',
                  borderRadius: 'var(--radius-md)',
                  fontSize: 'var(--text-sm)',
                  background: 'var(--color-error)',
                  color: '#fff',
                  cursor: deleteConfirming ? 'not-allowed' : 'pointer',
                  opacity: deleteConfirming ? 0.6 : 1,
                  display: 'flex', alignItems: 'center', gap: 'var(--space-1)',
                }}
              >
                {deleteConfirming
                  ? <Loader2 size={13} style={{ animation: 'spin 1s linear infinite' }} />
                  : <Trash2 size={13} />}
                Excluir
              </button>
            </div>
          </div>
        </div>
      )}

      <style>{`@keyframes spin { to { transform: rotate(360deg) } }`}</style>
    </div>
  )
}
