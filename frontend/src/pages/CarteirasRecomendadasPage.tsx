import { useState, useMemo, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Sparkles,
  ShieldCheck,
  DollarSign,
  Rocket,
  Sliders,
  Calculator,
  ArrowRight,
  TrendingUp,
  Info,
  CheckCircle2,
  RotateCcw,
  Percent,
} from 'lucide-react'
import {
  useRecommendedPortfolios,
  useSimulateRecommendedPortfolio,
} from '@/hooks/useRecommendedPortfolios'
import { formatBRL, fmtMoney, assetBadgeClass } from '@/utils/format'

type StrategyKey = 'patrimonio' | 'proventos' | 'performance'

const STRATEGY_CONFIG: Record<
  StrategyKey,
  { label: string; icon: React.ElementType; color: string; bg: string; border: string }
> = {
  patrimonio: {
    label: 'Aumento de Patrimônio',
    icon: ShieldCheck,
    color: 'var(--color-primary)',
    bg: 'oklch(from var(--color-primary) l c h / 0.1)',
    border: 'oklch(from var(--color-primary) l c h / 0.25)',
  },
  proventos: {
    label: 'Renda Passiva',
    icon: DollarSign,
    color: 'var(--color-success)',
    bg: 'oklch(from var(--color-success) l c h / 0.1)',
    border: 'oklch(from var(--color-success) l c h / 0.25)',
  },
  performance: {
    label: 'Performance & Crescimento',
    icon: Rocket,
    color: 'var(--color-orange, #f97316)',
    bg: 'oklch(from var(--color-orange, #f97316) l c h / 0.1)',
    border: 'oklch(from var(--color-orange, #f97316) l c h / 0.25)',
  },
}

