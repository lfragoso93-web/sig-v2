import { Outlet } from 'react-router-dom'
import Topbar from '@/components/layout/Topbar'
import AddTransactionModal from '@/components/modals/AddTransactionModal'
import { useState } from 'react'

export default function AppLayout() {
  const [showAddModal, setShowAddModal] = useState(false)

  return (
    <div className="min-h-screen flex flex-col bg-light-50 dark:bg-dark-800">
      <Topbar onAddLancamento={() => setShowAddModal(true)} />
      <main className="flex-1 pt-14">
        <Outlet />
      </main>
      {showAddModal && (
        <AddTransactionModal onClose={() => setShowAddModal(false)} />
      )}
    </div>
  )
}
