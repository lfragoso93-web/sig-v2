import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Link } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import PasswordInput from '@/components/ui/PasswordInput'

const schema = z.object({
  email: z.string().email('E-mail inválido'),
  password: z.string().min(6, 'Mínimo 6 caracteres'),
})

type FormData = z.infer<typeof schema>

export default function Login() {
  const { login } = useAuth()

  const { register, handleSubmit, formState: { errors, isSubmitting }, setError } = useForm<FormData>({
    resolver: zodResolver(schema),
  })

  const onSubmit = async (data: FormData) => {
    try {
      await login(data.email, data.password)
    } catch {
      setError('root', { message: 'E-mail ou senha inválidos' })
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
      <h2 className="text-xl font-bold text-center" style={{ color: 'var(--color-text)' }}>Entrar</h2>

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
          autoComplete="current-password"
        />
        {errors.password && <p className="text-xs" style={{ color: 'var(--color-error)' }}>{errors.password.message}</p>}
        <div className="text-right">
          <Link
            to="/auth/esqueceu-senha"
            className="text-xs hover:underline"
            style={{ color: 'var(--color-primary)' }}
          >
            Esqueceu a senha?
          </Link>
        </div>
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
        {isSubmitting ? 'Entrando...' : 'Entrar'}
      </button>

      <p className="text-center text-sm" style={{ color: 'var(--color-text-muted)' }}>
        Não tem conta?{' '}
        <Link to="/auth/registro" className="hover:underline" style={{ color: 'var(--color-primary)' }}>Cadastre-se</Link>
      </p>
    </form>
  )
}
