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
    <div className="flex h-screen overflow-hidden" style={{ background: 'var(--color-bg)' }}>
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Topbar />
        <main className="flex-1 overflow-y-auto p-3 pb-[76px] lg:pb-3 lg:p-5">
          <Outlet />
        </main>
        <BottomNav />
      </div>
      {transactionModal.open && (
        <AddTransactionModal onClose={closeTransactionModal} />
      )}
    </div>
  )
}
