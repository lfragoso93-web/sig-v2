import { useState } from 'react'
import { Search, RefreshCw } from 'lucide-react'
import { useAssets } from '@/hooks/useAssets'
import { useQueryClient } from '@tanstack/react-query'
import { formatBRL } from '@/utils/format'

const ASSET_TYPE_OPTIONS = [
  { label: 'Todos os tipos',       value: ''                  },
  { label: 'Ações',               value: 'ACAO'               },
  { label: 'FIIs',                 value: 'FII'               },
  { label: 'ETFs Nacionais',       value: 'ETF_NACIONAL'      },
  { label: 'BDRs',                 value: 'BDR'               },
  { label: 'Stocks',               value: 'STOCK'             },
  { label: 'ETFs Internacionais',  value: 'ETF_INTERNACIONAL' },
  { label: 'Criptos',              value: 'CRIPTO'            },
  { label: 'Tesouro Direto',       value: 'TESOURO_DIRETO'    },
  { label: 'Renda Fixa',           value: 'RENDA_FIXA'        },
]

const PAGE_SIZE = 50

export default function AssetsPage() {
  const qc = useQueryClient()
  const [q, setQ]             = useState('')
  const [assetType, setType]  = useState('')
  const [page, setPage]       = useState(1)

  // Reset página ao mudar filtro
  function handleTypeChange(v: string) { setType(v); setPage(1) }
  function handleSearch(v: string)     { setQ(v);    setPage(1) }

  const { data, isFetching, isLoading } = useAssets({
    page,
    page_size: PAGE_SIZE,
    asset_type: assetType || undefined,
    q: q || undefined,
  })

  const items  = data?.items  ?? []
  const total  = data?.total  ?? 0
  const pages  = data?.pages  ?? 1

  return (
    <div className="page-container">

      {/* Cabeçalho */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Ativos</h1>
          <p className="page-subtitle">Todos os ativos cadastrados no sistema</p>
        </div>
        <button
          onClick={() => qc.invalidateQueries({ queryKey: ['assets'] })}
          disabled={isFetching}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors disabled:opacity-50"
          style={{ background: 'oklch(from var(--color-primary) l c h / 0.12)', color: 'var(--color-primary)' }}
          aria-label="Atualizar lista de ativos"
        >
          <RefreshCw size={12} className={isFetching ? 'animate-spin' : ''} aria-hidden="true" />
          Atualizar
        </button>
      </div>

      {/* Filtros */}
      <div className="flex flex-wrap items-center gap-2">

        {/* Busca por ticker/nome */}
        <div className="relative flex-1 min-w-[180px] max-w-xs">
          <Search
            size={14}
            className="absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none"
            style={{ color: 'var(--color-text-muted)' }}
            aria-hidden="true"
          />
          <input
            type="text"
            value={q}
            onChange={e => handleSearch(e.target.value)}
            placeholder="Buscar ticker ou nome…"
            className="input pl-8 text-xs w-full"
            aria-label="Buscar ativo"
          />
        </div>

        {/* Filtro por tipo */}
        <select
          value={assetType}
          onChange={e => handleTypeChange(e.target.value)}
          className="input text-xs"
          aria-label="Filtrar por tipo de ativo"
        >
          {ASSET_TYPE_OPTIONS.map(o => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>

        {/* Contador */}
        <span className="text-xs ml-auto" style={{ color: 'var(--color-text-muted)' }}>
          {isLoading ? '—' : `${total.toLocaleString('pt-BR')} ativo${total !== 1 ? 's' : ''}`}
        </span>
      </div>

      {/* Tabela */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[600px] text-xs" style={{ borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--color-divider)' }}>
                <th className="px-4 py-3 text-left font-semibold w-28" style={{ color: 'var(--color-text-muted)' }}>Ticker</th>
                <th className="px-4 py-3 text-left font-semibold"       style={{ color: 'var(--color-text-muted)' }}>Nome</th>
                <th className="px-4 py-3 text-left font-semibold w-36"  style={{ color: 'var(--color-text-muted)' }}>Tipo</th>
                <th className="px-4 py-3 text-right font-semibold w-32" style={{ color: 'var(--color-text-muted)' }}>Último preço</th>
                <th className="px-4 py-3 text-right font-semibold w-36" style={{ color: 'var(--color-text-muted)' }}>Atualizado em</th>
              </tr>
            </thead>
            <tbody>
              {isLoading && (
                [...Array(10)].map((_, i) => (
                  <tr key={i}>
                    {[...Array(5)].map((__, j) => (
                      <td key={j} className="px-4 py-3">
                        <div className="h-4 skeleton rounded" />
                      </td>
                    ))}
                  </tr>
                ))
              )}

              {!isLoading && items.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-10 text-center" style={{ color: 'var(--color-text-muted)' }}>
                    {q || assetType ? 'Nenhum ativo encontrado com os filtros aplicados.' : 'Nenhum ativo cadastrado.'}
                  </td>
                </tr>
              )}

              {!isLoading && items.map((asset, idx) => (
                <tr
                  key={asset.id}
                  style={{
                    borderBottom: '1px solid oklch(from var(--color-text) l c h / 0.05)',
                    background: idx % 2 !== 0 ? 'var(--color-surface-offset)' : 'transparent',
                  }}
                  onMouseEnter={e => (e.currentTarget.style.background = 'oklch(from var(--color-primary) l c h / 0.04)')}
                  onMouseLeave={e => (e.currentTarget.style.background = idx % 2 !== 0 ? 'var(--color-surface-offset)' : 'transparent')}
                >
                  <td className="px-4 py-2.5 font-mono font-semibold" style={{ color: 'var(--color-primary)' }}>
                    {asset.ticker}
                  </td>
                  <td className="px-4 py-2.5" style={{ color: 'var(--color-text)' }}>
                    {asset.name ?? <span style={{ color: 'var(--color-text-faint)' }}>—</span>}
                  </td>
                  <td className="px-4 py-2.5">
                    <span
                      className="badge"
                      style={{
                        background: 'oklch(from var(--color-primary) l c h / 0.10)',
                        color: 'var(--color-primary)',
                        fontSize: '10px',
                      }}
                    >
                      {asset.asset_type}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-right tabular-nums" style={{ color: asset.last_price ? 'var(--color-text)' : 'var(--color-text-faint)' }}>
                    {asset.last_price != null ? formatBRL(asset.last_price) : '—'}
                  </td>
                  <td className="px-4 py-2.5 text-right" style={{ color: 'var(--color-text-muted)' }}>
                    {asset.last_price_updated_at
                      ? new Date(asset.last_price_updated_at).toLocaleDateString('pt-BR')
                      : <span style={{ color: 'var(--color-text-faint)' }}>—</span>
                    }
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Paginação */}
      {pages > 1 && (
        <div className="flex items-center justify-between">
          <span className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
            Página {page} de {pages}
          </span>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-3 py-1.5 rounded text-xs font-medium disabled:opacity-40 transition-colors"
              style={{
                background: page === 1 ? 'var(--color-surface-offset)' : 'oklch(from var(--color-primary) l c h / 0.12)',
                color: page === 1 ? 'var(--color-text-muted)' : 'var(--color-primary)',
              }}
              aria-label="Página anterior"
            >
              ← Anterior
            </button>

            {/* Janela de páginas: mostra até 5 botões ao redor da atual */}
            {Array.from({ length: Math.min(5, pages) }, (_, i) => {
              const start = Math.max(1, Math.min(page - 2, pages - 4))
              const n = start + i
              return n <= pages ? (
                <button
                  key={n}
                  onClick={() => setPage(n)}
                  className="px-2.5 py-1.5 rounded text-xs font-medium transition-colors"
                  style={{
                    background: n === page ? 'var(--color-primary)' : 'transparent',
                    color: n === page ? 'var(--color-text-inverse)' : 'var(--color-text-muted)',
                    fontWeight: n === page ? 600 : 400,
                  }}
                  aria-label={`Página ${n}`}
                  aria-current={n === page ? 'page' : undefined}
                >
                  {n}
                </button>
              ) : null
            })}

            <button
              onClick={() => setPage(p => Math.min(pages, p + 1))}
              disabled={page === pages}
              className="px-3 py-1.5 rounded text-xs font-medium disabled:opacity-40 transition-colors"
              style={{
                background: page === pages ? 'var(--color-surface-offset)' : 'oklch(from var(--color-primary) l c h / 0.12)',
                color: page === pages ? 'var(--color-text-muted)' : 'var(--color-primary)',
              }}
              aria-label="Próxima página"
            >
              Próxima →
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
