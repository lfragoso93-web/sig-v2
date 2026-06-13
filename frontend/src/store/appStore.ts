import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface TransactionModalPrefill {
  /** chave da aba (ex: 'acao', 'fii', 'tesouro', 'cripto', etc.) */
  tab?: string
  ticker?: string
  assetName?: string
  /** Campos para modo edicao */
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

  setTheme: (t: 'dark' | 'light') => void
  setSelectedPortfolio: (id: number) => void
  setSelectedPortfolioId: (id: number) => void
  selectPortfolio: (id: number) => void

  openTransactionModal: (prefill?: TransactionModalPrefill) => void
  closeTransactionModal: () => void

  toggleSidebar: () => void
  closeSidebar: () => void
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      theme: 'dark',
      selectedPortfolioId: null,
      transactionModal: { open: false },
      sidebarOpen: false,

      setTheme: (theme) => {
        document.documentElement.setAttribute('data-theme', theme)
        set({ theme })
      },
      setSelectedPortfolio:   (id) => set({ selectedPortfolioId: id }),
      setSelectedPortfolioId: (id) => set({ selectedPortfolioId: id }),
      selectPortfolio:        (id) => set({ selectedPortfolioId: id }),

      openTransactionModal: (prefill) =>
        set({ transactionModal: { open: true, prefill } }),

      closeTransactionModal: () =>
        set({ transactionModal: { open: false, prefill: undefined } }),

      toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
      closeSidebar:  () => set({ sidebarOpen: false }),
    }),
    {
      name: 'sig-app',
      partialize: (state) => ({
        theme: state.theme,
        selectedPortfolioId: state.selectedPortfolioId,
      }),
    }
  )
)
