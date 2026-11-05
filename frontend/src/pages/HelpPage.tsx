import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ArrowRight,
  Bot,
  BookOpen,
  Calculator,
  ChartNoAxesCombined,
  ChevronDown,
  CircleHelp,
  CornerDownRight,
  FileText,
  Landmark,
  Search,
  Send,
  ShieldCheck,
  Sparkles,
  Trash2,
  Wallet,
  X,
} from 'lucide-react'
import api from '@/services/api'

type HelpArticle = {
  category: string
  question: string
  answer: string
  keywords?: string
  href?: string
  action?: string
}

type HelpChatSource = {
  document: string
  section: string
  excerpt: string
}

type HelpChatRouteSuggestion = {
  label: string
  path: string
  description?: string
}

type HelpChatMessage = {
  question: string
  answer: string
  sources: HelpChatSource[]
  suggested_routes?: HelpChatRouteSuggestion[]
  mode?: string
}

const categories = [
  'Tudo',
  'Primeiros passos',
  'Carteira e dados',
  'Rentabilidade',
  'Recursos',
  'Conta e segurança',
]

const articles: HelpArticle[] = [
  {
    category: 'Primeiros passos',
    question: 'Por onde começo a usar o SGI?',
    answer:
      'Crie ou selecione uma carteira, registre suas operações e confira se os ativos e as cotações estão corretos. As telas de patrimônio, proventos e rentabilidade são calculadas a partir dos dados persistidos da carteira.',
    href: '/carteira',
    action: 'Abrir Resumo',
    keywords: 'iniciar começar configurar cadastro',
  },
  {
    category: 'Primeiros passos',
    question: 'Como crio ou troco de carteira?',
    answer:
      'Use o seletor de carteira na barra superior. Nele você pode escolher uma carteira existente ou criar outra. As informações mostradas nas páginas passam a considerar a carteira selecionada.',
    href: '/carteira/configuracoes',
    action: 'Ver configurações',
    keywords: 'seletor nova carteira trocar selecionar',
  },
  {
    category: 'Carteira e dados',
    question: 'Qual é a fonte dos saldos e das posições?',
    answer:
      'As transações registradas são o livro-razão da carteira. Posições, custos e resultados são projeções dessas operações, combinadas com preços e demais dados persistidos. As telas financeiras não consultam provedores diretamente.',
    href: '/carteira/patrimonio',
    action: 'Abrir Patrimônio',
    keywords: 'saldo posição custo ledger transação preço',
  },
  {
    category: 'Carteira e dados',
    question: 'Como registro uma compra, venda ou outra operação?',
    answer:
      'Abra Transações para consultar e administrar os lançamentos. Também é possível iniciar uma nova operação pelo atalho Alt+N. Confira carteira, ativo, tipo, data, quantidade, preço e custos antes de salvar.',
    href: '/carteira/transacoes',
    action: 'Abrir Transações',
    keywords: 'lançamento operação ativo compra venda taxa atalho novo alt+n',
  },
  {
    category: 'Carteira e dados',
    question: 'Posso importar operações por CSV?',
    answer:
      'Sim. No menu do usuário, escolha Importar CSV. A importação é associada à carteira selecionada; revise o arquivo e o resultado apresentado antes de continuar. Os dados importados passam a compor o histórico de transações.',
    keywords: 'arquivo csv importar planilha upload extrato notas',
  },
  {
    category: 'Carteira e dados',
    question: 'Com que frequência os preços e o patrimônio são atualizados?',
    answer:
      'A rotina de preços roda de hora em hora em dias úteis entre 09h e 18h. Criptoativos também são atualizados de hora em hora fora dessa janela e nos fins de semana. O snapshot oficial da carteira é diário às 21h, inclusive sábados, domingos e feriados, usando os dados persistidos disponíveis.',
    keywords: 'cotação atualização preço fechamento snapshot horário fim de semana',
  },
  {
    category: 'Carteira e dados',
    question: 'Por que um ativo aparece sem preço ou com cobertura parcial?',
    answer:
      'O sistema não inventa cotações. Se não houver preço persistido adequado para a data, o valor pode ficar indisponível ou a cobertura pode ser marcada como parcial. Verifique o ativo, o histórico de preços e a data da última atualização.',
    href: '/carteira/patrimonio',
    action: 'Conferir Patrimônio',
    keywords: 'lacuna falta preço indisponível parcial estimado',
  },
  {
    category: 'Carteira e dados',
    question: 'O que é um evento corporativo?',
    answer:
      'É um evento do ativo, como split, grupamento, bonificação ou subscrição, que pode alterar a quantidade projetada ou gerar um direito. Eventos sem data ou evidência suficiente permanecem pendentes; o sistema não deve inventar preço, caixa ou liquidação de frações.',
    href: '/carteira/patrimonio',
    action: 'Abrir Patrimônio',
    keywords: 'split grupamento bonificação subscrição fração ação desdobramento',
  },
  {
    category: 'Rentabilidade',
    question: 'O que significa TWR?',
    answer:
      'TWR é a rentabilidade ponderada pelo tempo. Ela compõe os retornos dos períodos e busca medir o desempenho da carteira sem tratar aportes e retiradas como se fossem rendimento. A fórmula composta é (1 + r1) × (1 + r2) × … × (1 + rn) − 1.',
    href: '/carteira/rentabilidade',
    action: 'Abrir Rentabilidade',
    keywords: 'time weighted return fórmula retorno taxa rentabilidade twr composto',
  },
  {
    category: 'Rentabilidade',
    question: 'Como o sistema calcula “No Ano” na matriz?',
    answer:
      '“No Ano” compõe os retornos mensais do ano-calendário. Os percentuais mensais não são somados: cada fator mensal é multiplicado pelo seguinte e, ao final, subtrai-se 1.',
    href: '/carteira/rentabilidade',
    action: 'Ver matriz anual',
    keywords: 'ytd anual janeiro dezembro acumulado ano calendário',
  },
  {
    category: 'Rentabilidade',
    question: 'O que é “Acumulado desde o início”?',
    answer:
      'É o TWR composto desde a primeira data processada, mostrado a partir do snapshot de fechamento do período. Por exemplo, −28,672% em 2024 seguido de +43,2183% em 2025 resulta em aproximadamente +2,1547% acumulados: (1 − 0,28672) × (1 + 0,432183) − 1. Somar −28,672% e +43,2183% não dá o retorno acumulado.',
    href: '/carteira/rentabilidade',
    action: 'Abrir Rentabilidade',
    keywords: 'crescimento acumulado soma composição desde começo início',
  },
  {
    category: 'Rentabilidade',
    question: 'Por que o resultado em reais é diferente do TWR?',
    answer:
      'Resultado financeiro é um valor monetário que pode incluir ganhos realizados, ganhos não realizados e proventos. TWR é um percentual composto e ajustado para fluxos externos. São medidas diferentes e não devem ser comparadas como se fossem a mesma coisa.',
    href: '/carteira/rentabilidade',
    action: 'Abrir Rentabilidade',
    keywords: 'lucro prejuízo pnl resultado financeiro percentual diferenca',
  },
  {
    category: 'Rentabilidade',
    question: 'Por que o retorno mensal pode não bater com a variação do patrimônio?',
    answer:
      'A variação simples do patrimônio também reflete aportes e retiradas. O retorno mensal é composto a partir dos retornos diários da cadeia TWR, por isso os valores podem divergir.',
    href: '/carteira/rentabilidade',
    action: 'Abrir Rentabilidade',
    keywords: 'retorno mês diferença aporte patrimônio variação',
  },
  {
    category: 'Rentabilidade',
    question: 'O que significam “preço parcial” e “retorno estimado”?',
    answer:
      'Preço parcial indica que faltou preço persistido para algum ativo na data. Retorno estimado indica que o cálculo depende de inferências, por exemplo porque a carteira não tem uma conta-caixa explícita e os fluxos são inferidos das transações. Essas indicações descrevem a qualidade dos dados.',
    href: '/carteira/rentabilidade',
    action: 'Ver qualidade dos dados',
    keywords: 'has_partial_prices return_is_estimated flags qualidade cobertura',
  },
  {
    category: 'Recursos',
    question: 'Como funcionam os proventos?',
    answer:
      'O sistema apresenta proventos a partir dos eventos monetários persistidos e da posição histórica da carteira. Direitos são derivados para a carteira; o valor exibido depende dos dados de evento, posição e pagamento disponíveis.',
    href: '/carteira/proventos',
    action: 'Abrir Proventos',
    keywords: 'dividendo jcp rendimento data-com pagamento proventos',
  },
  {
    category: 'Recursos',
    question: 'O que posso acompanhar em Metas?',
    answer:
      'Você pode acompanhar metas de patrimônio, proventos e rentabilidade, além de metas livres. A tela também permite comparar a alocação atual por classe com os percentuais alvo configurados.',
    href: '/carteira/metas',
    action: 'Abrir Metas',
    keywords: 'objetivo alvo progresso classe alocação metas',
  },
  {
    category: 'Recursos',
    question: 'O que a página Análise e a IA respondem?',
    answer:
      'A página reúne indicadores determinísticos de diversificação, concentração e rebalanceamento. A área de IA explica esses dados e permite perguntas sobre a alocação, riscos e proventos da carteira selecionada. Ela não é um assistente que responde sobre toda a documentação do sistema.',
    href: '/carteira/analise',
    action: 'Abrir Análise',
    keywords: 'inteligência artificial chat pergunta rebalanceamento carteira',
  },
  {
    category: 'Recursos',
    question: 'A Calculadora de rendimentos altera minha carteira?',
    answer:
      'Não. Ela faz uma projeção isolada no navegador com aporte inicial, aporte mensal, taxa anual e prazo. Não consulta nem altera a carteira e não considera impostos, inflação, tarifas ou variação da taxa ao longo do tempo.',
    href: '/carteira/ferramentas/rendimentos',
    action: 'Abrir Calculadora',
    keywords: 'simulação juros aporte rendimento composto calculadora',
  },
  {
    category: 'Recursos',
    question: 'Como funciona o Simulador de Renda Fixa?',
    answer:
      'Ele compara dois cenários de renda fixa a partir do produto, taxa e prazo informados e estima valores bruto e líquido, imposto e taxa equivalente. É uma simulação: não consulta ofertas de mercado, não lê a carteira e não substitui informes da instituição ou orientação fiscal.',
    href: '/carteira/ferramentas/renda-fixa',
    action: 'Abrir Simulador RF',
    keywords: 'cdb lci lca imposto taxa equivalente prazo renda fixa',
  },
  {
    category: 'Recursos',
    question: 'Para que serve a área de IRPF?',
    answer:
      'A área organiza informações e apurações relacionadas às operações da carteira para apoiar a conferência do imposto. Confira os dados e documentos das instituições financeiras: o sistema não substitui a declaração oficial nem orientação fiscal.',
    href: '/carteira/irpf',
    action: 'Abrir IRPF',
    keywords: 'imposto declaração darf imposto de renda fiscal irpf',
  },
  {
    category: 'Conta e segurança',
    question: 'Como altero meus dados ou minha senha?',
    answer:
      'Abra Configurações para editar o perfil e administrar as opções de segurança disponíveis para sua conta. Use uma senha exclusiva e mantenha os dados de recuperação atualizados.',
    href: '/carteira/configuracoes',
    action: 'Abrir Configurações',
    keywords: 'perfil senha email nome usuário',
  },
  {
    category: 'Conta e segurança',
    question: 'Como funciona a autenticação de dois fatores?',
    answer:
      'Quando habilitada nas configurações de segurança, a autenticação multifator solicita um código temporário além da senha durante o acesso. Guarde os códigos de recuperação em local seguro.',
    href: '/carteira/configuracoes',
    action: 'Ver segurança da conta',
    keywords: 'mfa multifator 2fa totp código segurança autenticacao',
  },
  {
    category: 'Conta e segurança',
    question: 'Como funciona o limite para solicitar redefinição de senha?',
    answer:
      'São permitidas duas solicitações por conta em uma janela de dois minutos. Uma terceira solicitação bloqueia novos envios por 60 minutos. Um SuperAdmin pode remover o bloqueio pelo painel administrativo; essa ação fica registrada na auditoria.',
    keywords: 'esqueci senha reset bloqueio limite 2 minutos 60 admin',
  },
]

