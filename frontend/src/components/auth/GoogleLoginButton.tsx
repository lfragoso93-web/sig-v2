import { useState } from 'react'
import api from '@/services/api'
import { Loader2 } from 'lucide-react'

interface GoogleLoginButtonProps {
  label?: string
  onError?: (msg: string) => void
}

export default function GoogleLoginButton({
  label = 'Continuar com o Google',
  onError,
}: GoogleLoginButtonProps) {
  const [loading, setLoading] = useState(false)

  const handleClick = async () => {
    setLoading(true)
    try {
      const { data } = await api.get<{ url: string; enabled: boolean }>(
        '/auth/google/url'
      )
      if (data.enabled && data.url) {
        window.location.href = data.url
      } else {
        onError?.(
          'Google OAuth não está ativado no ambiente atual (requer GOOGLE_CLIENT_ID).'
        )
      }
    } catch {
      onError?.('Falha ao conectar com o serviço do Google. Tente novamente.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <button
      type="button"
      onClick={handleClick}
      disabled={loading}
      className="btn w-full"
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '0.625rem',
        background: 'var(--color-surface)',
        border: '1px solid var(--color-border)',
        color: 'var(--color-text)',
        fontWeight: 500,
        fontSize: 'var(--text-sm)',
        padding: '0.625rem 1rem',
        borderRadius: 'var(--radius-md)',
        cursor: loading ? 'not-allowed' : 'pointer',
        boxShadow: 'var(--shadow-xs)',
      }}
    >
      {loading ? (
        <Loader2 size={16} className="animate-spin" />
      ) : (
        <svg width="18" height="18" viewBox="0 0 24 24">
          <path
            fill="#4285F4"
            d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
          />
          <path
            fill="#34A853"
            d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
          />
          <path
            fill="#FBBC05"
            d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
          />
          <path
            fill="#EA4335"
            d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
          />
        </svg>
      )}
      <span>{label}</span>
    </button>
  )
}
