import type { LucideIcon } from 'lucide-react'

interface Props {
  icon: LucideIcon
  title: string
  description: string
  action?: {
    label: string
    onClick: () => void
  }
}

export default function EmptyState({ icon: Icon, title, description, action }: Props) {
  return (
    <div
      style={{
        display:        'flex',
        flexDirection:  'column',
        alignItems:     'center',
        justifyContent: 'center',
        textAlign:      'center',
        padding:        '4rem 1.5rem',
        gap:            '0.75rem',
      }}
    >
      {/* Ícone */}
      <div
        style={{
          width:           48,
          height:          48,
          borderRadius:    'var(--radius-xl)',
          background:      'oklch(from var(--color-primary) l c h / 0.1)',
          display:         'flex',
          alignItems:      'center',
          justifyContent:  'center',
          flexShrink:      0,
        }}
      >
        <Icon size={22} style={{ color: 'var(--color-primary)' }} />
      </div>

      {/* Texto */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', maxWidth: 320 }}>
        <p style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--color-text)', margin: 0 }}>
          {title}
        </p>
        <p style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', margin: 0, lineHeight: 1.5 }}>
          {description}
        </p>
      </div>

      {/* Botão de ação opcional */}
      {action && (
        <button
          onClick={action.onClick}
          style={{
            marginTop:    '0.5rem',
            padding:      '0.5rem 1.25rem',
            borderRadius: 'var(--radius-md)',
            border:       'none',
            background:   'var(--color-primary)',
            color:        'var(--color-text-inverse)',
            fontSize:     'var(--text-sm)',
            fontWeight:   600,
            cursor:       'pointer',
            transition:   'opacity 150ms ease',
          }}
          onMouseEnter={e => (e.currentTarget.style.opacity = '0.85')}
          onMouseLeave={e => (e.currentTarget.style.opacity = '1')}
        >
          {action.label}
        </button>
      )}
    </div>
  )
}
