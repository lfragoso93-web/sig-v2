import api from './api'
import type {
  CorporateEventReviewDecision,
  CorporateEventReviewFilters,
  CorporateEventReviewItem,
  CorporateEventReviewPage,
  CorporateEventEvidenceGroup,
  CorporateExchangeProjectionPlan,
} from '@/types/corporateEventReview'

export const corporateEventReviewService = {
  projectionPlan: (eventId: number, sourceQuantity: string, totalCost: string) =>
    api
      .post<CorporateExchangeProjectionPlan>(
        `/admin/corporate-events/${eventId}/projection-plan`,
        { source_quantity: sourceQuantity, total_cost: totalCost },
      )
      .then(response => response.data),

  evidence: (eventId: number) =>
    api
      .get<CorporateEventEvidenceGroup>(`/admin/corporate-events/${eventId}/evidence`)
      .then(response => response.data),

  list: (filters: CorporateEventReviewFilters) =>
    api
      .get<CorporateEventReviewPage>('/admin/corporate-events/review', {
        params: filters,
      })
      .then(response => response.data),

  review: (
    eventId: number,
    decision: CorporateEventReviewDecision,
    note: string,
  ) =>
    api
      .post<CorporateEventReviewItem>(
        `/admin/corporate-events/${eventId}/review`,
        { decision, note },
      )
      .then(response => response.data),
}
