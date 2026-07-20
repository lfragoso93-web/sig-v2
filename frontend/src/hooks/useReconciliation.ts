import { useQuery } from '@tanstack/react-query'

import api from '@/services/api'

export interface ReconciliationCheck {
  field: string
  expected: number
  observed: number
  difference: number
  tolerance: number
  is_reconciled: boolean
}

export type ClassReconciliationStatus =
  | 'evaluated'
  | 'not_comparable_unsupported_classes'
  | 'missing_portfolio_snapshot'
  | 'missing_class_snapshots'

export interface ClassReconciliation {
  is_reconciled: boolean | null
  is_comparable: boolean
  status: ClassReconciliationStatus
  unsupported_asset_types: string[]
  snapshot_date: string | null
  checks: ReconciliationCheck[]
}

export interface IntradayReconciliation {
  portfolio_id: number
  valuation_mode: 'intraday'
  valuation_updated_at: string | null
  snapshot_evaluated: false
  money_tolerance: number
  is_reconciled: boolean
  failed_fields: string[]
  checks: ReconciliationCheck[]
  source_contracts: string[]
  positions_groups_count: number
  distribution_classes_count: number
}

function contractError(contract: string, field: string): never {
  throw new Error(`Contrato ${contract} inválido: ${field}`)
}

function record(value: unknown, contract: string): Record<string, unknown> {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) {
    return contractError(contract, 'payload')
  }
  return value as Record<string, unknown>
}

function exactKeys(
  value: Record<string, unknown>,
  keys: readonly string[],
  contract: string,
): void {
  const allowed = new Set(keys)
  const unexpected = Object.keys(value).find(key => !allowed.has(key))
  if (unexpected) contractError(contract, unexpected)
  const missing = keys.find(key => !(key in value))
  if (missing) contractError(contract, missing)
}

function finiteNumber(value: unknown, contract: string, field: string): number {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    return contractError(contract, field)
  }
  return value
}

function stringArray(value: unknown, contract: string, field: string): string[] {
  if (!Array.isArray(value) || value.some(item => typeof item !== 'string')) {
    return contractError(contract, field)
  }
  return value
}

function parseCheck(value: unknown, contract: string, index: number): ReconciliationCheck {
  const check = record(value, contract)
  const prefix = `checks[${index}]`
  exactKeys(check, [
    'field',
    'expected',
    'observed',
    'difference',
    'tolerance',
    'is_reconciled',
  ], contract)
  if (typeof check.field !== 'string') contractError(contract, `${prefix}.field`)
  if (typeof check.is_reconciled !== 'boolean') {
    contractError(contract, `${prefix}.is_reconciled`)
  }

  return {
    field: check.field,
    expected: finiteNumber(check.expected, contract, `${prefix}.expected`),
    observed: finiteNumber(check.observed, contract, `${prefix}.observed`),
    difference: finiteNumber(check.difference, contract, `${prefix}.difference`),
    tolerance: finiteNumber(check.tolerance, contract, `${prefix}.tolerance`),
    is_reconciled: check.is_reconciled,
  }
}

function checks(value: unknown, contract: string): ReconciliationCheck[] {
  if (!Array.isArray(value)) contractError(contract, 'checks')
  return value.map((item, index) => parseCheck(item, contract, index))
}

const CLASS_STATUSES = new Set<ClassReconciliationStatus>([
  'evaluated',
  'not_comparable_unsupported_classes',
  'missing_portfolio_snapshot',
  'missing_class_snapshots',
])

