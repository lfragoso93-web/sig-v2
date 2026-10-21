import { describe, it, expect, beforeEach } from 'vitest'
import { useAppStore } from './appStore'

describe('appStore portfolio persistence', () => {
  beforeEach(() => {
    localStorage.clear()
    useAppStore.setState({
      selectedPortfolioId: null,
      theme: 'dark',
      sidebarCollapsed: false,
    })
  })

  it('updates and persists selectedPortfolioId in localStorage', () => {
    useAppStore.getState().setSelectedPortfolio(42)
    expect(useAppStore.getState().selectedPortfolioId).toBe(42)

    const raw = localStorage.getItem('sig-app')
    expect(raw).toBeTruthy()
    const parsed = JSON.parse(raw!)
    expect(parsed.state.selectedPortfolioId).toBe(42)
  })

  it('clears selectedPortfolioId when requested', () => {
    useAppStore.getState().setSelectedPortfolio(42)
    expect(useAppStore.getState().selectedPortfolioId).toBe(42)

    useAppStore.getState().clearSelectedPortfolio()
    expect(useAppStore.getState().selectedPortfolioId).toBeNull()
  })

  it('allows alias selectors selectPortfolio and setSelectedPortfolioId', () => {
    useAppStore.getState().setSelectedPortfolioId(101)
    expect(useAppStore.getState().selectedPortfolioId).toBe(101)

    useAppStore.getState().selectPortfolio(202)
    expect(useAppStore.getState().selectedPortfolioId).toBe(202)
  })

  it('coerces string ids to positive integers safely', () => {
    useAppStore.getState().setSelectedPortfolio('55' as unknown as number)
    expect(useAppStore.getState().selectedPortfolioId).toBe(55)

    useAppStore.getState().setSelectedPortfolio('invalid' as unknown as number)
    expect(useAppStore.getState().selectedPortfolioId).toBeNull()

    useAppStore.getState().setSelectedPortfolio(-1)
    expect(useAppStore.getState().selectedPortfolioId).toBeNull()
  })
})
