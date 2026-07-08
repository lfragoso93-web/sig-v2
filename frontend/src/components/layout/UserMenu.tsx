import { useState, useRef, useEffect } from 'react'
import { ChevronDown, FileUp, LogOut, Settings } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import { useAppStore } from '@/store/appStore'
import ImportCSVModal from '@/components/modals/ImportCSVModal'

export default function UserMenu() {
  const { user, logout } = useAuthStore()
  const selectedPortfolioId = useAppStore(s => s.selectedPortfolioId)
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const [showImport, setShowImport] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handler(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  function handleLogout() {
    logout()
    navigate('/')
  }

  if (!user) return null

  const initials = user.name
    .split(' ')
    .slice(0, 2)
    .map(w => w[0].toUpperCase())
    .join('')

  return (
    <>
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
          <div style={{
            width: '28px', height: '28px',
            borderRadius: 'var(--radius-full)',
            background: 'oklch(from var(--color-primary) l c h / 0.15)',
            color: 'var(--color-primary)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: '11px', fontWeight: 700, flexShrink: 0,
          }}>
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

          <ChevronDown size={12} style={{
            color: 'var(--color-text-muted)',
            transition: 'transform var(--transition-interactive)',
            transform: open ? 'rotate(180deg)' : 'rotate(0deg)',
            flexShrink: 0,
          }} />
        </button>

        {open && (
          <div style={{
            position: 'absolute', top: 'calc(100% + var(--space-2))', right: 0,
            minWidth: '220px',
            background: 'var(--color-surface)',
            border: '1px solid var(--color-border)',
            borderRadius: 'var(--radius-lg)',
            boxShadow: 'var(--shadow-lg)',
            overflow: 'hidden', zIndex: 100,
          }}>
            <div style={{
              padding: 'var(--space-3) var(--space-4)',
              borderBottom: '1px solid var(--color-divider)',
              background: 'var(--color-surface-offset)',
            }}>
              <p style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--color-text)', margin: 0 }}>{user.name}</p>
              <p style={{ fontSize: '11px', color: 'var(--color-text-muted)', margin: 0, marginTop: '2px' }}>{user.email}</p>
            </div>

            <div style={{ padding: 'var(--space-1)' }}>
              <button
                onClick={() => { setOpen(false); navigate('/carteira/configuracoes') }}
                style={{
                  width: '100%', display: 'flex', alignItems: 'center',
                  gap: 'var(--space-3)', padding: 'var(--space-2) var(--space-3)',
                  borderRadius: 'var(--radius-md)', border: 'none',
                  background: 'transparent', color: 'var(--color-text)',
                  fontSize: 'var(--text-xs)', cursor: 'pointer', textAlign: 'left',
                }}
                onMouseEnter={e => (e.currentTarget.style.background = 'var(--color-surface-offset)')}
                onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
              >
                <Settings size={14} style={{ color: 'var(--color-text-muted)', flexShrink: 0 }} />
                Configurações
              </button>

              <button
                disabled={!selectedPortfolioId}
                onClick={() => {
                  if (!selectedPortfolioId) return
                  setOpen(false)
                  setShowImport(true)
                }}
                title={selectedPortfolioId ? 'Importar transações por CSV' : 'Selecione uma carteira para importar CSV'}
                style={{
                  width: '100%', display: 'flex', alignItems: 'center',
                  gap: 'var(--space-3)', padding: 'var(--space-2) var(--space-3)',
                  borderRadius: 'var(--radius-md)', border: 'none',
                  background: 'transparent', color: selectedPortfolioId ? 'var(--color-text)' : 'var(--color-text-faint)',
                  fontSize: 'var(--text-xs)', cursor: selectedPortfolioId ? 'pointer' : 'not-allowed', textAlign: 'left',
                  opacity: selectedPortfolioId ? 1 : 0.6,
                }}
                onMouseEnter={e => { if (selectedPortfolioId) e.currentTarget.style.background = 'var(--color-surface-offset)' }}
                onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
              >
                <FileUp size={14} style={{ color: 'var(--color-text-muted)', flexShrink: 0 }} />
                Importar CSV
              </button>

              <div style={{ height: '1px', background: 'var(--color-divider)', margin: 'var(--space-1) 0' }} />

              <button
                onClick={handleLogout}
                style={{
                  width: '100%', display: 'flex', alignItems: 'center',
                  gap: 'var(--space-3)', padding: 'var(--space-2) var(--space-3)',
                  borderRadius: 'var(--radius-md)', border: 'none',
                  background: 'transparent', color: 'var(--color-notification)',
                  fontSize: 'var(--text-xs)', fontWeight: 500, cursor: 'pointer', textAlign: 'left',
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

      {showImport && selectedPortfolioId && (
        <ImportCSVModal
          portfolioId={selectedPortfolioId}
          onClose={() => setShowImport(false)}
        />
      )}
    </>
  )
}
