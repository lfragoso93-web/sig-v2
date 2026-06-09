import { create } from 'zustand'

interface Portfolio {
  id: number
  name: string
}

interface AppState {
  selectedPortfolioId: number | null
  portfolios: Portfolio[]
  setPortfolios: (portfolios: Portfolio[]) => void
  selectPortfolio: (id: number) => void
}

export const useAppStore = create<AppState>((set) => ({
  selectedPortfolioId: null,
  portfolios: [],
  setPortfolios: (portfolios: Portfolio[]) =>
    set({ portfolios, selectedPortfolioId: portfolios[0]?.id ?? null }),
  selectPortfolio: (id: number) => set({ selectedPortfolioId: id }),
}))
