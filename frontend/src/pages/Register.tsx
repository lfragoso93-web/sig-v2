import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useNavigate, Link } from 'react-router-dom'
import api from '@/services/api'
import PasswordInput from '@/components/ui/PasswordInput'

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
      await api.post('/auth/register', data)
      navigate('/login')
    } catch {
      setError('root', { message: 'Erro ao cadastrar. Tente novamente.' })
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
      <h2 className="text-xl font-bold text-center" style={{ color: 'var(--color-text)' }}>Criar conta</h2>

      <div className="flex flex-col gap-1.5">
        <label className="text-sm" style={{ color: 'var(--color-text-muted)' }}>Nome</label>
        <input
          {...register('name')}
          type="text"
          autoComplete="name"
          className="input w-full"
          style={{ fontSize: 16 }}
        />
        {errors.name && <p className="text-xs" style={{ color: 'var(--color-error)' }}>{errors.name.message}</p>}
      </div>

      <div className="flex flex-col gap-1.5">
        <label className="text-sm" style={{ color: 'var(--color-text-muted)' }}>E-mail</label>
        <input
          {...register('email')}
          type="email"
          autoComplete="email"
          className="input w-full"
          style={{ fontSize: 16 }}
        />
        {errors.email && <p className="text-xs" style={{ color: 'var(--color-error)' }}>{errors.email.message}</p>}
      </div>

      <div className="flex flex-col gap-1.5">
        <label className="text-sm" style={{ color: 'var(--color-text-muted)' }}>Senha</label>
        <PasswordInput
          {...register('password')}
          className="input w-full"
          style={{ fontSize: 16 }}
          autoComplete="new-password"
        />
        {errors.password && <p className="text-xs" style={{ color: 'var(--color-error)' }}>{errors.password.message}</p>}
      </div>

      {errors.root && (
        <p className="text-sm text-center" style={{ color: 'var(--color-error)' }}>{errors.root.message}</p>
      )}

      <button
        type="submit"
        disabled={isSubmitting}
        className="btn btn-primary w-full font-semibold"
        style={{ minHeight: 44 }}
      >
        {isSubmitting ? 'Criando...' : 'Criar conta'}
      </button>

      <p className="text-center text-sm" style={{ color: 'var(--color-text-muted)' }}>
        Já tem conta?{' '}
        <Link to="/login" className="hover:underline" style={{ color: 'var(--color-primary)' }}>Entrar</Link>
      </p>
    </form>
  )
}
