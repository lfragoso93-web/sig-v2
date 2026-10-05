import { useEffect, useLayoutEffect, useRef } from 'react'
import { Outlet, useLocation, useNavigationType } from 'react-router-dom'
import { useAppStore } from '@/store/appStore'
import Sidebar from './Sidebar'
import Topbar from './Topbar'
import BottomNav from './BottomNav'
import AddTransactionModal from '@/components/modals/AddTransactionModal'
import { findAnchorElement, resolveScrollRestoration } from '@/utils/scrollRestoration'

export default function AppLayout() {
  const { sidebarOpen, closeSidebar, transactionModal, closeTransactionModal } = useAppStore()
  const overlayRef = useRef<HTMLDivElement>(null)
  const mainRef = useRef<HTMLElement>(null)
  const scrollPositions = useRef(new Map<string, number>())
  const location = useLocation()
  const navigationType = useNavigationType()

  useEffect(() => {
    const el = overlayRef.current
    if (!el) return
    const handler = (e: MouseEvent) => { if (e.target === el) closeSidebar() }
    el.addEventListener('click', handler)
    return () => el.removeEventListener('click', handler)
  }, [closeSidebar])

  useEffect(() => {
    return () => {
      const el = mainRef.current
      if (el) scrollPositions.current.set(location.key, el.scrollTop)
    }
  }, [location.key])

  useLayoutEffect(() => {
    const el = mainRef.current
    if (!el) return

    const action = resolveScrollRestoration(
      navigationType,
      location.hash,
      scrollPositions.current.get(location.key),
    )

    if (action.kind === 'anchor') {
      const anchor = findAnchorElement(action.hash, el)
      if (anchor) anchor.scrollIntoView({ block: 'start' })
      return
    }

    el.scrollTo({ top: action.kind === 'restore' ? action.top : 0, left: 0 })
  }, [location.hash, location.key, location.pathname, navigationType])

  return (
    <div
      style={{
        display:       'flex',
        flexDirection: 'column',
        minHeight:     '100dvh',
        height:        '100dvh',
        overflow:      'hidden',
        background:    'var(--color-bg)',
      }}
    >
      <Topbar />

      <div style={{ display: 'flex', flex: 1, minHeight: 0, overflow: 'hidden', position: 'relative' }}>
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

        <Sidebar />

        <main
          ref={mainRef}
          style={{
            flex:       1,
            minWidth:   0,
            overflowY:  'auto',
            overflowX:  'clip',
            height:     '100%',
            background: 'var(--color-bg)',
          }}
          className="lg:pb-0 pb-[calc(60px+env(safe-area-inset-bottom,0px))]"
        >
          <Outlet />
        </main>
      </div>

      <BottomNav />

      {transactionModal.open && (
        <AddTransactionModal onClose={closeTransactionModal} />
      )}
    </div>
  )
}
