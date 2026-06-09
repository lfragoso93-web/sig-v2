import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { User, ChevronDown, LogOut, Settings } from 'lucide-react'
import { useAuthStore } from '@/store/authStore'

export default function UserMenu() {
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  // Fecha ao clicar fora
  useEffect(() => {
    function handler(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  function handleLogout() {
    logout()
    navigate('/login')
  }

  if (!user) return null

  // Iniciais do nome
  const initials = user.name
    .split(' ')
    .slice(0, 2)
    .map(w => w[0].toUpperCase())
    .join('')

  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 'var(--space-2)',
          padding: 'var(--space-1) var(--space-2)',
          borderRadius: 'var(--radius-md)',
          border: '1px solid var(--color-border)',
          background: open ? 'var(--color-surface-offset)' : 'transparent',
          cursor: 'pointer',
          transition: 'background var(--transition-interactive)',
        }}
        aria-label="Menu do usuário"
        aria-expanded={open}
      >
        {/* Avatar */}
        <div
          style={{
            width: '28px',
            height: '28px',
            borderRadius: 'var(--radius-full)',
            background: 'oklch(from var(--color-primary) l c h / 0.15)',
            color: 'var(--color-primary)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '11px',
            fontWeight: 700,
            flexShrink: 0,
          }}
        >
          {initials}
        </div>

        <div style={{ textAlign: 'left', lineHeight: 1.2 }}>
          <p style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--color-text)', margin: 0, maxWidth: '120px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {user.name}
          </p>
          <p style={{ fontSize: '10px', color: 'var(--color-text-muted)', margin: 0, maxWidth: '120px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {user.email}
          </p>
        </div>

        <ChevronDown
          size={12}
          style={{
            color: 'var(--color-text-muted)',
            transition: 'transform var(--transition-interactive)',
            transform: open ? 'rotate(180deg)' : 'rotate(0deg)',
            flexShrink: 0,
          }}
        />
      </button>

      {/* Dropdown */}
      {open && (
        <div
          style={{
            position: 'absolute',
            top: 'calc(100% + var(--space-2))',
            right: 0,
            minWidth: '200px',
            background: 'var(--color-surface)',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius-lg)',
            boxShadow: 'var(--shadow-lg)',
            overflow: 'hidden',
            zIndex: 100,
          }}
        >
          {/* Header info */}
          <div
            style={{
              padding: 'var(--space-3) var(--space-4)',
              borderBottom: '1px solid var(--color-divider)',
              background: 'var(--color-surface-offset)',
            }}
          >
            <p style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--color-text)', margin: 0 }}>
              {user.name}
            </p>
            <p style={{ fontSize: '11px', color: 'var(--color-text-muted)', margin: 0, marginTop: '2px' }}>
              {user.email}
            </p>
          </div>

          {/* Opções */}
          <div style={{ padding: 'var(--space-1)' }}>
            <button
              onClick={() => { setOpen(false); navigate('/app/configuracoes') }}
              style={{
                width: '100%',
                display: 'flex',
                alignItems: 'center',
                gap: 'var(--space-3)',
                padding: 'var(--space-2) var(--space-3)',
                borderRadius: 'var(--radius-md)',
                border: 'none',
                background: 'transparent',
                color: 'var(--color-text)',
                fontSize: 'var(--text-xs)',
                cursor: 'pointer',
                textAlign: 'left',
                transition: 'background var(--transition-interactive)',
              }}
              onMouseEnter={e => (e.currentTarget.style.background = 'var(--color-surface-offset)')}
              onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
            >
              <Settings size={14} style={{ color: 'var(--color-text-muted)', flexShrink: 0 }} />
              Configurações
            </button>

            <div style={{ height: '1px', background: 'var(--color-divider)', margin: 'var(--space-1) 0' }} />

            <button
              onClick={handleLogout}
              style={{
                width: '100%',
                display: 'flex',
                alignItems: 'center',
                gap: 'var(--space-3)',
                padding: 'var(--space-2) var(--space-3)',
                borderRadius: 'var(--radius-md)',
                border: 'none',
                background: 'transparent',
                color: 'var(--color-notification)',
                fontSize: 'var(--text-xs)',
                fontWeight: 500,
                cursor: 'pointer',
                textAlign: 'left',
                transition: 'background var(--transition-interactive)',
              }}
              onMouseEnter={e => (e.currentTarget.style.background = 'var(--color-notification-highlight)')}
              onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
            >
              <LogOut size={14} style={{ flexShrink: 0 }} />
              Sair
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
