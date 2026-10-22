import { useEffect, useState, useRef } from 'react'
import { useNavigate, useSearchParams, Link } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import api from '@/services/api'
import { Loader2, AlertCircle, ShieldCheck, ArrowLeft } from 'lucide-react'
import { getApiValidationErrorMessage } from '@/utils/apiError'

export default function GoogleCallbackPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const { loginWithTokens } = useAuth()

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Desafio MFA se a conta vinculada tiver 2FA ativo
  const [mfaToken, setMfaToken] = useState<string | null>(null)
  const [mfaCode, setMfaCode] = useState('')
  const [isVerifyingMfa, setIsVerifyingMfa] = useState(false)

  const code = searchParams.get('code')
  const state = searchParams.get('state')
  const hasExecutedRef = useRef(false)

  useEffect(() => {
    if (!code || !state) {
      setError('Parâmetros de autenticação incompletos ou inválidos.')
      setLoading(false)
      return
    }

    if (hasExecutedRef.current) return
    hasExecutedRef.current = true

    let isMounted = true

    const exchangeCode = async () => {
      try {
        const { data } = await api.post<{
          access_token?: string
          refresh_token?: string
          mfa_required?: boolean
          mfa_token?: string
        }>('/auth/google/callback', { code, state })

        if (!isMounted) return

        if (data.mfa_required && data.mfa_token) {
          setMfaToken(data.mfa_token)
          setLoading(false)
          return
        }

        if (data.access_token && data.refresh_token) {
          await loginWithTokens(data.access_token, data.refresh_token)
        } else {
          setError('Resposta de autenticação inválida.')
          setLoading(false)
        }
      } catch (err: unknown) {
        if (!isMounted) return
        setError(
          getApiValidationErrorMessage(
            err,
            'Falha ao autenticar com o Google. Tente novamente.'
          )
        )
        setLoading(false)
      }
    }

    void exchangeCode()

    return () => {
      isMounted = false
    }
  }, [code, state])

  const handleVerifyMfa = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!mfaToken || !mfaCode.trim()) return
    setError(null)
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
      setError(
        getApiValidationErrorMessage(
          err,
          'Código de verificação incorreto ou expirado.'
        )
      )
    } finally {
      setIsVerifyingMfa(false)
    }
  }

  // ── Desafio MFA ──────────────────────────────────────────────────────────
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
            Sua conta Google está vinculada a um perfil com MFA ativo. Digite o código de 6 dígitos.
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

        {error && (
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
            {error}
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
          onClick={() => navigate('/auth/login', { replace: true })}
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

  // ── Carregamento / Processamento do OAuth ─────────────────────────────────
  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '2rem 1rem' }}>
        <Loader2 size={32} className="animate-spin" style={{ margin: '0 auto 1rem', color: 'var(--color-primary)' }} />
        <h3 style={{ fontSize: 'var(--text-base)', fontWeight: 600, color: 'var(--color-text)', margin: 0 }}>
          Autenticando com o Google…
        </h3>
        <p style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', marginTop: '0.5rem' }}>
          Validando suas credenciais de forma segura.
        </p>
      </div>
    )
  }

  // ── Erro de autenticação ─────────────────────────────────────────────────
  return (
    <div style={{ textAlign: 'center', padding: '1.5rem 0' }}>
      <AlertCircle size={36} style={{ color: 'var(--color-notification)', margin: '0 auto 1rem' }} />
      <h3 style={{ fontSize: 'var(--text-base)', fontWeight: 600, color: 'var(--color-text)', margin: 0 }}>
        Falha na Autenticação
      </h3>
      <p style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', marginTop: '0.5rem', marginBottom: '1.5rem' }}>
        {error}
      </p>
      <Link to="/auth/login" className="btn btn-primary" style={{ textDecoration: 'none', display: 'inline-block' }}>
        Voltar para a página de login
      </Link>
    </div>
  )
}
