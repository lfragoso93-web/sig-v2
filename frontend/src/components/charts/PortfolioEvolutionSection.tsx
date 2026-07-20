import { useEffect, useState } from 'react'
import { BarChart2, TrendingUp } from 'lucide-react'

import {
  useClassDailyEvolution,
  useClassMonthlyEvolution,
  useClassTwrAvailability,
  useDailyEvolution,
  useMonthlyEvolution,
  type PeriodOption,
} from '@/hooks/useEvolution'
import { ASSET_CLASS_ALL, assetTypeLabel } from '@/utils/assetTypes'
import EvolutionBarChart from './EvolutionBarChart'
import EvolutionClassSelect from './EvolutionClassSelect'
import EvolutionLineChart from './EvolutionLineChart'
import EvolutionQueryState from './EvolutionQueryState'

const PERIODS: { label: string; value: PeriodOption }[] = [
  { label: '6m', value: '6m' },
  { label: '12m', value: '12m' },
  { label: '24m', value: '24m' },
  { label: 'Tudo', value: 'all' },
]

type ViewMode = 'diario' | 'mensal'

function ToggleGroup<T extends string>({
  options,
  value,
  onChange,
}: {
  options: { label: string; value: T }[]
  value: T
  onChange: (value: T) => void
}) {
  return (
    <div className="flex" style={{ border: '1px solid var(--color-border)', borderRadius: 'var(--radius-lg)' }}>
      {options.map(option => (
        <button
          key={option.value}
          type="button"
          onClick={() => onChange(option.value)}
          className="px-3 py-1.5 text-xs font-medium transition-colors"
          style={{
            background: value === option.value ? 'var(--color-primary)' : 'transparent',
            color: value === option.value ? '#fff' : 'var(--color-text-muted)',
          }}
        >
          {option.label}
        </button>
      ))}
    </div>
  )
}

export default function PortfolioEvolutionSection({ portfolioId }: { portfolioId: number }) {
  const [period, setPeriod] = useState<PeriodOption>('12m')
  const [view, setView] = useState<ViewMode>('mensal')
  const [assetClass, setAssetClass] = useState(ASSET_CLASS_ALL)
  const classAvailabilityQuery = useClassTwrAvailability(portfolioId)
  const activeAssetType = assetClass === ASSET_CLASS_ALL ? null : assetClass
  const selectedAvailability = activeAssetType
    ? classAvailabilityQuery.data?.find(item => item.asset_type === activeAssetType)
    : null
  const availableClassAssetType = selectedAvailability?.available
    ? activeAssetType
    : null

  useEffect(() => {
    if (
      classAvailabilityQuery.isLoading
      || !classAvailabilityQuery.data
      || assetClass === ASSET_CLASS_ALL
    ) return
    if (!classAvailabilityQuery.data.some(item => item.asset_type === assetClass)) {
      setAssetClass(ASSET_CLASS_ALL)
    }
  }, [assetClass, classAvailabilityQuery.data, classAvailabilityQuery.isLoading])

  const dailyQuery = useDailyEvolution(activeAssetType ? null : portfolioId, period)
  const monthlyQuery = useMonthlyEvolution(activeAssetType ? null : portfolioId, period)
  const classDailyQuery = useClassDailyEvolution(portfolioId, availableClassAssetType, period)
  const classMonthlyQuery = useClassMonthlyEvolution(portfolioId, availableClassAssetType, period)
  const dailyData = activeAssetType ? classDailyQuery.data : dailyQuery.data
  const monthlyData = activeAssetType ? classMonthlyQuery.data : monthlyQuery.data
  const activeQuery = activeAssetType
    ? view === 'mensal' ? classMonthlyQuery : classDailyQuery
    : view === 'mensal' ? monthlyQuery : dailyQuery
  const data = view === 'mensal' ? monthlyData : dailyData
  const waitingForAvailability = Boolean(activeAssetType && classAvailabilityQuery.isLoading)
  const availabilityFailed = Boolean(activeAssetType && classAvailabilityQuery.isError)
  const classHistoryUnavailable = Boolean(
    activeAssetType
    && !classAvailabilityQuery.isLoading
    && !classAvailabilityQuery.isError
    && selectedAvailability?.available !== true,
  )

  return (
    <div className="card">
      <div className="section-card-header" style={{ justifyContent: 'space-between' }}>
        <div className="flex items-center gap-2">
          {view === 'diario'
            ? <TrendingUp size={14} style={{ color: 'var(--color-primary)' }} />
            : <BarChart2 size={14} style={{ color: 'var(--color-primary)' }} />}
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="section-card-title">Evolução do Patrimônio</span>
              {activeAssetType && (
                <span
                  className="text-xs font-semibold px-2 py-0.5 rounded-full"
                  style={{
                    color: 'var(--color-primary)',
                    background: 'oklch(from var(--color-primary) l c h / 0.1)',
                  }}
                >
                  {assetTypeLabel(activeAssetType)}
                </span>
              )}
            </div>
            <p className="text-xs mt-1" style={{ color: 'var(--color-text-faint)' }}>
              {activeAssetType
                ? 'Fechamentos canônicos da classe selecionada.'
                : 'Fechamentos canônicos; não representa o valuation intradiário dos cards.'}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <EvolutionClassSelect
            value={assetClass}
            availability={classAvailabilityQuery.data}
            isLoading={classAvailabilityQuery.isLoading}
            onChange={setAssetClass}
          />
          {classAvailabilityQuery.isError && (
            <button
              type="button"
              className="text-xs font-semibold"
              style={{ color: 'var(--color-error)' }}
              onClick={() => { void classAvailabilityQuery.refetch() }}
            >
              Recarregar classes
            </button>
          )}
          <ToggleGroup<ViewMode>
            options={[{ label: 'Diário', value: 'diario' }, { label: 'Mensal', value: 'mensal' }]}
            value={view}
            onChange={setView}
          />
          <ToggleGroup<PeriodOption> options={PERIODS} value={period} onChange={setPeriod} />
        </div>
      </div>
      <div className="p-4">
        {classHistoryUnavailable ? (
          <div
            className="h-64 flex items-center justify-center text-sm text-center px-6"
            style={{ color: 'var(--color-text-muted)' }}
          >
            {selectedAvailability?.reason
              ?? 'Histórico canônico ainda não disponível para esta classe.'}
          </div>
        ) : (
          <EvolutionQueryState
            isLoading={waitingForAvailability || activeQuery.isLoading}
            isError={availabilityFailed || activeQuery.isError}
            isEmpty={!data?.length}
            onRetry={() => {
              if (availabilityFailed) void classAvailabilityQuery.refetch()
              else void activeQuery.refetch()
            }}
          >
            {view === 'diario' ? (
              <EvolutionLineChart data={dailyData ?? []} />
            ) : (
              <EvolutionBarChart data={monthlyData ?? []} />
            )}
          </EvolutionQueryState>
        )}
      </div>
    </div>
  )
}
