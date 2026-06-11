import { useState } from 'react'
import { Plus, Pencil, Trash2, TrendingUp, TrendingDown, Minus, Loader2 } from 'lucide-react'
import {
  useTreasury,
  useCreateTreasury,
  useUpdateTreasury,
  useDeleteTreasury,
  TreasuryInvestment,
  TreasuryCreatePayload,
} from '@/hooks/useTreasury'
import { useTesouroSearch } from '@/hooks/useTesouroSearch'

// ── helpers ─────────────────────────────────────────────────────

const fmt = (v: number | null | undefined, decimals = 2) =>
  v == null ? '—' : v.toLocaleString('pt-BR', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })

const fmtBRL = (v: number | null | undefined) =>
  v == null ? '—' : v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })

const fmtDate = (s: string | null | undefined) =>
  s ? new Date(s + 'T00:00:00').toLocaleDateString('pt-BR') : '—'

const today = () => new Date().toISOString().slice(0, 10)

// ── tipos internos ───────────────────────────────────────────────

interface FormState {
  brapi_name: string
  invested_value: string
  purchase_date: string
  maturity_date: string
  is_active: boolean
}

const emptyForm = (): FormState => ({
  brapi_name: '',
  invested_value: '',
  purchase_date: today(),
  maturity_date: '',
  is_active: true,
})

function toPayload(f: FormState): TreasuryCreatePayload {
  return {
    brapi_name: f.brapi_name,
    invested_value: parseFloat(f.invested_value),
    purchase_date: f.purchase_date,
    maturity_date: f.maturity_date || null,
    is_active: f.is_active,
  }
}

// ── Props ───────────────────────────────────────────────────────

interface Props {
  portfolioId: number
}

// ── Componente principal ───────────────────────────────────────────

