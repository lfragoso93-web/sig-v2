import { useState, useRef, UIEvent } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Link } from 'react-router-dom'
import { Eye, EyeOff, FileText, CheckCircle2, AlertCircle } from 'lucide-react'
import api from '@/services/api'
import { getApiValidationErrorMessage } from '@/utils/apiError'
import { useAuth } from '@/contexts/AuthContext'
import { PASSWORD_POLICY_HELP, isStrongPassword } from '@/utils/passwordPolicy'
import GoogleLoginButton from '@/components/auth/GoogleLoginButton'
import Modal from '@/components/ui/Modal'

const schema = z.object({
  name: z.string().min(2, 'Nome deve ter pelo menos 2 caracteres'),
  email: z.string().email('E-mail inválido'),
  password: z.string().refine(isStrongPassword, {
    message: PASSWORD_POLICY_HELP,
  }),
  confirm: z.string(),
  acceptedTerms: z.literal(true, {
    errorMap: () => ({ message: 'Você precisa ler e aceitar os Termos de Uso para continuar' }),
  }),
}).refine(d => d.password === d.confirm, {
  message: 'As senhas não coincidem',
  path: ['confirm'],
})
type FormData = z.infer<typeof schema>

export function EulaContent() {
  return (
    <div className="flex flex-col gap-4 text-xs leading-relaxed text-[var(--color-text-muted)]">
      <div className="rounded-lg p-3 bg-[var(--color-surface-offset)] border border-[var(--color-border)] text-[var(--color-text)]">
        <p className="font-semibold text-sm mb-1 text-[var(--color-primary)]">
          Termo de Adesão, Isenção de Responsabilidade e Política de Uso da Plataforma SIG
        </p>
        <p className="text-[11px] text-[var(--color-text-muted)]">
          Última atualização: Outubro de 2026. Leia atentamente todas as disposições antes de prosseguir.
        </p>
      </div>

      <section>
        <h4 className="font-bold text-[var(--color-text)] mb-1">1. Natureza Exclusiva de Ferramenta Tecnológica e Gerencial</h4>
        <p>
          O <strong>SIG (Sistema de Investimentos)</strong> é um software de organização pessoal e consolidação gerencial de carteiras de investimentos. 
          O SIG <strong>não é</strong> instituição financeira, corretora de valores, consultoria financeira ou casa de análise. A plataforma 
          <strong>não realiza</strong> recomendações de compra, venda, alocação de ativos ou assessoria de investimentos, e suas funcionalidades 
          não são reguladas pela Comissão de Valores Mobiliários (CVM) ou pelo Banco Central do Brasil (BACEN).
        </p>
      </section>

      <section>
        <h4 className="font-bold text-[var(--color-text)] mb-1">2. Responsabilidade Única e Exclusiva pelos Dados e Lançamentos</h4>
        <p>
          Todo e qualquer dado inserido no sistema — incluindo, mas não se limitando a: transações de compra e venda, quantidades, preços pagos, 
          taxas, custos, datas e notas de corretagem — é de <strong>responsabilidade única, exclusiva e intransferível do usuário</strong>. 
          O SIG não audita, não valida e não tem obrigação de conferir a fidedignidade ou a integridade dos dados cadastrados pelo usuário ou 
          importados via planilhas/extratos.
        </p>
      </section>

      <section>
        <h4 className="font-bold text-[var(--color-text)] mb-1">3. Cotações, Proventos, Indicadores e Provedores Externos</h4>
        <p>
          O compromisso do SIG é exclusivamente o de empregar esforços razoáveis para disponibilizar cotações, indicadores macroeconômicos (como CDI, 
          IPCA e IBOVESPA) e eventos corporativos de maneira clara e o mais próxima possível da realidade do mercado. Contudo, tais informações 
          são obtidas de fontes e provedores públicos ou de terceiros (como B3, Banco Central, BRAPI, Yahoo Finance, etc.) e estão sujeitas 
          a atrasos operacionais (delays), indisponibilidades, divergências de arredondamento ou inconsistências técnicas fora do controle do SIG.
        </p>
      </section>

      <section>
        <h4 className="font-bold text-[var(--color-text)] mb-1">4. Cálculos, Rentabilidade, Metas e Simulações Fiscais (IRPF)</h4>
        <p>
          Todos os cálculos de rentabilidade (como TWR/MWR), preço médio ponderado, estimativas de proventos futuros e demonstrativos fiscais 
          para declaração de IRPF constituem meras simulações aritméticas de apoio à gestão pessoal. <strong>Não substituem, sob nenhuma hipótese</strong>, 
          as notas de corretagem, informes de rendimentos oficiais das fontes pagadoras, extratos de custódia da B3/Ceip/Tesouro Direto ou a 
          orientação de um contador especializado. O usuário é o único responsável pelo recolhimento de tributos devidos e pelo cumprimento de 
          suas obrigações legais.
        </p>
      </section>

      <section>
        <h4 className="font-bold text-[var(--color-text)] mb-1">5. Isenção Ampla e Total de Responsabilidade</h4>
        <p>
          Em nenhuma circunstância o SIG, seus desenvolvedores, mantenedores ou operadores serão responsabilizados por quaisquer danos diretos, 
          indiretos, lucros cessantes, perdas financeiras, multas fiscais ou decisões de investimento tomadas com base nas visualizações, análises, 
          gráficos ou relatórios gerados pela plataforma. O uso de todos os recursos é de livre e espontânea vontade e sob o 
          <strong>risco exclusivo do usuário</strong>.
        </p>
      </section>

      <section>
        <h4 className="font-bold text-[var(--color-text)] mb-1">6. Segurança da Informação e Privacidade</h4>
        <p>
          A plataforma adota padrões modernos de criptografia para tráfego (HTTPS/TLS) e persistência de credenciais (hashing criptográfico). 
          O usuário é responsável por manter o sigilo de sua senha de acesso e eventuais códigos de duplo fator (TOTP/MFA). O usuário possui 
          o direito de solicitar a exclusão irrevogável de sua conta e de todos os dados a ela vinculados a qualquer momento através do painel de configurações.
        </p>
      </section>
    </div>
  )
}

