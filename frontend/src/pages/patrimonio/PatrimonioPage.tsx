import { NavLink, Outlet, useMatch } from 'react-router-dom'
import { TrendingDown, Building2, Banknote, Wallet } from 'lucide-react'

const TABS = [
  { to: 'renda-variavel', icon: TrendingDown, label: 'Renda Variável' },
  { to: 'tesouro',        icon: Building2,    label: 'Tesouro Direto' },
  { to: 'renda-fixa',     icon: Banknote,     label: 'Renda Fixa'     },
]

export default function PatrimonioPage() {
  // Se estiver exatamente em /carteira/patrimonio (sem subitem), mostra visão consolidada
  const isRoot = useMatch('/carteira/patrimonio')

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-6)', padding: 'var(--space-6)' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
        <Wallet size={20} style={{ color: 'var(--color-primary)' }} />
        <h1 style={{ fontSize: 'var(--text-xl)', fontWeight: 700, color: 'var(--color-text)', margin: 0 }}>
          Patrimônio
        </h1>
      </div>

      {/* Tabs de navegação para subrotas */}
      <div
        style={{
          display: 'flex',
          gap: 'var(--space-1)',
          borderBottom: '1px solid var(--color-divider)',
          paddingBottom: 0,
        }}
      >
        {TABS.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            style={({ isActive }) => ({
              display: 'flex',
              alignItems: 'center',
              gap: 'var(--space-2)',
              padding: 'var(--space-2) var(--space-4)',
              fontSize: 'var(--text-sm)',
              fontWeight: isActive ? 600 : 400,
              color: isActive ? 'var(--color-primary)' : 'var(--color-text-muted)',
              borderBottom: isActive ? '2px solid var(--color-primary)' : '2px solid transparent',
              marginBottom: '-1px',
              textDecoration: 'none',
              transition: 'color var(--transition-interactive)',
              whiteSpace: 'nowrap',
            })}
          >
            <Icon size={14} />
            {label}
          </NavLink>
        ))}
      </div>

      {/* Conteúdo: visão consolidada quando na raiz, subpágina quando em subitem */}
      {isRoot ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-8)' }}>
          {/* Placeholder visão consolidada — será implementada no Sprint 1 */}
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
            <Wallet size={32} style={{ color: 'var(--color-text-faint)' }} />
            <p style={{ margin: 0, fontSize: 'var(--text-sm)', fontWeight: 500 }}>
              Visão consolidada em desenvolvimento
            </p>
            <p style={{ margin: 0, fontSize: 'var(--text-xs)', color: 'var(--color-text-faint)', maxWidth: '32ch' }}>
              Selecione uma categoria acima ou aguarde a implementação completa.
            </p>
          </div>
        </div>
      ) : (
        <Outlet />
      )}
    </div>
  )
}
