import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { useAuth } from '@/contexts/AuthContext'
import { Eye, EyeOff, TrendingUp } from 'lucide-react'

const schema = z.object({
  email: z.string().email('E-mail inválido'),
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
      const err = e as { response?: { data?: { detail?: string } } }
      setApiError(err?.response?.data?.detail ?? 'Credenciais inválidas.')
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-light-100 dark:bg-dark-900 p-4">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="flex flex-col items-center mb-8">
          <div className="w-12 h-12 rounded-xl bg-brand-primary/10 flex items-center justify-center mb-3">
            <TrendingUp size={24} className="text-brand-primary" />
          </div>
          <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">SIG v2</h1>
          <p className="text-sm text-muted mt-1">Sistema de Investimentos</p>
        </div>

        <div className="card p-6 shadow-lg">
          <h2 className="text-base font-semibold mb-6 text-gray-900 dark:text-gray-100">Entrar</h2>

          <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                E-mail
              </label>
              <input
                type="email"
                autoComplete="email"
                placeholder="seu@email.com"
                className={errors.email ? 'input-error' : 'input'}
                {...register('email')}
              />
              {errors.email && (
                <p className="text-xs text-rose-400 mt-1">{errors.email.message}</p>
              )}
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                Senha
              </label>
              <div className="relative">
                <input
                  type={showPass ? 'text' : 'password'}
                  autoComplete="current-password"
                  placeholder="••••••••"
                  className={errors.password ? 'input-error pr-10' : 'input pr-10'}
                  {...register('password')}
                />
                <button
                  type="button"
                  onClick={() => setShowPass(p => !p)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
                  aria-label={showPass ? 'Ocultar senha' : 'Mostrar senha'}
                >
                  {showPass ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
              {errors.password && (
                <p className="text-xs text-rose-400 mt-1">{errors.password.message}</p>
              )}
            </div>

            {apiError && (
              <p className="text-xs text-rose-400 bg-rose-500/10 px-3 py-2 rounded-lg">
                {apiError}
              </p>
            )}

            <button type="submit" disabled={isSubmitting} className="btn-primary justify-center mt-2">
              {isSubmitting ? (
                <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
              ) : 'Entrar'}
            </button>
          </form>

          <p className="text-xs text-center text-muted mt-4">
            Não tem conta?{' '}
            <Link to="/register" className="text-brand-primary hover:underline">Cadastrar</Link>
          </p>
        </div>
      </div>
    </div>
  )
}
