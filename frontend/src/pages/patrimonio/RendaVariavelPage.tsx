import { TrendingDown } from 'lucide-react'

export default function RendaVariavelPage() {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 'var(--space-16)',
        borderRadius: 'var(--radius-lg)',
        border: '1px dashed var(--color-border)',
        color: 'var(--color-text-muted)',
        gap: 'var(--space-3)',
        textAlign: 'center',
      }}
    >
      <TrendingDown size={32} style={{ color: 'var(--color-text-faint)' }} />
      <p style={{ margin: 0, fontSize: 'var(--text-sm)', fontWeight: 500 }}>Renda Variável</p>
      <p style={{ margin: 0, fontSize: 'var(--text-xs)', color: 'var(--color-text-faint)', maxWidth: '32ch' }}>
        Ações, FIIs, ETFs, BDRs e cripto — em desenvolvimento.
      </p>
    </div>
  )
}
