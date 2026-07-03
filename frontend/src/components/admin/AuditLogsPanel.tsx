import { useState, useCallback } from 'react'
import {
  BookOpen,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  Filter,
  X,
} from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { auditService } from '@/services/auditService'
import type { AuditLogResponse } from '@/types/audit'
import clsx from 'clsx'

const ACTIONS_COLORS: Record<string, string> = {
  CREATE: '#10b981',
  READ: '#3b82f6',
  UPDATE: '#f59e0b',
  DELETE: '#ef4444',
  EXPORT: '#8b5cf6',
  IMPORT: '#ec4899',
  LOGIN: '#06b6d4',
  LOGOUT: '#6b7280',
  BACKUP: '#14b8a6',
  RESTORE: '#f97316',
}

const STATUS_COLORS: Record<string, string> = {
  SUCCESS: '#10b981',
  FAILED: '#ef4444',
  PARTIAL: '#f59e0b',
}

function ActionBadge({ action }: { action: string }) {
  const color = ACTIONS_COLORS[action] || '#6b7280'
  return (
    <span
      className="px-2.5 py-1 rounded-full text-xs font-semibold"
      style={{ background: `${color}15`, color }}
    >
      {action}
    </span>
  )
}

function StatusBadge({ status }: { status: string }) {
  const color = STATUS_COLORS[status] || '#6b7280'
  const icon = status === 'SUCCESS' ? '✓' : status === 'FAILED' ? '✗' : '–'
  return (
    <span
      className="px-2 py-0.5 rounded text-xs font-medium flex items-center gap-1"
      style={{ background: `${color}20`, color }}
    >
      {icon} {status}
    </span>
  )
}

