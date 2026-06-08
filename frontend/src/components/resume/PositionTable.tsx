import { useState } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'
import clsx from 'clsx'
import { PositionGroup, PositionItem } from '@/services/portfolioService'
import { formatBRL, formatPercent, formatQuantity, signClass } from '@/utils/format'

const ASSET_TYPE_LABELS: Record<string, string> = {
  ACAO_NACIONAL:     'Ações',
  FII:               'FIIs',
  ETF_NACIONAL:      'ETFs Nacionais',
  TESOURO_DIRETO:    'Tesouro Direto',
  STOCK:             'Stocks',
  ETF_INTERNACIONAL: 'ETFs Internacionais',
  CRIPTO:            'Criptomoedas',
  RENDA_FIXA:        'Renda Fixa',
}

function AssetRow({ position }: { position: PositionItem }) {
  return (
    <tr className="group">
      <td className="px-3 py-2 border-b border-light-border/30 dark:border-dark-border/30">
        <div className="flex items-center gap-2">
          {position.logo_url ? (
            <img src={position.logo_url} alt={position.ticker} width={24} height={24} loading="lazy"
              className="rounded-full w-6 h-6 object-contain bg-light-200 dark:bg-dark-500" />
          ) : (
            <div className="w-6 h-6 rounded-full bg-brand-primary/20 flex items-center justify-center">
              <span className="text-xs font-bold text-brand-primary">{position.ticker[0]}</span>
            </div>
          )}
          <div>
            <div className="text-xs font-semibold text-gray-800 dark:text-gray-200">{position.ticker}</div>
            <div className="text-xs text-muted truncate max-w-32">{position.name}</div>
          </div>
        </div>
      </td>
      <td className="px-3 py-2 border-b border-light-border/30 dark:border-dark-border/30 text-xs tabular-nums text-right">
        {formatQuantity(position.quantity)}
      </td>
      <td className="px-3 py-2 border-b border-light-border/30 dark:border-dark-border/30 text-xs tabular-nums text-right">
        {formatBRL(position.average_price)}
      </td>
      <td className="px-3 py-2 border-b border-light-border/30 dark:border-dark-border/30 text-xs tabular-nums text-right">
        {formatBRL(position.current_price)}
      </td>
      <td className={clsx('px-3 py-2 border-b border-light-border/30 dark:border-dark-border/30 text-xs tabular-nums text-right font-medium', signClass(position.variation_percent))}>
        {formatPercent(position.variation_percent)}
      </td>
      <td className={clsx('px-3 py-2 border-b border-light-border/30 dark:border-dark-border/30 text-xs tabular-nums text-right font-medium', signClass(position.rentability_percent))}>
        {formatPercent(position.rentability_percent)}
      </td>
      <td className="px-3 py-2 border-b border-light-border/30 dark:border-dark-border/30 text-xs tabular-nums text-right font-medium text-gray-800 dark:text-gray-200">
        {formatBRL(position.current_value)}
      </td>
      <td className="px-3 py-2 border-b border-light-border/30 dark:border-dark-border/30 text-center">
        {position.score !== undefined ? (
          <span className="badge-gray">{position.score}</span>
        ) : <span className="text-muted">—</span>}
      </td>
      <td className="px-3 py-2 border-b border-light-border/30 dark:border-dark-border/30 text-xs tabular-nums text-right">
        {position.portfolio_percent.toFixed(2)}%
      </td>
      <td className="px-3 py-2 border-b border-light-border/30 dark:border-dark-border/30 text-xs tabular-nums text-right">
        {position.ideal_percent !== undefined ? `${position.ideal_percent.toFixed(2)}%` : '—'}
      </td>
      <td className="px-3 py-2 border-b border-light-border/30 dark:border-dark-border/30 text-center">
        {position.should_buy === true && <span className="badge-green">Sim</span>}
        {position.should_buy === false && <span className="badge-gray">Não</span>}
        {position.should_buy === undefined && <span className="text-muted">—</span>}
      </td>
      <td className="px-3 py-2 border-b border-light-border/30 dark:border-dark-border/30 text-center">
        <button className="btn-ghost p-1 opacity-0 group-hover:opacity-100 transition-opacity" aria-label="Opções">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
            <circle cx="12" cy="5" r="1.5" /><circle cx="12" cy="12" r="1.5" /><circle cx="12" cy="19" r="1.5" />
          </svg>
        </button>
      </td>
    </tr>
  )
}

function GroupRow({ group }: { group: PositionGroup }) {
  const [open, setOpen] = useState(true)

  return (
    <>
      {/* Header do grupo */}
      <tr
        className="bg-light-100 dark:bg-dark-700 cursor-pointer hover:bg-light-200 dark:hover:bg-dark-600 transition-colors"
        onClick={() => setOpen(o => !o)}
      >
        <td className="px-3 py-2.5" colSpan={3}>
          <div className="flex items-center gap-2">
            {open ? <ChevronDown size={14} className="text-muted" /> : <ChevronRight size={14} className="text-muted" />}
            <span className="text-xs font-semibold text-gray-700 dark:text-gray-300">
              {ASSET_TYPE_LABELS[group.asset_type] ?? group.asset_type}
            </span>
            <span className="badge-gray">{group.count}</span>
          </div>
        </td>
        <td className="px-3 py-2.5 text-right">
          <span className="text-xs font-semibold text-gray-700 dark:text-gray-300">
            {formatBRL(group.total_value)}
          </span>
        </td>
        <td className={clsx('px-3 py-2.5 text-right text-xs font-semibold', signClass(group.variation_percent))}>
          {formatPercent(group.variation_percent)}
        </td>
        <td className={clsx('px-3 py-2.5 text-right text-xs font-semibold', signClass(group.rentability_percent))}>
          {formatPercent(group.rentability_percent)}
        </td>
        <td className="px-3 py-2.5" />
        <td className="px-3 py-2.5" />
        <td className="px-3 py-2.5 text-right text-xs text-muted">{group.portfolio_percent.toFixed(2)}%</td>
        <td className="px-3 py-2.5 text-right text-xs text-muted">
          {group.ideal_percent !== undefined ? `${group.ideal_percent.toFixed(2)}%` : '—'}
        </td>
        <td className="px-3 py-2.5" />
        <td className="px-3 py-2.5" />
      </tr>

      {/* Linhas de posições */}
      {open && group.positions.map(pos => (
        <AssetRow key={pos.id} position={pos} />
      ))}
    </>
  )
}

export default function PositionTable({ groups }: { groups: PositionGroup[] }) {
  if (!groups.length) return null

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[900px]">
        <thead>
          <tr className="border-b border-light-border dark:border-dark-border">
            {['Ativo', 'Quant.', 'Preço Médio', 'Preço Atual', 'Variação', 'Rentabilidade', 'Saldo', 'Nota', '% Carteira', '% Ideal', 'Comprar?', ''].map(h => (
              <th key={h} className="px-3 py-2 text-xs font-medium text-muted text-right first:text-left last:w-8">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {groups.map(group => (
            <GroupRow key={group.asset_type} group={group} />
          ))}
        </tbody>
      </table>
    </div>
  )
}