export function parseClassReconciliation(payload: unknown): ClassReconciliation {
  const contract = 'class-reconciliation.v1'
  const value = record(payload, contract)
  exactKeys(value, [
    'is_reconciled',
    'is_comparable',
    'status',
    'unsupported_asset_types',
    'snapshot_date',
    'checks',
  ], contract)

  if (value.is_reconciled !== null && typeof value.is_reconciled !== 'boolean') {
    contractError(contract, 'is_reconciled')
  }
  if (typeof value.is_comparable !== 'boolean') contractError(contract, 'is_comparable')
  if (typeof value.status !== 'string'
    || !CLASS_STATUSES.has(value.status as ClassReconciliationStatus)) {
    contractError(contract, 'status')
  }
  if (value.snapshot_date !== null && typeof value.snapshot_date !== 'string') {
    contractError(contract, 'snapshot_date')
  }

  return {
    is_reconciled: value.is_reconciled,
    is_comparable: value.is_comparable,
    status: value.status as ClassReconciliationStatus,
    unsupported_asset_types: stringArray(
      value.unsupported_asset_types,
      contract,
      'unsupported_asset_types',
    ),
    snapshot_date: value.snapshot_date,
    checks: checks(value.checks, contract),
  }
}

export function parseIntradayReconciliation(payload: unknown): IntradayReconciliation {
  const contract = 'intraday-reconciliation.v1'
  const value = record(payload, contract)
  exactKeys(value, [
    'portfolio_id',
    'valuation_mode',
    'valuation_updated_at',
    'snapshot_evaluated',
    'money_tolerance',
    'is_reconciled',
    'failed_fields',
    'checks',
    'source_contracts',
    'positions_groups_count',
    'distribution_classes_count',
  ], contract)

  const portfolioId = finiteNumber(value.portfolio_id, contract, 'portfolio_id')
  const groupsCount = finiteNumber(
    value.positions_groups_count,
    contract,
    'positions_groups_count',
  )
  const classesCount = finiteNumber(
    value.distribution_classes_count,
    contract,
    'distribution_classes_count',
  )
  if (!Number.isInteger(portfolioId)) contractError(contract, 'portfolio_id')
  if (!Number.isInteger(groupsCount) || groupsCount < 0) {
    contractError(contract, 'positions_groups_count')
  }
  if (!Number.isInteger(classesCount) || classesCount < 0) {
    contractError(contract, 'distribution_classes_count')
  }
  if (value.valuation_mode !== 'intraday') contractError(contract, 'valuation_mode')
  if (value.snapshot_evaluated !== false) contractError(contract, 'snapshot_evaluated')
  if (value.valuation_updated_at !== null
    && typeof value.valuation_updated_at !== 'string') {
    contractError(contract, 'valuation_updated_at')
  }
  if (typeof value.is_reconciled !== 'boolean') contractError(contract, 'is_reconciled')

  return {
    portfolio_id: portfolioId,
    valuation_mode: 'intraday',
    valuation_updated_at: value.valuation_updated_at as string | null,
    snapshot_evaluated: false,
    money_tolerance: finiteNumber(value.money_tolerance, contract, 'money_tolerance'),
    is_reconciled: value.is_reconciled,
    failed_fields: stringArray(value.failed_fields, contract, 'failed_fields'),
    checks: checks(value.checks, contract),
    source_contracts: stringArray(value.source_contracts, contract, 'source_contracts'),
    positions_groups_count: groupsCount,
    distribution_classes_count: classesCount,
  }
}

export function useClassReconciliation(portfolioId: number | null) {
  return useQuery<ClassReconciliation>({
    queryKey: ['class-snapshot-reconciliation', portfolioId],
    queryFn: () => api
      .get(`/performance/${portfolioId}/classes/reconciliation/latest`)
      .then(response => parseClassReconciliation(response.data)),
    enabled: !!portfolioId,
    staleTime: 5 * 60 * 1000,
  })
}

export function useIntradayReconciliation(portfolioId: number | null) {
  return useQuery<IntradayReconciliation>({
    queryKey: ['intraday-reconciliation', portfolioId],
    queryFn: () => api
      .get(`/portfolios/${portfolioId}/reconciliation/intraday`)
      .then(response => parseIntradayReconciliation(response.data)),
    enabled: !!portfolioId,
    staleTime: 2 * 60 * 1000,
  })
}
