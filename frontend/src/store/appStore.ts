import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'

export interface TransactionModalPrefill {
  tab?: string
  ticker?: string
  assetName?: string
  treasurySlug?: string
  maturityDate?: string | null
  transactionId?: number
  fixedIncomeContractId?: number | null
  operation?: 'buy' | 'sell'
  quantity?: number
  price?: number
  fees?: number
  date?: string
  notes?: string | null
  currency?: string
}

interface ModalState {
  open: boolean
  prefill?: TransactionModalPrefill
}

interface AppState {
  theme: 'dark' | 'light'
  selectedPortfolioId: number | null
  transactionModal: ModalState
  sidebarOpen: boolean
  sidebarCollapsed: boolean

  setTheme: (t: 'dark' | 'light') => void
  setSelectedPortfolio: (id: number) => void
  setSelectedPortfolioId: (id: number) => void
  selectPortfolio: (id: number) => void
  clearSelectedPortfolio: () => void

  openTransactionModal: (prefill?: TransactionModalPrefill) => void
  closeTransactionModal: () => void

  toggleSidebar: () => void
  closeSidebar: () => void
  toggleSidebarCollapsed: () => void
}

function getInitialPersistedState(): {
  theme?: 'dark' | 'light'
  selectedPortfolioId?: number | null
  sidebarCollapsed?: boolean
} {
  try {
    if (typeof window === 'undefined' || !window.localStorage) return {}
    const raw = window.localStorage.getItem('sig-app')
    if (!raw) return {}
    const parsed = JSON.parse(raw)
    return (parsed && typeof parsed === 'object' && parsed.state) ? parsed.state : {}
  } catch {
    return {}
  }
}

const initialPersisted = getInitialPersistedState()

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      theme: initialPersisted.theme ?? 'dark',
      selectedPortfolioId: typeof initialPersisted.selectedPortfolioId === 'number'
        ? initialPersisted.selectedPortfolioId
        : null,
      transactionModal: { open: false },
      sidebarOpen: false,
      sidebarCollapsed: initialPersisted.sidebarCollapsed ?? false,

      setTheme: (theme) => {
        document.documentElement.setAttribute('data-theme', theme)
        set({ theme })
      },
      setSelectedPortfolio:   (id) => set({ selectedPortfolioId: id }),
      setSelectedPortfolioId: (id) => set({ selectedPortfolioId: id }),
      selectPortfolio:        (id) => set({ selectedPortfolioId: id }),
      clearSelectedPortfolio: ()  => set({ selectedPortfolioId: null }),

      openTransactionModal: (prefill) =>
        set({ transactionModal: { open: true, prefill } }),

      closeTransactionModal: () =>
        set({ transactionModal: { open: false, prefill: undefined } }),

      toggleSidebar:          () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
      closeSidebar:           () => set({ sidebarOpen: false }),
      toggleSidebarCollapsed: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
    }),
    {
      name: 'sig-app',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        theme:               state.theme,
        selectedPortfolioId: state.selectedPortfolioId,
        sidebarCollapsed:    state.sidebarCollapsed,
      }),
    }
  )
)
