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
    <div className="min-h-screen flex items-center justify-center" style={{ background: 'var(--color-bg)' }}>
      <div
        className="w-full max-w-sm rounded-xl p-8 shadow-lg"
        style={{ background: 'var(--color-surface)', border: '1px solid var(--color-border)' }}
      >
        <h1 className="text-2xl font-bold mb-6 text-center">Criar conta</h1>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <label className="block text-sm mb-1" style={{ color: 'var(--color-text-muted)' }}>Nome</label>
            <input {...register('name')} className="input w-full" />
            {errors.name && <p className="text-xs mt-1" style={{ color: 'var(--color-error)' }}>{errors.name.message}</p>}
          </div>
          <div>
            <label className="block text-sm mb-1" style={{ color: 'var(--color-text-muted)' }}>E-mail</label>
            <input {...register('email')} type="email" className="input w-full" />
            {errors.email && <p className="text-xs mt-1" style={{ color: 'var(--color-error)' }}>{errors.email.message}</p>}
          </div>
          <div>
            <label className="block text-sm mb-1" style={{ color: 'var(--color-text-muted)' }}>Senha</label>
            <input {...register('password')} type="password" className="input w-full" />
            {errors.password && <p className="text-xs mt-1" style={{ color: 'var(--color-error)' }}>{errors.password.message}</p>}
          </div>
          {errors.root && <p className="text-sm text-center" style={{ color: 'var(--color-error)' }}>{errors.root.message}</p>}
          <button type="submit" disabled={isSubmitting} className="btn btn-primary w-full py-2 font-semibold">
            {isSubmitting ? 'Criando...' : 'Criar conta'}
          </button>
          <p className="text-center text-sm" style={{ color: 'var(--color-text-muted)' }}>
            Já tem conta?{' '}
            <Link to="/auth/login" className="hover:underline" style={{ color: 'var(--color-primary)' }}>Entrar</Link>
          </p>
        </form>
      </div>
    </div>
  )
}
