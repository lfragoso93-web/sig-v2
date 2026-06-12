import { useState } from 'react'
import clsx from 'clsx'
import { TrendingUp, Target, Wallet, DollarSign } from 'lucide-react'
import { usePortfolioList } from '@/hooks/usePortfolio'
import {
  useProventosSummary,
  useProventosDistribution,
  useProventosEvolucao,
  useProventosHistoricoMensal,
  useProventosList,
} from '@/hooks/useProventos'
import { formatBRL, formatPercent } from '@/utils/format'
import ProventosBarChart from '@/components/charts/ProventosBarChart'
import ProventosDonutChart from '@/components/charts/ProventosDonutChart'
import ProventosHistoricoTable from '@/components/proventos/ProventosHistoricoTable'
import MeusProventosTable from '@/components/proventos/MeusProventosTable'
import EmptyState from '@/components/ui/EmptyState'

const PERIOD_OPTIONS = [
  { label: 'Últimos 12 meses', value: '12m' },
  { label: 'Últimos 24 meses', value: '24m' },
  { label: 'Este ano',         value: 'ytd' },
  { label: 'Desde o início',   value: 'all' },
]

const ASSET_TYPE_OPTIONS = [
  { label: 'Todos os tipos',       value: ''              },
  { label: 'Ações',               value: 'ACAO_NACIONAL'  },
  { label: 'FIIs',                 value: 'FII'           },
  { label: 'ETFs Nacionais',       value: 'ETF_NACIONAL'  },
  { label: 'Tesouro Direto',       value: 'TESOURO_DIRETO'},
  { label: 'Stocks',               value: 'STOCK'         },
  { label: 'ETFs Internacionais',  value: 'ETF_INTERNACIONAL' },
  { label: 'Criptomoedas',         value: 'CRIPTO'        },
  { label: 'Renda Fixa',           value: 'RENDA_FIXA'    },
]

const YEARS = [new Date().getFullYear(), new Date().getFullYear() - 1, new Date().getFullYear() - 2]

