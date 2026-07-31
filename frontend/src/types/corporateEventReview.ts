export type CorporateEventReviewDecision = 'APPROVE' | 'REJECT'

export interface CorporateEventReviewItem {
  id: number
  asset_id: number
  ticker: string
  event_type: string
  effective_date: string
  quantity_factor: string
  source_provider: string
  source_event_id: string | null
  reconciliation_status: string
  status: string
  is_canonical: boolean
  requires_review: boolean
  review_reason: string | null
  reviewed_at: string | null
  reviewed_by_user_id: number | null
  review_note: string | null
}

export interface CorporateEventReviewPage {
  items: CorporateEventReviewItem[]
  total: number
  page: number
  page_size: number
}

export interface CorporateEventReviewFilters {
  page: number
  page_size: number
  ticker?: string
  reconciliation_status?: string
}

export interface CorporateEventEvidence {
  id: number
  source_provider: string
  source_event_id: string | null
  event_type: string
  effective_date: string
  record_date: string | null
  ex_date: string | null
  payment_date: string | null
  quantity_factor: string
  cash_component: string | null
  subscription_price: string | null
  destination_cost_allocation: string | null
  quantity_step: string | null
  fractional_settlement_price: string | null
  cash_treatment: string | null
  currency: string
  isin_code: string | null
  destination_isin_code: string | null
  reconciliation_status: string
  status: string
  is_canonical: boolean
  raw_metadata: Record<string, unknown> | null
}

export interface CorporateEventEvidenceComparison {
  field: string
  values: Record<string, string | null>
  divergent: boolean
}

export interface CorporateEventEvidenceGroup {
  selected_event_id: number
  reconciliation_group_hash: string | null
  evidences: CorporateEventEvidence[]
  comparisons: CorporateEventEvidenceComparison[]
  economic_effect: string
  terms_complete: boolean
  automatic_application_supported: boolean
  missing_terms: string[]
  destination_resolution_status: string | null
  destination_asset_id: number | null
  destination_ticker: string | null
  destination_candidate_ids: number[]
}

export interface CorporateExchangeProjectionPlan {
  event_id: number
  source_asset_id: number
  destination_asset_id: number
  source_quantity_before: string
  source_quantity_after: string
  destination_quantity_delta: string
  destination_fractional_quantity: string
  total_cost_before: string
  allocated_source_cost: string | null
  allocated_destination_cost: string | null
  cash_component_total: string
  cash_treatment: string | null
  executable: boolean
  blocking_reasons: string[]
}
