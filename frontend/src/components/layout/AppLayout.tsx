import { useEffect } from 'react'
import { Outlet } from 'react-router-dom'
import { Sun, Moon, Plus } from 'lucide-react'
import Sidebar from './Sidebar'
import UserMenu from './UserMenu'
import AddTransactionModal from '@/components/modals/AddTransactionModal'
import { useAppStore } from '@/store/appStore'
import { usePortfolioList } from '@/hooks/usePortfolio'

export default function AppLayout() {
  const {
    theme, setTheme,
    selectedPortfolioId, setSelectedPortfolioId,
    transactionModal, openTransactionModal, closeTransactionModal,
  } = useAppStore()

  // Auto-seleciona a primeira carteira se nenhuma estiver selecionada
  const { data: portfolios } = usePortfolioList()
  useEffect(() => {
    if (!selectedPortfolioId && portfolios && portfolios.length > 0) {
      setSelectedPortfolioId(portfolios[0].id)
    }
  }, [portfolios, selectedPortfolioId, setSelectedPortfolioId])

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
          {/* Botão Novo Lançamento — abre sem prefill */}
          <button
            onClick={() => openTransactionModal()}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium bg-brand-600 hover:bg-brand-500 text-white transition-colors duration-150"
          >
            <Plus size={14} />
            Novo Lançamento
          </button>

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

      {/* Modal global de lançamento — controlado pelo store */}
      {transactionModal.open && (
        <AddTransactionModal onClose={closeTransactionModal} />
      )}
    </div>
  )
}
