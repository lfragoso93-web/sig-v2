import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useNavigate, Link } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import api from '@/services/api'

const schema = z.object({
  email: z.string().email('E-mail inválido'),
  password: z.string().min(6, 'Mínimo 6 caracteres'),
})

type FormData = z.infer<typeof schema>

export default function Login() {
  const navigate = useNavigate()
  const login = useAuthStore((s: { login: (token: string, user: unknown) => void }) => s.login)

  const { register, handleSubmit, formState: { errors, isSubmitting }, setError } = useForm<FormData>({
    resolver: zodResolver(schema),
  })

  const onSubmit = async (data: FormData) => {
    try {
      const params = new URLSearchParams()
      params.append('username', data.email)
      params.append('password', data.password)
      const res = await api.post('/auth/token', params, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      })
      login(res.data.access_token, res.data.user)
      navigate('/')
    } catch {
      setError('root', { message: 'Credenciais inválidas' })
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-950">
      <div className="w-full max-w-sm bg-gray-900 rounded-xl p-8 shadow-lg">
        <h1 className="text-2xl font-bold text-white mb-6 text-center">SIG v2</h1>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <label className="block text-sm text-gray-400 mb-1">E-mail</label>
            <input {...register('email')} type="email" className="w-full bg-gray-800 text-white rounded-lg px-3 py-2 border border-gray-700 focus:outline-none focus:border-teal-500" />
            {errors.email && <p className="text-red-400 text-xs mt-1">{errors.email.message}</p>}
          </div>
          <div>
            <label className="block text-sm text-gray-400 mb-1">Senha</label>
            <input {...register('password')} type="password" className="w-full bg-gray-800 text-white rounded-lg px-3 py-2 border border-gray-700 focus:outline-none focus:border-teal-500" />
            {errors.password && <p className="text-red-400 text-xs mt-1">{errors.password.message}</p>}
          </div>
          {errors.root && <p className="text-red-400 text-sm text-center">{errors.root.message}</p>}
          <button type="submit" disabled={isSubmitting} className="w-full bg-teal-600 hover:bg-teal-500 text-white font-semibold py-2 rounded-lg transition">
            {isSubmitting ? 'Entrando...' : 'Entrar'}
          </button>
          <p className="text-center text-gray-500 text-sm">Não tem conta? <Link to="/register" className="text-teal-400 hover:underline">Cadastre-se</Link></p>
        </form>
      </div>
    </div>
  )
}
