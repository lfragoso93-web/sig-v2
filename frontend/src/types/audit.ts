export interface AuditLogResponse {
  id: number
  user_id: number
  action: string
  resource_type: string
  resource_id: number | null
  portfolio_id: number | null
  ip_address: string | null
  user_agent: string | null
  status: string
  error_message: string | null
  created_at: string
}

export interface AuditLogDetail extends AuditLogResponse {
  old_values: Record<string, any> | null
  new_values: Record<string, any> | null
  changes: Record<string, any> | null
}

export interface PaginatedAuditLogs {
  items: AuditLogResponse[]
  total: number
  page: number
  page_size: number
  pages: number
}

export interface AuditStatsResponse {
  total_logs: number
  logs_today: number
  logs_this_week: number
  actions_breakdown: Record<string, number>
  resource_types_breakdown: Record<string, number>
  failed_operations: number
}

export interface UserAuditStatsResponse {
  user_id: number
  total_actions: number
  actions_breakdown: Record<string, number>
  last_action: string | null
  failed_actions: number
}
