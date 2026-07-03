import api from './api'
import type {
  AuditLogDetail,
  PaginatedAuditLogs,
  AuditStatsResponse,
  UserAuditStatsResponse,
} from '@/types/audit'

interface AuditLogsParams {
  page?: number
  page_size?: number
  user_id?: number | null
  resource_type?: string | null
  action?: string | null
  portfolio_id?: number | null
  status?: string | null
  date_from?: string | null
  date_to?: string | null
  search?: string | null
}

export const auditService = {
  async getAuditLogs(params: AuditLogsParams): Promise<PaginatedAuditLogs> {
    const response = await api.get('/admin/audit-logs', { params })
    return response.data
  },

  async getAuditLogDetail(logId: number): Promise<AuditLogDetail> {
    const response = await api.get(`/admin/audit-logs/${logId}`)
    return response.data
  },

  async getUserAuditLogs(userId: number, params?: Omit<AuditLogsParams, 'user_id'>): Promise<PaginatedAuditLogs> {
    const response = await api.get(`/admin/audit-logs/user/${userId}`, { params })
    return response.data
  },

  async getAuditStats(): Promise<AuditStatsResponse> {
    const response = await api.get('/admin/audit-logs/stats')
    return response.data
  },

  async getUserAuditStats(userId: number): Promise<UserAuditStatsResponse> {
    const response = await api.get(`/admin/audit-logs/user/${userId}/stats`)
    return response.data
  },

  async cleanupAuditLogs(daysToKeep: number = 90, dryRun: boolean = true): Promise<{ deleted_count: number; freed_space_mb: number }> {
    const response = await api.delete('/admin/audit-logs/cleanup', {
      params: { days_to_keep: daysToKeep, dry_run: dryRun },
    })
    return response.data
  },
}
