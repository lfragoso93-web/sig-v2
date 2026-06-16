import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import api from '@/services/api'
import { Eye, EyeOff, TrendingUp } from 'lucide-react'

const schema = z.object({
  name:            z.string().min(2, 'Nome muito curto'),
  email:           z.string().email('E-mail inválido'),
  password:        z.string().min(8, 'Mínimo 8 caracteres'),
  confirmPassword: z.string(),
}).refine(d => d.password === d.confirmPassword, {
  message: 'As senhas não coincidem',
  path: ['confirmPassword'],
})

type FormData = z.infer<typeof schema>

const field: React.CSSProperties = {
  width: '100%',
  padding: '0.625rem 0.75rem',
  borderRadius: 'var(--radius-md)',
  border: '1px solid var(--color-border)',
  background: 'var(--color-surface-2)',
  color: 'var(--color-text)',
  fontSize: '16px',
  outline: 'none',
  boxSizing: 'border-box',
}

const fieldError: React.CSSProperties = { ...field, borderColor: 'var(--color-error)' }

const labelStyle: React.CSSProperties = {
  fontSize: 'var(--text-xs)', fontWeight: 500, color: 'var(--color-text)',
}

const errorStyle: React.CSSProperties = {
  fontSize: 'var(--text-xs)', color: 'var(--color-error)', margin: 0,
}

