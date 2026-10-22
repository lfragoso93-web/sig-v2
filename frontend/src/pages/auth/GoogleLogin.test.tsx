import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import GoogleLoginButton from '@/components/auth/GoogleLoginButton'

describe('GoogleLoginButton', () => {
  it('renders with default label', () => {
    render(<GoogleLoginButton />)
    expect(screen.getByText('Continuar com o Google')).toBeDefined()
  })

  it('renders with custom label', () => {
    render(<GoogleLoginButton label="Cadastrar com o Google" />)
    expect(screen.getByText('Cadastrar com o Google')).toBeDefined()
  })
})