export default function RegisterPage() {
  const { loginWithTokens } = useAuth()
  const [showPass, setShowPass] = useState(false)
  const [modalOpen, setModalOpen] = useState(false)
  const [hasScrolledToBottom, setHasScrolledToBottom] = useState(false)
  const [apiError, setApiError] = useState('')

  const scrollRef = useRef<HTMLDivElement>(null)

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { acceptedTerms: undefined as unknown as true },
  })

  const accepted = watch('acceptedTerms')

  const handleScroll = (e: UIEvent<HTMLDivElement>) => {
    const { scrollTop, scrollHeight, clientHeight } = e.currentTarget
    // Allow 20px tolerance for scroll reaching bottom
    if (scrollHeight - scrollTop - clientHeight < 20) {
      setHasScrolledToBottom(true)
    }
  }

  const handleAcceptInModal = () => {
    setValue('acceptedTerms', true, { shouldValidate: true })
    setModalOpen(false)
  }

  const onSubmit = async (data: FormData) => {
    setApiError('')
    try {
      const { data: tokens } = await api.post<{
        access_token: string
        refresh_token: string
      }>('/auth/register', {
        name: data.name,
        email: data.email,
        password: data.password,
      })
      await loginWithTokens(tokens.access_token, tokens.refresh_token)
    } catch (e: unknown) {
      setApiError(getApiValidationErrorMessage(e, 'Erro ao criar conta. Tente novamente.'))
    }
  }

  const fieldGap: React.CSSProperties = { display: 'flex', flexDirection: 'column', gap: '0.375rem' }
  const labelStyle: React.CSSProperties = { fontSize: 'var(--text-xs)', fontWeight: 500, color: 'var(--color-text-muted)' }
  const errStyle: React.CSSProperties = { fontSize: 'var(--text-xs)', color: 'var(--color-error, var(--color-notification))', margin: 0 }

  return (
    <>
      <form onSubmit={handleSubmit(onSubmit)} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
        <div style={{ marginBottom: '0.25rem' }}>
          <h2 style={{ fontSize: 'var(--text-lg)', fontWeight: 650, color: 'var(--color-text)', margin: 0, letterSpacing: '-0.01em' }}>
            Criar conta
          </h2>
          <p style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', margin: '0.25rem 0 0' }}>
            Preencha os dados para se cadastrar
          </p>
        </div>

        {/* Google OAuth */}
        <GoogleLoginButton label="Cadastrar com o Google" onError={(msg) => setApiError(msg)} />

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', margin: '0.125rem 0' }}>
          <div style={{ flex: 1, height: '1px', background: 'var(--color-divider)' }} />
          <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>ou</span>
          <div style={{ flex: 1, height: '1px', background: 'var(--color-divider)' }} />
        </div>

        {/* Nome */}
        <div style={fieldGap}>
          <label style={labelStyle}>Nome</label>
          <input
            type="text"
            autoComplete="name"
            placeholder="Seu nome completo"
            className={errors.name ? 'input-error' : 'input'}
            {...register('name')}
          />
          {errors.name && <p style={errStyle}>{errors.name.message}</p>}
        </div>

        {/* E-mail */}
        <div style={fieldGap}>
          <label style={labelStyle}>E-mail</label>
          <input
            type="email"
            autoComplete="email"
            placeholder="seu@email.com"
            className={errors.email ? 'input-error' : 'input'}
            {...register('email')}
          />
          {errors.email && <p style={errStyle}>{errors.email.message}</p>}
        </div>

        {/* Senha */}
        <div style={fieldGap}>
          <label style={labelStyle}>Senha</label>
          <div style={{ position: 'relative' }}>
            <input
              type={showPass ? 'text' : 'password'}
              autoComplete="new-password"
              placeholder="Minimo 10 caracteres"
              className={errors.password ? 'input-error' : 'input'}
              style={{ paddingRight: '2.5rem' }}
              {...register('password')}
            />
            <button
              type="button"
              onClick={() => setShowPass(p => !p)}
              style={{
                position: 'absolute',
                right: '0.75rem',
                top: '50%',
                transform: 'translateY(-50%)',
                background: 'none',
                border: 'none',
                cursor: 'pointer',
                padding: 0,
                color: 'var(--color-text-muted)',
                display: 'flex',
                alignItems: 'center',
              }}
              aria-label={showPass ? 'Ocultar senha' : 'Mostrar senha'}
            >
              {showPass ? <EyeOff size={15} /> : <Eye size={15} />}
            </button>
          </div>
          <p style={{ ...errStyle, color: errors.password ? errStyle.color : 'var(--color-text-muted)' }}>
            {errors.password?.message ?? PASSWORD_POLICY_HELP}
          </p>
        </div>

        {/* Confirmar senha */}
        <div style={fieldGap}>
          <label style={labelStyle}>Confirmar senha</label>
          <input
            type={showPass ? 'text' : 'password'}
            autoComplete="new-password"
            placeholder="Repita a senha"
            className={errors.confirm ? 'input-error' : 'input'}
            {...register('confirm')}
          />
          {errors.confirm && <p style={errStyle}>{errors.confirm.message}</p>}
        </div>

        {/* ── Box de Leitura Obrigatória e Aceite dos Termos ── */}
        <div
          style={{
            borderRadius: 'var(--radius-md)',
            border: `1px solid ${
              errors.acceptedTerms
                ? 'oklch(from var(--color-notification) l c h / 0.5)'
                : accepted
                ? 'oklch(from var(--color-success) l c h / 0.4)'
                : 'var(--color-border)'
            }`,
            background: accepted
              ? 'oklch(from var(--color-success) l c h / 0.05)'
              : 'var(--color-surface-offset)',
            padding: '0.75rem',
            display: 'flex',
            flexDirection: 'column',
            gap: '0.5rem',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--color-text)', display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
              <FileText size={14} style={{ color: 'var(--color-primary)' }} />
              Termos de Uso e Isenção de Responsabilidade
            </span>
            {accepted && (
              <span className="flex items-center gap-1 text-[11px] font-semibold text-[var(--color-success)]">
                <CheckCircle2 size={12} /> Lido e aceito
              </span>
            )}
          </div>

          <p style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', lineHeight: 1.4, margin: 0 }}>
            Para garantir a transparência jurídica, é obrigatório abrir e ler integralmente o termo de isenção de responsabilidade antes de prosseguir com o cadastro.
          </p>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginTop: '0.25rem' }}>
            <button
              type="button"
              onClick={() => {
                setModalOpen(true)
              }}
              className="btn btn-secondary text-xs py-1.5 px-3 flex items-center gap-1.5"
              style={{ fontWeight: 600 }}
            >
              <FileText size={13} />
              {accepted ? 'Rever Termos de Uso' : 'Abrir e Ler os Termos de Uso'}
            </button>

            {/* Checkbox espelho controlado após leitura */}
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.375rem', cursor: hasScrolledToBottom || accepted ? 'pointer' : 'not-allowed', opacity: hasScrolledToBottom || accepted ? 1 : 0.6 }}>
              <input
                type="checkbox"
                disabled={!hasScrolledToBottom && !accepted}
                style={{ accentColor: 'var(--color-primary)' }}
                {...register('acceptedTerms')}
              />
              <span style={{ fontSize: '11px', color: 'var(--color-text)' }}>
                Aceito os termos
              </span>
            </label>
          </div>
        </div>

        {errors.acceptedTerms && (
          <p style={{ ...errStyle, marginTop: '-0.5rem' }}>{errors.acceptedTerms.message}</p>
        )}

        {/* Erro de API */}
        {apiError && (
          <div
            style={{
              fontSize: 'var(--text-xs)',
              color: 'var(--color-notification)',
              background: 'oklch(from var(--color-notification) l c h / 0.08)',
              border: '1px solid oklch(from var(--color-notification) l c h / 0.2)',
              borderRadius: 'var(--radius-md)',
              padding: '0.5rem 0.75rem',
            }}
          >
            {apiError}
          </div>
        )}

        <button
          type="submit"
          disabled={isSubmitting || !accepted}
          className="btn btn-primary w-full"
          style={{
            fontWeight: 600,
            marginTop: '0.25rem',
            opacity: !accepted ? 0.5 : 1,
            transition: 'opacity 0.2s',
          }}
        >
          {isSubmitting ? 'Criando conta…' : 'Criar conta'}
        </button>

        <p style={{ fontSize: 'var(--text-xs)', textAlign: 'center', color: 'var(--color-text-muted)', margin: 0 }}>
          Já tem conta?{' '}
          <Link to="/login" style={{ color: 'var(--color-primary)', textDecoration: 'none', fontWeight: 500 }}>
            Entrar
          </Link>
        </p>
      </form>

      {/* Modal com scroll obrigatório para leitura do Termo */}
      <Modal
        open={modalOpen}
        title="Termos de Uso e Isenção de Responsabilidade"
        onClose={() => setModalOpen(false)}
      >
        <div className="flex flex-col gap-4">
          {!hasScrolledToBottom && !accepted && (
            <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-[oklch(from_var(--color-primary)_l_c_h_/_0.08)] border border-[oklch(from_var(--color-primary)_l_c_h_/_0.2)] text-xs text-[var(--color-primary)]">
              <AlertCircle size={14} className="shrink-0" />
              <span>Role o texto até o final para habilitar o botão de aceite.</span>
            </div>
          )}

          <div
            ref={scrollRef}
            onScroll={handleScroll}
            className="overflow-y-auto max-h-[55vh] pr-2 border rounded-lg p-3 bg-[var(--color-surface)] border-[var(--color-divider)]"
            style={{ scrollbarWidth: 'thin' }}
          >
            <EulaContent />
          </div>

          <div className="flex items-center justify-between pt-2 border-t border-[var(--color-divider)]">
            <span className="text-[11px] text-[var(--color-text-muted)]">
              {hasScrolledToBottom || accepted
                ? '✓ Leitura completa registrada'
                : 'Por favor, role até o fim do documento'}
            </span>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setModalOpen(false)}
                className="btn btn-secondary text-xs px-3 py-1.5"
              >
                Fechar
              </button>
              <button
                type="button"
                onClick={handleAcceptInModal}
                disabled={!hasScrolledToBottom && !accepted}
                className="btn btn-primary text-xs px-4 py-1.5 disabled:opacity-40"
              >
                Li e Aceito Integralmente
              </button>
            </div>
          </div>
        </div>
      </Modal>
    </>
  )
}
