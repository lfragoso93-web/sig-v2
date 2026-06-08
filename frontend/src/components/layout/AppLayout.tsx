import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import { Sun, Moon } from 'lucide-react'
import Sidebar from './Sidebar'
import { usePortfolios } from '@/hooks/usePortfolios'
import { useAppStore } from '@/store/appStore'

export default function AppLayout() {
  const [collapsed, setCollapsed] = useState(false)
  const { theme, setTheme, selectedPortfolioId, setSelectedPortfolioId } = useAppStore()
  const { data: portfolios = [] } = usePortfolios()

  return (
    <div className="flex h-screen overflow-hidden bg-bg">
      {/* Sidebar */}
      <Sidebar
        portfolios={portfolios}
        selectedPortfolioId={selectedPortfolioId}
        onSelectPortfolio={setSelectedPortfolioId}
        collapsed={collapsed}
        onToggleCollapse={() => setCollapsed(c => !c)}
      />

      {/* Conteúdo principal */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Topbar */}
        <header className="flex items-center justify-end gap-2 px-6 py-3 border-b border-light-border dark:border-dark-border bg-surface shrink-0">
          <button
            onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
            className="p-2 rounded hover:bg-surface-2 transition-colors text-muted"
            aria-label="Alternar tema"
            data-theme-toggle
          >
            {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
          </button>
        </header>

        {/* Página */}
        <main className="flex-1 overflow-y-auto px-6 py-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
