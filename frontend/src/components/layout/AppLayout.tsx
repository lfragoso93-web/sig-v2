import { useEffect } from 'react'
import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import Topbar from './Topbar'
import BottomNav from './BottomNav'
import UserMenu from './UserMenu'
import AddTransactionModal from '@/components/modals/AddTransactionModal'
import { useAppStore } from '@/store/appStore'
import { usePortfolioList } from '@/hooks/usePortfolio'

export default function AppLayout() {
  const {
    selectedPortfolioId, setSelectedPortfolioId,
    transactionModal, closeTransactionModal,
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
      {/* Sidebar (fixa no desktop, drawer no mobile) */}
      <Sidebar />

      {/* Conteúdo principal */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Topbar */}
        <Topbar />

        {/* Página */}
        <main
          className="flex-1 overflow-y-auto"
          style={{
            // Padding adaptativo: menor no mobile, maior no desktop
            padding: 'var(--space-3)',
          }}
        >
          {/* Wrapper com padding desktop via breakpoint */}
          <div className="lg:px-3 lg:py-2">
            <Outlet />
          </div>
        </main>

        {/* Bottom Navigation — só mobile (<1024px) */}
        <BottomNav />
      </div>

      {/* Espaçamento inferior no mobile para não sobrepor o BottomNav */}
      <style>{`
        @media (max-width: 1023px) {
          main > div {
            padding-bottom: 72px;
          }
        }
      `}</style>

      {/* Modal global de lançamento */}
      {transactionModal.open && (
        <AddTransactionModal onClose={closeTransactionModal} />
      )}
    </div>
  )
}
