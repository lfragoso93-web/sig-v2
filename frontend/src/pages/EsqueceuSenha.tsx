import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Link } from 'react-router-dom'
import api from '@/services/api'

// --- Etapa 1: solicitar o token ---
const emailSchema = z.object({
  email: z.string().email('E-mail inválido'),
})

// --- Etapa 2: nova senha ---
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

  // --- Formulário etapa 1 ---
  const emailForm = useForm<EmailForm>({
    resolver: zodResolver(emailSchema),
  })

  // --- Formulário etapa 2 ---
  const resetForm = useForm<ResetForm>({
    resolver: zodResolver(resetSchema),
  })

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
      await api.post('/api/v1/auth/reset-password', {
        token: resetToken,
        new_password: data.new_password,
      })
      setStep('done')
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      resetForm.setError('root', {
        message: detail || 'Token inválido ou expirado. Solicite um novo link.',
      })
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-950">
      <div className="w-full max-w-sm bg-gray-900 rounded-xl p-8 shadow-lg">

        {/* Etapa 1: informar e-mail */}
        {step === 'email' && (
          <>
            <h1 className="text-xl font-bold text-white mb-1 text-center">Recuperar senha</h1>
            <p className="text-gray-400 text-sm text-center mb-6">
              Informe seu e-mail para receber as instruções.
            </p>
            <form onSubmit={emailForm.handleSubmit(onRequestReset)} className="space-y-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1">E-mail</label>
                <input
                  {...emailForm.register('email')}
                  type="email"
                  autoFocus
                  placeholder="seu@email.com"
                  className="w-full bg-gray-800 text-white rounded-lg px-3 py-2 border border-gray-700 focus:outline-none focus:border-teal-500"
                />
                {emailForm.formState.errors.email && (
                  <p className="text-red-400 text-xs mt-1">{emailForm.formState.errors.email.message}</p>
                )}
              </div>
              {emailForm.formState.errors.root && (
                <p className="text-red-400 text-sm text-center">{emailForm.formState.errors.root.message}</p>
              )}
              <button
                type="submit"
                disabled={emailForm.formState.isSubmitting}
                className="w-full bg-teal-600 hover:bg-teal-500 text-white font-semibold py-2 rounded-lg transition"
              >
                {emailForm.formState.isSubmitting ? 'Aguarde...' : 'Continuar'}
              </button>
              <p className="text-center text-gray-500 text-sm">
                <Link to="/auth/login" className="text-teal-400 hover:underline">← Voltar ao login</Link>
              </p>
            </form>
          </>
        )}

        {/* Etapa 2: nova senha */}
        {step === 'reset' && (
          <>
            <h1 className="text-xl font-bold text-white mb-1 text-center">Nova senha</h1>
            <p className="text-gray-400 text-sm text-center mb-6">
              Defina a nova senha para <span className="text-teal-400">{emailSent}</span>
            </p>
            <form onSubmit={resetForm.handleSubmit(onResetPassword)} className="space-y-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1">Nova senha</label>
                <input
                  {...resetForm.register('new_password')}
                  type="password"
                  autoFocus
                  placeholder="Mínimo 8 caracteres"
                  className="w-full bg-gray-800 text-white rounded-lg px-3 py-2 border border-gray-700 focus:outline-none focus:border-teal-500"
                />
                {resetForm.formState.errors.new_password && (
                  <p className="text-red-400 text-xs mt-1">{resetForm.formState.errors.new_password.message}</p>
                )}
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">Confirmar senha</label>
                <input
                  {...resetForm.register('confirm_password')}
                  type="password"
                  placeholder="Repita a nova senha"
                  className="w-full bg-gray-800 text-white rounded-lg px-3 py-2 border border-gray-700 focus:outline-none focus:border-teal-500"
                />
                {resetForm.formState.errors.confirm_password && (
                  <p className="text-red-400 text-xs mt-1">{resetForm.formState.errors.confirm_password.message}</p>
                )}
              </div>
              {resetForm.formState.errors.root && (
                <p className="text-red-400 text-sm text-center">{resetForm.formState.errors.root.message}</p>
              )}
              <button
                type="submit"
                disabled={resetForm.formState.isSubmitting}
                className="w-full bg-teal-600 hover:bg-teal-500 text-white font-semibold py-2 rounded-lg transition"
              >
                {resetForm.formState.isSubmitting ? 'Salvando...' : 'Redefinir senha'}
              </button>
              <button
                type="button"
                onClick={() => setStep('email')}
                className="w-full text-gray-500 text-sm hover:text-gray-300 transition"
              >
                ← Solicitar novamente
              </button>
            </form>
          </>
        )}

        {/* Etapa 3: sucesso */}
        {step === 'done' && (
          <div className="text-center space-y-4">
            <div className="text-4xl">✅</div>
            <h1 className="text-xl font-bold text-white">Senha redefinida!</h1>
            <p className="text-gray-400 text-sm">
              Sua senha foi atualizada com sucesso. Agora você pode fazer login.
            </p>
            <Link
              to="/auth/login"
              className="block w-full bg-teal-600 hover:bg-teal-500 text-white font-semibold py-2 rounded-lg transition text-center"
            >
              Ir para o login
            </Link>
          </div>
        )}
      </div>
    </div>
  )
}
