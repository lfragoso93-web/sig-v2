import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Link } from 'react-router-dom'
import api from '@/services/api'
import { getApiErrorDetail } from '@/utils/apiError'

const emailSchema = z.object({
  email: z.string().email('E-mail inválido'),
})

const resetSchema = z.object({
  new_password: z.string().min(8, 'Mínimo 8 caracteres'),
  confirm_password: z.string(),
}).refine((d) => d.new_password === d.confirm_password, {
  message: 'As senhas não coincidem',
  path: ['confirm_password'],
})

type EmailForm = z.infer<typeof emailSchema>
type ResetForm = z.infer<typeof resetSchema>

const titleStyle: React.CSSProperties = {
  fontSize: 'var(--text-lg)',
  fontWeight: 650,
  color: 'var(--color-text)',
  margin: 0,
  letterSpacing: '-0.01em',
}

const subtitleStyle: React.CSSProperties = {
  fontSize: 'var(--text-xs)',
  color: 'var(--color-text-muted)',
  margin: '0.25rem 0 0',
}

const labelStyle: React.CSSProperties = {
  fontSize: 'var(--text-xs)',
  fontWeight: 500,
  color: 'var(--color-text-muted)',
}

const errorStyle: React.CSSProperties = {
  fontSize: 'var(--text-xs)',
  color: 'var(--color-error)',
  margin: '0.25rem 0 0',
}

export default function EsqueceuSenha() {
  const [step, setStep] = useState<'email' | 'reset' | 'done'>('email')
  const [resetToken, setResetToken] = useState('')
  const [emailSent, setEmailSent] = useState('')

  const emailForm = useForm<EmailForm>({ resolver: zodResolver(emailSchema) })
  const resetForm = useForm<ResetForm>({ resolver: zodResolver(resetSchema) })

  const onRequestReset = async (data: EmailForm) => {
    try {
      const res = await api.post('/auth/forgot-password', { email: data.email })
      setResetToken(res.data.reset_token)
      setEmailSent(data.email)
      setStep('reset')
    } catch {
      emailForm.setError('root', { message: 'Erro ao solicitar recuperação. Tente novamente.' })
    }
  }

  const onResetPassword = async (data: ResetForm) => {
    try {
      await api.post('/auth/reset-password', { token: resetToken, new_password: data.new_password })
      setStep('done')
    } catch (error: unknown) {
      resetForm.setError('root', {
        message: getApiErrorDetail(error) ?? 'Token inválido ou expirado. Solicite um novo link.',
      })
    }
  }

  if (step === 'email') {
    return (
      <form onSubmit={emailForm.handleSubmit(onRequestReset)} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
        <div style={{ marginBottom: '0.25rem' }}>
          <h2 style={titleStyle}>Recuperar senha</h2>
          <p style={subtitleStyle}>Informe seu e-mail para receber as instruções.</p>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.375rem' }}>
          <label style={labelStyle}>E-mail</label>
          <input
            {...emailForm.register('email')}
            type="email"
            autoFocus
            placeholder="seu@email.com"
            className="input w-full"
          />
          {emailForm.formState.errors.email && <p style={errorStyle}>{emailForm.formState.errors.email.message}</p>}
        </div>

        {emailForm.formState.errors.root && <p style={errorStyle}>{emailForm.formState.errors.root.message}</p>}

        <button type="submit" disabled={emailForm.formState.isSubmitting} className="btn btn-primary w-full" style={{ fontWeight: 600, marginTop: '0.25rem' }}>
          {emailForm.formState.isSubmitting ? 'Enviando...' : 'Enviar instruções'}
        </button>

        <p style={{ fontSize: 'var(--text-xs)', textAlign: 'center', color: 'var(--color-text-muted)', margin: 0 }}>
          Lembrou? <Link to="/auth/login" className="hover:underline" style={{ color: 'var(--color-primary)' }}>Entrar</Link>
        </p>
      </form>
    )
  }

  if (step === 'reset') {
    return (
      <form onSubmit={resetForm.handleSubmit(onResetPassword)} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
        <div style={{ marginBottom: '0.25rem' }}>
          <h2 style={titleStyle}>Nova senha</h2>
          <p style={subtitleStyle}>Defina uma nova senha para <strong>{emailSent}</strong>.</p>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.375rem' }}>
          <label style={labelStyle}>Nova senha</label>
          <input {...resetForm.register('new_password')} type="password" autoFocus className="input w-full" />
          {resetForm.formState.errors.new_password && <p style={errorStyle}>{resetForm.formState.errors.new_password.message}</p>}
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.375rem' }}>
          <label style={labelStyle}>Confirmar senha</label>
          <input {...resetForm.register('confirm_password')} type="password" className="input w-full" />
          {resetForm.formState.errors.confirm_password && <p style={errorStyle}>{resetForm.formState.errors.confirm_password.message}</p>}
        </div>

        {resetForm.formState.errors.root && <p style={errorStyle}>{resetForm.formState.errors.root.message}</p>}

        <button type="submit" disabled={resetForm.formState.isSubmitting} className="btn btn-primary w-full" style={{ fontWeight: 600, marginTop: '0.25rem' }}>
          {resetForm.formState.isSubmitting ? 'Salvando...' : 'Salvar nova senha'}
        </button>
      </form>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem', textAlign: 'center' }}>
      <div className="text-4xl">✅</div>
      <h2 style={{ ...titleStyle, textAlign: 'center' }}>Senha alterada!</h2>
      <p style={{ fontSize: 'var(--text-sm)', color: 'var(--color-text-muted)', margin: 0 }}>Sua senha foi redefinida com sucesso.</p>
      <Link to="/auth/login" className="btn btn-primary block w-full font-semibold text-center">Ir para o login</Link>
    </div>
  )
}
