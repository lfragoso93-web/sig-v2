import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'

export interface TransactionModalPrefill {
  tab?: string
  ticker?: string
  assetName?: string
  transactionId?: number
  operation?: 'buy' | 'sell'
  quantity?: number
  price?: number
  fees?: number
  date?: string
  notes?: string
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

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      theme: 'dark',
      selectedPortfolioId: null,
      transactionModal: { open: false },
      sidebarOpen: false,
      sidebarCollapsed: false,

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
        sidebarCollapsed:    state.sidebarCollapsed,
        // Persiste a carteira selecionada para evitar flash de "sem carteira" no reload
        selectedPortfolioId: state.selectedPortfolioId,
      }),
    }
  )
)
