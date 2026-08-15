import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

const source = readFileSync(resolve(process.cwd(), 'src/pages/WelcomePage.tsx'), 'utf8')

describe('WelcomePage onboarding persistence boundary', () => {
  it('does not swallow the remote onboarding update', () => {
    expect(source).toContain("await api.patch('/users/me/onboarding')")
    expect(source).not.toContain("try { await api.patch('/users/me/onboarding') } catch")
    expect(source).toContain('await refreshUser()')
  })

  it('does not create a duplicate portfolio when onboarding completion is retried', () => {
    expect(source).toContain('if (!created)')
    expect(source).toContain('setPortfolioCreated(true)')
    expect(source).toContain('!walletName.trim() && !portfolioCreated')
  })

  it('keeps the user on the page and exposes a recoverable error', () => {
    expect(source).toContain('setFinishError(')
    expect(source).toContain('role="alert"')
    expect(source).toContain("? <><Check size={14} /> Concluir</>")
  })
})
