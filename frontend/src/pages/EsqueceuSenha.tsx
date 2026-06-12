import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Link } from 'react-router-dom'
import api from '@/services/api'

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

export default function EsqueceuSenha() {
  const [step, setStep] = useState<'email' | 'reset' | 'done'>('email')
  const [resetToken, setResetToken] = useState('')
  const [emailSent, setEmailSent] = useState('')

  const emailForm = useForm<EmailForm>({ resolver: zodResolver(emailSchema) })
  const resetForm = useForm<ResetForm>({ resolver: zodResolver(resetSchema) })

  const onRequestReset = async (data: EmailForm) => {
    try {
      const res = await api.post('/api/v1/auth/forgot-password', { email: data.email })
      setResetToken(res.data.reset_token)
      setEmailSent(data.email)
      setStep('reset')
    } catch {
      emailForm.setError('root', { message: 'Erro ao solicitar recuperação. Tente novamente.' })
    }
  }

  const onResetPassword = async (data: ResetForm) => {
    try {
      await api.post('/api/v1/auth/reset-password', { token: resetToken, new_password: data.new_password })
      setStep('done')
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      resetForm.setError('root', { message: detail || 'Token inválido ou expirado. Solicite um novo link.' })
    }
  }

  const cardCls = "w-full max-w-sm rounded-xl p-8 shadow-lg"
  const cardStyle = { background: 'var(--color-surface)', border: '1px solid var(--color-border)' }
  const wrapCls = "min-h-screen flex items-center justify-center"
  const wrapStyle = { background: 'var(--color-bg)' }

  return (
    <div className={wrapCls} style={wrapStyle}>
      <div className={cardCls} style={cardStyle}>

        {step === 'email' && (
          <>
            <h1 className="text-xl font-bold mb-1 text-center">Recuperar senha</h1>
            <p className="text-sm text-center mb-6" style={{ color: 'var(--color-text-muted)' }}>
              Informe seu e-mail para receber as instruções.
            </p>
            <form onSubmit={emailForm.handleSubmit(onRequestReset)} className="space-y-4">
              <div>
                <label className="block text-sm mb-1" style={{ color: 'var(--color-text-muted)' }}>E-mail</label>
                <input
                  {...emailForm.register('email')}
                  type="email"
                  autoFocus
                  placeholder="seu@email.com"
                  className="input w-full"
                />
                {emailForm.formState.errors.email && (
                  <p className="text-xs mt-1" style={{ color: 'var(--color-error)' }}>{emailForm.formState.errors.email.message}</p>
                )}
              </div>
              {emailForm.formState.errors.root && (
                <p className="text-sm text-center" style={{ color: 'var(--color-error)' }}>{emailForm.formState.errors.root.message}</p>
              )}
              <button
                type="submit"
                disabled={emailForm.formState.isSubmitting}
                className="btn btn-primary w-full py-2 font-semibold"
              >
                {emailForm.formState.isSubmitting ? 'Enviando...' : 'Enviar instruções'}
              </button>
              <p className="text-center text-sm" style={{ color: 'var(--color-text-muted)' }}>
                Lembrou?{' '}
                <Link to="/auth/login" className="hover:underline" style={{ color: 'var(--color-primary)' }}>Entrar</Link>
              </p>
            </form>
          </>
        )}

        {step === 'reset' && (
          <>
            <h1 className="text-xl font-bold mb-1 text-center">Nova senha</h1>
            <p className="text-sm text-center mb-6" style={{ color: 'var(--color-text-muted)' }}>
              Defina uma nova senha para <strong>{emailSent}</strong>.
            </p>
            <form onSubmit={resetForm.handleSubmit(onResetPassword)} className="space-y-4">
              <div>
                <label className="block text-sm mb-1" style={{ color: 'var(--color-text-muted)' }}>Nova senha</label>
                <input {...resetForm.register('new_password')} type="password" autoFocus className="input w-full" />
                {resetForm.formState.errors.new_password && (
                  <p className="text-xs mt-1" style={{ color: 'var(--color-error)' }}>{resetForm.formState.errors.new_password.message}</p>
                )}
              </div>
              <div>
                <label className="block text-sm mb-1" style={{ color: 'var(--color-text-muted)' }}>Confirmar senha</label>
                <input {...resetForm.register('confirm_password')} type="password" className="input w-full" />
                {resetForm.formState.errors.confirm_password && (
                  <p className="text-xs mt-1" style={{ color: 'var(--color-error)' }}>{resetForm.formState.errors.confirm_password.message}</p>
                )}
              </div>
              {resetForm.formState.errors.root && (
                <p className="text-sm text-center" style={{ color: 'var(--color-error)' }}>{resetForm.formState.errors.root.message}</p>
              )}
              <button
                type="submit"
                disabled={resetForm.formState.isSubmitting}
                className="btn btn-primary w-full py-2 font-semibold"
              >
                {resetForm.formState.isSubmitting ? 'Salvando...' : 'Salvar nova senha'}
              </button>
            </form>
          </>
        )}

        {step === 'done' && (
          <div className="text-center space-y-4">
            <div className="text-4xl">✅</div>
            <h1 className="text-xl font-bold">Senha alterada!</h1>
            <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>Sua senha foi redefinida com sucesso.</p>
            <Link to="/auth/login" className="btn btn-primary block w-full py-2 font-semibold text-center">
              Ir para o login
            </Link>
          </div>
        )}
      </div>
    </div>
  )
}