export default function RegisterPage() {
  const navigate = useNavigate()
  const [showPass, setShowPass] = useState(false)
  const [apiError, setApiError] = useState('')

  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormData>({
    resolver: zodResolver(schema),
  })

  const onSubmit = async (data: FormData) => {
    setApiError('')
    try {
      await api.post('/auth/register', {
        name:     data.name,
        email:    data.email,
        password: data.password,
      })
      navigate('/login', { state: { registered: true } })
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } }
      setApiError(err?.response?.data?.detail ?? 'Erro ao criar conta.')
    }
  }

  const focusBorder  = (e: React.FocusEvent<HTMLInputElement>) => { e.target.style.borderColor = 'var(--color-primary)' }
  const blurBorder   = (e: React.FocusEvent<HTMLInputElement>, hasErr: boolean) => {
    e.target.style.borderColor = hasErr ? 'var(--color-error)' : 'var(--color-border)'
  }

  return (
    <div style={{
      minHeight: '100vh', display: 'flex', alignItems: 'center',
      justifyContent: 'center', background: 'var(--color-bg)', padding: '1rem',
    }}>
      <div style={{ width: '100%', maxWidth: 380 }}>

        {/* Logo */}
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', marginBottom: '2rem' }}>
          <div style={{
            width: 48, height: 48, borderRadius: 'var(--radius-xl)',
            background: 'oklch(from var(--color-primary) l c h / 0.12)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '0.75rem',
          }}>
            <TrendingUp size={24} color="var(--color-primary)" />
          </div>
          <h1 style={{ fontSize: 'var(--text-xl)', fontWeight: 700, color: 'var(--color-text)', margin: 0 }}>SIG v2</h1>
          <p style={{ fontSize: 'var(--text-sm)', color: 'var(--color-text-muted)', margin: '0.25rem 0 0' }}>
            Sistema de Gestão de Investimentos
          </p>
        </div>

        {/* Card */}
        <div style={{
          background: 'var(--color-surface)', border: '1px solid var(--color-border)',
          borderRadius: 'var(--radius-xl)', padding: '1.5rem', boxShadow: 'var(--shadow-lg)',
        }}>
          <h2 style={{ fontSize: 'var(--text-lg)', fontWeight: 600, color: 'var(--color-text)', margin: '0 0 1.5rem' }}>
            Criar conta
          </h2>

          <form onSubmit={handleSubmit(onSubmit)} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>

            {/* Nome */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.375rem' }}>
              <label style={labelStyle}>Nome</label>
              <input
                type="text" autoComplete="name" placeholder="Seu nome completo"
                style={errors.name ? fieldError : field}
                onFocus={focusBorder}
                onBlur={e => blurBorder(e, !!errors.name)}
                {...register('name')}
              />
              {errors.name && <p style={errorStyle}>{errors.name.message}</p>}
            </div>

            {/* E-mail */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.375rem' }}>
              <label style={labelStyle}>E-mail</label>
              <input
                type="email" autoComplete="email" placeholder="seu@email.com"
                style={errors.email ? fieldError : field}
                onFocus={focusBorder}
                onBlur={e => blurBorder(e, !!errors.email)}
                {...register('email')}
              />
              {errors.email && <p style={errorStyle}>{errors.email.message}</p>}
            </div>

            {/* Senha */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.375rem' }}>
              <label style={labelStyle}>Senha</label>
              <div style={{ position: 'relative' }}>
                <input
                  type={showPass ? 'text' : 'password'}
                  placeholder="Mínimo 8 caracteres"
                  style={{ ...(errors.password ? fieldError : field), paddingRight: '2.5rem' }}
                  onFocus={focusBorder}
                  onBlur={e => blurBorder(e, !!errors.password)}
                  {...register('password')}
                />
                <button type="button" onClick={() => setShowPass(p => !p)} style={{
                  position: 'absolute', right: '0.75rem', top: '50%', transform: 'translateY(-50%)',
                  background: 'none', border: 'none', cursor: 'pointer', padding: 0,
                  color: 'var(--color-text-muted)', display: 'flex', alignItems: 'center',
                }} aria-label={showPass ? 'Ocultar senha' : 'Mostrar senha'}>
                  {showPass ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
              {errors.password && <p style={errorStyle}>{errors.password.message}</p>}
            </div>

            {/* Confirmar senha */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.375rem' }}>
              <label style={labelStyle}>Confirmar senha</label>
              <input
                type="password" placeholder="Repita a senha"
                style={errors.confirmPassword ? fieldError : field}
                onFocus={focusBorder}
                onBlur={e => blurBorder(e, !!errors.confirmPassword)}
                {...register('confirmPassword')}
              />
              {errors.confirmPassword && <p style={errorStyle}>{errors.confirmPassword.message}</p>}
            </div>

            {/* Erro da API */}
            {apiError && (
              <p style={{
                fontSize: 'var(--text-xs)', color: 'var(--color-error)',
                background: 'oklch(from var(--color-error) l c h / 0.08)',
                border: '1px solid oklch(from var(--color-error) l c h / 0.2)',
                borderRadius: 'var(--radius-md)', padding: '0.5rem 0.75rem', margin: 0,
              }}>{apiError}</p>
            )}

            {/* Submit */}
            <button type="submit" disabled={isSubmitting} style={{
              width: '100%', padding: '0.625rem', borderRadius: 'var(--radius-md)',
              border: 'none',
              background: isSubmitting ? 'var(--color-primary-highlight)' : 'var(--color-primary)',
              color: 'var(--color-text-inverse)',
              fontSize: 'var(--text-sm)', fontWeight: 600,
              cursor: isSubmitting ? 'not-allowed' : 'pointer',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              gap: '0.5rem', marginTop: '0.5rem', transition: 'background 150ms ease',
            }}>
              {isSubmitting
                ? <span style={{
                    width: 16, height: 16,
                    border: '2px solid rgba(255,255,255,0.3)', borderTopColor: 'white',
                    borderRadius: '50%', animation: 'spin 0.7s linear infinite', display: 'inline-block',
                  }} />
                : 'Criar conta'
              }
            </button>
          </form>

          <p style={{ fontSize: 'var(--text-xs)', textAlign: 'center', color: 'var(--color-text-muted)', marginTop: '1rem', marginBottom: 0 }}>
            Já tem conta?{' '}
            <Link to="/login" style={{ color: 'var(--color-primary)', textDecoration: 'none', fontWeight: 500 }}>
              Entrar
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
