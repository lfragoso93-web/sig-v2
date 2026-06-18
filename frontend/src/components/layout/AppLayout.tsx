import { useEffect } from 'react'
import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import Topbar from './Topbar'
import BottomNav from './BottomNav'
import AddTransactionModal from '@/components/modals/AddTransactionModal'
import { useAppStore } from '@/store/appStore'
import { usePortfolioList } from '@/hooks/usePortfolio'

export default function AppLayout() {
  const {
    selectedPortfolioId, setSelectedPortfolioId,
    transactionModal, closeTransactionModal,
  } = useAppStore()

  const { data: portfolios } = usePortfolioList()
  useEffect(() => {
    if (!selectedPortfolioId && portfolios && portfolios.length > 0) {
      setSelectedPortfolioId(portfolios[0].id)
    }
  }, [portfolios, selectedPortfolioId, setSelectedPortfolioId])

  return (
    <div
      className="flex flex-col h-screen overflow-hidden"
      style={{ background: 'var(--color-bg)' }}
    >
      {/* ── Topbar — full width, acima de tudo ── */}
      <Topbar />

      {/* ── Sidebar + conteúdo principal ── */}
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />

        <div className="flex flex-col flex-1 overflow-hidden">
          {/*
            overflow-x: auto no <main> para que tabelas largas
            possam rolar horizontalmente sem cortar colunas.
            overflow-y: auto para o scroll vertical normal da página.
          */}
          <main
            className="flex-1 overflow-y-auto overflow-x-auto"
            style={{
              padding:       'clamp(0.75rem, 1.5vw, 1.25rem)',
              paddingBottom: 'calc(clamp(0.75rem, 1.5vw, 1.25rem) + env(safe-area-inset-bottom, 0px))',
            }}
          >
            <div
              style={{
                /* largura mínima garante que tabelas com muitas colunas
                   nunca comprimam as células — usam scroll horizontal */
                minWidth: 0,
              }}
            >
              <Outlet />
            </div>
          </main>

          {/* Nav bottom mobile */}
          <BottomNav />
        </div>
      </div>

      {transactionModal.open && (
        <AddTransactionModal onClose={closeTransactionModal} />
      )}
    </div>
  )
}
