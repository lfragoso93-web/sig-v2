import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { useAuth } from '@/contexts/AuthContext'
import { Eye, EyeOff, ShieldCheck, ArrowLeft } from 'lucide-react'
import { getApiValidationErrorMessage } from '@/utils/apiError'
import GoogleLoginButton from '@/components/auth/GoogleLoginButton'
import api from '@/services/api'

const loginEmailSchema = z.string().trim().email('E-mail inválido')

export const loginSchema = z.object({
  email:    loginEmailSchema,
  password: z.string().min(6, 'Mínimo 6 caracteres'),
})
type FormData = z.infer<typeof loginSchema>

export default function LoginPage() {
  const { login, loginWithTokens } = useAuth()
  const [showPass, setShowPass] = useState(false)
  const [apiError, setApiError] = useState('')

  // Estado para fluxo MFA (2FA TOTP)
  const [mfaToken, setMfaToken] = useState<string | null>(null)
  const [mfaCode, setMfaCode] = useState('')
  const [isVerifyingMfa, setIsVerifyingMfa] = useState(false)

  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormData>({
    resolver: zodResolver(loginSchema),
  })

  const onSubmit = async (data: FormData) => {
    setApiError('')
    try {
      const res = await login(data.email, data.password)
      if (res && res.mfa_required && res.mfa_token) {
        setMfaToken(res.mfa_token)
      }
    } catch (e: unknown) {
      setApiError(getApiValidationErrorMessage(e, 'Credenciais inválidas.'))
    }
  }

  const handleVerifyMfa = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!mfaToken || !mfaCode.trim()) return
    setApiError('')
    setIsVerifyingMfa(true)
    try {
      const { data } = await api.post<{
        access_token: string
        refresh_token: string
      }>('/auth/mfa/verify', {
        mfa_token: mfaToken,
        code: mfaCode.trim(),
      })
      await loginWithTokens(data.access_token, data.refresh_token)
    } catch (err: unknown) {
      setApiError(
        getApiValidationErrorMessage(
          err,
          'Código de verificação incorreto ou expirado.'
        )
      )
    } finally {
      setIsVerifyingMfa(false)
    }
  }

  // ── Tela do desafio de MFA ──────────────────────────────────────────────
  if (mfaToken) {
    return (
      <form
        onSubmit={handleVerifyMfa}
        style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}
      >
        <div style={{ marginBottom: '0.25rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
            <ShieldCheck size={20} style={{ color: 'var(--color-primary)' }} />
            <h2
              style={{
                fontSize: 'var(--text-lg)',
                fontWeight: 650,
                color: 'var(--color-text)',
                margin: 0,
                letterSpacing: '-0.01em',
              }}
            >
              Verificação em Duas Etapas
            </h2>
          </div>
          <p
            style={{
              fontSize: 'var(--text-xs)',
              color: 'var(--color-text-muted)',
              margin: '0.25rem 0 0',
            }}
          >
            Insira o código de 6 dígitos gerado pelo seu app autenticador ou um código de recuperação.
          </p>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.375rem' }}>
          <label style={{ fontSize: 'var(--text-xs)', fontWeight: 500, color: 'var(--color-text-muted)' }}>
            Código de Verificação
          </label>
          <input
            type="text"
            autoFocus
            autoComplete="one-time-code"
            placeholder="000000"
            maxLength={12}
            className="input w-full text-center tracking-widest text-lg font-mono"
            value={mfaCode}
            onChange={(e) => setMfaCode(e.target.value)}
          />
        </div>

        {apiError && (
          <div
            style={{
              fontSize: 'var(--text-xs)',
              color: 'var(--color-notification)',
              background: 'oklch(from var(--color-notification) l c h / 0.08)',
              border: '1px solid oklch(from var(--color-notification) l c h / 0.2)',
              borderRadius: 'var(--radius-md)',
              padding: '0.5rem 0.75rem',
            }}
          >
            {apiError}
          </div>
        )}

        <button
          type="submit"
          disabled={isVerifyingMfa || !mfaCode.trim()}
          className="btn btn-primary w-full"
          style={{ fontWeight: 600, marginTop: '0.25rem' }}
        >
          {isVerifyingMfa ? 'Validando…' : 'Confirmar e Entrar'}
        </button>

        <button
          type="button"
          onClick={() => {
            setMfaToken(null)
            setMfaCode('')
            setApiError('')
          }}
          className="btn btn-ghost w-full"
          style={{
            fontSize: 'var(--text-xs)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '0.375rem',
            color: 'var(--color-text-muted)',
          }}
        >
          <ArrowLeft size={14} /> Voltar para o login
        </button>
      </form>
    )
  }

  // ── Tela padrão de login ────────────────────────────────────────────────
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

      {/* Google OAuth (Issue #97) */}
      <GoogleLoginButton onError={(msg) => setApiError(msg)} />

      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', margin: '0.125rem 0' }}>
        <div style={{ flex: 1, height: '1px', background: 'var(--color-divider)' }} />
        <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>ou</span>
        <div style={{ flex: 1, height: '1px', background: 'var(--color-divider)' }} />
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
