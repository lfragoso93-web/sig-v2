import { create } from 'zustand'

type Theme = 'light' | 'dark'

interface AppState {
  theme: Theme
  selectedPortfolioId: number | null
  setTheme: (t: Theme) => void
  setSelectedPortfolioId: (id: number) => void
}

export const useAppStore = create<AppState>((set) => ({
  theme: window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light',
  selectedPortfolioId: null,

  setTheme: (theme) => {
    document.documentElement.setAttribute('data-theme', theme)
    set({ theme })
  },

  setSelectedPortfolioId: (id) => set({ selectedPortfolioId: id }),
}))
