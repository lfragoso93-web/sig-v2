import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { ChevronDown, ChevronUp } from 'lucide-react'
import api from '@/services/api'
import { useAuth } from '@/contexts/AuthContext'
import { Eye, EyeOff } from 'lucide-react'

const schema = z.object({
  name:          z.string().min(2, 'Informe seu nome'),
  email:         z.string().email('E-mail inválido'),
  password:      z.string().min(8, 'Mínimo 8 caracteres'),
  confirm:       z.string(),
  acceptedTerms: z.literal(true, {
    message: 'Você precisa aceitar os termos para continuar',
  }),
}).refine(d => d.password === d.confirm, {
  message: 'As senhas não coincidem',
  path: ['confirm'],
})
type FormData = z.infer<typeof schema>

function EulaText() {
  return (
    <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', lineHeight: 1.6 }}>
      <p style={{ fontWeight: 600, marginBottom: '0.5rem', color: 'var(--color-text)' }}>
        Política de Privacidade e Termos de Uso — SIG v2
      </p>

      <p style={{ marginBottom: '0.5rem' }}>
        <strong>1. Responsabilidade dos dados</strong><br />
        Todas as informações inseridas nesta plataforma — incluindo transações financeiras, valores de ativos,
        dados pessoais e quaisquer outros registros — são de <strong>exclusiva responsabilidade do usuário</strong>.
        O SIG v2 não verifica, valida nem garante a veracidade ou precisão dos dados cadastrados.
      </p>

      <p style={{ marginBottom: '0.5rem' }}>
        <strong>2. Uso da plataforma</strong><br />
        Esta é uma ferramenta de controle pessoal de investimentos. Não constitui assessoria financeira,
        recomendação de investimento ou serviço regulado pela CVM ou pelo Banco Central do Brasil.
        Decisões de investimento são de inteira responsabilidade do usuário.
      </p>

      <p style={{ marginBottom: '0.5rem' }}>
        <strong>3. Armazenamento de dados</strong><br />
        Os dados são armazenados de forma segura com criptografia em trânsito (HTTPS) e em repouso.
        Senhas são armazenadas com hash bcrypt e nunca são acessíveis em texto plano.
        Você pode solicitar a exclusão completa da sua conta e dados a qualquer momento.
      </p>

      <p style={{ marginBottom: '0.5rem' }}>
        <strong>4. Cotações e dados de mercado</strong><br />
        Os preços e indicadores exibidos são obtidos de fontes externas (BRAPI, yfinance, Alpha Vantage)
        e podem apresentar atrasos ou inconsistências. O sistema não garante a precisão em tempo real
        dessas informações.
      </p>

      <p style={{ marginBottom: 0 }}>
        <strong>5. Limitação de responsabilidade</strong><br />
        O SIG v2 não se responsabiliza por perdas financeiras, decisões equivocadas ou danos decorrentes
        do uso da plataforma. O uso é feito por conta e risco do usuário.
      </p>
    </div>
  )
}

