import { useEffect, useRef } from 'react'
import { Outlet } from 'react-router-dom'
import { useAppStore } from '@/store/appStore'
import Sidebar from './Sidebar'
import Topbar from './Topbar'
import AddTransactionModal from '@/components/modals/AddTransactionModal'

export default function AppLayout() {
  const { sidebarOpen, closeSidebar, transactionModal, closeTransactionModal } = useAppStore()
  const overlayRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const el = overlayRef.current
    if (!el) return
    const handler = (e: MouseEvent) => { if (e.target === el) closeSidebar() }
    el.addEventListener('click', handler)
    return () => el.removeEventListener('click', handler)
  }, [closeSidebar])

  return (
    <div
      style={{
        display:       'flex',
        flexDirection: 'column',
        height:        '100dvh',
        overflow:      'hidden',
        background:    'var(--color-bg)',
      }}
    >
      {/* Topbar */}
      <Topbar />

      {/* Body: sidebar + main */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden', position: 'relative' }}>

        {/* Overlay mobile */}
        {sidebarOpen && (
          <div
            ref={overlayRef}
            style={{
              position: 'fixed', inset: 0, zIndex: 40,
              background: 'oklch(0.1 0.01 240 / 0.55)',
              backdropFilter: 'blur(2px)',
            }}
            className="lg:hidden"
            aria-hidden="true"
          />
        )}

        {/* Sidebar */}
        <Sidebar />

        {/* Main content — expande em qualquer largura */}
        <main
          style={{
            flex:       1,
            minWidth:   0,
            overflowY:  'auto',
            overflowX:  'hidden',
            height:     '100%',
            background: 'var(--color-bg)',
          }}
        >
          <Outlet />
        </main>
      </div>

      {/* Modal global de transação */}
      {transactionModal.open && (
        <AddTransactionModal onClose={closeTransactionModal} />
      )}
    </div>
  )
}
