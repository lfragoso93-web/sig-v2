import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useNavigate, Link } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import api from '@/services/api'
import PasswordInput from '@/components/ui/PasswordInput'

const schema = z.object({
  email: z.string().email('E-mail inválido'),
  password: z.string().min(6, 'Mínimo 6 caracteres'),
})

type FormData = z.infer<typeof schema>

export default function Login() {
  const navigate = useNavigate()
  const login = useAuthStore((s) => s.login)

  const { register, handleSubmit, formState: { errors, isSubmitting }, setError } = useForm<FormData>({
    resolver: zodResolver(schema),
  })

  const onSubmit = async (data: FormData) => {
    try {
      const res = await api.post('/auth/login', {
        email: data.email,
        password: data.password,
      })
      api.defaults.headers.common['Authorization'] = `Bearer ${res.data.access_token}`
      if (res.data.refresh_token) {
        localStorage.setItem('sig_refresh', res.data.refresh_token)
      }
      const me = await api.get('/users/me')
      login(res.data.access_token, me.data)
      navigate('/carteira')
    } catch {
      setError('root', { message: 'E-mail ou senha inválidos' })
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center" style={{ background: 'var(--color-bg)' }}>
      <div
        className="w-full max-w-sm rounded-xl p-8 shadow-lg"
        style={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)' }}
      >
        <h1 className="text-2xl font-bold mb-6 text-center">SIG v2</h1>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">

          <div>
            <label className="block text-sm mb-1" style={{ color: 'var(--color-text-muted)' }}>E-mail</label>
            <input
              {...register('email')}
              type="email"
              className="input w-full"
            />
            {errors.email && <p className="text-xs mt-1" style={{ color: 'var(--color-error)' }}>{errors.email.message}</p>}
          </div>

          <div>
            <label className="block text-sm mb-1" style={{ color: 'var(--color-text-muted)' }}>Senha</label>
            <PasswordInput
              {...register('password')}
              className="input w-full"
            />
            {errors.password && <p className="text-xs mt-1" style={{ color: 'var(--color-error)' }}>{errors.password.message}</p>}
            <div className="text-right mt-1">
              <Link to="/auth/esqueceu-senha" className="text-xs hover:underline" style={{ color: 'var(--color-primary)' }}>
                Esqueceu a senha?
              </Link>
            </div>
          </div>

          {errors.root && <p className="text-sm text-center" style={{ color: 'var(--color-error)' }}>{errors.root.message}</p>}

          <button
            type="submit"
            disabled={isSubmitting}
            className="btn btn-primary w-full py-2 font-semibold"
          >
            {isSubmitting ? 'Entrando...' : 'Entrar'}
          </button>

          <p className="text-center text-sm" style={{ color: 'var(--color-text-muted)' }}>
            Não tem conta?{' '}
            <Link to="/auth/registro" className="hover:underline" style={{ color: 'var(--color-primary)' }}>Cadastre-se</Link>
          </p>

        </form>
      </div>
    </div>
  )
}
