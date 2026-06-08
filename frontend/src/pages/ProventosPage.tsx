import { useState } from 'react'
import clsx from 'clsx'
import { TrendingUp, Target, Wallet, ChevronDown, DollarSign } from 'lucide-react'
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
  { label: 'Este ano', value: 'ytd' },
  { label: 'Desde o início', value: 'all' },
]

const ASSET_TYPE_OPTIONS = [
  { label: 'Todos os tipos', value: '' },
  { label: 'Ações', value: 'ACAO_NACIONAL' },
  { label: 'FIIs', value: 'FII' },
  { label: 'ETFs Nacionais', value: 'ETF_NACIONAL' },
  { label: 'Tesouro Direto', value: 'TESOURO_DIRETO' },
  { label: 'Stocks', value: 'STOCK' },
  { label: 'ETFs Internacionais', value: 'ETF_INTERNACIONAL' },
  { label: 'Criptomoedas', value: 'CRIPTO' },
  { label: 'Renda Fixa', value: 'RENDA_FIXA' },
]

const YEARS = [new Date().getFullYear(), new Date().getFullYear() - 1, new Date().getFullYear() - 2]

export default function ProventosPage() {
  const { data: portfolios } = usePortfolioList()
  const [selectedPortfolio, setSelectedPortfolio] = useState<number | null>(null)
  const portfolioId = selectedPortfolio ?? (portfolios?.[0]?.id ?? 0)

  const [tipoGrafico, setTipoGrafico] = useState<'mensal' | 'anual'>('mensal')
  const [period, setPeriod] = useState('12m')
  const [assetTypeFilter, setAssetTypeFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [yearFilter, setYearFilter] = useState<number | undefined>(undefined)

  const { data: summary } = useProventosSummary(portfolioId)
  const { data: distribution } = useProventosDistribution(portfolioId)
  const { data: evolucao, isLoading: loadingEvolucao } = useProventosEvolucao(portfolioId, tipoGrafico, period)
  const { data: historico, isLoading: loadingHistorico } = useProventosHistoricoMensal(portfolioId, statusFilter, assetTypeFilter)
  const { data: lista, isLoading: loadingLista } = useProventosList(portfolioId, yearFilter, statusFilter || undefined, assetTypeFilter || undefined)

  return (
    <div className="p-4 md:p-6 flex flex-col gap-5 max-w-[1400px] mx-auto">

      {/* Portfolio selector */}
      {(portfolios?.length ?? 0) > 1 && (
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted">Carteira:</span>
          {portfolios!.map(p => (
            <button key={p.id} onClick={() => setSelectedPortfolio(p.id)}
              className={clsx('px-3 py-1 rounded text-xs font-medium transition-colors',
                portfolioId === p.id ? 'bg-brand-primary text-white' : 'btn-secondary'
              )}>{p.name}</button>
          ))}
        </div>
      )}

      {/* Layout principal: painel esquerdo + conteúdo */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-5">

        {/* Painel esquerdo */}
        <div className="flex flex-col gap-4">
          {/* KPIs */}
          <div className="card p-4 flex flex-col gap-3">
            <div>
              <div className="flex items-center justify-between mb-0.5">
                <span className="text-xs text-muted">Média Mensal (últ. 12 meses)</span>
              </div>
              <div className="flex items-end gap-2">
                <span className="text-lg font-bold tabular-nums text-gray-900 dark:text-gray-100">
                  {summary ? formatBRL(summary.media_mensal) : '—'}
                </span>
                {summary && summary.meta_mensal > 0 && (
                  <span className="text-xs text-muted mb-0.5">/ {formatBRL(summary.meta_mensal)}</span>
                )}
              </div>
              {summary && summary.meta_mensal > 0 && (
                <span className="text-xs text-positive font-medium">
                  {summary.meta_percent.toFixed(2)}%
                </span>
              )}
            </div>

            <div className="border-t border-light-border dark:border-dark-border pt-3">
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted">Total de 12 meses</span>
                <ChevronDown size={14} className="text-muted" />
              </div>
              <span className="text-base font-bold tabular-nums text-gray-900 dark:text-gray-100">
                {summary ? formatBRL(summary.total_12m) : '—'}
              </span>
            </div>

            <div className="border-t border-light-border dark:border-dark-border pt-3">
              <span className="text-xs text-muted block mb-0.5">Total da carteira</span>
              <span className="text-base font-bold tabular-nums text-gray-900 dark:text-gray-100">
                {summary ? formatBRL(summary.total_carteira) : '—'}
              </span>
            </div>
          </div>

          {/* Distribuição */}
          <div className="card p-4">
            <span className="text-xs font-medium text-gray-700 dark:text-gray-300 block mb-3">
              Distribuição de proventos em 12 meses
            </span>
            {distribution?.length ? (
              <ProventosDonutChart data={distribution} />
            ) : (
              <div className="h-40 flex items-center justify-center text-xs text-muted">Sem dados</div>
            )}
          </div>
        </div>

        {/* Conteúdo principal */}
        <div className="lg:col-span-3 flex flex-col gap-5">

          {/* Gráfico evolução */}
          <div className="card p-4">
            <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
              <div className="flex items-center gap-2">
                <TrendingUp size={16} className="text-brand-primary" />
                <span className="text-sm font-semibold text-gray-800 dark:text-gray-200">Evolução de Proventos</span>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                {/* Toggle mensal/anual */}
                <div className="flex rounded-lg border border-light-border dark:border-dark-border overflow-hidden">
                  {(['mensal', 'anual'] as const).map(t => (
                    <button key={t} onClick={() => setTipoGrafico(t)}
                      className={clsx('px-3 py-1 text-xs font-medium transition-colors capitalize',
                        tipoGrafico === t
                          ? 'bg-brand-primary/15 text-brand-primary'
                          : 'text-muted hover:text-gray-700 dark:hover:text-gray-300'
                      )}>{t.charAt(0).toUpperCase() + t.slice(1)}</button>
                  ))}
                </div>

                {/* Período */}
                <select
                  value={period}
                  onChange={e => setPeriod(e.target.value)}
                  className="input py-1 text-xs w-auto pr-7"
                >
                  {PERIOD_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>

                {/* Tipo de ativo */}
                <select
                  value={assetTypeFilter}
                  onChange={e => setAssetTypeFilter(e.target.value)}
                  className="input py-1 text-xs w-auto pr-7"
                >
                  {ASSET_TYPE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
              </div>
            </div>

            {loadingEvolucao ? (
              <div className="h-56 animate-pulse bg-light-200 dark:bg-dark-500 rounded" />
            ) : evolucao?.length ? (
              <ProventosBarChart data={evolucao} />
            ) : (
              <div className="h-56 flex items-center justify-center text-xs text-muted">Sem dados</div>
            )}
          </div>

          {/* Histórico mensal */}
          <div className="card">
            <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 border-b border-light-border dark:border-dark-border">
              <div className="flex items-center gap-2">
                <Wallet size={16} className="text-brand-primary" />
                <span className="text-sm font-semibold text-gray-800 dark:text-gray-200">Histórico mensal</span>
                {historico && (
                  <span className="text-xs font-bold text-gray-800 dark:text-gray-200">
                    Total {formatBRL(historico.reduce((a, r) => a + r.total, 0))}
                  </span>
                )}
              </div>
              <div className="flex gap-2">
                <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} className="input py-1 text-xs w-auto pr-7">
                  <option value="">Recebidos + A receber</option>
                  <option value="RECEBIDO">Recebidos</option>
                  <option value="A_RECEBER">A receber</option>
                </select>
                <select value={assetTypeFilter} onChange={e => setAssetTypeFilter(e.target.value)} className="input py-1 text-xs w-auto pr-7">
                  {ASSET_TYPE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
              </div>
            </div>
            {loadingHistorico ? (
              <div className="h-32 animate-pulse m-4 bg-light-200 dark:bg-dark-500 rounded" />
            ) : (
              <ProventosHistoricoTable data={historico ?? []} />
            )}
          </div>

          {/* Meus Proventos */}
          <div className="card">
            <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 border-b border-light-border dark:border-dark-border">
              <div className="flex items-center gap-2">
                <Target size={16} className="text-brand-primary" />
                <span className="text-sm font-semibold text-gray-800 dark:text-gray-200">Meus proventos</span>
                {lista && (
                  <span className="text-xs font-bold text-gray-800 dark:text-gray-200">
                    Total {formatBRL(lista.reduce((a, i) => a + i.total_value, 0))}
                  </span>
                )}
              </div>
              <div className="flex gap-2">
                <select value={yearFilter ?? ''} onChange={e => setYearFilter(e.target.value ? Number(e.target.value) : undefined)} className="input py-1 text-xs w-auto pr-7">
                  <option value="">Todos os anos</option>
                  {YEARS.map(y => <option key={y} value={y}>{y}</option>)}
                </select>
                <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)} className="input py-1 text-xs w-auto pr-7">
                  <option value="">Todos os status</option>
                  <option value="RECEBIDO">Recebido</option>
                  <option value="A_RECEBER">A Receber</option>
                </select>
                <select value={assetTypeFilter} onChange={e => setAssetTypeFilter(e.target.value)} className="input py-1 text-xs w-auto pr-7">
                  {ASSET_TYPE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                </select>
              </div>
            </div>
            {loadingLista ? (
              <div className="h-32 animate-pulse m-4 bg-light-200 dark:bg-dark-500 rounded" />
            ) : lista?.length ? (
              <MeusProventosTable data={lista} />
            ) : (
              <EmptyState icon={DollarSign} title="Nenhum provento encontrado" description="Os proventos são registrados automaticamente via BRAPI." />
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
