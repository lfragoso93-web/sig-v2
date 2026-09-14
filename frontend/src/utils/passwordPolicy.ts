import { z } from 'zod'

export const PASSWORD_MIN_LENGTH = 10
export const PASSWORD_POLICY_HELP =
  'Minimo 10 caracteres, com maiuscula, minuscula, numero e caractere especial.'

const UPPERCASE_RE = /[A-Z]/
const LOWERCASE_RE = /[a-z]/
const NUMBER_RE = /\d/
const SPECIAL_RE = /[!@#$%^&*(),.?":{}|<>]/

export function getPasswordPolicyError(password: string): string | null {
  if (password.length < PASSWORD_MIN_LENGTH) {
    return `Minimo ${PASSWORD_MIN_LENGTH} caracteres.`
  }
  if (!UPPERCASE_RE.test(password)) {
    return 'Inclua ao menos uma letra maiuscula.'
  }
  if (!LOWERCASE_RE.test(password)) {
    return 'Inclua ao menos uma letra minuscula.'
  }
  if (!NUMBER_RE.test(password)) {
    return 'Inclua ao menos um numero.'
  }
  if (!SPECIAL_RE.test(password)) {
    return 'Inclua ao menos um caractere especial.'
  }
  return null
}

export function isStrongPassword(password: string): boolean {
  return getPasswordPolicyError(password) === null
}

export const strongPasswordSchema = z.string().superRefine((password, ctx) => {
  const message = getPasswordPolicyError(password)
  if (message) {
    ctx.addIssue({ code: z.ZodIssueCode.custom, message })
  }
})