function normalize(value: string): string {
  return value
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLocaleLowerCase('pt-BR')
    .trim()
}

const shortcuts = [
  {
    label: 'Patrimônio',
    href: '/carteira/patrimonio',
    icon: Wallet,
  },
  {
    label: 'Rentabilidade',
    href: '/carteira/rentabilidade',
    icon: ChartNoAxesCombined,
  },
  {
    label: 'Proventos',
    href: '/carteira/proventos',
    icon: Landmark,
  },
  {
    label: 'Calculadoras',
    href: '/carteira/ferramentas/rendimentos',
    icon: Calculator,
  },
  {
    label: 'Comparar ativos',
    href: '/carteira/ferramentas/comparador',
    icon: ChartNoAxesCombined,
  },
]

const starterQuestions = [
  'Como é calculado o TWR acumulado?',
  'Por que o resultado em reais é diferente do TWR?',
  'Com que frequência os preços e o snapshot das 21h são atualizados?',
  'Como importar operações via planilha CSV?',
]

export default function HelpPage() {
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState('Tudo')
  const [chatQuestion, setChatQuestion] = useState('')
  const [chatMessages, setChatMessages] = useState<HelpChatMessage[]>([])
  const [chatLoading, setChatLoading] = useState(false)
  const [chatError, setChatError] = useState<string | null>(null)

  const filteredArticles = useMemo(() => {
    const normalizedQuery = normalize(query)
    return articles.filter(article => {
      const matchesCategory =
        category === 'Tudo' || article.category === category
      const content = normalize(
        `${article.question} ${article.answer} ${article.category} ${
          article.keywords ?? ''
        }`
      )
      return matchesCategory && (!normalizedQuery || content.includes(normalizedQuery))
    })
  }, [category, query])

  async function handleSendQuestion(questionText: string) {
    const question = questionText.trim()
    if (question.length < 3 || chatLoading) return

    setChatQuestion('')
    setChatLoading(true)
    setChatError(null)
    try {
      const response = await api.post<{
        answer: string
        sources: HelpChatSource[]
        suggested_routes?: HelpChatRouteSuggestion[]
        mode?: string
      }>('/help/ask', { question })

      setChatMessages(current => [
        ...current,
        { question, ...response.data },
      ])
    } catch {
      setChatError(
        'Não foi possível consultar a documentação agora. Tente novamente em instantes.'
      )
    } finally {
      setChatLoading(false)
    }
  }

  return (
    <div className="page-container">
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-6 pb-8">
        {/* Hero Header */}
        <section
          className="card overflow-hidden"
          style={{
            background:
              'linear-gradient(135deg, var(--color-surface), oklch(from var(--color-primary) l c h / 0.1))',
            borderColor: 'var(--color-border)',
          }}
        >
          <div className="p-6 sm:p-8">
            <div className="mb-3 flex items-center justify-between gap-2">
              <div
                className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide"
                style={{ color: 'var(--color-primary)' }}
              >
                <BookOpen size={16} /> Central de ajuda
              </div>
              <span
                className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium"
                style={{
                  background: 'oklch(from var(--color-primary) l c h / 0.12)',
                  color: 'var(--color-primary)',
                }}
              >
                <Sparkles size={12} />
                Assistente Grounded SGI
              </span>
            </div>

            <h1
              className="text-2xl font-bold sm:text-3xl"
              style={{ color: 'var(--color-text)' }}
            >
              Como podemos ajudar?
            </h1>
            <p
              className="mt-2 max-w-2xl text-sm leading-relaxed"
              style={{ color: 'var(--color-text-muted)' }}
            >
              Encontre explicações sobre as telas, os cálculos e os dados da sua
              carteira. Nosso assistente consulta a documentação oficial e te orienta na navegação.
            </p>

            <label className="relative mt-5 block max-w-2xl">
              <Search
                size={17}
                className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2"
                style={{ color: 'var(--color-text-faint)' }}
              />
              <input
                type="search"
                aria-label="Buscar na ajuda"
                placeholder="Busque por um assunto, cálculo ou recurso..."
                value={query}
                onChange={event => setQuery(event.target.value)}
                className="input w-full py-3 pl-10 pr-10 text-sm shadow-sm"
              />
              {query && (
                <button
                  type="button"
                  aria-label="Limpar busca"
                  onClick={() => setQuery('')}
                  className="absolute right-3 top-1/2 -translate-y-1/2"
                  style={{ color: 'var(--color-text-faint)' }}
                >
                  <X size={16} />
                </button>
              )}
            </label>

            {/* Quick Pills */}
            <div className="mt-4 flex flex-wrap items-center gap-2">
              <span
                className="text-xs font-medium"
                style={{ color: 'var(--color-text-faint)' }}
              >
                Tópicos sugeridos:
              </span>
              {['TWR', 'Importação CSV', 'Snapshot 21h', 'Eventos e Splits', 'IRPF'].map(
                pill => (
                  <button
                    key={pill}
                    type="button"
                    onClick={() => setQuery(pill)}
                    className="rounded-full border px-2.5 py-1 text-xs transition-colors hover:border-primary"
                    style={{
                      borderColor: 'var(--color-border)',
                      background: 'var(--color-surface)',
                      color: 'var(--color-text-muted)',
                    }}
                  >
                    {pill}
                  </button>
                )
              )}
            </div>
          </div>
        </section>

        {/* Shortcuts for main pages */}
        <section aria-label="Atalhos para as páginas principais">
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
            {shortcuts.map(({ label, href, icon: Icon }) => (
              <Link
                key={href}
                to={href}
                className="card flex items-center gap-3 p-4 transition-all hover:border-primary hover:shadow-sm"
              >
                <span
                  className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg"
                  style={{
                    background: 'oklch(from var(--color-primary) l c h / 0.12)',
                    color: 'var(--color-primary)',
                  }}
                >
                  <Icon size={17} />
                </span>
                <span
                  className="min-w-0 flex-1 text-sm font-semibold truncate"
                  style={{ color: 'var(--color-text)' }}
                >
                  {label}
                </span>
                <ArrowRight
                  size={14}
                  style={{ color: 'var(--color-text-faint)' }}
                />
              </Link>
            ))}
          </div>
        </section>

        {/* AI & Documentation Assistant Chat */}
        <section
          className="card overflow-hidden"
          aria-labelledby="document-chat-heading"
        >
          <div
            className="flex items-center justify-between border-b p-4 sm:p-5"
            style={{ borderColor: 'var(--color-divider)' }}
          >
            <div className="flex items-center gap-3">
              <span
                className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg"
                style={{
                  background: 'oklch(from var(--color-primary) l c h / 0.12)',
                  color: 'var(--color-primary)',
                }}
              >
                <Bot size={18} />
              </span>
              <div>
                <h2
                  id="document-chat-heading"
                  className="text-base font-semibold"
                  style={{ color: 'var(--color-text)' }}
                >
                  Assistente documental
                </h2>
                <p
                  className="mt-1 text-xs leading-relaxed"
                  style={{ color: 'var(--color-text-muted)' }}
                >
                  Pergunte sobre o SGI. As respostas mostram trechos e seções das fontes consultadas.
                </p>
              </div>
            </div>

            {chatMessages.length > 0 && (
              <button
                type="button"
                onClick={() => setChatMessages([])}
                className="inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1 text-xs font-medium transition-colors hover:border-error"
                style={{
                  borderColor: 'var(--color-border)',
                  color: 'var(--color-text-muted)',
                }}
                title="Limpar histórico"
              >
                <Trash2 size={13} />
                <span className="hidden sm:inline">Limpar</span>
              </button>
            )}
          </div>

          <div className="flex flex-col gap-3 p-4 sm:p-5">
            {/* Empty state: Starter Prompts */}
            {chatMessages.length === 0 && (
              <div
                className="rounded-xl border border-dashed p-4 text-left"
                style={{ borderColor: 'var(--color-border)' }}
              >
                <p
                  className="text-xs font-semibold"
                  style={{ color: 'var(--color-text)' }}
                >
                  Sugestões de perguntas para testar com 1 clique:
                </p>
                <div className="mt-2.5 grid grid-cols-1 gap-2 sm:grid-cols-2">
                  {starterQuestions.map(q => (
                    <button
                      key={q}
                      type="button"
                      onClick={() => void handleSendQuestion(q)}
                      disabled={chatLoading}
                      className="group flex items-start gap-2 rounded-lg border p-2.5 text-xs text-left transition-all hover:border-primary"
                      style={{
                        borderColor: 'var(--color-border)',
                        background: 'var(--color-surface)',
                        color: 'var(--color-text)',
                      }}
                    >
                      <CornerDownRight
                        size={13}
                        className="mt-0.5 shrink-0 transition-transform group-hover:translate-x-0.5"
                        style={{ color: 'var(--color-primary)' }}
                      />
                      <span>{q}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Chat Thread */}
            {chatMessages.length > 0 && (
              <div
                className="flex max-h-96 flex-col gap-3 overflow-y-auto"
                aria-live="polite"
              >
                {chatMessages.map((message, index) => (
                  <article
                    key={`${index}-${message.question}`}
                    className="flex flex-col gap-2"
                  >
                    <div
                      className="ml-auto max-w-[90%] rounded-xl px-3 py-2 text-sm"
                      style={{
                        background: 'oklch(from var(--color-primary) l c h / 0.12)',
                        color: 'var(--color-text)',
                      }}
                    >
                      {message.question}
                    </div>
                    <div
                      className="max-w-[96%] rounded-xl border px-3 py-2.5 text-sm leading-relaxed"
                      style={{
                        borderColor: 'var(--color-border)',
                        color: 'var(--color-text-muted)',
                      }}
                    >
                      {message.mode === 'llm' && (
                        <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold" style={{ color: 'var(--color-primary)' }}>
                          <Sparkles size={13} />
                          <span>Resposta sintetizada por IA (Grounded)</span>
                        </div>
                      )}
                      <p className="whitespace-pre-line">{message.answer}</p>

                      {/* Navigation pills */}
                      {message.suggested_routes && message.suggested_routes.length > 0 && (
                        <div className="mt-3 flex flex-wrap items-center gap-2 pt-2 border-t" style={{ borderColor: 'var(--color-divider)' }}>
                          <span className="text-[11px] font-semibold" style={{ color: 'var(--color-text-faint)' }}>
                            Navegar para:
                          </span>
                          {message.suggested_routes.map(route => (
                            <Link
                              key={route.path}
                              to={route.path}
                              className="inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-xs font-semibold transition-all hover:border-primary"
                              style={{
                                borderColor: 'var(--color-primary)',
                                background: 'oklch(from var(--color-primary) l c h / 0.08)',
                                color: 'var(--color-primary)',
                              }}
                            >
                              <span>{route.label}</span>
                              <ArrowRight size={11} />
                            </Link>
                          ))}
                        </div>
                      )}

                      {/* Source excerpts */}
                      {message.sources.length > 0 && (
                        <div className="mt-3 flex flex-col gap-2">
                          {message.sources.map((source, sourceIndex) => (
                            <div
                              key={`${source.document}-${source.section}-${sourceIndex}`}
                              className="rounded-lg p-3"
                              style={{ background: 'var(--color-surface-offset)' }}
                            >
                              <p
                                className="text-[11px] font-semibold"
                                style={{ color: 'var(--color-primary)' }}
                              >
                                {source.document} · {source.section}
                              </p>
                              <p
                                className="mt-1 whitespace-pre-wrap text-xs leading-relaxed"
                                style={{ color: 'var(--color-text-muted)' }}
                              >
                                {source.excerpt}
                              </p>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </article>
                ))}
              </div>
            )}

            {chatError && (
              <p
                role="alert"
                className="text-xs"
                style={{ color: 'var(--color-error)' }}
              >
                {chatError}
              </p>
            )}

            <form
              onSubmit={event => {
                event.preventDefault()
                void handleSendQuestion(chatQuestion)
              }}
              className="flex items-center gap-2"
            >
              <input
                type="text"
                aria-label="Pergunta sobre a documentação"
                placeholder="Ex.: Como é calculado o TWR acumulado?"
                value={chatQuestion}
                onChange={event => setChatQuestion(event.target.value)}
                maxLength={500}
                disabled={chatLoading}
                className="input min-w-0 flex-1 px-3 py-2 text-sm"
              />
              <button
                type="submit"
                disabled={chatLoading || chatQuestion.trim().length < 3}
                className="btn btn-primary flex shrink-0 items-center gap-1.5 px-3 py-2 text-xs"
              >
                <Send size={13} /> {chatLoading ? 'Buscando…' : 'Perguntar'}
              </button>
            </form>

            <p
              className="text-[11px]"
              style={{ color: 'var(--color-text-faint)' }}
            >
              Limite de 10 perguntas por minuto. A consulta usa documentação do
              sistema, não dados da sua carteira.
            </p>
          </div>
        </section>

        {/* Perguntas e respostas (FAQ) */}
        <section className="card p-4 sm:p-5" aria-labelledby="faq-heading">
          <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2
                id="faq-heading"
                className="text-base font-semibold"
                style={{ color: 'var(--color-text)' }}
              >
                Perguntas e respostas
              </h2>
              <p
                className="mt-1 text-xs"
                style={{ color: 'var(--color-text-muted)' }}
              >
                {filteredArticles.length}{' '}
                {filteredArticles.length === 1
                  ? 'resposta encontrada'
                  : 'respostas encontradas'}
              </p>
            </div>
            <Link
              to="/carteira/analise"
              className="inline-flex items-center gap-1.5 text-xs font-semibold"
              style={{ color: 'var(--color-primary)' }}
            >
              Pergunte sobre sua carteira à IA <ArrowRight size={13} />
            </Link>
          </div>

          <div
            className="mb-4 flex gap-2 overflow-x-auto pb-1"
            role="group"
            aria-label="Filtrar por categoria"
          >
            {categories.map(item => (
              <button
                key={item}
                type="button"
                aria-pressed={category === item}
                onClick={() => setCategory(item)}
                className="shrink-0 rounded-full border px-3 py-1.5 text-xs font-medium transition-colors"
                style={{
                  borderColor:
                    category === item
                      ? 'var(--color-primary)'
                      : 'var(--color-border)',
                  background:
                    category === item
                      ? 'oklch(from var(--color-primary) l c h / 0.12)'
                      : 'transparent',
                  color:
                    category === item
                      ? 'var(--color-primary)'
                      : 'var(--color-text-muted)',
                }}
              >
                {item}
              </button>
            ))}
          </div>

          {filteredArticles.length ? (
            <div
              className="divide-y"
              style={{ borderColor: 'var(--color-divider)' }}
            >
              {filteredArticles.map(article => (
                <details
                  key={article.question}
                  className="group py-3 first:pt-1 last:pb-1"
                >
                  <summary
                    className="flex cursor-pointer list-none items-start justify-between gap-4 text-sm font-medium marker:hidden [&::-webkit-details-marker]:hidden"
                    style={{ color: 'var(--color-text)' }}
                  >
                    <span>{article.question}</span>
                    <span
                      className="flex shrink-0 items-center gap-2 text-xs font-normal"
                      style={{ color: 'var(--color-text-faint)' }}
                    >
                      {article.category}
                      <ChevronDown
                        size={14}
                        className="transition-transform group-open:rotate-180"
                      />
                    </span>
                  </summary>
                  <div
                    className="max-w-3xl pb-1 pl-0 pt-3 text-sm leading-relaxed sm:pl-1"
                    style={{ color: 'var(--color-text-muted)' }}
                  >
                    <p>{article.answer}</p>
                    {article.href && article.action && (
                      <Link
                        to={article.href}
                        className="mt-3 inline-flex items-center gap-1.5 text-xs font-semibold"
                        style={{ color: 'var(--color-primary)' }}
                      >
                        {article.action} <ArrowRight size={13} />
                      </Link>
                    )}
                  </div>
                </details>
              ))}
            </div>
          ) : (
            <div className="flex flex-col items-center gap-2 py-10 text-center">
              <CircleHelp
                size={24}
                style={{ color: 'var(--color-text-faint)' }}
              />
              <p
                className="text-sm font-semibold"
                style={{ color: 'var(--color-text)' }}
              >
                Não encontramos essa resposta
              </p>
              <p
                className="max-w-md text-xs"
                style={{ color: 'var(--color-text-muted)' }}
              >
                Tente outro termo ou escolha “Tudo” para pesquisar em todas as
                categorias.
              </p>
              <button
                type="button"
                onClick={() => {
                  setQuery('')
                  setCategory('Tudo')
                }}
                className="mt-1 text-xs font-semibold"
                style={{ color: 'var(--color-primary)' }}
              >
                Limpar filtros
              </button>
            </div>
          )}
        </section>

        {/* Security / Disclaimer */}
        <section
          className="flex flex-col gap-3 rounded-xl border p-4 sm:flex-row sm:items-center sm:justify-between sm:p-5"
          style={{
            borderColor: 'var(--color-border)',
            background: 'var(--color-surface)',
          }}
        >
          <div className="flex items-start gap-3">
            <ShieldCheck
              size={18}
              className="mt-0.5 shrink-0"
              style={{ color: 'var(--color-success)' }}
            />
            <div>
              <h2
                className="text-sm font-semibold"
                style={{ color: 'var(--color-text)' }}
              >
                Sobre os dados e as estimativas
              </h2>
              <p
                className="mt-1 max-w-2xl text-xs leading-relaxed"
                style={{ color: 'var(--color-text-muted)' }}
              >
                O SGI é uma ferramenta de acompanhamento. Confira operações,
                informes e documentos das instituições financeiras; cálculos e
                simulações não são recomendação de investimento nem substituem
                orientação fiscal.
              </p>
            </div>
          </div>
          <Link
            to="/carteira/irpf"
            className="inline-flex shrink-0 items-center gap-1.5 text-xs font-semibold"
            style={{ color: 'var(--color-primary)' }}
          >
            <FileText size={14} /> Área de IRPF <ArrowRight size={13} />
          </Link>
        </section>
      </div>
    </div>
  )
}