export default function ProventosPage() {
  const { data: portfolios } = usePortfolioList()
  const [selectedPortfolio, setSelectedPortfolio] = useState<number | null>(null)
  const portfolioId = selectedPortfolio ?? (portfolios?.[0]?.id ?? 0)

  const [tipoGrafico,    setTipoGrafico]    = useState<'mensal' | 'anual'>('mensal')
  const [period,         setPeriod]         = useState('12m')
  const [assetTypeFilter,setAssetTypeFilter] = useState('')
  const [statusFilter,   setStatusFilter]   = useState('')
  const [yearFilter,     setYearFilter]     = useState<number | undefined>(undefined)

  const { data: summary }      = useProventosSummary(portfolioId)
  const { data: distribution } = useProventosDistribution(portfolioId)
  const { data: evolucao,  isLoading: loadingEvolucao  } = useProventosEvolucao(portfolioId, tipoGrafico, period)
  const { data: historico, isLoading: loadingHistorico } = useProventosHistoricoMensal(portfolioId, statusFilter, assetTypeFilter)
  const { data: lista,     isLoading: loadingLista     } = useProventosList(portfolioId, yearFilter, statusFilter || undefined, assetTypeFilter || undefined)

  return (
    <div className="p-4 md:p-6 flex flex-col gap-5 max-w-[1400px] mx-auto">

      {/* Seletor de carteira */}
      {(portfolios?.length ?? 0) > 1 && (
        <div className="flex items-center gap-2">
          <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>Carteira:</span>
          {portfolios!.map(p => (
            <button
              key={p.id}
              onClick={() => setSelectedPortfolio(p.id)}
              className="px-3 py-1 rounded text-xs font-medium transition-colors"
              style={{
                background: portfolioId === p.id ? 'oklch(from var(--color-primary) l c h / 0.15)' : 'var(--color-surface-offset)',
                color: portfolioId === p.id ? 'var(--color-primary)' : 'var(--color-text-muted)',
              }}
            >
              {p.name}
            </button>
          ))}
        </div>
      )}

      {/* Layout principal */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-5">

        {/* Painel esquerdo: KPIs + Donut */}
        <div className="flex flex-col gap-4">
          <div className="card p-4 flex flex-col gap-3">
            {/* KPI: Total recebido */}
            <div>
              <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>Total recebido</span>
              <div className="text-lg font-bold tabular-nums" style={{ color: 'var(--color-text)' }}>
                {formatBRL(summary?.total_recebido ?? 0)}
              </div>
            </div>
            <div style={{ borderTop: '1px solid var(--color-divider)' }} />
            {/* KPI: Média mensal */}
            <div>
              <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>Média mensal (12m)</span>
              <div className="text-base font-bold tabular-nums" style={{ color: 'var(--color-text)' }}>
                {formatBRL(summary?.media_mensal_12m ?? 0)}
              </div>
            </div>
            <div style={{ borderTop: '1px solid var(--color-divider)' }} />
            {/* KPI: Yield on Cost */}
            <div>
              <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>Yield on Cost</span>
              <div className="text-base font-bold tabular-nums" style={{ color: 'var(--color-primary)' }}>
                {formatPercent(summary?.yield_on_cost ?? 0)}
              </div>
            </div>
          </div>

          {/* Donut por tipo */}
          {distribution && distribution.length > 0 ? (
            <div className="card p-4">
              <p className="text-xs font-semibold mb-3">Por tipo de ativo</p>
              <ProventosDonutChart data={distribution} />
            </div>
          ) : null}
        </div>

        {/* Conteúdo principal: gráficos + tabelas */}
        <div className="lg:col-span-3 flex flex-col gap-5">

          {/* Controles de período + tipo */}
          <div className="flex flex-wrap items-center gap-2">
            <select
              value={period}
              onChange={e => setPeriod(e.target.value)}
              className="input text-xs"
            >
              {PERIOD_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
            <select
              value={assetTypeFilter}
              onChange={e => setAssetTypeFilter(e.target.value)}
              className="input text-xs"
            >
              {ASSET_TYPE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
            {/* Toggle mensal/anual */}
            <div
              className="flex items-center gap-1 p-1 rounded-lg"
              style={{ background: 'var(--color-surface-offset)' }}
            >
              {(['mensal', 'anual'] as const).map(v => (
                <button
                  key={v}
                  onClick={() => setTipoGrafico(v)}
                  className="px-3 py-1 rounded text-xs font-medium transition-colors capitalize"
                  style={{
                    background: tipoGrafico === v ? 'oklch(from var(--color-primary) l c h / 0.15)' : 'transparent',
                    color: tipoGrafico === v ? 'var(--color-primary)' : 'var(--color-text-muted)',
                  }}
                >
                  {v}
                </button>
              ))}
            </div>
          </div>

          {/* Gráfico de evolução */}
          <div className="card p-4">
            <p className="text-xs font-semibold mb-3">Evolução de proventos</p>
            {loadingEvolucao ? (
              <div className="h-48 skeleton rounded-lg" />
            ) : evolucao && evolucao.length > 0 ? (
              <ProventosBarChart data={evolucao} />
            ) : (
              <div className="h-48 flex items-center justify-center text-xs" style={{ color: 'var(--color-text-muted)' }}>
                Sem dados para o período selecionado.
              </div>
            )}
          </div>

          {/* Histórico mensal */}
          <div className="card p-4">
            <p className="text-xs font-semibold mb-3">Histórico mensal</p>
            {loadingHistorico ? (
              <div className="flex flex-col gap-2">
                {[...Array(6)].map((_, i) => <div key={i} className="h-8 skeleton rounded" />)}
              </div>
            ) : (
              <ProventosHistoricoTable data={historico ?? []} />
            )}
          </div>

          {/* Meus proventos (lista detalhada) */}
          <div className="card p-4">
            <div className="flex items-center justify-between mb-3">
              <p className="text-xs font-semibold">Meus proventos</p>
              {/* Filtro por ano */}
              <div className="flex items-center gap-1">
                <button
                  onClick={() => setYearFilter(undefined)}
                  className="px-2 py-0.5 rounded text-xs font-medium transition-colors"
                  style={{
                    background: yearFilter === undefined ? 'oklch(from var(--color-primary) l c h / 0.15)' : 'transparent',
                    color: yearFilter === undefined ? 'var(--color-primary)' : 'var(--color-text-muted)',
                  }}
                >
                  Todos
                </button>
                {YEARS.map(y => (
                  <button
                    key={y}
                    onClick={() => setYearFilter(y)}
                    className="px-2 py-0.5 rounded text-xs font-medium transition-colors"
                    style={{
                      background: yearFilter === y ? 'oklch(from var(--color-primary) l c h / 0.15)' : 'transparent',
                      color: yearFilter === y ? 'var(--color-primary)' : 'var(--color-text-muted)',
                    }}
                  >
                    {y}
                  </button>
                ))}
              </div>
            </div>
            {loadingLista ? (
              <div className="flex flex-col gap-2">
                {[...Array(4)].map((_, i) => <div key={i} className="h-10 skeleton rounded" />)}
              </div>
            ) : (
              <MeusProventosTable data={lista ?? []} />
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