export default function TesouroDiretoPage({ portfolioId }: Props) {
  const { data: investments = [], isLoading } = useTreasury(portfolioId)
  const createMut = useCreateTreasury(portfolioId)
  const updateMut = useUpdateTreasury(portfolioId)
  const deleteMut = useDeleteTreasury(portfolioId)

  // modal state
  const [showModal, setShowModal] = useState(false)
  const [editItem,  setEditItem]  = useState<TreasuryInvestment | null>(null)
  const [form,      setForm]      = useState<FormState>(emptyForm())
  const [formError, setFormError] = useState('')

  // autocomplete: query separada para controlar o hook
  const [tesouroQuery, setTesouroQuery] = useState('')
  const [showSugg,     setShowSugg]     = useState(false)
  const { items: tesouroItems } = useTesouroSearch(tesouroQuery, showModal)

  // confirm delete
  const [deleteTarget, setDeleteTarget] = useState<TreasuryInvestment | null>(null)

  // ── handlers modal ───────────────────────────────────────────

  function openCreate() {
    setEditItem(null)
    setForm(emptyForm())
    setFormError('')
    setTesouroQuery('')
    setShowSugg(false)
    setShowModal(true)
  }

  function openEdit(item: TreasuryInvestment) {
    setEditItem(item)
    setForm({
      brapi_name:     item.brapi_name,
      invested_value: String(item.invested_value),
      purchase_date:  item.purchase_date,
      maturity_date:  item.maturity_date ?? '',
      is_active:      item.is_active,
    })
    setFormError('')
    setTesouroQuery('')
    setShowSugg(false)
    setShowModal(true)
  }

  function closeModal() {
    setShowModal(false)
    setEditItem(null)
    setFormError('')
    setTesouroQuery('')
    setShowSugg(false)
  }

  function setField<K extends keyof FormState>(k: K, v: FormState[K]) {
    setForm(f => ({ ...f, [k]: v }))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setFormError('')
    const val = parseFloat(form.invested_value)
    if (!form.brapi_name.trim()) return setFormError('Informe o título.')
    if (isNaN(val) || val <= 0)  return setFormError('Valor investido deve ser positivo.')
    if (!form.purchase_date)      return setFormError('Informe a data de compra.')
    try {
      if (editItem) {
        await updateMut.mutateAsync({ id: editItem.id, data: toPayload(form) })
      } else {
        await createMut.mutateAsync(toPayload(form))
      }
      closeModal()
    } catch {
      setFormError('Erro ao salvar. Verifique os dados e tente novamente.')
    }
  }

  async function handleDelete() {
    if (!deleteTarget) return
    await deleteMut.mutateAsync(deleteTarget.id)
    setDeleteTarget(null)
  }

  // ── render ────────────────────────────────────────────────────

  const isMutating = createMut.isPending || updateMut.isPending

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <h3 style={{ margin: 0, fontSize: 'var(--text-base)', fontWeight: 600, color: 'var(--color-text)' }}>
          Tesouro Direto
        </h3>
        <button onClick={openCreate} style={btnPrimary}>
          <Plus size={15} /> Adicionar
        </button>
      </div>

      {/* Tabela */}
      {isLoading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 'var(--space-12)' }}>
          <Loader2 size={24} style={{ animation: 'spin 1s linear infinite', color: 'var(--color-text-muted)' }} />
        </div>
      ) : investments.length === 0 ? (
        <div style={{
          textAlign: 'center', padding: 'var(--space-12) var(--space-8)',
          color: 'var(--color-text-muted)', fontSize: 'var(--text-sm)',
          border: '1px dashed var(--color-border)', borderRadius: 'var(--radius-lg)',
        }}>
          Nenhum título cadastrado. Clique em “Adicionar” para começar.
        </div>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 'var(--text-sm)' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--color-border)' }}>
                {['Título','Compra','Vencimento','Valor Invest.','Preço Atual','Valor Atual','Resultado','Status',''].map(h => (
                  <th key={h} style={{
                    padding: 'var(--space-2) var(--space-3)',
                    textAlign: h === '' ? 'center' : 'left',
                    fontWeight: 600, color: 'var(--color-text-muted)',
                    fontSize: 'var(--text-xs)', whiteSpace: 'nowrap',
                  }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {investments.map(inv => {
                const positivo = (inv.lucro_prejuizo ?? 0) >= 0
                const neutro   = inv.lucro_prejuizo == null
                return (
                  <tr key={inv.id} style={{ borderBottom: '1px solid var(--color-divider)' }}>
                    <td style={{ padding: 'var(--space-2) var(--space-3)', fontWeight: 500, color: 'var(--color-text)' }}>
                      {inv.brapi_name}
                    </td>
                    <td style={{ padding: 'var(--space-2) var(--space-3)', color: 'var(--color-text-muted)' }}>
                      {fmtDate(inv.purchase_date)}
                    </td>
                    <td style={{ padding: 'var(--space-2) var(--space-3)', color: 'var(--color-text-muted)' }}>
                      {fmtDate(inv.maturity_date)}
                    </td>
                    <td style={{ padding: 'var(--space-2) var(--space-3)', fontVariantNumeric: 'tabular-nums' }}>
                      {fmtBRL(inv.invested_value)}
                    </td>
                    <td style={{ padding: 'var(--space-2) var(--space-3)', fontVariantNumeric: 'tabular-nums', color: 'var(--color-text-muted)' }}>
                      {fmtBRL(inv.current_price)}
                    </td>
                    <td style={{ padding: 'var(--space-2) var(--space-3)', fontVariantNumeric: 'tabular-nums', fontWeight: 500 }}>
                      {fmtBRL(inv.valor_atual)}
                    </td>
                    <td style={{ padding: 'var(--space-2) var(--space-3)' }}>
                      <span style={{
                        display: 'inline-flex', alignItems: 'center', gap: 'var(--space-1)',
                        color: neutro ? 'var(--color-text-muted)' : positivo ? 'var(--color-success)' : 'var(--color-error)',
                        fontVariantNumeric: 'tabular-nums',
                      }}>
                        {neutro ? <Minus size={12} /> : positivo ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
                        {neutro ? '—' : `${fmtBRL(inv.lucro_prejuizo)} (${fmt(inv.rentabilidade_pct)}%)`}
                      </span>
                    </td>
                    <td style={{ padding: 'var(--space-2) var(--space-3)' }}>
                      <span style={{
                        display: 'inline-block',
                        padding: '2px var(--space-2)',
                        borderRadius: 'var(--radius-full)',
                        fontSize: 'var(--text-xs)',
                        background: inv.is_active ? 'var(--color-success-highlight)' : 'var(--color-surface-offset)',
                        color: inv.is_active ? 'var(--color-success)' : 'var(--color-text-muted)',
                        fontWeight: 500,
                      }}>
                        {inv.is_active ? 'Ativo' : 'Encerrado'}
                      </span>
                    </td>
                    <td style={{ padding: 'var(--space-2) var(--space-3)' }}>
                      <div style={{ display: 'flex', gap: 'var(--space-1)' }}>
                        <button onClick={() => openEdit(inv)} title="Editar" style={iconBtn}>
                          <Pencil size={15} />
                        </button>
                        <button onClick={() => setDeleteTarget(inv)} title="Excluir"
                          style={{ ...iconBtn, color: 'var(--color-error)' }}>
                          <Trash2 size={15} />
                        </button>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* ===== Modal Cadastro / Edição ===== */}
      {showModal && (
        <div
          style={overlayStyle}
          onClick={e => { if (e.target === e.currentTarget) closeModal() }}
        >
          <div style={modalStyle}>
            <h2 style={{ margin: '0 0 var(--space-4)', fontSize: 'var(--text-base)', fontWeight: 600 }}>
              {editItem ? 'Editar Título' : 'Adicionar Título'}
            </h2>

            <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>

              {/* brapi_name autocomplete */}
              <div style={{ position: 'relative' }}>
                <label style={labelStyle}>Título</label>
                <input
                  type="text"
                  value={form.brapi_name}
                  onChange={e => {
                    setField('brapi_name', e.target.value)
                    setTesouroQuery(e.target.value)
                    setShowSugg(true)
                  }}
                  onBlur={() => setTimeout(() => setShowSugg(false), 150)}
                  placeholder="Ex: TESOURO SELIC 2029"
                  required
                  style={inputStyle}
                />
                {showSugg && tesouroItems.length > 0 && (
                  <ul style={{
                    position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 10,
                    background: 'var(--color-surface-2)',
                    border: '1px solid var(--color-border)',
                    borderRadius: 'var(--radius-md)',
                    listStyle: 'none', margin: 0, padding: 'var(--space-1)',
                    maxHeight: 200, overflowY: 'auto',
                    boxShadow: 'var(--shadow-md)',
                  }}>
                    {tesouroItems.map(item => (
                      <li
                        key={item.ticker}
                        onMouseDown={() => {
                          setField('brapi_name', item.name)
                          if (item.maturity_date) setField('maturity_date', item.maturity_date.slice(0, 10))
                          setTesouroQuery('')
                          setShowSugg(false)
                        }}
                        style={{
                          padding: 'var(--space-2) var(--space-3)',
                          cursor: 'pointer',
                          borderRadius: 'var(--radius-sm)',
                          fontSize: 'var(--text-xs)',
                          color: 'var(--color-text)',
                        }}
                      >
                        <span style={{ fontWeight: 500 }}>{item.name}</span>
                        {item.maturity_date && (
                          <span style={{ color: 'var(--color-text-muted)', marginLeft: 'var(--space-2)' }}>
                            venc. {fmtDate(item.maturity_date)}
                          </span>
                        )}
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              {/* valor investido */}
              <div>
                <label style={labelStyle}>Valor Investido (R$)</label>
                <input
                  type="number" step="0.01" min="0.01"
                  value={form.invested_value}
                  onChange={e => setField('invested_value', e.target.value)}
                  placeholder="1000.00"
                  required
                  style={inputStyle}
                />
              </div>

              {/* datas */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-3)' }}>
                <div>
                  <label style={labelStyle}>Data de Compra</label>
                  <input type="date" value={form.purchase_date}
                    onChange={e => setField('purchase_date', e.target.value)}
                    required style={inputStyle} />
                </div>
                <div>
                  <label style={labelStyle}>Vencimento (opcional)</label>
                  <input type="date" value={form.maturity_date}
                    onChange={e => setField('maturity_date', e.target.value)}
                    style={inputStyle} />
                </div>
              </div>

              {/* is_active */}
              <label style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', fontSize: 'var(--text-sm)', cursor: 'pointer' }}>
                <input type="checkbox" checked={form.is_active}
                  onChange={e => setField('is_active', e.target.checked)} />
                Investimento ativo
              </label>

              {formError && (
                <p style={{ margin: 0, fontSize: 'var(--text-xs)', color: 'var(--color-error)' }}>{formError}</p>
              )}

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 'var(--space-2)', marginTop: 'var(--space-2)' }}>
                <button type="button" onClick={closeModal} style={btnSecondary}>Cancelar</button>
                <button type="submit" disabled={isMutating} style={btnPrimary}>
                  {isMutating && <Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} />}
                  {editItem ? 'Salvar' : 'Adicionar'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ===== Modal Confirmação Exclusão ===== */}
      {deleteTarget && (
        <div
          style={overlayStyle}
          onClick={e => { if (e.target === e.currentTarget) setDeleteTarget(null) }}
        >
          <div style={{ ...modalStyle, maxWidth: 400 }}>
            <h2 style={{ margin: '0 0 var(--space-2)', fontSize: 'var(--text-base)', fontWeight: 600 }}>
              Excluir Título
            </h2>
            <p style={{ margin: '0 0 var(--space-4)', fontSize: 'var(--text-sm)', color: 'var(--color-text-muted)' }}>
              Deseja remover <strong>{deleteTarget.brapi_name}</strong>? Esta ação não pode ser desfeita.
            </p>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 'var(--space-2)' }}>
              <button onClick={() => setDeleteTarget(null)} style={btnSecondary}>Cancelar</button>
              <button onClick={handleDelete} disabled={deleteMut.isPending}
                style={{ ...btnPrimary, background: 'var(--color-error)' }}>
                {deleteMut.isPending && <Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} />}
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

// ── estilos ──────────────────────────────────────────────────────────

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: 'var(--space-2) var(--space-3)',
  border: '1px solid var(--color-border)',
  borderRadius: 'var(--radius-md)',
  background: 'var(--color-bg)',
  color: 'var(--color-text)',
  fontSize: 'var(--text-sm)',
}

const labelStyle: React.CSSProperties = {
  display: 'block',
  fontSize: 'var(--text-xs)',
  fontWeight: 500,
  color: 'var(--color-text-muted)',
  marginBottom: 'var(--space-1)',
}

const btnPrimary: React.CSSProperties = {
  display: 'inline-flex', alignItems: 'center', gap: 'var(--space-1)',
  padding: 'var(--space-2) var(--space-4)',
  background: 'var(--color-primary)', color: '#fff',
  border: 'none', borderRadius: 'var(--radius-md)',
  fontSize: 'var(--text-sm)', fontWeight: 500, cursor: 'pointer',
}

const btnSecondary: React.CSSProperties = {
  display: 'inline-flex', alignItems: 'center', gap: 'var(--space-1)',
  padding: 'var(--space-2) var(--space-4)',
  background: 'var(--color-surface-offset)', color: 'var(--color-text)',
  border: '1px solid var(--color-border)', borderRadius: 'var(--radius-md)',
  fontSize: 'var(--text-sm)', fontWeight: 500, cursor: 'pointer',
}

const iconBtn: React.CSSProperties = {
  background: 'none', border: 'none', cursor: 'pointer',
  color: 'var(--color-text-muted)', padding: 'var(--space-1)',
  borderRadius: 'var(--radius-sm)',
}

const overlayStyle: React.CSSProperties = {
  position: 'fixed', inset: 0, zIndex: 50,
  background: 'oklch(0 0 0 / 0.45)',
  display: 'flex', alignItems: 'center', justifyContent: 'center',
  padding: 'var(--space-4)',
}

const modalStyle: React.CSSProperties = {
  background: 'var(--color-surface)',
  borderRadius: 'var(--radius-xl)',
  padding: 'var(--space-6)',
  width: '100%', maxWidth: 480,
  boxShadow: 'var(--shadow-lg)',
}
