import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import api from '@/services/api'
import { Eye, EyeOff } from 'lucide-react'

const schema = z.object({
  name:     z.string().min(2, 'Informe seu nome'),
  email:    z.string().email('E-mail inválido'),
  password: z.string().min(8, 'Mínimo 8 caracteres'),
  confirm:  z.string(),
}).refine(d => d.password === d.confirm, {
  message: 'As senhas não coincidem',
  path: ['confirm'],
})
type FormData = z.infer<typeof schema>

export default function RegisterPage() {
  const navigate = useNavigate()
  const [showPass, setShowPass] = useState(false)
  const [apiError, setApiError] = useState('')

  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormData>({
    resolver: zodResolver(schema),
  })

  const onSubmit = async (data: FormData) => {
    setApiError('')
    try {
      await api.post('/auth/register', { name: data.name, email: data.email, password: data.password })
      navigate('/auth/login?registered=1')
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } } }
      setApiError(err?.response?.data?.detail ?? 'Erro ao criar conta. Tente novamente.')
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>

      <div style={{ marginBottom: '0.25rem' }}>
        <h2 style={{ fontSize: 'var(--text-lg)', fontWeight: 650, color: 'var(--color-text)', margin: 0, letterSpacing: '-0.01em' }}>
          Criar conta
        </h2>
        <p style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', margin: '0.25rem 0 0' }}>
          Preencha os dados para se cadastrar
        </p>
      </div>

      {/* Nome */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.375rem' }}>
        <label style={{ fontSize: 'var(--text-xs)', fontWeight: 500, color: 'var(--color-text-muted)' }}>Nome</label>
        <input
          type="text"
          autoComplete="name"
          placeholder="Seu nome completo"
          className={errors.name ? 'input-error' : 'input'}
          {...register('name')}
        />
        {errors.name && <p style={{ fontSize: 'var(--text-xs)', color: 'var(--color-notification)', margin: 0 }}>{errors.name.message}</p>}
      </div>

      {/* E-mail */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.375rem' }}>
        <label style={{ fontSize: 'var(--text-xs)', fontWeight: 500, color: 'var(--color-text-muted)' }}>E-mail</label>
        <input
          type="email"
          autoComplete="email"
          placeholder="seu@email.com"
          className={errors.email ? 'input-error' : 'input'}
          {...register('email')}
        />
        {errors.email && <p style={{ fontSize: 'var(--text-xs)', color: 'var(--color-notification)', margin: 0 }}>{errors.email.message}</p>}
      </div>

      {/* Senha */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.375rem' }}>
        <label style={{ fontSize: 'var(--text-xs)', fontWeight: 500, color: 'var(--color-text-muted)' }}>Senha</label>
        <div style={{ position: 'relative' }}>
          <input
            type={showPass ? 'text' : 'password'}
            autoComplete="new-password"
            placeholder="Mínimo 8 caracteres"
            className={errors.password ? 'input-error' : 'input'}
            style={{ paddingRight: '2.5rem' }}
            {...register('password')}
          />
          <button
            type="button" onClick={() => setShowPass(p => !p)}
            style={{ position: 'absolute', right: '0.75rem', top: '50%', transform: 'translateY(-50%)',
              background: 'none', border: 'none', cursor: 'pointer', padding: 0,
              color: 'var(--color-text-muted)', display: 'flex', alignItems: 'center' }}
            aria-label={showPass ? 'Ocultar senha' : 'Mostrar senha'}
          >
            {showPass ? <EyeOff size={15} /> : <Eye size={15} />}
          </button>
        </div>
        {errors.password && <p style={{ fontSize: 'var(--text-xs)', color: 'var(--color-notification)', margin: 0 }}>{errors.password.message}</p>}
      </div>

      {/* Confirmar senha */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.375rem' }}>
        <label style={{ fontSize: 'var(--text-xs)', fontWeight: 500, color: 'var(--color-text-muted)' }}>Confirmar senha</label>
        <input
          type={showPass ? 'text' : 'password'}
          autoComplete="new-password"
          placeholder="Repita a senha"
          className={errors.confirm ? 'input-error' : 'input'}
          {...register('confirm')}
        />
        {errors.confirm && <p style={{ fontSize: 'var(--text-xs)', color: 'var(--color-notification)', margin: 0 }}>{errors.confirm.message}</p>}
      </div>

      {/* Erro da API */}
      {apiError && (
        <div style={{
          fontSize: 'var(--text-xs)', color: 'var(--color-notification)',
          background: 'oklch(from var(--color-notification) l c h / 0.08)',
          border: '1px solid oklch(from var(--color-notification) l c h / 0.2)',
          borderRadius: 'var(--radius-md)', padding: '0.5rem 0.75rem',
        }}>{apiError}</div>
      )}

      <button
        type="submit" disabled={isSubmitting}
        className="btn btn-primary w-full"
        style={{ fontWeight: 600, marginTop: '0.25rem' }}
      >
        {isSubmitting ? 'Criando conta…' : 'Criar conta'}
      </button>

      <p style={{ fontSize: 'var(--text-xs)', textAlign: 'center', color: 'var(--color-text-muted)', margin: 0 }}>
        Já tem conta?{' '}
        <Link to="/auth/login" style={{ color: 'var(--color-primary)', textDecoration: 'none', fontWeight: 500 }}>
          Entrar
        </Link>
      </p>
    </form>
  )
}
