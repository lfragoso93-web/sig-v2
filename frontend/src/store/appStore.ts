import { create } from 'zustand'

type Theme = 'light' | 'dark' | 'system'

interface AppState {
  selectedPortfolioId: number | null
  theme: Theme
  setSelectedPortfolio: (id: number | null) => void
  setTheme: (t: Theme) => void
}

export const useAppStore = create<AppState>((set) => ({
  selectedPortfolioId: null,
  theme: 'system',

  setSelectedPortfolio: (id) => set({ selectedPortfolioId: id }),

  setTheme: (t) => {
    set({ theme: t })
    const root = document.documentElement
    if (t === 'system') {
      root.removeAttribute('data-theme')
    } else {
      root.setAttribute('data-theme', t)
    }
  },
}))