export default function RegisterPage() {
  const { loginWithTokens } = useAuth()
  const [showPass, setShowPass]   = useState(false)
  const [eulaOpen, setEulaOpen]   = useState(false)
  const [apiError, setApiError]   = useState('')

  const { register, handleSubmit, watch, formState: { errors, isSubmitting } } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { acceptedTerms: undefined as unknown as true },
  })

  const accepted = watch('acceptedTerms')

  const onSubmit = async (data: FormData) => {
    setApiError('')
    try {
      const { data: tokens } = await api.post<{
        access_token: string
        refresh_token: string
      }>('/auth/register', {
        name:     data.name,
        email:    data.email,
        password: data.password,
      })
      await loginWithTokens(tokens.access_token, tokens.refresh_token)
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } }
      setApiError(err?.response?.data?.detail ?? 'Erro ao criar conta. Tente novamente.')
    }
  }

  const fieldGap: React.CSSProperties = { display: 'flex', flexDirection: 'column', gap: '0.375rem' }
  const labelStyle: React.CSSProperties = { fontSize: 'var(--text-xs)', fontWeight: 500, color: 'var(--color-text-muted)' }
  const errStyle: React.CSSProperties  = { fontSize: 'var(--text-xs)', color: 'var(--color-notification)', margin: 0 }

  return (
    <form onSubmit={handleSubmit(onSubmit)} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>

      <div style={{ marginBottom: '0.25rem' }}>
        <h2 style={{ fontSize: 'var(--text-lg)', fontWeight: 650, color: 'var(--color-text)', margin: 0, letterSpacing: '-0.01em' }}>
          Criar conta
        </h2>
        <p style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', margin: '0.25rem 0 0' }}>
          Preencha os dados para se cadastrar
        </p>
      </div>

      {/* Nome */}
      <div style={fieldGap}>
        <label style={labelStyle}>Nome</label>
        <input
          type="text" autoComplete="name" placeholder="Seu nome completo"
          className={errors.name ? 'input-error' : 'input'}
          {...register('name')}
        />
        {errors.name && <p style={errStyle}>{errors.name.message}</p>}
      </div>

      {/* E-mail */}
      <div style={fieldGap}>
        <label style={labelStyle}>E-mail</label>
        <input
          type="email" autoComplete="email" placeholder="seu@email.com"
          className={errors.email ? 'input-error' : 'input'}
          {...register('email')}
        />
        {errors.email && <p style={errStyle}>{errors.email.message}</p>}
      </div>

      {/* Senha */}
      <div style={fieldGap}>
        <label style={labelStyle}>Senha</label>
        <div style={{ position: 'relative' }}>
          <input
            type={showPass ? 'text' : 'password'}
            autoComplete="new-password" placeholder="Mínimo 8 caracteres"
            className={errors.password ? 'input-error' : 'input'}
            style={{ paddingRight: '2.5rem' }}
            {...register('password')}
          />
          <button
            type="button" onClick={() => setShowPass(p => !p)}
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
        {errors.password && <p style={errStyle}>{errors.password.message}</p>}
      </div>

      {/* Confirmar senha */}
      <div style={fieldGap}>
        <label style={labelStyle}>Confirmar senha</label>
        <input
          type={showPass ? 'text' : 'password'}
          autoComplete="new-password" placeholder="Repita a senha"
          className={errors.confirm ? 'input-error' : 'input'}
          {...register('confirm')}
        />
        {errors.confirm && <p style={errStyle}>{errors.confirm.message}</p>}
      </div>

      {/* ── EULA / Política de privacidade ── */}
      <div
        style={{
          borderRadius: 'var(--radius-md)',
          border: `1px solid ${
            errors.acceptedTerms
              ? 'oklch(from var(--color-notification) l c h / 0.5)'
              : 'var(--color-border)'
          }`,
          overflow: 'hidden',
          background: 'var(--color-surface-offset)',
        }}
      >
        {/* Cabeçalho colapsável */}
        <button
          type="button"
          onClick={() => setEulaOpen(o => !o)}
          style={{
            width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            padding: '0.625rem 0.75rem', background: 'none', border: 'none', cursor: 'pointer',
            gap: '0.5rem',
          }}
          aria-expanded={eulaOpen}
        >
          <span style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--color-text)', textAlign: 'left' }}>
            📋 Termos de Uso e Política de Privacidade
          </span>
          {eulaOpen
            ? <ChevronUp  size={14} style={{ color: 'var(--color-text-muted)', flexShrink: 0 }} />
            : <ChevronDown size={14} style={{ color: 'var(--color-text-muted)', flexShrink: 0 }} />}
        </button>

        {/* Texto colapsável */}
        {eulaOpen && (
          <div
            style={{
              maxHeight: '14rem', overflowY: 'auto', padding: '0 0.75rem 0.75rem',
              borderTop: '1px solid var(--color-divider)',
              scrollbarWidth: 'thin',
            }}
          >
            <div style={{ paddingTop: '0.75rem' }}>
              <EulaText />
            </div>
          </div>
        )}

        {/* Checkbox de aceite */}
        <label
          style={{
            display: 'flex', alignItems: 'flex-start', gap: '0.625rem',
            padding: '0.625rem 0.75rem',
            borderTop: eulaOpen ? '1px solid var(--color-divider)' : 'none',
            cursor: 'pointer',
            background: accepted
              ? 'oklch(from var(--color-success) l c h / 0.06)'
              : 'transparent',
            transition: 'background 0.2s',
          }}
        >
          <input
            type="checkbox"
            style={{ marginTop: '0.1rem', accentColor: 'var(--color-primary)', flexShrink: 0 }}
            {...register('acceptedTerms')}
          />
          <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', lineHeight: 1.5 }}>
            Li e concordo com os{' '}
            <button
              type="button"
              onClick={() => setEulaOpen(o => !o)}
              style={{
                background: 'none', border: 'none', padding: 0, cursor: 'pointer',
                color: 'var(--color-primary)', fontWeight: 500, fontSize: 'inherit',
                textDecoration: 'underline',
              }}
            >
              Termos de Uso e Política de Privacidade
            </button>
            {' '}do SIG v2. Estou ciente de que as informações inseridas são de minha exclusiva responsabilidade.
          </span>
        </label>
      </div>

      {errors.acceptedTerms && (
        <p style={{ ...errStyle, marginTop: '-0.5rem' }}>{errors.acceptedTerms.message}</p>
      )}

      {/* Erro de API */}
      {apiError && (
        <div style={{
          fontSize: 'var(--text-xs)', color: 'var(--color-notification)',
          background: 'oklch(from var(--color-notification) l c h / 0.08)',
          border: '1px solid oklch(from var(--color-notification) l c h / 0.2)',
          borderRadius: 'var(--radius-md)', padding: '0.5rem 0.75rem',
        }}>{apiError}</div>
      )}

      <button
        type="submit" disabled={isSubmitting || !accepted}
        className="btn btn-primary w-full"
        style={{ fontWeight: 600, marginTop: '0.25rem', opacity: (!accepted) ? 0.5 : 1, transition: 'opacity 0.2s' }}
      >
        {isSubmitting ? 'Criando conta…' : 'Criar conta'}
      </button>

      <p style={{ fontSize: 'var(--text-xs)', textAlign: 'center', color: 'var(--color-text-muted)', margin: 0 }}>
        Já tem conta?{' '}
        <Link to="/login" style={{ color: 'var(--color-primary)', textDecoration: 'none', fontWeight: 500 }}>
          Entrar
        </Link>
      </p>
    </form>
  )
}
