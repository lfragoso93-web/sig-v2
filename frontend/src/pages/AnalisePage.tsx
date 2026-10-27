import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  PieChart,
  ArrowUpRight,
  ArrowDownRight,
  CheckCircle2,
  TrendingUp,
  AlertTriangle,
  Layers,
  Info,
  RefreshCw,
  Sparkles,
  HelpCircle,
  Send,
  Calculator,
  ShieldCheck,
  Coins,
  Sliders,
} from 'lucide-react'
import { useAppStore } from '@/store/appStore'
import { usePortfolios } from '@/hooks/usePortfolios'
import {
  usePortfolioAnalysis,
  type ClassAnalysisDetail,
} from '@/hooks/usePortfolioAnalysis'
import {
  usePortfolioAiAnalysis,
  useSimulateContribution,
  useAskPortfolioAi,
  type ContributionStrategy,
} from '@/hooks/usePortfolioAiAnalysis'
import { formatBRL } from '@/utils/format'
import KpiCard from '@/components/ui/KpiCard'
import EmptyState from '@/components/ui/EmptyState'

function healthColor(score: number): string {
  if (score >= 80) return 'var(--color-success)'
  if (score >= 60) return 'var(--color-primary)'
  if (score >= 40) return 'var(--color-warning)'
  return 'var(--color-notification)'
}

function healthLabel(score: number): string {
  if (score >= 80) return 'Excelente'
  if (score >= 60) return 'Equilibrada'
  if (score >= 40) return 'Atenção'
  return 'Desbalanceada'
}

function concentrationBadge(level: string): { bg: string; text: string; label: string } {
  switch (level) {
    case 'critical':
      return { bg: 'oklch(from var(--color-notification) l c h / 0.12)', text: 'var(--color-notification)', label: 'Crítico' }
    case 'warning':
      return { bg: 'oklch(from var(--color-warning) l c h / 0.15)', text: 'var(--color-warning)', label: 'Atenção' }
    case 'balanced':
      return { bg: 'oklch(from var(--color-primary) l c h / 0.12)', text: 'var(--color-primary)', label: 'Equilibrado' }
    default:
      return { bg: 'oklch(from var(--color-success) l c h / 0.12)', text: 'var(--color-success)', label: 'Baixo' }
  }
}

