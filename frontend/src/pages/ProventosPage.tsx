import { useState } from 'react'
import { RefreshCw } from 'lucide-react'
import { usePortfolioList } from '@/hooks/usePortfolio'
import {
  useProventosSummary,
  useProventosDistribuicao,
  useProventosHistoricoMensal,
  useProventosList,
  useSyncProventos,
} from '@/hooks/useProventos'
import { formatBRL } from '@/utils/format'
import ProventosDonutChart from '@/components/charts/ProventosDonutChart'
import ProventosHistoricoTable from '@/components/proventos/ProventosHistoricoTable'
import MeusProventosTable from '@/components/proventos/MeusProventosTable'

const ASSET_TYPE_OPTIONS = [
  { label: 'Todos os tipos',       value: ''                  },
  { label: 'Ações',               value: 'ACAO'               },
  { label: 'FIIs',                 value: 'FII'               },
  { label: 'ETFs Nacionais',       value: 'ETF_NACIONAL'      },
  { label: 'Stocks',               value: 'STOCK'             },
  { label: 'ETFs Internacionais',  value: 'ETF_INTERNACIONAL' },
]

const YEARS = [
  new Date().getFullYear(),
  new Date().getFullYear() - 1,
  new Date().getFullYear() - 2,
]

export default function ProventosPage() {
  const { data: portfolios } = usePortfolioList()
  const [selectedPortfolio, setSelectedPortfolio] = useState<number | null>(null)
  const portfolioId = selectedPortfolio ?? (portfolios?.[0]?.id ?? 0)

  const [assetTypeFilter, setAssetTypeFilter] = useState('')
  const [statusFilter,    setStatusFilter]    = useState('')  // '' | 'RECEBIDO' | 'A_RECEBER'
  const [yearFilter,      setYearFilter]      = useState<number | undefined>(undefined)

  const { data: summary }      = useProventosSummary(portfolioId)
  const { data: distribuicao } = useProventosDistribuicao(portfolioId)
  const { data: historico,  isLoading: loadingHistorico } = useProventosHistoricoMensal(
    portfolioId,
    statusFilter  || undefined,
    assetTypeFilter || undefined,
  )
  const { data: lista, isLoading: loadingLista } = useProventosList(portfolioId, {
    status:     statusFilter    || undefined,
    year:       yearFilter,
    asset_type: assetTypeFilter || undefined,
    page_size:  100,
  })

  const sync = useSyncProventos(portfolioId || null)

  return (
    <div className="p-4 md:p-6 flex flex-col gap-5 max-w-[1400px] mx-auto">

      {/* Cabecalho: titulo + botao sync */}
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <h1 className="text-base font-bold" style={{ color: 'var(--color-text)' }}>Proventos</h1>
        <button
          onClick={() => sync.mutate()}
          disabled={sync.isPending || !portfolioId}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors disabled:opacity-50"
          style={{
            background: 'oklch(from var(--color-primary) l c h / 0.12)',
            color: 'var(--color-primary)',
          }}
        >
          <RefreshCw size={12} className={sync.isPending ? 'animate-spin' : ''} />
          {sync.isPending ? 'Sincronizando…' : 'Sincronizar proventos'}
        </button>
      </div>

      {/* Seletor de carteira */}
      {(portfolios?.length ?? 0) > 1 && (
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>Carteira:</span>
          {portfolios!.map(p => (
            <button
              key={p.id}
              onClick={() => setSelectedPortfolio(p.id)}
              className="px-3 py-1 rounded text-xs font-medium transition-colors"
              style={{
                background: portfolioId === p.id
                  ? 'oklch(from var(--color-primary) l c h / 0.15)'
                  : 'var(--color-surface-offset)',
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

            <div>
              <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>Total recebido</span>
              <div className="text-lg font-bold tabular-nums" style={{ color: 'var(--color-text)' }}>
                {formatBRL(summary?.total_recebido ?? 0)}
              </div>
            </div>

            <div style={{ borderTop: '1px solid var(--color-divider)' }} />

            <div>
              <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>A receber</span>
              <div className="text-base font-bold tabular-nums" style={{ color: 'var(--color-primary)' }}>
                {formatBRL(summary?.total_a_receber ?? 0)}
              </div>
            </div>

            <div style={{ borderTop: '1px solid var(--color-divider)' }} />

            <div>
              <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>Últimos 12 meses</span>
              <div className="text-base font-bold tabular-nums" style={{ color: 'var(--color-text)' }}>
                {formatBRL(summary?.total_12m ?? 0)}
              </div>
            </div>

            <div style={{ borderTop: '1px solid var(--color-divider)' }} />

            <div>
              <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>Média mensal (12m)</span>
              <div className="text-base font-bold tabular-nums" style={{ color: 'var(--color-text)' }}>
                {formatBRL(summary?.media_mensal_12m ?? 0)}
              </div>
            </div>
          </div>

          {/* Donut por ativo */}
          {(distribuicao?.length ?? 0) > 0 && (
            <div className="card p-4">
              <p className="text-xs font-semibold mb-3" style={{ color: 'var(--color-text)' }}>
                Por ativo (12m)
              </p>
              <ProventosDonutChart data={distribuicao!} />
            </div>
          )}
        </div>

        {/* Conteudo principal */}
        <div className="lg:col-span-3 flex flex-col gap-5">

          {/* Filtros globais */}
          <div className="flex flex-wrap items-center gap-2">

            {/* Filtro status: Todos / Recebidos / A Receber */}
            <div
              className="flex items-center gap-1 p-1 rounded-lg"
              style={{ background: 'var(--color-surface-offset)' }}
            >
              {[{ label: 'Todos', value: '' }, { label: 'Recebidos', value: 'RECEBIDO' }, { label: 'A Receber', value: 'A_RECEBER' }].map(o => (
                <button
                  key={o.value}
                  onClick={() => setStatusFilter(o.value)}
                  className="px-3 py-1 rounded text-xs font-medium transition-colors"
                  style={{
                    background: statusFilter === o.value
                      ? 'oklch(from var(--color-primary) l c h / 0.15)'
                      : 'transparent',
                    color: statusFilter === o.value ? 'var(--color-primary)' : 'var(--color-text-muted)',
                  }}
                >
                  {o.label}
                </button>
              ))}
            </div>

            {/* Filtro tipo de ativo */}
            <select
              value={assetTypeFilter}
              onChange={e => setAssetTypeFilter(e.target.value)}
              className="input text-xs"
            >
              {ASSET_TYPE_OPTIONS.map(o => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>

          {/* Historico mensal */}
          <div className="card p-4">
            <p className="text-xs font-semibold mb-3" style={{ color: 'var(--color-text)' }}>Histórico mensal</p>
            {loadingHistorico ? (
              <div className="flex flex-col gap-2">
                {[...Array(4)].map((_, i) => <div key={i} className="h-8 skeleton rounded" />)}
              </div>
            ) : (
              <ProventosHistoricoTable data={historico ?? []} />
            )}
          </div>

          {/* Lista de proventos */}
          <div className="card p-4">
            <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
              <p className="text-xs font-semibold" style={{ color: 'var(--color-text)' }}>Meus proventos</p>

              {/* Filtro por ano */}
              <div className="flex items-center gap-1">
                <button
                  onClick={() => setYearFilter(undefined)}
                  className="px-2 py-0.5 rounded text-xs font-medium transition-colors"
                  style={{
                    background: yearFilter === undefined
                      ? 'oklch(from var(--color-primary) l c h / 0.15)'
                      : 'transparent',
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
                      background: yearFilter === y
                        ? 'oklch(from var(--color-primary) l c h / 0.15)'
                        : 'transparent',
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
                {[...Array(5)].map((_, i) => <div key={i} className="h-10 skeleton rounded" />)}
              </div>
            ) : (
              <MeusProventosTable data={lista?.items ?? []} />
            )}

            {/* Rodape: total de registros */}
            {(lista?.total ?? 0) > 0 && (
              <p className="text-[10px] mt-3 text-right" style={{ color: 'var(--color-text-faint)' }}>
                {lista!.total} provento{lista!.total !== 1 ? 's' : ''}
              </p>
            )}
          </div>

        </div>
      </div>
    </div>
  )
}
