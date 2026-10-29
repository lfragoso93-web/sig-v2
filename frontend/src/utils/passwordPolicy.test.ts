import { describe, expect, it } from 'vitest'
import { getPasswordPolicyError, isStrongPassword, strongPasswordSchema } from './passwordPolicy'

describe('passwordPolicy', () => {
  it('rejects passwords shorter than 10 characters', () => {
    expect(getPasswordPolicyError('Aa1!aaaaa')).toBe('Minimo 10 caracteres.')
  })

  it.each([
    ['missing uppercase', 'aa1!aaaaaa', 'Inclua ao menos uma letra maiuscula.'],
    ['missing lowercase', 'AA1!AAAAAA', 'Inclua ao menos uma letra minuscula.'],
    ['missing number', 'Aa!!aaaaaa', 'Inclua ao menos um numero.'],
    ['missing special', 'Aa11aaaaaa', 'Inclua ao menos um caractere especial.'],
    ['common sequence 123456', 'Aa!123456a', 'Senha contem sequencia obvia ou comum nao permitida.'],
    ['common sequence qwerty', 'Qwerty123!', 'Senha contem sequencia obvia ou comum nao permitida.'],
  ])('rejects %s', (_case, password, message) => {
    expect(getPasswordPolicyError(password)).toBe(message)
    expect(strongPasswordSchema.safeParse(password).success).toBe(false)
  })

  it('accepts strong passwords at the canonical boundary', () => {
    expect(isStrongPassword('Aa1!aaaaaa')).toBe(true)
    expect(strongPasswordSchema.parse('Aa1!aaaaaa')).toBe('Aa1!aaaaaa')
  })
})
