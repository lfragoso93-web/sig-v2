import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import Landing from './Landing'

describe('Landing Page', () => {
  it('renders SGI branding and no legacy SIG or version labels', () => {
    const { container } = render(
      <MemoryRouter>
        <Landing />
      </MemoryRouter>
    )

    // Heading
    const h1 = screen.getByRole('heading', { level: 1 })
    expect(h1.textContent).toMatch(/precisão institucional/i)

    // Should NOT have version badge or v2 (isolated word "versão" or "v2")
    expect(screen.queryByText(/\bversão\b/i)).toBeNull()
    expect(screen.queryByText(/\bv2\b/i)).toBeNull()

    // Canonical SGI logo and title
    expect(container.textContent).toContain('SGI')
    expect(container.textContent).toContain('Sistema de Gestão de Investimentos')

    // Links to login and register
    const loginLinks = screen.getAllByRole('link', { name: /entrar/i })
    expect(loginLinks.length).toBeGreaterThan(0)

    const registerLinks = screen.getAllByRole('link', { name: /começar grátis|criar conta gratuita/i })
    expect(registerLinks.length).toBeGreaterThan(0)

    // Verify presence of asset classes
    expect(screen.getByText('Ações Brasileiras')).toBeTruthy()
    expect(screen.getByText('Fundos Imobiliários')).toBeTruthy()
    expect(screen.getAllByText('Tesouro Direto').length).toBeGreaterThan(0)
    expect(screen.getByText('Criptomoedas')).toBeTruthy()
  })
})
