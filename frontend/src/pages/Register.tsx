import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useNavigate, Link } from 'react-router-dom'
import api from '@/services/api'

const schema = z.object({
  name: z.string().min(2, 'Nome obrigatório'),
  email: z.string().email('E-mail inválido'),
  password: z.string().min(6, 'Mínimo 6 caracteres'),
})

type FormData = z.infer<typeof schema>

export default function Register() {
  const navigate = useNavigate()

  const { register, handleSubmit, formState: { errors, isSubmitting }, setError } = useForm<FormData>({
    resolver: zodResolver(schema),
  })

  const onSubmit = async (data: FormData) => {
    try {
      await api.post('/api/v1/auth/register', data)
      navigate('/auth/login')
    } catch {
      setError('root', { message: 'Erro ao cadastrar. Tente novamente.' })
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-950">
      <div className="w-full max-w-sm bg-gray-900 rounded-xl p-8 shadow-lg">
        <h1 className="text-2xl font-bold text-white mb-6 text-center">Criar conta</h1>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <label className="block text-sm text-gray-400 mb-1">Nome</label>
            <input {...register('name')} className="w-full bg-gray-800 text-white rounded-lg px-3 py-2 border border-gray-700 focus:outline-none focus:border-teal-500" />
            {errors.name && <p className="text-red-400 text-xs mt-1">{errors.name.message}</p>}
          </div>
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
            {isSubmitting ? 'Criando...' : 'Criar conta'}
          </button>
          <p className="text-center text-gray-500 text-sm">Já tem conta? <Link to="/auth/login" className="text-teal-400 hover:underline">Entrar</Link></p>
        </form>
      </div>
    </div>
  )
}
