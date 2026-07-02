import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { Database, Download, Trash2, RotateCcw, Loader2, AlertTriangle, CheckCircle } from 'lucide-react'
import api from '@/services/api'

interface Backup {
  filename: string
  backup_id: string
  size_mb: number
  created_at: string
}

interface BackupsResponse {
  success: boolean
  backups: Backup[]
  total_size_mb: number
  count: number
  error?: string
}

const fetchBackups = () => api.get<BackupsResponse>('/admin/database/backups').then(r => r.data)

export default function BackupPanel() {
  const [expandedSection, setExpandedSection] = useState<string | null>('backups')
  const [selectedBackup, setSelectedBackup] = useState<string | null>(null)
  const [showRestoreWarning, setShowRestoreWarning] = useState(false)
  const [feedback, setFeedback] = useState<{ msg: string; isError: boolean } | null>(null)

  const { data: backupsData, isLoading: isLoadingBackups, refetch } = useQuery({
    queryKey: ['admin_backups'],
    queryFn: fetchBackups,
    refetchInterval: 5000,
  })

  const createBackup = useMutation({
    mutationFn: () => api.post('/admin/database/backup', {}),
    onSuccess: () => {
      setFeedback({ msg: 'Backup iniciado em background. Acompanhe pelo log do servidor.', isError: false })
      setTimeout(() => refetch(), 2000)
    },
    onError: (e: any) => {
      const detail = e?.response?.data?.detail
      setFeedback({
        msg: typeof detail === 'string' ? detail : 'Erro ao criar backup.',
        isError: true,
      })
    },
  })

  const deleteBackup = useMutation({
    mutationFn: (filename: string) =>
      api.delete(`/admin/database/backups/${filename}`),
    onSuccess: () => {
      setFeedback({ msg: 'Backup deletado com sucesso.', isError: false })
      refetch()
    },
    onError: (e: any) => {
      const detail = e?.response?.data?.detail
      setFeedback({
        msg: typeof detail === 'string' ? detail : 'Erro ao deletar backup.',
        isError: true,
      })
    },
  })

  const restoreBackup = useMutation({
    mutationFn: (filename: string) =>
      api.post('/admin/database/restore', {}, { params: { backup_filename: filename } }),
    onSuccess: () => {
      setFeedback({ msg: 'Restauração iniciada em background. TODOS os dados serão sobrescritos!', isError: false })
      setSelectedBackup(null)
      setShowRestoreWarning(false)
      setTimeout(() => refetch(), 2000)
    },
    onError: (e: any) => {
      const detail = e?.response?.data?.detail
      setFeedback({
        msg: typeof detail === 'string' ? detail : 'Erro ao restaurar backup.',
        isError: true,
      })
    },
  })

  const downloadBackup = (filename: string) => {
    const link = document.createElement('a')
    link.href = `${api.defaults.baseURL}/admin/database/backups/${filename}`
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  const isOpen = expandedSection === 'backups'

  return (
    <div style={{
      background: 'var(--color-surface)',
      border: '1px solid oklch(from var(--color-text) l c h / 0.1)',
      borderRadius: 'var(--radius-lg)',
      padding: '1.5rem',
      marginBottom: '1.5rem',
    }}>
      {/* Header */}
      <button
        onClick={() => setExpandedSection(isOpen ? null : 'backups')}
        style={{
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0.5rem 0',
          background: 'none',
          border: 'none',
          cursor: 'pointer',
          textAlign: 'left',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <Database size={18} style={{ color: 'var(--color-primary)' }} />
          <span style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--color-text)' }}>
            Backup & Restore
          </span>
        </div>
        {isOpen
          ? <ChevronUp size={16} style={{ color: 'var(--color-text-muted)' }} />
          : <ChevronDown size={16} style={{ color: 'var(--color-text-muted)' }} />}
      </button>

      {isOpen && (
        <div style={{ marginTop: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {/* Feedback */}
          {feedback && (
            <div
              style={{
                display: 'flex',
                gap: '0.75rem',
                padding: '0.75rem 1rem',
                borderRadius: 'var(--radius-md)',
                background: feedback.isError
                  ? 'oklch(from var(--color-error) l c h / 0.1)'
                  : 'oklch(from var(--color-success) l c h / 0.1)',
                border: `1px solid ${
                  feedback.isError
                    ? 'oklch(from var(--color-error) l c h / 0.3)'
                    : 'oklch(from var(--color-success) l c h / 0.3)'
                }`,
              }}
            >
              {feedback.isError
                ? <AlertTriangle size={16} style={{ color: 'var(--color-error)', marginTop: 2 }} />
                : <CheckCircle size={16} style={{ color: 'var(--color-success)', marginTop: 2 }} />}
              <span style={{
                fontSize: 'var(--text-sm)',
                color: feedback.isError ? 'var(--color-error)' : 'var(--color-success)',
              }}>
                {feedback.msg}
              </span>
            </div>
          )}

          {/* Create Backup Button */}
          <button
            onClick={() => createBackup.mutate()}
            disabled={createBackup.isPending}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '0.5rem',
              padding: '0.625rem 1rem',
              borderRadius: 'var(--radius-md)',
              border: 'none',
              background: createBackup.isPending ? 'oklch(from var(--color-primary) l c h / 0.6)' : 'var(--color-primary)',
              color: 'var(--color-text-inverse)',
              fontSize: 'var(--text-sm)',
              fontWeight: 500,
              cursor: createBackup.isPending ? 'not-allowed' : 'pointer',
            }}
          >
            {createBackup.isPending && <Loader2 size={14} />}
            {createBackup.isPending ? 'Criando...' : 'Criar Backup Agora'}
          </button>

          {/* Backups List */}
          <div>
            <p style={{
              margin: '0 0 0.75rem',
              fontSize: 'var(--text-xs)',
              fontWeight: 600,
              color: 'var(--color-text-muted)',
              textTransform: 'uppercase',
            }}>
              Backups Disponíveis {backupsData && `(${backupsData.count})`}
            </p>

            {isLoadingBackups && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '1rem' }}>
                <Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} />
                <span style={{ fontSize: 'var(--text-sm)', color: 'var(--color-text-muted)' }}>
                  Carregando backups...
                </span>
              </div>
            )}

            {!isLoadingBackups && backupsData && backupsData.count === 0 && (
              <p style={{
                padding: '1rem',
                fontSize: 'var(--text-sm)',
                color: 'var(--color-text-muted)',
                background: 'oklch(from var(--color-text) l c h / 0.02)',
                borderRadius: 'var(--radius-md)',
              }}>
                Nenhum backup disponível. Crie um backup para começar.
              </p>
            )}

            {!isLoadingBackups && backupsData && backupsData.count > 0 && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {backupsData.backups.map((backup) => (
                  <div
                    key={backup.filename}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '0.75rem 1rem',
                      borderRadius: 'var(--radius-md)',
                      border: '1px solid oklch(from var(--color-text) l c h / 0.1)',
                      background: selectedBackup === backup.filename
                        ? 'oklch(from var(--color-primary) l c h / 0.05)'
                        : 'transparent',
                    }}
                  >
                    <div style={{ flex: 1 }}>
                      <p style={{
                        margin: '0',
                        fontSize: 'var(--text-sm)',
                        fontWeight: 500,
                        color: 'var(--color-text)',
                      }}>
                        {backup.backup_id}
                      </p>
                      <p style={{
                        margin: '0.25rem 0 0',
                        fontSize: 'var(--text-xs)',
                        color: 'var(--color-text-muted)',
                      }}>
                        {backup.size_mb} MB — {new Date(backup.created_at).toLocaleString('pt-BR')}
                      </p>
                    </div>
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                      <button
                        onClick={() => downloadBackup(backup.filename)}
                        title="Download"
                        style={{
                          padding: '0.5rem',
                          borderRadius: 'var(--radius-md)',
                          border: '1px solid oklch(from var(--color-text) l c h / 0.12)',
                          background: 'transparent',
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                        }}
                      >
                        <Download size={14} style={{ color: 'var(--color-text-muted)' }} />
                      </button>
                      <button
                        onClick={() => {
                          setSelectedBackup(backup.filename)
                          setShowRestoreWarning(true)
                        }}
                        disabled={restoreBackup.isPending}
                        title="Restaurar"
                        style={{
                          padding: '0.5rem',
                          borderRadius: 'var(--radius-md)',
                          border: '1px solid oklch(from var(--color-text) l c h / 0.12)',
                          background: 'transparent',
                          cursor: restoreBackup.isPending ? 'not-allowed' : 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          opacity: restoreBackup.isPending ? 0.6 : 1,
                        }}
                      >
                        {restoreBackup.isPending
                          ? <Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} />
                          : <RotateCcw size={14} style={{ color: 'var(--color-warning)' }} />}
                      </button>
                      <button
                        onClick={() => deleteBackup.mutate(backup.filename)}
                        disabled={deleteBackup.isPending}
                        title="Deletar"
                        style={{
                          padding: '0.5rem',
                          borderRadius: 'var(--radius-md)',
                          border: '1px solid oklch(from var(--color-text) l c h / 0.12)',
                          background: 'transparent',
                          cursor: deleteBackup.isPending ? 'not-allowed' : 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          opacity: deleteBackup.isPending ? 0.6 : 1,
                        }}
                      >
                        {deleteBackup.isPending
                          ? <Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} />
                          : <Trash2 size={14} style={{ color: 'var(--color-error)' }} />}
                      </button>
                    </div>
                  </div>
                ))}
                <p style={{
                  margin: '0.75rem 0 0',
                  fontSize: 'var(--text-xs)',
                  color: 'var(--color-text-muted)',
                }}>
                  Espaço total usado: {backupsData.total_size_mb} MB
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Restore Warning Modal */}
      {showRestoreWarning && selectedBackup && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 50,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '1rem',
            background: 'oklch(0.12 0.01 240 / 0.7)',
            backdropFilter: 'blur(4px)',
          }}
          onClick={() => {
            setShowRestoreWarning(false)
            setSelectedBackup(null)
          }}
        >
          <div
            style={{
              width: '100%',
              maxWidth: 420,
              background: 'var(--color-surface)',
              border: '1px solid oklch(from var(--color-text) l c h / 0.08)',
              borderRadius: 'var(--radius-xl)',
              boxShadow: 'var(--shadow-lg)',
              overflow: 'hidden',
            }}
            onClick={e => e.stopPropagation()}
          >
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.75rem',
              padding: '1.5rem',
              borderBottom: '1px solid oklch(from var(--color-text) l c h / 0.07)',
              background: 'oklch(from var(--color-error) l c h / 0.05)',
            }}>
              <AlertTriangle size={20} style={{ color: 'var(--color-error)' }} />
              <span style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--color-error)' }}>
                Confirmar Restauração
              </span>
            </div>

            <div style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <p style={{
                margin: 0,
                fontSize: 'var(--text-sm)',
                color: 'var(--color-text)',
              }}>
                Você está prestes a restaurar o banco de dados a partir de um backup.
              </p>

              <div style={{
                padding: '0.75rem 1rem',
                borderRadius: 'var(--radius-md)',
                background: 'oklch(from var(--color-error) l c h / 0.1)',
                border: '1px solid oklch(from var(--color-error) l c h / 0.3)',
              }}>
                <p style={{
                  margin: 0,
                  fontSize: 'var(--text-xs)',
                  fontWeight: 600,
                  color: 'var(--color-error)',
                }}>
                  ATENÇÃO
                </p>
                <p style={{
                  margin: '0.5rem 0 0',
                  fontSize: 'var(--text-xs)',
                  color: 'var(--color-error)',
                }}>
                  Esta ação sobrescreverá TODOS os dados atuais do banco com os dados do backup.
                  Esta ação é IRREVERSÍVEL.
                </p>
              </div>

              <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
                <button
                  onClick={() => {
                    setShowRestoreWarning(false)
                    setSelectedBackup(null)
                  }}
                  style={{
                    padding: '0.5rem 1rem',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid oklch(from var(--color-text) l c h / 0.12)',
                    background: 'transparent',
                    color: 'var(--color-text-muted)',
                    fontSize: 'var(--text-sm)',
                    cursor: 'pointer',
                  }}
                >
                  Cancelar
                </button>
                <button
                  onClick={() => restoreBackup.mutate(selectedBackup)}
                  disabled={restoreBackup.isPending}
                  style={{
                    padding: '0.5rem 1rem',
                    borderRadius: 'var(--radius-md)',
                    border: 'none',
                    background: restoreBackup.isPending ? 'oklch(from var(--color-error) l c h / 0.6)' : 'var(--color-error)',
                    color: 'var(--color-text-inverse)',
                    fontSize: 'var(--text-sm)',
                    fontWeight: 600,
                    cursor: restoreBackup.isPending ? 'not-allowed' : 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.375rem',
                  }}
                >
                  {restoreBackup.isPending && <Loader2 size={14} />}
                  {restoreBackup.isPending ? 'Restaurando...' : 'Restaurar'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function ChevronUp({ size }: { size: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <polyline points="18 15 12 9 6 15" />
    </svg>
  )
}

function ChevronDown({ size }: { size: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <polyline points="6 9 12 15 18 9" />
    </svg>
  )
}
