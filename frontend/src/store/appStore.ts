import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface AppState {
  theme: 'dark' | 'light'
  selectedPortfolioId: number | null
  setTheme: (t: 'dark' | 'light') => void
  setSelectedPortfolio: (id: number) => void
  // aliases para compatibilidade
  setSelectedPortfolioId: (id: number) => void
  selectPortfolio: (id: number) => void
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      theme: 'dark',
      selectedPortfolioId: null,
      setTheme: (theme) => set({ theme }),
      setSelectedPortfolio: (id) => set({ selectedPortfolioId: id }),
      setSelectedPortfolioId: (id) => set({ selectedPortfolioId: id }),
      selectPortfolio: (id) => set({ selectedPortfolioId: id }),
    }),
    {
      name: 'sig-app',
      partialize: (state) => ({ theme: state.theme, selectedPortfolioId: state.selectedPortfolioId }),
    }
  )
)
