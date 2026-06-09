import { Outlet } from 'react-router-dom'
import { Sun, Moon } from 'lucide-react'
import Sidebar from './Sidebar'
import UserMenu from './UserMenu'
import { useAppStore } from '@/store/appStore'

export default function AppLayout() {
  const { theme, setTheme } = useAppStore()

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: 'var(--color-bg)' }}>
      {/* Sidebar */}
      <Sidebar />

      {/* Conteúdo principal */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Topbar */}
        <header
          className="flex items-center justify-end gap-2 px-5 shrink-0"
          style={{
            height: '52px',
            borderBottom: '1px solid var(--color-divider)',
            background: 'var(--color-surface)',
          }}
        >
          {/* Toggle tema */}
          <button
            onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
            style={{
              padding: 'var(--space-2)',
              borderRadius: 'var(--radius-md)',
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              color: 'var(--color-text-muted)',
              display: 'flex',
              alignItems: 'center',
              transition: 'color var(--transition-interactive)',
            }}
            aria-label="Alternar tema"
            data-theme-toggle
          >
            {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
          </button>

          {/* Menu do usuário */}
          <UserMenu />
        </header>

        {/* Página */}
        <main
          className="flex-1 overflow-y-auto"
          style={{ padding: 'var(--space-6)' }}
        >
          <Outlet />
        </main>
      </div>
    </div>
  )
}
