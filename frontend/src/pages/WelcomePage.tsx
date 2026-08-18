import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { TrendingUp, LayoutDashboard, ArrowRightLeft, BarChart2, Rocket, Check, Plus, Loader2, X } from 'lucide-react'
import { useCreatePortfolio } from '@/hooks/usePortfolios'
import { useAuth } from '@/contexts/AuthContext'
import api from '@/services/api'

// ── Confetti ────────────────────────────────────────────
function launchConfetti() {
  const colors = ['#4f98a3', '#6daa45', '#e8af34', '#fdab43', '#a86fdf', '#5591c7', '#d163a7']
  const layer = document.createElement('div')
  layer.style.cssText = 'position:fixed;inset:0;pointer-events:none;overflow:hidden;z-index:9999;'
  document.body.appendChild(layer)
  for (let i = 0; i < 90; i++) {
    const c = document.createElement('div')
    const size = 6 + Math.random() * 6
    c.style.cssText = [
      'position:absolute',
      `left:${Math.random() * 100}%`,
      `top:-20px`,
      `width:${size}px`,
      `height:${size}px`,
      `background:${colors[Math.floor(Math.random() * colors.length)]}`,
      `border-radius:${Math.random() > 0.5 ? '50%' : '2px'}`,
      `animation:sig-fall ${1.2 + Math.random() * 1.4}s ${Math.random() * 0.5}s linear both`,
    ].join(';')
    layer.appendChild(c)
  }
  if (!document.getElementById('sig-confetti-style')) {
    const style = document.createElement('style')
    style.id = 'sig-confetti-style'
    style.textContent = '@keyframes sig-fall{0%{transform:translateY(0) rotate(0deg);opacity:1}100%{transform:translateY(110vh) rotate(720deg);opacity:0}}'
    document.head.appendChild(style)
  }
  setTimeout(() => document.body.removeChild(layer), 2800)
}

// ── Steps definition ──────────────────────────────────────
const STEPS = [
  {
    id: 1,
    icon: TrendingUp,
    color: 'var(--color-primary)',
    label: 'Passo 1 de 5',
    title: 'Suas Carteiras',
    desc: 'No SIG, tudo gira em torno de carteiras. Crie uma para cada corretora, estratégia ou perfil e acompanhe cada uma de forma independente.',
    pills: ['📂 Múltiplas carteiras', '🔀 Por corretora ou estratégia', '📊 Relatórios individuais', '🎯 Metas por carteira'],
  },
  {
    id: 2,
    icon: LayoutDashboard,
    color: 'var(--color-blue)',
    label: 'Passo 2 de 5',
    title: 'Dashboard — Visão Geral',
    desc: 'A tela principal mostra sua posição consolidada: patrimônio total, rentabilidade, distribuição por ativo e evolução histórica em tempo real.',
    pills: ['📈 Patrimônio total', '🥧 Distribuição por ativo', '📅 Evolução histórica', '🔄 Atualização em tempo real'],
  },
  {
    id: 3,
    icon: ArrowRightLeft,
    color: 'var(--color-gold)',
    label: 'Passo 3 de 5',
    title: 'Lançamentos',
    desc: 'Registre suas compras, vendas e proventos. O SIG calcula automaticamente preço médio, posição atual, IR a pagar e rentabilidade de cada ativo.',
    pills: ['📥 Compra & venda', '💵 Dividendos e JCP', '📋 Preço médio automático', '🔢 Cálculo de IR'],
  },
  {
    id: 4,
    icon: BarChart2,
    color: 'var(--color-success)',
    label: 'Passo 4 de 5',
    title: 'Rentabilidade & Metas',
    desc: 'Acompanhe sua performance real, compare com CDI e IBOV, e defina metas de alocação para manter sua estratégia no trilho com alertas de rebalanceamento.',
    pills: ['📉 vs. CDI / IBOV', '🏆 Metas por ativo', '⚖️ Rebalanceamento', '🗓️ Histórico mensal'],
  },
  {
    id: 5,
    icon: Rocket,
    color: 'var(--color-primary)',
    label: 'Passo 5 de 5 — Hora de começar!',
    title: 'Crie sua primeira carteira',
    desc: 'Dê um nome para sua carteira — pode ser o nome da corretora, da estratégia ou o que preferir. Você pode criar mais e renomear a qualquer momento.',
    pills: [],
  },
]

// ── Stepper dots ──────────────────────────────────────────────────
function StepDot({ n, state }: { n: number; state: 'pending' | 'active' | 'done' }) {
  return (
    <div
      style={{
        width: 28, height: 28, borderRadius: '50%', flexShrink: 0,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: '.6875rem', fontWeight: 700, transition: 'all .25s',
        border: `2px solid ${
          state === 'done'   ? 'var(--color-success)' :
          state === 'active' ? 'var(--color-primary)' :
          'var(--color-border)'
        }`,
        background: (
          state === 'done'   ? 'var(--color-success)' :
          state === 'active' ? 'var(--color-primary)' :
          'var(--color-surface-offset)'
        ),
        color: state === 'pending' ? 'var(--color-text-faint)' : (
          state === 'done' ? '#fff' : 'var(--color-text-inverse)'
        ),
        boxShadow: state === 'active' ? '0 0 0 4px oklch(from var(--color-primary) l c h / 0.2)' : 'none',
      }}
    >
      {state === 'done' ? <Check size={11} /> : n}
    </div>
  )
}

