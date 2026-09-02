import { describe, expect, it } from 'vitest'

import { loginSchema } from './LoginPage'

describe('LoginPage validation', () => {
  it('accepts the local synthetic superadmin email', () => {
    expect(loginSchema.safeParse({
      email: 'admin@sig.local',
      password: 'Admin@1234!',
    }).success).toBe(true)
  })

  it('keeps accepting standard user emails', () => {
    expect(loginSchema.safeParse({
      email: 'investidor@example.com',
      password: '123456',
    }).success).toBe(true)
  })

  it('rejects malformed emails before submitting login', () => {
    expect(loginSchema.safeParse({
      email: 'sem-email',
      password: '123456',
    }).success).toBe(false)
  })
})
