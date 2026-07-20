import type { ClassTwrAvailability } from '@/hooks/useEvolution'
import { ASSET_CLASS_ALL, buildAssetClassOptions } from '@/utils/assetTypes'

interface EvolutionClassSelectProps {
  value: string
  availability: ClassTwrAvailability[] | undefined
  isLoading: boolean
  onChange: (value: string) => void
}

export default function EvolutionClassSelect({
  value,
  availability,
  isLoading,
  onChange,
}: EvolutionClassSelectProps) {
  const options = buildAssetClassOptions(availability?.map(item => item.asset_type) ?? [])
  const resolvedValue = options.some(option => option.value === value)
    ? value
    : ASSET_CLASS_ALL

  return (
    <select
      aria-label="Classe do histórico"
      value={resolvedValue}
      disabled={isLoading}
      onChange={event => onChange(event.target.value)}
      style={{
        padding: '4px 28px 4px 10px',
        height: 30,
        borderRadius: 'var(--radius-md)',
        border: '1px solid var(--color-border)',
        background: 'var(--color-surface-2)',
        color: 'var(--color-text)',
        fontSize: 'var(--text-xs)',
        fontWeight: 500,
        cursor: isLoading ? 'wait' : 'pointer',
      }}
    >
      {options.map(option => (
        <option key={option.value} value={option.value}>{option.label}</option>
      ))}
    </select>
  )
}