// ── WelcomePage ───────────────────────────────────────────────────
export default function WelcomePage() {
  const { user, refreshUser } = useAuth()
  const navigate = useNavigate()
  const [current, setCurrent] = useState(1)
  const [walletName, setWalletName] = useState('')
  const [finishing, setFinishing] = useState(false)
  const [portfolioCreated, setPortfolioCreated] = useState(false)
  const [finishError, setFinishError] = useState<string | null>(null)
  const { mutateAsync: createPortfolio } = useCreatePortfolio()

  // Sem guard de redirecionamento aqui — o ProtectedRoute já cuida disso.
  // Se o usuário já completou onboarding e acessar /welcome diretamente,
  // o ProtectedRoute NÃO irá redirecionar (onboarding_completed=true),
  // porém navegamos para /carteira para evitar que o usuário fique preso.
  // Isso é feito abaixo apenas como safeguard passive.

  const markDone = async () => {
    await api.patch('/users/me/onboarding')
    await refreshUser()
  }

  const handleSkip = async () => {
    setFinishing(true)
    setFinishError(null)
    try {
      await markDone()
      navigate('/carteira', { replace: true })
    } catch {
      setFinishError('Não foi possível concluir o onboarding. Tente novamente.')
      setFinishing(false)
    }
  }

  const handleCreate = async () => {
    if (!portfolioCreated && !walletName.trim()) return
    setFinishing(true)
    setFinishError(null)
    let created = portfolioCreated
    try {
      if (!created) {
        await createPortfolio({ name: walletName.trim() })
        created = true
        setPortfolioCreated(true)
      }
      await markDone()
      launchConfetti()
      setTimeout(() => navigate('/carteira', { replace: true }), 900)
    } catch {
      setFinishError(
        created
          ? 'Carteira criada, mas não foi possível concluir o onboarding. Tente concluir novamente.'
          : 'Não foi possível criar a carteira. Tente novamente.',
      )
      setFinishing(false)
    }
  }

  const next = () => { if (current < 5) setCurrent(c => c + 1) }
  const prev = () => { if (current > 1) setCurrent(c => c - 1) }

  const step = STEPS[current - 1]
  const StepIcon = step.icon

  return (
    <div style={{
      minHeight: '100dvh', background: 'var(--color-bg)',
      display: 'flex', flexDirection: 'column', alignItems: 'center',
      justifyContent: 'center', padding: '1.5rem 1rem',
    }}>

      <div style={{ width: '100%', maxWidth: 560, display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>

        {/* Logo */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '.5rem' }}>
            <div style={{
              width: 32, height: 32, borderRadius: 'var(--radius-md)',
              background: 'var(--color-primary)', display: 'flex',
              alignItems: 'center', justifyContent: 'center',
            }}>
              <TrendingUp size={16} color="white" />
            </div>
            <span style={{ fontSize: '.875rem', fontWeight: 700, letterSpacing: '-.02em', color: 'var(--color-text)' }}>SIG</span>
          </div>
          <button
            onClick={handleSkip}
            disabled={finishing}
            style={{
              fontSize: '.75rem', color: 'var(--color-text-faint)', background: 'none',
              border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '.375rem',
            }}
          >
            <X size={12} /> Pular tour
          </button>
        </div>

        {/* Card */}
        <div style={{
          background: 'var(--color-surface)', border: '1px solid var(--color-border)',
          borderRadius: 'var(--radius-xl)', padding: '2rem', boxShadow: 'var(--shadow-lg)',
        }}>

          {/* Header de boas-vindas */}
          <div style={{ textAlign: 'center', paddingBottom: '1.5rem', borderBottom: '1px solid var(--color-divider)', marginBottom: '1.5rem' }}>
            <div style={{
              width: 64, height: 64, borderRadius: '50%', margin: '0 auto 1rem',
              background: 'oklch(from var(--color-primary) l c h / 0.15)',
              border: '2px solid var(--color-primary)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: '1.5rem', fontWeight: 700, color: 'var(--color-primary)',
            }}>
              {(user?.name ?? user?.email ?? '?')[0].toUpperCase()}
            </div>
            <h1 style={{ fontSize: '1.25rem', fontWeight: 700, letterSpacing: '-.02em', color: 'var(--color-text)', marginBottom: '.375rem' }}>
              Bem-vindo ao SIG, {user?.name?.split(' ')[0] ?? 'você'}! 👋
            </h1>
            <p style={{ fontSize: '.8125rem', color: 'var(--color-text-muted)', maxWidth: '38ch', margin: '0 auto', lineHeight: 1.6 }}>
              Você está a poucos passos de ter o controle completo dos seus investimentos.
            </p>
          </div>

          {/* Progress bar */}
          <div style={{ height: 3, background: 'var(--color-divider)', borderRadius: 'var(--radius-full)', overflow: 'hidden', marginBottom: '1.5rem' }}>
            <div style={{
              height: '100%', background: 'var(--color-primary)', borderRadius: 'var(--radius-full)',
              width: `${(current / 5) * 100}%`, transition: 'width .4s cubic-bezier(.16,1,.3,1)',
            }} />
          </div>

          {/* Stepper */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '1.5rem' }}>
            {STEPS.map((s, i) => (
              <>
                <StepDot
                  key={s.id}
                  n={s.id}
                  state={current > s.id ? 'done' : current === s.id ? 'active' : 'pending'}
                />
                {i < STEPS.length - 1 && (
                  <div key={`line-${s.id}`} style={{
                    flex: 1, height: 2, maxWidth: 40,
                    background: current > s.id ? 'var(--color-success)' : 'var(--color-divider)',
                    transition: 'background .3s',
                  }} />
                )}
              </>
            ))}
          </div>

          {/* Step content */}
          <div>
            <div style={{
              width: 48, height: 48, borderRadius: 'var(--radius-lg)',
              background: `oklch(from ${step.color} l c h / 0.14)`,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              marginBottom: '1rem',
            }}>
              <StepIcon size={22} style={{ color: step.color }} />
            </div>

            <p style={{ fontSize: '.6875rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '.06em', color: 'var(--color-primary)', marginBottom: '.375rem' }}>
              {step.label}
            </p>
            <h2 style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--color-text)', marginBottom: '.5rem', letterSpacing: '-.015em' }}>
              {step.title}
            </h2>
            <p style={{ fontSize: '.8125rem', color: 'var(--color-text-muted)', lineHeight: 1.6, maxWidth: '46ch' }}>
              {step.desc}
            </p>

            {step.pills.length > 0 && (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '.5rem', marginTop: '1rem' }}>
                {step.pills.map(pill => (
                  <span key={pill} style={{
                    display: 'inline-flex', alignItems: 'center', gap: '.375rem',
                    background: 'var(--color-surface-offset)', border: '1px solid var(--color-border)',
                    borderRadius: 'var(--radius-full)', padding: '.3rem .75rem',
                    fontSize: '.75rem', color: 'var(--color-text-muted)',
                  }}>{pill}</span>
                ))}
              </div>
            )}

            {/* Step 5 — criar carteira */}
            {current === 5 && (
              <div style={{ marginTop: '1.25rem', display: 'flex', flexDirection: 'column', gap: '.75rem' }}>
                <label style={{ fontSize: '.75rem', fontWeight: 500, color: 'var(--color-text-muted)' }}>Nome da carteira</label>
                <div style={{ display: 'flex', gap: '.5rem' }}>
                  <input
                    value={walletName}
                    onChange={e => setWalletName(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && handleCreate()}
                    placeholder="Ex: Renda Variável, XP, Longo Prazo…"
                    maxLength={40}
                    disabled={finishing || portfolioCreated}
                    className="input"
                    style={{ flex: 1 }}
                  />
                  <button
                    onClick={handleCreate}
                    disabled={(!walletName.trim() && !portfolioCreated) || finishing}
                    className="btn btn-primary"
                    style={{ paddingLeft: '.875rem', paddingRight: '.875rem' }}
                  >
                    {finishing
                      ? <Loader2 size={16} className="animate-spin" />
                      : portfolioCreated
                        ? <><Check size={14} /> Concluir</>
                        : <><Plus size={14} /> Criar</>
                    }
                  </button>
                </div>
                <p style={{ fontSize: '.75rem', color: 'var(--color-text-faint)' }}>
                  Você pode renomear ou excluir carteiras a qualquer momento em Configurações.
                </p>
              </div>
            )}
          </div>

          {finishError && (
            <p role="alert" style={{ fontSize: '.75rem', color: 'var(--color-error)', marginTop: '1rem' }}>
              {finishError}
            </p>
          )}

          {/* Nav */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '1.5rem', paddingTop: '1.5rem', borderTop: '1px solid var(--color-divider)' }}>
            <span style={{ fontSize: '.75rem', color: 'var(--color-text-faint)' }}>{current} / 5</span>
            <div style={{ display: 'flex', gap: '.5rem', alignItems: 'center' }}>
              {current > 1 && (
                <button onClick={prev} className="btn btn-ghost" style={{ padding: '.5rem .875rem', fontSize: '.8125rem' }}>
                  ← Voltar
                </button>
              )}
              {current < 5 && (
                <button onClick={next} className="btn btn-primary">
                  {current === 4 ? 'Criar carteira' : 'Próximo'}
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><polyline points="9 18 15 12 9 6" /></svg>
                </button>
              )}
            </div>
          </div>
        </div>

        <p style={{ fontSize: '.6875rem', color: 'var(--color-text-faint)', textAlign: 'center' }}>
          SIG · Sistema de Investimentos e Gestão
        </p>
      </div>
    </div>
  )
}