function AuditLogRow({ log, onExpand, isExpanded }: { log: AuditLogResponse; onExpand: () => void; isExpanded: boolean }) {
  const { data: details } = useQuery({
    queryKey: ['auditLogDetail', log.id],
    queryFn: () => auditService.getAuditLogDetail(log.id),
    enabled: isExpanded,
  })

  return (
    <>
      <tr
        className="border-b transition-colors cursor-pointer hover:bg-[var(--color-surface-offset)]"
        style={{ borderColor: 'var(--color-divider)' }}
        onClick={onExpand}
      >
        <td className="px-4 py-3 text-sm">
          {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </td>
        <td className="px-4 py-3 text-xs tabular-nums" style={{ color: 'var(--color-text-muted)' }}>
          {log.id}
        </td>
        <td className="px-4 py-3 text-sm" style={{ color: 'var(--color-text-muted)' }}>
          {new Date(log.created_at).toLocaleString('pt-BR')}
        </td>
        <td className="px-4 py-3 text-sm font-medium">{log.user_id}</td>
        <td className="px-4 py-3">
          <ActionBadge action={log.action} />
        </td>
        <td className="px-4 py-3 text-sm" style={{ color: 'var(--color-text-muted)' }}>
          {log.resource_type}
        </td>
        <td className="px-4 py-3 text-sm tabular-nums">{log.resource_id || '—'}</td>
        <td className="px-4 py-3">
          <StatusBadge status={log.status} />
        </td>
      </tr>
      {isExpanded && details && (
        <tr style={{ borderColor: 'var(--color-divider)', background: 'var(--color-surface-offset)' }}>
          <td colSpan={8} className="px-4 py-4">
            <div className="space-y-4">
              {details.ip_address && (
                <div>
                  <p className="text-xs font-semibold" style={{ color: 'var(--color-text-muted)' }}>
                    IP Address
                  </p>
                  <p className="text-sm font-mono">{details.ip_address}</p>
                </div>
              )}
              {details.error_message && (
                <div className="rounded-lg p-3" style={{ background: '#ef444420' }}>
                  <p className="text-xs font-semibold text-red-600">Error</p>
                  <p className="text-sm mt-1 font-mono">{details.error_message}</p>
                </div>
              )}
              {details.changes && Object.keys(details.changes).length > 0 && (
                <div>
                  <p className="text-xs font-semibold mb-2" style={{ color: 'var(--color-text-muted)' }}>
                    Changes
                  </p>
                  <div className="space-y-2">
                    {Object.entries(details.changes).map(([key, value]: [string, any]) => (
                      <div key={key} className="rounded p-2" style={{ background: 'var(--color-surface-dynamic)' }}>
                        <p className="text-xs font-semibold text-amber-600 mb-1">{key}</p>
                        <div className="grid grid-cols-2 gap-2 text-xs">
                          <div>
                            <span style={{ color: 'var(--color-text-muted)' }}>Old: </span>
                            <span className="font-mono">{JSON.stringify(value.old)}</span>
                          </div>
                          <div>
                            <span style={{ color: 'var(--color-text-muted)' }}>New: </span>
                            <span className="font-mono">{JSON.stringify(value.new)}</span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </td>
        </tr>
      )}
    </>
  )
}

export default function AuditLogsPanel() {
  const [page, setPage] = useState(1)
  const [pageSize] = useState(50)
  const [showFilters, setShowFilters] = useState(false)
  const [expandedId, setExpandedId] = useState<number | null>(null)

  const [filters, setFilters] = useState({
    user_id: null as number | null,
    resource_type: null as string | null,
    action: null as string | null,
    status: null as string | null,
    date_from: null as string | null,
    date_to: null as string | null,
    search: null as string | null,
  })

  const { data: logs, isLoading: logsLoading, refetch } = useQuery({
    queryKey: ['auditLogs', page, pageSize, filters],
    queryFn: () =>
      auditService.getAuditLogs({
        page,
        page_size: pageSize,
        ...filters,
      }),
  })

  const { data: stats } = useQuery({
    queryKey: ['auditStats'],
    queryFn: () => auditService.getAuditStats(),
  })

  const handleFilterChange = useCallback((key: string, value: any) => {
    setFilters(prev => ({ ...prev, [key]: value || null }))
    setPage(1)
  }, [])

  const handleClearFilters = useCallback(() => {
    setFilters({
      user_id: null,
      resource_type: null,
      action: null,
      status: null,
      date_from: null,
      date_to: null,
      search: null,
    })
    setPage(1)
  }, [])

  const hasActiveFilters = Object.values(filters).some(v => v !== null)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
           <h2 className="text-xl font-bold flex items-center gap-2" style={{ color: 'var(--color-text)' }}>
             <BookOpen size={24} />
             Audit Logs
           </h2>
          <p className="text-sm mt-1" style={{ color: 'var(--color-text-muted)' }}>
            Rastreamento de operações de usuários no sistema
          </p>
        </div>
        <button
          type="button"
          onClick={() => refetch()}
          className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors"
          style={{
            background: 'var(--color-surface-offset)',
            border: '1px solid var(--color-border)',
            color: 'var(--color-text)',
          }}
        >
          <RefreshCw size={14} />
          Atualizar
        </button>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
          <div className="rounded-lg p-4" style={{ background: 'var(--color-surface-offset)' }}>
            <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
              Total
            </p>
            <p className="text-2xl font-bold mt-1" style={{ color: 'var(--color-primary)' }}>
              {stats.total_logs.toLocaleString('pt-BR')}
            </p>
          </div>
          <div className="rounded-lg p-4" style={{ background: 'var(--color-surface-offset)' }}>
            <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
              Hoje
            </p>
            <p className="text-2xl font-bold mt-1" style={{ color: 'var(--color-success)' }}>
              {stats.logs_today}
            </p>
          </div>
          <div className="rounded-lg p-4" style={{ background: 'var(--color-surface-offset)' }}>
            <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
              Esta Semana
            </p>
            <p className="text-2xl font-bold mt-1" style={{ color: 'var(--color-primary)' }}>
              {stats.logs_this_week}
            </p>
          </div>
          <div className="rounded-lg p-4" style={{ background: 'var(--color-surface-offset)' }}>
            <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
              Falhadas
            </p>
            <p className={clsx('text-2xl font-bold mt-1', stats.failed_operations > 0 ? 'text-red-500' : 'text-gray-400')}>
              {stats.failed_operations}
            </p>
          </div>
          <div className="rounded-lg p-4" style={{ background: 'var(--color-surface-offset)' }}>
            <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
              Ações
            </p>
            <p className="text-2xl font-bold mt-1" style={{ color: 'var(--color-primary)' }}>
              {Object.keys(stats.actions_breakdown).length}
            </p>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="rounded-lg" style={{ border: '1px solid var(--color-border)' }}>
        <button
          type="button"
          onClick={() => setShowFilters(!showFilters)}
          className="w-full flex items-center justify-between p-4 text-left font-semibold"
          style={{ color: 'var(--color-text)' }}
        >
          <div className="flex items-center gap-2">
            <Filter size={16} />
            Filtros {hasActiveFilters && `(${Object.values(filters).filter(v => v !== null).length})`}
          </div>
          {showFilters ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </button>

        {showFilters && (
          <div
            className="border-t p-4 space-y-4"
            style={{ borderColor: 'var(--color-divider)', background: 'var(--color-surface-offset)' }}
          >
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              <div>
                <label className="text-xs font-semibold" style={{ color: 'var(--color-text-muted)' }}>
                  User ID
                </label>
                <input
                  type="number"
                  value={filters.user_id || ''}
                  onChange={e => handleFilterChange('user_id', e.target.value ? parseInt(e.target.value) : null)}
                  placeholder="Filtrar por usuário"
                  className="w-full mt-1 px-3 py-2 rounded-lg text-sm"
                  style={{
                    background: 'var(--color-surface-dynamic)',
                    border: '1px solid var(--color-border)',
                    color: 'var(--color-text)',
                  }}
                />
              </div>
              <div>
                <label className="text-xs font-semibold" style={{ color: 'var(--color-text-muted)' }}>
                  Ação
                </label>
                <select
                  value={filters.action || ''}
                  onChange={e => handleFilterChange('action', e.target.value)}
                  className="w-full mt-1 px-3 py-2 rounded-lg text-sm"
                  style={{
                    background: 'var(--color-surface-dynamic)',
                    border: '1px solid var(--color-border)',
                    color: 'var(--color-text)',
                  }}
                >
                  <option value="">Todas</option>
                  {Object.keys(ACTIONS_COLORS).map(action => (
                    <option key={action} value={action}>
                      {action}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs font-semibold" style={{ color: 'var(--color-text-muted)' }}>
                  Status
                </label>
                <select
                  value={filters.status || ''}
                  onChange={e => handleFilterChange('status', e.target.value)}
                  className="w-full mt-1 px-3 py-2 rounded-lg text-sm"
                  style={{
                    background: 'var(--color-surface-dynamic)',
                    border: '1px solid var(--color-border)',
                    color: 'var(--color-text)',
                  }}
                >
                  <option value="">Todos</option>
                  {Object.keys(STATUS_COLORS).map(status => (
                    <option key={status} value={status}>
                      {status}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs font-semibold" style={{ color: 'var(--color-text-muted)' }}>
                  Tipo de Recurso
                </label>
                <input
                  type="text"
                  value={filters.resource_type || ''}
                  onChange={e => handleFilterChange('resource_type', e.target.value)}
                  placeholder="Portfolio, Transaction..."
                  className="w-full mt-1 px-3 py-2 rounded-lg text-sm"
                  style={{
                    background: 'var(--color-surface-dynamic)',
                    border: '1px solid var(--color-border)',
                    color: 'var(--color-text)',
                  }}
                />
              </div>
              <div>
                <label className="text-xs font-semibold" style={{ color: 'var(--color-text-muted)' }}>
                  De
                </label>
                <input
                  type="date"
                  value={filters.date_from || ''}
                  onChange={e => handleFilterChange('date_from', e.target.value)}
                  className="w-full mt-1 px-3 py-2 rounded-lg text-sm"
                  style={{
                    background: 'var(--color-surface-dynamic)',
                    border: '1px solid var(--color-border)',
                    color: 'var(--color-text)',
                  }}
                />
              </div>
              <div>
                <label className="text-xs font-semibold" style={{ color: 'var(--color-text-muted)' }}>
                  Até
                </label>
                <input
                  type="date"
                  value={filters.date_to || ''}
                  onChange={e => handleFilterChange('date_to', e.target.value)}
                  className="w-full mt-1 px-3 py-2 rounded-lg text-sm"
                  style={{
                    background: 'var(--color-surface-dynamic)',
                    border: '1px solid var(--color-border)',
                    color: 'var(--color-text)',
                  }}
                />
              </div>
            </div>

            {hasActiveFilters && (
              <button
                type="button"
                onClick={handleClearFilters}
                className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors"
                style={{
                  background: 'var(--color-surface-dynamic)',
                  border: '1px solid var(--color-border)',
                  color: 'var(--color-text)',
                }}
              >
                <X size={14} />
                Limpar Filtros
              </button>
            )}
          </div>
        )}
      </div>

      {/* Table */}
      <div className="rounded-lg overflow-hidden" style={{ border: '1px solid var(--color-border)' }}>
        {logsLoading ? (
          <div className="p-8 text-center" style={{ color: 'var(--color-text-muted)' }}>
            Carregando...
          </div>
        ) : logs && logs.items.length > 0 ? (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr style={{ background: 'var(--color-surface-offset)', borderColor: 'var(--color-divider)' }}>
                    <th className="px-4 py-3 text-left text-xs font-semibold" style={{ color: 'var(--color-text-muted)' }}>
                      —
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-semibold" style={{ color: 'var(--color-text-muted)' }}>
                      ID
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-semibold" style={{ color: 'var(--color-text-muted)' }}>
                      Data
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-semibold" style={{ color: 'var(--color-text-muted)' }}>
                      Usuário
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-semibold" style={{ color: 'var(--color-text-muted)' }}>
                      Ação
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-semibold" style={{ color: 'var(--color-text-muted)' }}>
                      Recurso
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-semibold" style={{ color: 'var(--color-text-muted)' }}>
                      ID Recurso
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-semibold" style={{ color: 'var(--color-text-muted)' }}>
                      Status
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {logs.items.map(log => (
                    <AuditLogRow
                      key={log.id}
                      log={log}
                      isExpanded={expandedId === log.id}
                      onExpand={() => setExpandedId(expandedId === log.id ? null : log.id)}
                    />
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {logs.pages > 1 && (
              <div
                className="flex items-center justify-between p-4"
                style={{ background: 'var(--color-surface-offset)', borderTop: '1px solid var(--color-divider)' }}
              >
                <p className="text-xs" style={{ color: 'var(--color-text-muted)' }}>
                  Página {logs.page} de {logs.pages} • {logs.total} registros
                </p>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => setPage(p => Math.max(1, p - 1))}
                    disabled={logs.page === 1}
                    className="px-3 py-1.5 rounded text-sm font-medium disabled:opacity-50"
                    style={{
                      background: 'var(--color-surface-dynamic)',
                      border: '1px solid var(--color-border)',
                      color: 'var(--color-text)',
                    }}
                  >
                    Anterior
                  </button>
                  <button
                    type="button"
                    onClick={() => setPage(p => Math.min(logs.pages, p + 1))}
                    disabled={logs.page === logs.pages}
                    className="px-3 py-1.5 rounded text-sm font-medium disabled:opacity-50"
                    style={{
                      background: 'var(--color-surface-dynamic)',
                      border: '1px solid var(--color-border)',
                      color: 'var(--color-text)',
                    }}
                  >
                    Próximo
                  </button>
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="p-8 text-center" style={{ color: 'var(--color-text-muted)' }}>
            Nenhum log encontrado
          </div>
        )}
      </div>
    </div>
  )
}
