import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { useAuth } from '@/contexts/AuthContext'
import { Eye, EyeOff } from 'lucide-react'
import { getApiValidationErrorMessage } from '@/utils/apiError'

const schema = z.object({
  email:    z.string().email('E-mail inválido'),
  password: z.string().min(6, 'Mínimo 6 caracteres'),
})
type FormData = z.infer<typeof schema>

export default function LoginPage() {
  const { login } = useAuth()
  const [showPass, setShowPass] = useState(false)
  const [apiError, setApiError] = useState('')

  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormData>({
    resolver: zodResolver(schema),
  })

  const onSubmit = async (data: FormData) => {
    setApiError('')
    try {
      await login(data.email, data.password)
    } catch (e: unknown) {
      setApiError(getApiValidationErrorMessage(e, 'Credenciais inválidas.'))
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>

      <div style={{ marginBottom: '0.25rem' }}>
        <h2 style={{ fontSize: 'var(--text-lg)', fontWeight: 650, color: 'var(--color-text)', margin: 0, letterSpacing: '-0.01em' }}>
          Entrar
        </h2>
        <p style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', margin: '0.25rem 0 0' }}>
          Sistema de Gestão de Investimentos
        </p>
      </div>

      {/* E-mail */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.375rem' }}>
        <label style={{ fontSize: 'var(--text-xs)', fontWeight: 500, color: 'var(--color-text-muted)' }}>E-mail</label>
        <input
          type="email"
          autoComplete="email"
          placeholder="seu@email.com"
          className={errors.email ? 'input-error' : 'input'}
          {...register('email')}
        />
        {errors.email && (
          <p style={{ fontSize: 'var(--text-xs)', color: 'var(--color-error, var(--color-notification))', margin: 0 }}>
            {errors.email.message}
          </p>
        )}
      </div>

      {/* Senha */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.375rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <label style={{ fontSize: 'var(--text-xs)', fontWeight: 500, color: 'var(--color-text-muted)' }}>Senha</label>
          <Link to="/auth/esqueceu-senha" style={{ fontSize: 'var(--text-xs)', color: 'var(--color-primary)', textDecoration: 'none' }}>
            Esqueceu a senha?
          </Link>
        </div>
        <div style={{ position: 'relative' }}>
          <input
            type={showPass ? 'text' : 'password'}
            autoComplete="current-password"
            placeholder="••••••••"
            className={errors.password ? 'input-error' : 'input'}
            style={{ paddingRight: '2.5rem' }}
            {...register('password')}
          />
          <button
            type="button"
            onClick={() => setShowPass(p => !p)}
            style={{
              position: 'absolute', right: '0.75rem', top: '50%', transform: 'translateY(-50%)',
              background: 'none', border: 'none', cursor: 'pointer', padding: 0,
              color: 'var(--color-text-muted)', display: 'flex', alignItems: 'center',
            }}
            aria-label={showPass ? 'Ocultar senha' : 'Mostrar senha'}
          >
            {showPass ? <EyeOff size={15} /> : <Eye size={15} />}
          </button>
        </div>
        {errors.password && (
          <p style={{ fontSize: 'var(--text-xs)', color: 'var(--color-error, var(--color-notification))', margin: 0 }}>
            {errors.password.message}
          </p>
        )}
      </div>

      {/* Erro da API */}
      {apiError && (
        <div style={{
          fontSize: 'var(--text-xs)',
          color: 'var(--color-notification)',
          background: 'oklch(from var(--color-notification) l c h / 0.08)',
          border: '1px solid oklch(from var(--color-notification) l c h / 0.2)',
          borderRadius: 'var(--radius-md)',
          padding: '0.5rem 0.75rem',
        }}>
          {apiError}
        </div>
      )}

      {/* Submit */}
      <button
        type="submit"
        disabled={isSubmitting}
        className="btn btn-primary w-full"
        style={{ fontWeight: 600, marginTop: '0.25rem' }}
      >
        {isSubmitting ? 'Entrando…' : 'Entrar'}
      </button>

      <p style={{ fontSize: 'var(--text-xs)', textAlign: 'center', color: 'var(--color-text-muted)', margin: 0 }}>
        Não tem conta?{' '}
        <Link to="/auth/registro" style={{ color: 'var(--color-primary)', textDecoration: 'none', fontWeight: 500 }}>
          Cadastre-se
        </Link>
      </p>
    </form>
  )
}