export default function CarteirasRecomendadasPage() {
  const navigate = useNavigate()
  const { data: portfolios = [], isLoading, isError } = useRecommendedPortfolios()
  const simulateMutation = useSimulateRecommendedPortfolio()

  const [activeStrategy, setActiveStrategy] = useState<StrategyKey>('patrimonio')
  const [simulationAmount, setSimulationAmount] = useState<string>('5000')
  const [isCustomizingWeights, setIsCustomizingWeights] = useState<boolean>(false)
  const [customWeights, setCustomWeights] = useState<Record<string, number>>({})
  const [copiedSuccess, setCopiedSuccess] = useState<boolean>(false)

  const activePortfolio = useMemo(() => {
    return portfolios.find(p => p.strategy === activeStrategy) || portfolios[0]
  }, [portfolios, activeStrategy])

  // Inicializa pesos customizados quando o portfólio muda
  useEffect(() => {
    if (activePortfolio?.classes) {
      const initial: Record<string, number> = {}
      activePortfolio.classes.forEach(c => {
        initial[c.asset_type] = c.target_weight_pct
      })
      setCustomWeights(initial)
      setIsCustomizingWeights(false)
    }
  }, [activePortfolio])

  // Executa simulação automática ao carregar portfólio ou alterar valores
  useEffect(() => {
    if (activePortfolio && !simulateMutation.isPending) {
      const amt = parseFloat(simulationAmount.replace(/\D/g, '')) || 5000
      simulateMutation.mutate({
        strategy: activeStrategy,
        total_amount: amt,
        custom_class_weights: isCustomizingWeights ? customWeights : undefined,
      })
    }
  }, [activeStrategy, activePortfolio])

  const handleSimulate = (e?: React.FormEvent) => {
    if (e) e.preventDefault()
    const amt = parseFloat(simulationAmount.replace(/\D/g, ''))
    if (!amt || amt <= 0) return

    simulateMutation.mutate({
      strategy: activeStrategy,
      total_amount: amt,
      custom_class_weights: isCustomizingWeights ? customWeights : undefined,
    })
  }

  const handleWeightChange = (assetType: string, val: number) => {
    setCustomWeights(prev => ({
      ...prev,
      [assetType]: Math.max(0, Math.min(100, val)),
    }))
  }

  const totalCustomWeight = useMemo(() => {
    return Object.values(customWeights).reduce((a, b) => a + b, 0)
  }, [customWeights])

  const handleResetWeights = () => {
    if (activePortfolio?.classes) {
      const initial: Record<string, number> = {}
      activePortfolio.classes.forEach(c => {
        initial[c.asset_type] = c.target_weight_pct
      })
      setCustomWeights(initial)
      setIsCustomizingWeights(false)
      simulateMutation.mutate({
        strategy: activeStrategy,
        total_amount: parseFloat(simulationAmount.replace(/\D/g, '')) || 5000,
      })
    }
  }

  const handleApplyToMetas = () => {
    // Redireciona para /carteira/metas com parâmetros sugeridos
    setCopiedSuccess(true)
    setTimeout(() => {
      navigate('/carteira/metas')
    }, 900)
  }

  if (isLoading) {
    return (
      <div className="page-container flex flex-col gap-4">
        <div className="skeleton h-28 w-full rounded-2xl" />
        <div className="skeleton h-64 w-full rounded-2xl" />
        <div className="skeleton h-96 w-full rounded-2xl" />
      </div>
    )
  }

  if (isError || !activePortfolio) {
    return (
      <div className="page-container">
        <div className="card p-12 text-center flex flex-col items-center justify-center gap-3">
          <Info size={28} className="text-brand-400" />
          <h2 className="text-base font-semibold">Não foi possível carregar as carteiras recomendadas</h2>
          <p className="text-xs text-muted">Verifique sua conexão e tente novamente mais tarde.</p>
        </div>
      </div>
    )
  }

  const activeConfig = STRATEGY_CONFIG[activeStrategy]
  const simulationResult = simulateMutation.data

  return (
    <div className="page-container flex flex-col gap-6">
      {/* Header com apresentação */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b" style={{ borderColor: 'var(--color-divider)' }}>
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span
              className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold flex items-center gap-1.5"
              style={{ background: 'oklch(from var(--color-primary) l c h / 0.15)', color: 'var(--color-primary)' }}
            >
              <Sparkles size={12} /> Inteligência Artificial Global
            </span>
            <span className="text-xs text-muted">· Atualizada para o ciclo atual de mercado</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight" style={{ color: 'var(--color-text)' }}>
            Carteiras Recomendadas
          </h1>
          <p className="text-xs text-muted mt-0.5">
            Modelos de alocação multiclasse estruturados por premissas estratégicas e fundamentados na análise integrada de dados.
          </p>
        </div>

        {/* Abas das Premissas Estratégicas */}
        <div
          role="tablist"
          className="flex items-center gap-1 p-1 rounded-xl"
          style={{ background: 'var(--color-surface-offset)', border: '1px solid var(--color-border)' }}
        >
          {(['patrimonio', 'proventos', 'performance'] as const).map(strat => {
            const conf = STRATEGY_CONFIG[strat]
            const Icon = conf.icon
            const isActive = activeStrategy === strat
            return (
              <button
                key={strat}
                role="tab"
                aria-selected={isActive}
                onClick={() => setActiveStrategy(strat)}
                className="flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold transition-all cursor-pointer"
                style={{
                  background: isActive ? 'var(--color-surface)' : 'transparent',
                  color: isActive ? conf.color : 'var(--color-text-muted)',
                  boxShadow: isActive ? 'var(--shadow-sm)' : 'none',
                }}
              >
                <Icon size={14} />
                <span>{conf.label}</span>
              </button>
            )
          })}
        </div>
      </div>

      {/* Hero Card da Estratégia Ativa */}
      <div
        className="card p-6 relative overflow-hidden"
        style={{
          border: `1px solid ${activeConfig.border}`,
          background: `linear-gradient(135deg, ${activeConfig.bg} 0%, var(--color-surface) 100%)`,
        }}
      >
        <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-6">
          <div className="max-w-2xl">
            <div className="flex items-center gap-2.5 mb-2">
              <span
                className="px-2.5 py-1 rounded-md text-xs font-semibold uppercase tracking-wider"
                style={{ background: activeConfig.bg, color: activeConfig.color, border: `1px solid ${activeConfig.border}` }}
              >
                {activePortfolio.risk_profile}
              </span>
              <span className="text-xs text-muted">Horizonte: {activePortfolio.suggested_time_horizon}</span>
            </div>
            <h2 className="text-xl font-bold mb-2" style={{ color: 'var(--color-text)' }}>
              {activePortfolio.title}
            </h2>
            <p className="text-sm leading-relaxed mb-4" style={{ color: 'var(--color-text-muted)' }}>
              {activePortfolio.thesis}
            </p>
          </div>

          {/* Métricas-chave da Carteira */}
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 min-w-[280px]">
            <div className="p-3 rounded-xl bg-surface border" style={{ borderColor: 'var(--color-divider)' }}>
              <div className="text-[10px] uppercase font-semibold text-muted flex items-center gap-1">
                <TrendingUp size={11} className="text-primary" /> Retorno Anual
              </div>
              <div className="text-sm font-bold mt-1" style={{ color: 'var(--color-text)' }}>
                {activePortfolio.expected_annual_return}
              </div>
            </div>

            <div className="p-3 rounded-xl bg-surface border" style={{ borderColor: 'var(--color-divider)' }}>
              <div className="text-[10px] uppercase font-semibold text-muted flex items-center gap-1">
                <Percent size={11} className="text-success" /> Yield Médio
              </div>
              <div className="text-sm font-bold mt-1" style={{ color: 'var(--color-success)' }}>
                {activePortfolio.expected_dividend_yield}
              </div>
            </div>

            <div className="p-3 rounded-xl bg-surface border col-span-2 sm:col-span-1" style={{ borderColor: 'var(--color-divider)' }}>
              <div className="text-[10px] uppercase font-semibold text-muted flex items-center gap-1">
                <ShieldCheck size={11} className="text-brand-400" /> Score de Diversificação
              </div>
              <div className="text-sm font-bold mt-1 flex items-center gap-1.5" style={{ color: 'var(--color-text)' }}>
                <span>{activePortfolio.diversification_score}/100</span>
                <span className="text-[10px] px-1.5 py-0.2 rounded bg-success/15 text-success">Excelente</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Grid Principal: Alocação & Simulador */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Coluna Esquerda: Distribuição de Classes e Customização */}
        <div className="lg:col-span-6 flex flex-col gap-4">
          <div className="card p-5">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Sliders size={16} className="text-primary" />
                <h3 className="font-bold text-sm" style={{ color: 'var(--color-text)' }}>
                  Alocação por Classe de Ativos
                </h3>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setIsCustomizingWeights(v => !v)}
                  className="px-2.5 py-1 rounded-lg text-xs font-semibold transition-colors flex items-center gap-1.5"
                  style={{
                    background: isCustomizingWeights ? 'var(--color-primary)' : 'var(--color-surface-offset)',
                    color: isCustomizingWeights ? '#fff' : 'var(--color-text-muted)',
                  }}
                >
                  <Sliders size={12} />
                  <span>{isCustomizingWeights ? 'Modo Customizado' : 'Ajustar Pesos'}</span>
                </button>
                {isCustomizingWeights && (
                  <button
                    type="button"
                    onClick={handleResetWeights}
                    className="p-1 rounded text-muted hover:text-text transition-colors"
                    title="Restaurar pesos recomendados da IA"
                  >
                    <RotateCcw size={13} />
                  </button>
                )}
              </div>
            </div>

            {/* Barra visual de alocação multiclasse */}
            <div className="w-full h-3.5 rounded-full overflow-hidden flex mb-4 bg-surface-offset">
              {activePortfolio.classes.map(c => {
                const weight = isCustomizingWeights ? (customWeights[c.asset_type] ?? c.target_weight_pct) : c.target_weight_pct
                return (
                  <div
                    key={c.asset_type}
                    style={{
                      width: `${Math.max(1, (weight / (isCustomizingWeights ? (totalCustomWeight || 100) : 100)) * 100)}%`,
                      background:
                        c.asset_type === 'ACAO' ? '#3b82f6' :
                        c.asset_type === 'FII' ? '#10b981' :
                        c.asset_type === 'RENDA_FIXA' ? '#6366f1' :
                        c.asset_type === 'TESOURO_DIRETO' ? '#8b5cf6' :
                        c.asset_type === 'CRIPTO' ? '#f59e0b' : '#06b6d4',
                    }}
                    title={`${c.label}: ${weight.toFixed(1)}%`}
                  />
                )
              })}
            </div>

            {/* Lista de Classes com Sliders / Informações */}
            <div className="flex flex-col gap-3">
              {activePortfolio.classes.map(c => {
                const weight = isCustomizingWeights ? (customWeights[c.asset_type] ?? c.target_weight_pct) : c.target_weight_pct
                return (
                  <div key={c.asset_type} className="p-3 rounded-xl bg-surface-offset flex flex-col gap-2">
                    <div className="flex items-center justify-between text-xs">
                      <div className="flex items-center gap-2">
                        <span className={`asset-badge ${assetBadgeClass(c.asset_type)} text-[10px]`}>
                          {c.asset_type}
                        </span>
                        <span className="font-semibold text-text">{c.label}</span>
                      </div>
                      <span className="font-bold tabular-nums text-text">
                        {weight.toFixed(1)}%
                      </span>
                    </div>

                    <p className="text-[11px] text-muted leading-tight">
                      {c.description}
                    </p>

                    {isCustomizingWeights && (
                      <div className="flex items-center gap-3 mt-1">
                        <input
                          type="range"
                          min="0"
                          max="80"
                          step="1"
                          value={customWeights[c.asset_type] ?? c.target_weight_pct}
                          onChange={e => handleWeightChange(c.asset_type, parseFloat(e.target.value) || 0)}
                          className="w-full accent-primary cursor-pointer"
                        />
                        <div className="flex items-center gap-1 min-w-[58px]">
                          <input
                            type="number"
                            min="0"
                            max="100"
                            value={customWeights[c.asset_type] ?? c.target_weight_pct}
                            onChange={e => handleWeightChange(c.asset_type, parseFloat(e.target.value) || 0)}
                            className="input input-xs w-12 text-center"
                          />
                          <span className="text-[11px] text-muted">%</span>
                        </div>
                      </div>
                    )}
                  </div>
                )
              })}
            </div>

            {isCustomizingWeights && (
              <div className="mt-3 pt-3 border-t flex items-center justify-between text-xs" style={{ borderColor: 'var(--color-divider)' }}>
                <span className="text-muted">Total dos pesos definidos:</span>
                <span
                  className="font-bold tabular-nums"
                  style={{
                    color: Math.abs(totalCustomWeight - 100) < 0.1 ? 'var(--color-success)' : 'var(--color-notification)',
                  }}
                >
                  {totalCustomWeight.toFixed(1)}% {Math.abs(totalCustomWeight - 100) >= 0.1 && '(normalizado automaticamente)'}
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Coluna Direita: Simulador de Aporte */}
        <div className="lg:col-span-6 flex flex-col gap-4">
          <div className="card p-5">
            <div className="flex items-center gap-2 mb-2">
              <Calculator size={16} className="text-success" />
              <h3 className="font-bold text-sm" style={{ color: 'var(--color-text)' }}>
                Simulador de Aporte na Carteira
              </h3>
            </div>
            <p className="text-xs text-muted mb-4">
              Informe o valor que planeja investir para ver a distribuição exata em reais e a quantidade sugerida por ativo.
            </p>

            <form onSubmit={handleSimulate} className="flex flex-col gap-3">
              <div>
                <label className="text-[11px] font-semibold text-muted block mb-1">
                  Valor a Investir (R$)
                </label>
                <div className="flex gap-2">
                  <input
                    type="number"
                    min="100"
                    step="100"
                    placeholder="Ex: 5000"
                    value={simulationAmount}
                    onChange={e => setSimulationAmount(e.target.value)}
                    className="input text-sm flex-1 font-semibold"
                  />
                  <button
                    type="submit"
                    className="btn btn-primary px-4 text-xs font-semibold"
                    disabled={simulateMutation.isPending}
                  >
                    Simular
                  </button>
                </div>
              </div>

              {/* Botões de atalho rápido */}
              <div className="flex items-center gap-1.5 flex-wrap">
                {[1000, 2500, 5000, 10000, 20000].map(val => (
                  <button
                    key={val}
                    type="button"
                    onClick={() => {
                      setSimulationAmount(String(val))
                      simulateMutation.mutate({
                        strategy: activeStrategy,
                        total_amount: val,
                        custom_class_weights: isCustomizingWeights ? customWeights : undefined,
                      })
                    }}
                    className="px-2.5 py-1 rounded-md text-[11px] font-medium bg-surface-offset hover:bg-surface text-muted transition-colors cursor-pointer"
                  >
                    + {formatBRL(val)}
                  </button>
                ))}
              </div>
            </form>

            {/* Resultado da Simulação */}
            {simulationResult && (
              <div className="mt-5 pt-4 border-t flex flex-col gap-3" style={{ borderColor: 'var(--color-divider)' }}>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-muted">Total Alocado:</span>
                  <span className="font-bold text-text text-sm tabular-nums">
                    {formatBRL(simulationResult.total_amount)}
                  </span>
                </div>

                <div className="p-3 rounded-xl bg-surface-offset text-xs text-muted leading-relaxed">
                  {simulationResult.summary}
                </div>

                <div className="flex flex-col gap-2 max-h-[340px] overflow-y-auto pr-1">
                  {simulationResult.classes.map(c => (
                    <div key={c.asset_type} className="p-2.5 rounded-lg border bg-surface flex flex-col gap-2" style={{ borderColor: 'var(--color-divider)' }}>
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-bold text-text">{c.label} ({c.target_weight_pct.toFixed(0)}%)</span>
                        <span className="font-semibold text-primary tabular-nums">{formatBRL(c.allocated_amount)}</span>
                      </div>

                      <div className="flex flex-col gap-1.5">
                        {c.assets.map(a => (
                          <div key={a.ticker} className="flex items-center justify-between text-[11px] py-1 border-t" style={{ borderColor: 'var(--color-divider)' }}>
                            <div className="flex items-center gap-1.5">
                              <span className="font-bold text-text">{a.ticker}</span>
                              <span className="text-muted truncate max-w-[140px]">{a.name}</span>
                            </div>
                            <div className="text-right tabular-nums">
                              <div className="font-semibold text-text">{formatBRL(a.allocated_amount)}</div>
                              <div className="text-[10px] text-muted">
                                {a.suggested_quantity >= 1 ? `${Math.floor(a.suggested_quantity)} un.` : `${a.suggested_quantity} un.`}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Seção Detalhada: Teses e Ativos Selecionados pela IA */}
      <div className="card p-6 flex flex-col gap-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h3 className="text-base font-bold" style={{ color: 'var(--color-text)' }}>
              Composição e Teses de Investimento por Ativo
            </h3>
            <p className="text-xs text-muted">
              Justificativas analíticas e critérios de seleção estabelecidos para a estratégia {activeConfig.label}.
            </p>
          </div>

          <button
            type="button"
            onClick={handleApplyToMetas}
            className="btn btn-secondary flex items-center gap-2 self-start sm:self-auto text-xs font-semibold"
          >
            {copiedSuccess ? (
              <>
                <CheckCircle2 size={14} className="text-success" />
                <span>Aplicado! Redirecionando…</span>
              </>
            ) : (
              <>
                <span>Adotar Alocação em Minhas Metas</span>
                <ArrowRight size={13} />
              </>
            )}
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {activePortfolio.classes.flatMap(c =>
            c.assets.map(a => (
              <div
                key={a.ticker}
                className="p-4 rounded-xl border flex flex-col justify-between gap-3 bg-surface"
                style={{ borderColor: 'var(--color-divider)' }}
              >
                <div>
                  <div className="flex items-center justify-between gap-2 mb-1.5">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-sm text-text">{a.ticker}</span>
                      <span className={`asset-badge ${assetBadgeClass(a.asset_type)} text-[9px]`}>
                        {c.label}
                      </span>
                    </div>
                    <span className="text-xs font-semibold text-primary tabular-nums">
                      {a.target_weight_pct}% da carteira
                    </span>
                  </div>

                  <p className="text-xs font-medium text-text mb-2">{a.name}</p>

                  <div className="p-2.5 rounded-lg bg-surface-offset text-[11px] text-muted leading-relaxed">
                    <span className="font-semibold text-text block mb-0.5">Tese da IA:</span>
                    {a.reason}
                  </div>
                </div>

                <div className="flex items-center justify-between pt-2 border-t text-[11px]" style={{ borderColor: 'var(--color-divider)' }}>
                  <div className="text-muted">
                    Preço ref.: <span className="font-semibold text-text tabular-nums">{fmtMoney(a.current_price, 'BRL')}</span>
                  </div>
                  {a.expected_yield_pct != null && a.expected_yield_pct > 0 && (
                    <div className="text-success font-semibold tabular-nums">
                      Yield est.: {a.expected_yield_pct.toFixed(1)}% a.a.
                    </div>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}