function PortfolioAiSection({ portfolioId }: { portfolioId: number }) {
  const navigate = useNavigate()
  const { data: aiData, isLoading, error } = usePortfolioAiAnalysis(portfolioId)
  const { data: analysisData } = usePortfolioAnalysis(portfolioId)
  const simulateMutation = useSimulateContribution(portfolioId)
  const askMutation = useAskPortfolioAi(portfolioId)

  const [simAmount, setSimAmount] = useState('5000')
  const [strategy, setStrategy] = useState<ContributionStrategy>('patrimonio')
  const [questionInput, setQuestionInput] = useState('')
  const [qaList, setQaList] = useState<Array<{ q: string; a: string; metrics: string[] }>>([])

  const handleSimulate = (amountToSim: number, strat: ContributionStrategy = strategy) => {
    simulateMutation.mutate({ amount: amountToSim, strategy: strat })
  }

  const handleAsk = (q: string) => {
    if (!q.trim()) return
    askMutation.mutate(q, {
      onSuccess: res => {
        setQaList(prev => [{ q, a: res.answer, metrics: res.key_metrics_referenced }, ...prev])
        setQuestionInput('')
      },
    })
  }

  if (isLoading) {
    return (
      <div className="flex flex-col gap-4">
        <div className="skeleton h-36 w-full rounded-xl" />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="skeleton h-48 rounded-xl" />
          <div className="skeleton h-48 rounded-xl" />
        </div>
      </div>
    )
  }

  if (error || !aiData) {
    return (
      <div className="card p-6 text-center text-xs text-muted flex flex-col items-center gap-2">
        <AlertTriangle size={24} style={{ color: 'var(--color-warning)' }} />
        <span>Não foi possível gerar a síntese explicativa de IA no momento.</span>
      </div>
    )
  }

  const quickQuestions = [
    'Qual a classe mais prioritária para aportar?',
    'Onde está meu maior risco de concentração?',
    'Como melhorar meu score de alocação?',
    'Como está o fluxo de dividendos?',
  ]

  return (
    <div className="flex flex-col gap-6">
      {/* Executive Summary Card */}
      <div
        className="rounded-xl p-5 flex flex-col gap-4"
        style={{
          background: 'var(--color-surface)',
          border: '1px solid var(--color-border)',
          boxShadow: 'var(--shadow-sm)',
        }}
      >
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center gap-2.5">
            <div
              className="w-8 h-8 rounded-lg flex items-center justify-center"
              style={{
                background: 'oklch(from var(--color-primary) l c h / 0.12)',
                color: 'var(--color-primary)',
              }}
            >
              <Sparkles size={18} />
            </div>
            <div>
              <h2 className="text-sm font-semibold flex items-center gap-2">
                Síntese Executiva & Postura Estratégica
              </h2>
              <span className="text-[11px] text-muted">{aiData.posture_label}</span>
            </div>
          </div>
          <span
            className="text-[10px] px-2.5 py-1 rounded-full font-medium flex items-center gap-1.5"
            style={{
              background: 'oklch(from var(--color-primary) l c h / 0.1)',
              color: 'var(--color-primary)',
            }}
          >
            <ShieldCheck size={12} />
            IA Auditável · Não-alucinação
          </span>
        </div>

        <p className="text-xs leading-relaxed" style={{ color: 'var(--color-text)' }}>
          {aiData.executive_summary}
        </p>

        <p className="text-xs text-muted leading-relaxed italic">
          {aiData.posture_summary}
        </p>

        {/* Strengths & Attention Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
          {/* Strengths */}
          <div
            className="rounded-lg p-3.5 flex flex-col gap-2"
            style={{
              background: 'oklch(from var(--color-success) l c h / 0.05)',
              border: '1px solid oklch(from var(--color-success) l c h / 0.15)',
            }}
          >
            <span className="text-xs font-semibold flex items-center gap-1.5" style={{ color: 'var(--color-success)' }}>
              <CheckCircle2 size={14} /> Pontos Fortes Observados
            </span>
            <ul className="flex flex-col gap-1.5">
              {aiData.key_strengths.map((st, i) => (
                <li key={i} className="text-xs flex items-start gap-1.5" style={{ color: 'var(--color-text)' }}>
                  <span className="text-muted shrink-0">•</span>
                  <span>{st}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* Attention Points */}
          <div
            className="rounded-lg p-3.5 flex flex-col gap-2"
            style={{
              background: 'oklch(from var(--color-warning) l c h / 0.05)',
              border: '1px solid oklch(from var(--color-warning) l c h / 0.15)',
            }}
          >
            <span className="text-xs font-semibold flex items-center gap-1.5" style={{ color: 'var(--color-warning)' }}>
              <AlertTriangle size={14} /> Pontos de Atenção & Riscos
            </span>
            <ul className="flex flex-col gap-1.5">
              {aiData.attention_points.map((pt, i) => (
                <li key={i} className="text-xs flex items-start gap-1.5" style={{ color: 'var(--color-text)' }}>
                  <span className="text-muted shrink-0">•</span>
                  <span>{pt}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Rebalancing Strategy */}
        <div
          className="rounded-lg p-3 flex flex-col gap-1"
          style={{
            background: 'var(--color-surface-offset)',
            border: '1px solid var(--color-divider)',
          }}
        >
          <span className="text-xs font-semibold text-muted">Estratégia Recomendada de Rebalanceamento:</span>
          <p className="text-xs leading-relaxed" style={{ color: 'var(--color-text)' }}>
            {aiData.rebalancing_strategy}
          </p>
        </div>
      </div>

      {/* Contribution Simulator Widget */}
      <div
        className="rounded-xl p-5 flex flex-col gap-4"
        style={{
          background: 'var(--color-surface)',
          border: '1px solid var(--color-border)',
          boxShadow: 'var(--shadow-sm)',
        }}
      >
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center gap-2">
            <Calculator size={18} style={{ color: 'var(--color-primary)' }} />
            <h3 className="text-sm font-semibold">Simulador Inteligente de Próximo Aporte</h3>
          </div>
          <button
            type="button"
            onClick={() => navigate('/configuracoes?tab=distribuicao')}
            className="text-[11px] font-medium flex items-center gap-1 hover:underline text-muted"
          >
            <Sliders size={12} />
            Metas de Distribuição
            <ArrowUpRight size={11} />
          </button>
        </div>

        {/* Empty state banner when no targets or classes */}
        {analysisData?.classes?.length === 0 && (
          <div
            className="rounded-lg p-3.5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs"
            style={{
              background: 'oklch(from var(--color-primary) l c h / 0.08)',
              border: '1px solid oklch(from var(--color-primary) l c h / 0.2)',
            }}
          >
            <div className="flex items-center gap-2">
              <Layers size={16} style={{ color: 'var(--color-primary)' }} className="shrink-0" />
              <span>Sua carteira ainda não possui metas de distribuição cadastradas. Configure os percentuais desejados para simular aportes inteligentes.</span>
            </div>
            <button
              type="button"
              onClick={() => navigate('/configuracoes?tab=distribuicao')}
              className="btn btn-primary text-xs py-1 px-3 shrink-0 flex items-center gap-1"
            >
              Definir Metas
              <ArrowUpRight size={12} />
            </button>
          </div>
        )}

        {/* Strategy Selector (Item 6) */}
        <div className="flex flex-col gap-1.5">
          <label className="text-[11px] font-semibold text-muted">Objetivo do Aporte:</label>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
            {[
              { id: 'patrimonio', label: 'Acúmulo de Patrimônio', desc: 'Equilíbrio e diversificação', icon: Layers },
              { id: 'proventos', label: 'Proventos & Renda', desc: 'Maximização de dividendos', icon: Coins },
              { id: 'performance', label: 'Performance & Crescimento', desc: 'Retorno e valorização', icon: TrendingUp },
            ].map(item => {
              const isSelected = strategy === item.id
              const Icon = item.icon
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => {
                    const newStrat = item.id as ContributionStrategy
                    setStrategy(newStrat)
                    if (Number(simAmount) > 0) {
                      handleSimulate(Number(simAmount), newStrat)
                    }
                  }}
                  className="flex items-center gap-2.5 p-2.5 rounded-lg border text-left transition-all"
                  style={{
                    background: isSelected ? 'oklch(from var(--color-primary) l c h / 0.12)' : 'var(--color-surface-offset)',
                    borderColor: isSelected ? 'var(--color-primary)' : 'var(--color-border)',
                    color: isSelected ? 'var(--color-primary)' : 'var(--color-text)',
                  }}
                >
                  <Icon size={16} className="shrink-0" />
                  <div className="flex flex-col">
                    <span className="text-xs font-semibold">{item.label}</span>
                    <span className="text-[10px] text-muted">{item.desc}</span>
                  </div>
                </button>
              )
            })}
          </div>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <div className="flex items-center gap-1.5">
            <span className="text-xs text-muted">R$</span>
            <input
              type="number"
              value={simAmount}
              onChange={e => setSimAmount(e.target.value)}
              className="input text-xs w-32 py-1 px-2"
              placeholder="Ex: 5000"
              min="1"
            />
          </div>

          <div className="flex items-center gap-1.5">
            {[1000, 5000, 10000].map(val => (
              <button
                key={val}
                type="button"
                onClick={() => {
                  setSimAmount(val.toString())
                  handleSimulate(val)
                }}
                className="btn btn-secondary text-[11px] py-1 px-2.5"
              >
                R$ {val.toLocaleString('pt-BR')}
              </button>
            ))}
          </div>

          <button
            type="button"
            disabled={simulateMutation.isPending || !Number(simAmount)}
            onClick={() => handleSimulate(Number(simAmount))}
            className="btn btn-primary text-xs py-1.5 px-3 flex items-center gap-1.5 ml-auto"
          >
            {simulateMutation.isPending ? <RefreshCw size={12} className="animate-spin" /> : <Calculator size={14} />}
            Simular Aporte
          </button>
        </div>

        {/* Simulation Results */}
        {simulateMutation.data && (
          <div className="flex flex-col gap-4 pt-2">
            <div
              className="rounded-lg p-3 text-xs leading-relaxed"
              style={{
                background: 'oklch(from var(--color-primary) l c h / 0.08)',
                border: '1px solid oklch(from var(--color-primary) l c h / 0.15)',
              }}
            >
              <strong>Impacto do Aporte: </strong>
              {simulateMutation.data.overall_impact_summary}
            </div>

            {/* Tabela 1: Distribuição por Classes */}
            {simulateMutation.data.suggested_allocations.length > 0 && (
              <div className="flex flex-col gap-1.5">
                <span className="text-xs font-semibold text-muted">Distribuição por Classes de Ativos</span>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs text-left">
                    <thead>
                      <tr style={{ borderBottom: '1px solid var(--color-divider)' }}>
                        <th className="py-2 px-3 text-muted font-medium">Classe</th>
                        <th className="py-2 px-3 text-muted font-medium text-right">Valor Atual</th>
                        <th className="py-2 px-3 text-muted font-medium text-right">% Atual</th>
                        <th className="py-2 px-3 text-muted font-medium text-right">Meta %</th>
                        <th className="py-2 px-3 text-muted font-medium text-right font-semibold" style={{ color: 'var(--color-primary)' }}>Aporte Sugerido</th>
                        <th className="py-2 px-3 text-muted font-medium text-right">% Projetada</th>
                      </tr>
                    </thead>
                    <tbody>
                      {simulateMutation.data.suggested_allocations.map(alloc => (
                        <tr
                          key={alloc.asset_type}
                          style={{ borderBottom: '1px solid var(--color-divider)' }}
                        >
                          <td className="py-2.5 px-3 font-semibold">{alloc.label}</td>
                          <td className="py-2.5 px-3 text-right">{formatBRL(alloc.current_value)}</td>
                          <td className="py-2.5 px-3 text-right">{alloc.current_weight_pct.toFixed(1)}%</td>
                          <td className="py-2.5 px-3 text-right text-muted">{alloc.target_weight_pct ? `${alloc.target_weight_pct.toFixed(1)}%` : '—'}</td>
                          <td className="py-2.5 px-3 text-right font-bold" style={{ color: alloc.allocated_amount > 0 ? 'var(--color-success)' : 'var(--color-text-faint)' }}>
                            {alloc.allocated_amount > 0 ? `+ ${formatBRL(alloc.allocated_amount)}` : 'R$ 0,00'}
                          </td>
                          <td className="py-2.5 px-3 text-right font-medium">{alloc.projected_weight_pct.toFixed(1)}%</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Tabela 2: Ativos Recomendados para Aporte (Item 6) */}
            {simulateMutation.data.suggested_assets && simulateMutation.data.suggested_assets.length > 0 && (
              <div className="flex flex-col gap-2 pt-2">
                <div className="flex items-center justify-between flex-wrap gap-1">
                  <span className="text-xs font-semibold" style={{ color: 'var(--color-text)' }}>
                    Ativos Recomendados para Aporte ({simulateMutation.data.strategy === 'proventos' ? 'Foco em Proventos' : simulateMutation.data.strategy === 'performance' ? 'Foco em Performance' : 'Acúmulo de Patrimônio'})
                  </span>
                  <span className="text-[11px] text-muted">
                    Ativos selecionados de acordo com sua meta
                  </span>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs text-left">
                    <thead>
                      <tr style={{ borderBottom: '1px solid var(--color-divider)' }}>
                        <th className="py-2 px-3 text-muted font-medium">Ativo / Ticker</th>
                        <th className="py-2 px-3 text-muted font-medium">Classe</th>
                        <th className="py-2 px-3 text-muted font-medium text-right">Preço Atual</th>
                        <th className="py-2 px-3 text-muted font-medium text-right">Qtd. Estimada</th>
                        <th className="py-2 px-3 text-muted font-medium text-right font-semibold" style={{ color: 'var(--color-primary)' }}>Aporte Sugerido</th>
                        <th className="py-2 px-3 text-muted font-medium">Justificativa da Meta</th>
                      </tr>
                    </thead>
                    <tbody>
                      {simulateMutation.data.suggested_assets.map((asset, idx) => (
                        <tr
                          key={`${asset.ticker}-${idx}`}
                          style={{ borderBottom: '1px solid var(--color-divider)' }}
                        >
                          <td className="py-2.5 px-3">
                            <div className="flex flex-col">
                              <span className="font-semibold" style={{ color: 'var(--color-text)' }}>{asset.ticker}</span>
                              <span className="text-[10px] text-muted">{asset.name}</span>
                            </div>
                          </td>
                          <td className="py-2.5 px-3">
                            <span className="text-[10px] px-1.5 py-0.5 rounded font-medium" style={{ background: 'var(--color-surface-offset)', color: 'var(--color-text-muted)' }}>
                              {asset.asset_type}
                            </span>
                          </td>
                          <td className="py-2.5 px-3 text-right">
                            {asset.current_price > 0 ? formatBRL(asset.current_price) : '—'}
                          </td>
                          <td className="py-2.5 px-3 text-right font-medium">
                            {asset.suggested_quantity > 0 ? asset.suggested_quantity.toLocaleString('pt-BR', { maximumFractionDigits: 4 }) : '—'}
                          </td>
                          <td className="py-2.5 px-3 text-right font-bold" style={{ color: 'var(--color-success)' }}>
                            + {formatBRL(asset.suggested_amount)}
                          </td>
                          <td className="py-2.5 px-3 text-[11px] text-muted max-w-xs leading-tight">
                            {asset.reason}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Interactive Q&A Widget */}
      <div
        className="rounded-xl p-5 flex flex-col gap-4"
        style={{
          background: 'var(--color-surface)',
          border: '1px solid var(--color-border)',
          boxShadow: 'var(--shadow-sm)',
        }}
      >
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center gap-2">
            <HelpCircle size={18} style={{ color: 'var(--color-primary)' }} />
            <h3 className="text-sm font-semibold">Perguntas Rápidas sobre a Carteira (Q&A)</h3>
          </div>
          <span className="text-[11px] text-muted">Respostas estritamente ancoradas nas métricas</span>
        </div>

        {/* Quick prompt pills */}
        <div className="flex items-center gap-2 flex-wrap">
          {quickQuestions.map((q, i) => (
            <button
              key={i}
              type="button"
              disabled={askMutation.isPending}
              onClick={() => handleAsk(q)}
              className="text-[11px] py-1 px-3 rounded-full border transition-colors hover:border-primary"
              style={{
                background: 'var(--color-surface-offset)',
                borderColor: 'var(--color-border)',
                color: 'var(--color-text)',
              }}
            >
              {q}
            </button>
          ))}
        </div>

        {/* Custom Input */}
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={questionInput}
            onChange={e => setQuestionInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleAsk(questionInput)}
            placeholder="Faça uma pergunta sobre sua alocação, riscos ou proventos..."
            className="input text-xs flex-1 py-1.5 px-3"
            maxLength={200}
          />
          <button
            type="button"
            disabled={askMutation.isPending || !questionInput.trim()}
            onClick={() => handleAsk(questionInput)}
            className="btn btn-primary text-xs py-1.5 px-3 flex items-center gap-1.5 shrink-0"
          >
            {askMutation.isPending ? <RefreshCw size={12} className="animate-spin" /> : <Send size={12} />}
            Perguntar
          </button>
        </div>

        {/* Q&A Stream / Responses */}
        {qaList.length > 0 && (
          <div className="flex flex-col gap-3 pt-2">
            {qaList.map((item, idx) => (
              <div
                key={idx}
                className="rounded-lg p-3.5 flex flex-col gap-2"
                style={{
                  background: 'var(--color-surface-offset)',
                  border: '1px solid var(--color-border)',
                }}
              >
                <div className="flex items-center gap-2 text-xs font-semibold" style={{ color: 'var(--color-primary)' }}>
                  <HelpCircle size={14} />
                  <span>{item.q}</span>
                </div>
                <p className="text-xs leading-relaxed" style={{ color: 'var(--color-text)' }}>
                  {item.a}
                </p>
                {item.metrics.length > 0 && (
                  <div className="flex items-center gap-1.5 flex-wrap pt-1 text-[10px] text-muted">
                    <span>Métricas referenciadas:</span>
                    {item.metrics.map(m => (
                      <span
                        key={m}
                        className="px-1.5 py-0.5 rounded"
                        style={{ background: 'var(--color-surface)', border: '1px solid var(--color-divider)' }}
                      >
                        {m}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Audit Telemetry & Governance Box */}
      <div
        className="rounded-xl p-3.5 flex items-center justify-between flex-wrap gap-2 text-[11px] text-muted"
        style={{
          background: 'var(--color-surface-offset)',
          border: '1px solid var(--color-divider)',
        }}
      >
        <span>
          Motor: <strong>{aiData.metadata.provider}</strong> ({aiData.metadata.model}) · Resposta em {aiData.metadata.execution_time_ms}ms
        </span>
        <span className="italic">{aiData.metadata.disclaimer}</span>
      </div>
    </div>
  )
}

function ClassAnalysisCard({ detail }: { detail: ClassAnalysisDetail }) {
  const [expanded, setExpanded] = useState(false)
  const isBuy = detail.allocation.rebalance_action === 'buy'
  const isReduce = detail.allocation.rebalance_action === 'reduce'
  const concBadge = concentrationBadge(detail.concentration.risk_level)

  return (
    <div
      className="rounded-xl overflow-hidden"
      style={{
        background: 'var(--color-surface)',
        border: '1px solid var(--color-border)',
        boxShadow: 'var(--shadow-sm)',
      }}
    >
      {/* Header */}
      <div
        className="p-4 flex items-center justify-between flex-wrap gap-3 cursor-pointer"
        onClick={() => setExpanded(e => !e)}
        style={{ borderBottom: '1px solid var(--color-divider)' }}
      >
        <div className="flex items-center gap-3">
          <div
            className="w-10 h-10 rounded-lg flex items-center justify-center font-bold text-sm"
            style={{
              background: 'var(--color-surface-offset)',
              color: 'var(--color-primary)',
            }}
          >
            {detail.label.slice(0, 2).toUpperCase()}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-semibold text-sm">{detail.label}</span>
              <span
                className="text-[10px] px-2 py-0.5 rounded-full font-medium"
                style={{ background: concBadge.bg, color: concBadge.text }}
              >
                Risco {concBadge.label}
              </span>
            </div>
            <p className="text-xs text-muted">
              {detail.concentration.asset_count} ativo{detail.concentration.asset_count !== 1 ? 's' : ''} · {formatBRL(detail.allocation.current_value)}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-6">
          {/* Target comparison */}
          <div className="text-right">
            <div className="text-xs font-semibold tabular-nums">
              {detail.allocation.current_weight_pct.toFixed(1)}%
              {detail.allocation.target_weight_pct !== null && (
                <span className="text-muted font-normal"> / meta {detail.allocation.target_weight_pct.toFixed(1)}%</span>
              )}
            </div>
            {detail.allocation.gap_weight_pct !== null && (
              <span
                className="text-[11px] font-medium flex items-center justify-end gap-0.5"
                style={{
                  color: isBuy ? 'var(--color-primary)' : isReduce ? 'var(--color-warning)' : 'var(--color-success)',
                }}
              >
                {isBuy && <ArrowUpRight size={12} />}
                {isReduce && <ArrowDownRight size={12} />}
                {detail.allocation.gap_weight_pct > 0 ? `+${detail.allocation.gap_weight_pct.toFixed(1)}%` : `${detail.allocation.gap_weight_pct.toFixed(1)}%`}
              </span>
            )}
          </div>

          {/* Health Score Pill */}
          <div
            className="px-2.5 py-1 rounded-lg font-bold text-xs flex items-center gap-1"
            style={{
              background: 'var(--color-surface-offset)',
              color: healthColor(detail.health_score),
            }}
          >
            <span>{detail.health_score}</span>
            <span className="text-[10px] font-normal text-muted">/100</span>
          </div>
        </div>
      </div>

      {/* Body */}
      <div className="p-4 flex flex-col gap-4">
        {/* Allocation Progress Bar */}
        <div>
          <div className="flex justify-between text-xs mb-1.5">
            <span className="text-muted">Alocação no patrimônio</span>
            <span className="font-medium tabular-nums">
              {detail.allocation.current_weight_pct.toFixed(1)}%
              {detail.allocation.target_weight_pct !== null && ` de ${detail.allocation.target_weight_pct.toFixed(1)}%`}
            </span>
          </div>
          <div
            className="w-full rounded-full overflow-hidden"
            style={{ height: 8, background: 'var(--color-surface-offset)' }}
          >
            <div
              className="h-full rounded-full transition-all"
              style={{
                width: `${Math.min(detail.allocation.current_weight_pct, 100)}%`,
                background: isBuy ? 'var(--color-primary)' : isReduce ? 'var(--color-warning)' : 'var(--color-success)',
              }}
            />
          </div>
        </div>

        {/* Suggestion / Rebalance alert */}
        <div
          className="p-3 rounded-lg flex items-start gap-2.5 text-xs"
          style={{
            background: isBuy
              ? 'oklch(from var(--color-primary) l c h / 0.08)'
              : isReduce
              ? 'oklch(from var(--color-warning) l c h / 0.08)'
              : 'oklch(from var(--color-success) l c h / 0.08)',
            border: `1px solid ${
              isBuy
                ? 'oklch(from var(--color-primary) l c h / 0.2)'
                : isReduce
                ? 'oklch(from var(--color-warning) l c h / 0.2)'
                : 'oklch(from var(--color-success) l c h / 0.2)'
            }`,
          }}
        >
          {isBuy ? (
            <ArrowUpRight size={16} className="shrink-0 mt-0.5" style={{ color: 'var(--color-primary)' }} />
          ) : isReduce ? (
            <AlertTriangle size={16} className="shrink-0 mt-0.5" style={{ color: 'var(--color-warning)' }} />
          ) : (
            <CheckCircle2 size={16} className="shrink-0 mt-0.5" style={{ color: 'var(--color-success)' }} />
          )}
          <div className="flex flex-col gap-0.5">
            <span className="font-semibold" style={{ color: 'var(--color-text)' }}>
              {detail.allocation.suggested_action_label}
            </span>
            {detail.allocation.gap_value !== null && isBuy && (
              <span className="text-[11px] text-muted">
                Faltam {formatBRL(Math.abs(detail.allocation.gap_value))} para atingir a meta estipulada.
              </span>
            )}
          </div>
        </div>

        {/* KPI Grid for Class */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
          {/* Top Asset */}
          <div className="p-2.5 rounded-lg" style={{ background: 'var(--color-surface-offset)' }}>
            <span className="text-[10px] text-muted block mb-0.5">Top Ativo</span>
            <span className="font-semibold text-xs block truncate">
              {detail.concentration.top_asset?.ticker ?? '—'}
            </span>
            <span className="text-[10px] text-muted tabular-nums">
              {detail.concentration.top_asset
                ? `${detail.concentration.top_asset.weight_in_class_pct.toFixed(1)}% da classe`
                : 'Sem posições'}
            </span>
          </div>

          {/* Income (Proventos) */}
          <div className="p-2.5 rounded-lg" style={{ background: 'var(--color-surface-offset)' }}>
            <span className="text-[10px] text-muted block mb-0.5">Proventos Acumulados</span>
            <span className="font-semibold text-xs block tabular-nums">
              {detail.income.is_applicable ? formatBRL(detail.income.total_proventos) : 'N/A'}
            </span>
            <span className="text-[10px] text-muted truncate block">
              {detail.income.is_applicable && detail.income.weighted_dy_pct !== null
                ? `DY Histórico: ${detail.income.weighted_dy_pct.toFixed(1)}%`
                : 'Classe de valorização'}
            </span>
          </div>

          {/* Fixed Income / Indexer */}
          {detail.fixed_income.is_applicable ? (
            <div className="p-2.5 rounded-lg" style={{ background: 'var(--color-surface-offset)' }}>
              <span className="text-[10px] text-muted block mb-0.5">Indexadores RF</span>
              <span className="font-semibold text-xs block">
                CDI {detail.fixed_income.cdi_allocation_pct ?? 0}% · IPCA {detail.fixed_income.ipca_allocation_pct ?? 0}%
              </span>
              <span className="text-[10px] text-muted">
                Pré: {detail.fixed_income.pre_allocation_pct ?? 0}%
              </span>
            </div>
          ) : (
            <div className="p-2.5 rounded-lg" style={{ background: 'var(--color-surface-offset)' }}>
              <span className="text-[10px] text-muted block mb-0.5">Índice HHI</span>
              <span className="font-semibold text-xs block tabular-nums">
                {detail.concentration.hhi_score ?? '—'}
              </span>
              <span className="text-[10px] text-muted">
                {detail.concentration.risk_label}
              </span>
            </div>
          )}

          {/* Health Score */}
          <div className="p-2.5 rounded-lg" style={{ background: 'var(--color-surface-offset)' }}>
            <span className="text-[10px] text-muted block mb-0.5">Saúde da Classe</span>
            <span className="font-semibold text-xs block" style={{ color: healthColor(detail.health_score) }}>
              {detail.health_score}/100 · {healthLabel(detail.health_score)}
            </span>
            <span className="text-[10px] text-muted">Equilíbrio & risco</span>
          </div>
        </div>

        {/* Key findings bullets if expanded */}
        {expanded && detail.key_findings.length > 0 && (
          <div className="pt-2 border-t" style={{ borderColor: 'var(--color-divider)' }}>
            <span className="text-[11px] font-semibold text-muted block mb-1.5">Diagnósticos da Classe:</span>
            <ul className="list-disc list-inside text-xs space-y-1 text-muted">
              {detail.key_findings.map((f, i) => (
                <li key={i} style={{ color: 'var(--color-text)' }}>{f}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  )
}

export default function AnalisePage() {
  const { data: portfolios = [], isLoading: loadingPortfolios } = usePortfolios()
  const globalPortfolioId = useAppStore(state => state.selectedPortfolioId)
  const setGlobal = useAppStore(state => state.setSelectedPortfolioId)

  const hasPortfolios = Boolean(portfolios && portfolios.length > 0)
  const validGlobalPortfolioId = hasPortfolios && portfolios.some(p => Number(p.id) === Number(globalPortfolioId))
    ? globalPortfolioId
    : null
  const portfolioId: number | null = validGlobalPortfolioId ?? (portfolios[0]?.id ? Number(portfolios[0].id) : (globalPortfolioId ? Number(globalPortfolioId) : null))

  const [activeTab, setActiveTab] = useState<'ai' | 'classes'>('ai')

  useEffect(() => {
    if (loadingPortfolios || !portfolios) return
    if (portfolios.length === 0) return
    if (globalPortfolioId !== portfolioId && portfolioId && typeof setGlobal === 'function') {
      setGlobal(portfolioId)
    }
  }, [globalPortfolioId, loadingPortfolios, portfolioId, portfolios, setGlobal])

  const { data: analysis, isLoading, error, refetch } = usePortfolioAnalysis(portfolioId)

  if ((loadingPortfolios && !portfolioId) || (isLoading && !analysis)) {
    return (
      <div className="page-container flex flex-col gap-4">
        <div className="skeleton h-8 w-64 rounded" />
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="skeleton h-24 rounded-xl" />
          ))}
        </div>
        <div className="skeleton h-48 w-full rounded-xl" />
      </div>
    )
  }

  if (!portfolioId) {
    return (
      <div className="page-container">
        <EmptyState
          icon={PieChart}
          title="Nenhuma carteira selecionada"
          description="Selecione uma carteira na barra superior para visualizar os diagnósticos e análises por classe."
        />
      </div>
    )
  }

  if (error || !analysis) {
    return (
      <div className="page-container">
        <div className="card p-8 flex flex-col items-center justify-center text-center gap-3">
          <AlertTriangle size={32} style={{ color: 'var(--color-notification)' }} />
          <h2 className="text-base font-semibold">Não foi possível carregar a análise da carteira</h2>
          <p className="text-xs text-muted max-w-md">
            Verifique sua conexão ou se a carteira possui lançamentos cadastrados.
          </p>
          <button onClick={() => refetch()} className="btn btn-secondary text-xs flex items-center gap-2">
            <RefreshCw size={14} /> Tentar novamente
          </button>
        </div>
      </div>
    )
  }

  const score = analysis.overall_health_score
  const scoreColor = healthColor(score)

  return (
    <div className="page-container flex flex-col gap-6">
      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title flex items-center gap-2">
            <PieChart size={24} style={{ color: 'var(--color-primary)' }} />
            Análise de Carteira & IA
          </h1>
          <p className="page-subtitle">
            {analysis.portfolio_name} · Diagnóstico determinístico por classe, síntese explicativa e rebalanceamento
          </p>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <KpiCard
          label="Score de Alocação"
          value={`${score}/100`}
          valueColor={scoreColor}
          subLabel={`Classificação: ${healthLabel(score)}`}
        />
        <KpiCard
          label="Patrimônio Analisado"
          value={formatBRL(analysis.total_value)}
          subLabel={`${analysis.classes_analyzed_count} classes ativas`}
        />
        <KpiCard
          label="Classes com Desvio"
          value={analysis.rebalance_priority_classes.length.toString()}
          valueColor={analysis.rebalance_priority_classes.length > 0 ? 'var(--color-warning)' : 'var(--color-success)'}
          subLabel={
            analysis.rebalance_priority_classes.length > 0
              ? `${analysis.rebalance_priority_classes.join(', ')}`
              : 'Nenhuma classe crítica'
          }
        />
        <KpiCard
          label="Maior Divergência"
          value={analysis.max_divergence_class ?? 'Nenhuma'}
          subLabel="Prioridade máxima de rebalanceamento"
        />
      </div>

      {/* Tab Navigation */}
      <div className="flex items-center gap-2 border-b" style={{ borderColor: 'var(--color-divider)' }}>
        <button
          type="button"
          onClick={() => setActiveTab('ai')}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition-colors ${
            activeTab === 'ai'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted hover:text-text'
          }`}
          style={{
            borderColor: activeTab === 'ai' ? 'var(--color-primary)' : 'transparent',
            color: activeTab === 'ai' ? 'var(--color-primary)' : 'var(--color-text-faint)',
          }}
        >
          <Sparkles size={14} />
          Diagnóstico com IA & Simulador de Aportes
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('classes')}
          className={`flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition-colors ${
            activeTab === 'classes'
              ? 'border-primary text-primary'
              : 'border-transparent text-muted hover:text-text'
          }`}
          style={{
            borderColor: activeTab === 'classes' ? 'var(--color-primary)' : 'transparent',
            color: activeTab === 'classes' ? 'var(--color-primary)' : 'var(--color-text-faint)',
          }}
        >
          <Layers size={14} />
          Detalhamento por Classes ({analysis.classes_analyzed_count})
        </button>
      </div>

      {/* Tab 1: AI Diagnosis & Simulator */}
      {activeTab === 'ai' && (
        <PortfolioAiSection portfolioId={portfolioId} />
      )}

      {/* Tab 2: Classes Breakdown */}
      {activeTab === 'classes' && (
        <div className="flex flex-col gap-4">
          {/* Rebalance Priority Alert */}
          {analysis.rebalance_priority_classes.length > 0 && (
            <div
              className="rounded-xl p-4 flex items-start gap-3"
              style={{
                background: 'oklch(from var(--color-primary) l c h / 0.08)',
                border: '1px solid oklch(from var(--color-primary) l c h / 0.2)',
              }}
            >
              <TrendingUp size={20} style={{ color: 'var(--color-primary)' }} className="shrink-0 mt-0.5" />
              <div className="flex flex-col gap-1">
                <span className="font-semibold text-xs" style={{ color: 'var(--color-text)' }}>
                  Oportunidades de Rebalanceamento Identificadas
                </span>
                <p className="text-xs text-muted">
                  Para convergir à alocação estratégica de longo prazo, priorize aportes em: <strong>{analysis.rebalance_priority_classes.join(', ')}</strong>.
                </p>
              </div>
            </div>
          )}

          <div className="flex items-center justify-between">
            <h2 className="text-sm font-semibold flex items-center gap-2">
              <Layers size={16} /> Diagnóstico Detalhado por Classe
            </h2>
            <span className="text-xs text-muted">
              {analysis.classes_analyzed_count} classe{analysis.classes_analyzed_count !== 1 ? 's' : ''} avaliada{analysis.classes_analyzed_count !== 1 ? 's' : ''}
            </span>
          </div>

          {analysis.classes.length === 0 ? (
            <div className="card p-8 text-center text-xs text-muted">
              Nenhuma classe de ativos encontrada com posições ativas.
            </div>
          ) : (
            <div className="flex flex-col gap-3">
              {analysis.classes.map(cls => (
                <ClassAnalysisCard key={cls.asset_type} detail={cls} />
              ))}
            </div>
          )}
        </div>
      )}

      {/* Provenance Box */}
      <div
        className="rounded-xl p-4 flex items-start gap-3 text-xs"
        style={{
          background: 'var(--color-surface-offset)',
          border: '1px solid var(--color-divider)',
        }}
      >
        <Info size={16} className="text-muted shrink-0 mt-0.5" />
        <div className="flex flex-col gap-1">
          <span className="font-semibold text-muted">Proveniência Canônica dos Dados:</span>
          <p className="text-[11px] text-muted">
            Cálculo 100% determinístico baseado nos serviços canônicos de valuation intradiário, histórico de proventos e metas de <code>portfolio_class_targets</code>. Nenhuma chamada externa a provedores de rede é realizada no caminho de análise.
          </p>
        </div>
      </div>
    </div>
  )
}
