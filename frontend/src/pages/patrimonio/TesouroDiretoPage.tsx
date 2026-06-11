import { Building2 } from 'lucide-react'

export default function TesouroDiretoPage() {
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
      <Building2 size={32} style={{ color: 'var(--color-text-faint)' }} />
      <p style={{ margin: 0, fontSize: 'var(--text-sm)', fontWeight: 500 }}>Tesouro Direto</p>
      <p style={{ margin: 0, fontSize: 'var(--text-xs)', color: 'var(--color-text-faint)', maxWidth: '32ch' }}>
        Títulos públicos com rentabilidade e taxa de mercado — em desenvolvimento.
      </p>
    </div>
  )
}
