import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { X, Upload, Download, AlertCircle, CheckCircle, AlertTriangle } from 'lucide-react'
import api from '@/services/api'

interface Props {
  portfolioId: number
  onClose: () => void
  onSuccess?: () => void
}

interface ValidationRow {
  row_num: number
  errors: string[]
  warnings: string[]
  status: 'valid' | 'imported' | 'error' | 'warning' | 'skipped'
  ticker?: string
  operation?: string
  quantity?: number
}

interface ImportResult {
  success: boolean
  imported_count: number
  skipped_count: number
  error_count: number
  rows: ValidationRow[]
  global_errors: string[]
}

const REQUIRED_COLUMNS = ['ticker', 'asset_type', 'operation', 'quantity', 'price', 'date', 'fees', 'currency', 'notes']

export default function ImportCSVModal({ portfolioId, onClose, onSuccess }: Props) {
  const queryClient = useQueryClient()
  const [step, setStep] = useState<'upload' | 'preview' | 'results'>('upload')
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<string[][]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState<ImportResult | null>(null)
  const hasBlockingErrors = !!result && (
    !result.success ||
    result.error_count > 0 ||
    result.skipped_count > 0 ||
    result.global_errors.length > 0
  )

  const invalidateImportedData = () => {
    queryClient.invalidateQueries({ queryKey: ['transactions', portfolioId] })
    queryClient.invalidateQueries({ queryKey: ['portfolio-summary', portfolioId] })
    queryClient.invalidateQueries({ queryKey: ['positions', portfolioId] })
    queryClient.invalidateQueries({ queryKey: ['asset-distribution', portfolioId] })
    queryClient.invalidateQueries({ queryKey: ['patrimonio-history', portfolioId] })
    queryClient.invalidateQueries({ queryKey: ['summary', portfolioId] })
    queryClient.invalidateQueries({ queryKey: ['rentabilidade-kpis', portfolioId] })
    queryClient.invalidateQueries({ queryKey: ['rentabilidade-ativos', portfolioId] })
    queryClient.invalidateQueries({ queryKey: ['rentabilidade-classes', portfolioId] })
    queryClient.invalidateQueries({ queryKey: ['goals', portfolioId] })
  }

  const validateFile = async (selectedFile: File) => {
    setIsLoading(true)
    setResult(null)
    setError('')

    try {
      const formData = new FormData()
      formData.append('file', selectedFile)

      const response = await api.post(`/portfolios/${portfolioId}/import-csv`, formData, {
        params: { dry_run: true },
        headers: { 'Content-Type': 'multipart/form-data' },
      })

      setResult(response.data)
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      setError('Erro ao validar: ' + (detail || err?.message || 'Erro desconhecido'))
    } finally {
      setIsLoading(false)
    }
  }

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0]
    if (!selectedFile) return

    if (!selectedFile.name.toLowerCase().endsWith('.csv')) {
      setError('Por favor, selecione um arquivo CSV.')
      return
    }

    if (selectedFile.size > 5 * 1024 * 1024) {
      setError('Arquivo muito grande (máximo 5MB).')
      return
    }

    setFile(selectedFile)
    setResult(null)
    setError('')

    try {
      const text = await selectedFile.text()
      const lines = text.split('\n')
      const rows = lines
        .filter(l => l.trim())
        .slice(0, 11)
        .map(l => l.split(',').map(v => v.trim()))
      setPreview(rows)
      setStep('preview')
      await validateFile(selectedFile)
    } catch (err) {
      setError('Erro ao ler arquivo: ' + (err instanceof Error ? err.message : 'Erro desconhecido'))
    }
  }

  const handleDownloadTemplate = async () => {
    try {
      const response = await api.get('/assets/csv-template', { responseType: 'blob' })
      const blob = new Blob([response.data], { type: 'text/csv;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'portfolio_import_template.csv'
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (err) {
      setError('Erro ao baixar modelo: ' + (err instanceof Error ? err.message : 'Erro desconhecido'))
    }
  }

  const handleImport = async () => {
    if (!file) return
    if (!result || hasBlockingErrors) return

    setIsLoading(true)
    setError('')

    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await api.post(`/portfolios/${portfolioId}/import-csv`, formData, {
        params: { dry_run: false },
        headers: { 'Content-Type': 'multipart/form-data' },
      })

      const importResult: ImportResult = response.data
      setResult(importResult)
      setStep('results')

      if (importResult.success) {
        invalidateImportedData()
        onSuccess?.()
      }
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      setError('Erro ao importar: ' + (detail || err?.message || 'Erro desconhecido'))
    } finally {
      setIsLoading(false)
    }
  }

  return (
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
      onClick={e => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <div
        style={{
          width: '100%',
          maxWidth: step === 'results' ? 900 : 520,
          background: 'var(--color-surface)',
          border: '1px solid oklch(from var(--color-text) l c h / 0.08)',
          borderRadius: 'var(--radius-xl)',
          boxShadow: 'var(--shadow-lg)',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
          maxHeight: '90vh',
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '1.125rem 1.5rem',
            borderBottom: '1px solid oklch(from var(--color-text) l c h / 0.07)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <div
              style={{
                width: 32,
                height: 32,
                borderRadius: 'var(--radius-lg)',
                background: 'oklch(from var(--color-primary) l c h / 0.12)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <Upload size={15} style={{ color: 'var(--color-primary)' }} />
            </div>
            <div>
              <span style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--color-text)', display: 'block' }}>
                Importar Transações
              </span>
              <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>
                Use o modelo CSV para garantir compatibilidade
              </span>
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              padding: 4,
              color: 'var(--color-text-muted)',
              borderRadius: 'var(--radius-md)',
              display: 'flex',
              alignItems: 'center',
            }}
            aria-label="Fechar"
          >
            <X size={16} />
          </button>
        </div>

        <div style={{ flex: 1, overflow: 'auto', padding: '1.5rem' }}>
          {error && (
            <div
              style={{
                display: 'flex',
                gap: '0.75rem',
                padding: '0.75rem 1rem',
                borderRadius: 'var(--radius-md)',
                background: 'oklch(from var(--color-error) l c h / 0.1)',
                border: '1px solid oklch(from var(--color-error) l c h / 0.3)',
                marginBottom: '1rem',
              }}
            >
              <AlertCircle size={16} style={{ color: 'var(--color-error)', flexShrink: 0, marginTop: 2 }} />
              <span style={{ fontSize: 'var(--text-sm)', color: 'var(--color-error)' }}>{error}</span>
            </div>
          )}

          {step === 'upload' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
              <div
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  padding: '2rem',
                  border: '2px dashed oklch(from var(--color-text) l c h / 0.2)',
                  borderRadius: 'var(--radius-lg)',
                  background: 'oklch(from var(--color-text) l c h / 0.02)',
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                }}
                onClick={() => document.getElementById('file-input')?.click()}
                onDragOver={e => {
                  e.preventDefault()
                  e.currentTarget.style.background = 'oklch(from var(--color-primary) l c h / 0.08)'
                }}
                onDragLeave={e => {
                  e.currentTarget.style.background = 'oklch(from var(--color-text) l c h / 0.02)'
                }}
                onDrop={e => {
                  e.preventDefault()
                  const files = e.dataTransfer.files
                  if (files.length > 0) {
                    const input = document.getElementById('file-input') as HTMLInputElement
                    if (input) {
                      input.files = files
                      handleFileSelect({ target: input } as any)
                    }
                  }
                }}
              >
                <Upload size={32} style={{ color: 'var(--color-primary)', marginBottom: '0.5rem' }} />
                <p style={{ margin: '0.25rem 0 0', fontSize: 'var(--text-sm)', fontWeight: 500, color: 'var(--color-text)' }}>
                  Arraste seu arquivo CSV aqui
                </p>
                <p style={{ margin: '0.25rem 0 0', fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>
                  ou clique para selecionar
                </p>
              </div>

              <input
                id="file-input"
                type="file"
                accept=".csv"
                onChange={handleFileSelect}
                style={{ display: 'none' }}
              />

              {file && (
                <div
                  style={{
                    padding: '0.75rem 1rem',
                    background: 'oklch(from var(--color-success) l c h / 0.1)',
                    border: '1px solid oklch(from var(--color-success) l c h / 0.3)',
                    borderRadius: 'var(--radius-md)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                  }}
                >
                  <CheckCircle size={16} style={{ color: 'var(--color-success)' }} />
                  <span style={{ fontSize: 'var(--text-sm)', color: 'var(--color-success)' }}>
                    {file.name} ({(file.size / 1024).toFixed(1)} KB)
                  </span>
                </div>
              )}

              <div style={{ borderTop: '1px solid oklch(from var(--color-text) l c h / 0.1)', paddingTop: '1rem' }}>
                <p style={{ margin: '0 0 0.75rem', fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>
                  Modelo aceito
                </p>
                <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', lineHeight: 1.5, marginBottom: '0.75rem' }}>
                  Colunas obrigatórias: <strong>{REQUIRED_COLUMNS.join(', ')}</strong>. Operações aceitas: <strong>buy</strong> e <strong>sell</strong>. Data em <strong>YYYY-MM-DD</strong>.
                </div>
                <button
                  onClick={handleDownloadTemplate}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.375rem',
                    padding: '0.5rem 0.75rem',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid oklch(from var(--color-text) l c h / 0.12)',
                    background: 'transparent',
                    color: 'var(--color-primary)',
                    fontSize: 'var(--text-sm)',
                    cursor: 'pointer',
                    fontWeight: 500,
                  }}
                >
                  <Download size={14} />
                  Baixar modelo CSV
                </button>
              </div>
            </div>
          )}

          {step === 'preview' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div>
                <p style={{ margin: '0 0 0.75rem', fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>
                  Prévia do arquivo ({preview.length} linhas)
                </p>
                <div style={{ overflowX: 'auto', borderRadius: 'var(--radius-md)', border: '1px solid oklch(from var(--color-text) l c h / 0.1)' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 'var(--text-xs)' }}>
                    <tbody>
                      {preview.slice(0, 10).map((row, idx) => (
                        <tr
                          key={idx}
                          style={{
                            borderBottom: idx < preview.length - 1 ? '1px solid oklch(from var(--color-text) l c h / 0.1)' : 'none',
                            background: idx === 0 ? 'oklch(from var(--color-text) l c h / 0.05)' : 'transparent',
                          }}
                        >
                          {row.map((cell, cellIdx) => (
                            <td
                              key={cellIdx}
                              style={{
                                padding: '0.5rem 0.75rem',
                                color: idx === 0 ? 'var(--color-text-muted)' : 'var(--color-text)',
                                fontWeight: idx === 0 ? 600 : 400,
                                whiteSpace: 'nowrap',
                              }}
                            >
                              {cell || '—'}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {isLoading && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.75rem 1rem', borderRadius: 'var(--radius-md)', background: 'oklch(from var(--color-primary) l c h / 0.08)' }}>
                  <Upload size={14} style={{ color: 'var(--color-primary)' }} />
                  <span style={{ fontSize: 'var(--text-sm)', color: 'var(--color-primary)' }}>
                    Validando arquivo...
                  </span>
                </div>
              )}

              {result && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '0.75rem' }}>
                    <div style={{ padding: '0.75rem', borderRadius: 'var(--radius-md)', background: 'oklch(from var(--color-success) l c h / 0.1)', border: '1px solid oklch(from var(--color-success) l c h / 0.2)', textAlign: 'center' }}>
                      <p style={{ margin: '0 0 0.25rem', fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>Válidas</p>
                      <p style={{ margin: 0, fontSize: 'var(--text-lg)', fontWeight: 700, color: 'var(--color-success)' }}>
                        {result.rows.filter(row => row.status === 'valid').length}
                      </p>
                    </div>
                    <div style={{ padding: '0.75rem', borderRadius: 'var(--radius-md)', background: 'oklch(from var(--color-warning) l c h / 0.1)', border: '1px solid oklch(from var(--color-warning) l c h / 0.2)', textAlign: 'center' }}>
                      <p style={{ margin: '0 0 0.25rem', fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>Avisos</p>
                      <p style={{ margin: 0, fontSize: 'var(--text-lg)', fontWeight: 700, color: 'var(--color-warning)' }}>{result.skipped_count}</p>
                    </div>
                    <div style={{ padding: '0.75rem', borderRadius: 'var(--radius-md)', background: 'oklch(from var(--color-error) l c h / 0.1)', border: '1px solid oklch(from var(--color-error) l c h / 0.2)', textAlign: 'center' }}>
                      <p style={{ margin: '0 0 0.25rem', fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>Erros</p>
                      <p style={{ margin: 0, fontSize: 'var(--text-lg)', fontWeight: 700, color: 'var(--color-error)' }}>{result.error_count}</p>
                    </div>
                  </div>

                  {hasBlockingErrors ? (
                    <div style={{ display: 'flex', gap: '0.5rem', padding: '0.75rem 1rem', background: 'oklch(from var(--color-error) l c h / 0.1)', border: '1px solid oklch(from var(--color-error) l c h / 0.2)', borderRadius: 'var(--radius-md)' }}>
                      <AlertCircle size={14} style={{ color: 'var(--color-error)', flexShrink: 0, marginTop: 2 }} />
                      <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-error)' }}>
                        Corrija os erros ou avisos do CSV antes de confirmar. Nenhuma linha será importada parcialmente.
                      </span>
                    </div>
                  ) : (
                    <div style={{ display: 'flex', gap: '0.5rem', padding: '0.75rem 1rem', background: 'oklch(from var(--color-success) l c h / 0.1)', border: '1px solid oklch(from var(--color-success) l c h / 0.2)', borderRadius: 'var(--radius-md)' }}>
                      <CheckCircle size={14} style={{ color: 'var(--color-success)', flexShrink: 0, marginTop: 2 }} />
                      <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-success)' }}>
                        Arquivo validado. A importação será aplicada em lote único.
                      </span>
                    </div>
                  )}

                  {result.global_errors.map((err, idx) => (
                    <div key={idx} style={{ display: 'flex', gap: '0.5rem', padding: '0.5rem 0.75rem', background: 'oklch(from var(--color-error) l c h / 0.1)', border: '1px solid oklch(from var(--color-error) l c h / 0.2)', borderRadius: 'var(--radius-md)' }}>
                      <AlertCircle size={14} style={{ color: 'var(--color-error)', flexShrink: 0, marginTop: 2 }} />
                      <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-error)' }}>{err}</span>
                    </div>
                  ))}

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', maxHeight: 220, overflowY: 'auto' }}>
                    {result.rows.map(row => (
                      <div key={row.row_num} style={{ padding: '0.5rem 0.75rem', borderRadius: 'var(--radius-md)', background: row.status === 'valid' ? 'oklch(from var(--color-success) l c h / 0.08)' : row.status === 'error' ? 'oklch(from var(--color-error) l c h / 0.08)' : 'oklch(from var(--color-warning) l c h / 0.08)', border: '1px solid oklch(from var(--color-text) l c h / 0.08)' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: row.errors.length || row.warnings.length ? 4 : 0 }}>
                          {row.status === 'valid' ? <CheckCircle size={12} style={{ color: 'var(--color-success)' }} /> : row.status === 'error' ? <AlertCircle size={12} style={{ color: 'var(--color-error)' }} /> : <AlertTriangle size={12} style={{ color: 'var(--color-warning)' }} />}
                          <span style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: row.status === 'valid' ? 'var(--color-success)' : row.status === 'error' ? 'var(--color-error)' : 'var(--color-warning)' }}>
                            Linha {row.row_num}{row.ticker && ` — ${row.ticker} ${row.operation ?? ''}`}
                          </span>
                        </div>
                        {row.errors.length > 0 && (
                          <ul style={{ margin: '0.25rem 0 0 1.5rem', fontSize: 'var(--text-xs)', color: 'var(--color-error)', paddingLeft: 0 }}>
                            {row.errors.map((err, idx) => <li key={idx}>{err}</li>)}
                          </ul>
                        )}
                        {row.warnings.length > 0 && (
                          <ul style={{ margin: '0.25rem 0 0 1.5rem', fontSize: 'var(--text-xs)', color: 'var(--color-warning)', paddingLeft: 0 }}>
                            {row.warnings.map((warn, idx) => <li key={idx}>{warn}</li>)}
                          </ul>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {step === 'results' && result && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '1rem' }}>
                <div style={{ padding: '1rem', borderRadius: 'var(--radius-md)', background: 'oklch(from var(--color-success) l c h / 0.1)', border: '1px solid oklch(from var(--color-success) l c h / 0.2)', textAlign: 'center' }}>
                  <p style={{ margin: '0 0 0.25rem', fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>Importados</p>
                  <p style={{ margin: 0, fontSize: 'var(--text-lg)', fontWeight: 700, color: 'var(--color-success)' }}>{result.imported_count}</p>
                </div>
                <div style={{ padding: '1rem', borderRadius: 'var(--radius-md)', background: 'oklch(from var(--color-warning) l c h / 0.1)', border: '1px solid oklch(from var(--color-warning) l c h / 0.2)', textAlign: 'center' }}>
                  <p style={{ margin: '0 0 0.25rem', fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>Avisos</p>
                  <p style={{ margin: 0, fontSize: 'var(--text-lg)', fontWeight: 700, color: 'var(--color-warning)' }}>{result.skipped_count}</p>
                </div>
                <div style={{ padding: '1rem', borderRadius: 'var(--radius-md)', background: 'oklch(from var(--color-error) l c h / 0.1)', border: '1px solid oklch(from var(--color-error) l c h / 0.2)', textAlign: 'center' }}>
                  <p style={{ margin: '0 0 0.25rem', fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>Erros</p>
                  <p style={{ margin: 0, fontSize: 'var(--text-lg)', fontWeight: 700, color: 'var(--color-error)' }}>{result.error_count}</p>
                </div>
              </div>

              {result.global_errors.length > 0 && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  <p style={{ margin: 0, fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>Erros Globais</p>
                  {result.global_errors.map((err, idx) => (
                    <div key={idx} style={{ display: 'flex', gap: '0.5rem', padding: '0.5rem 0.75rem', background: 'oklch(from var(--color-error) l c h / 0.1)', border: '1px solid oklch(from var(--color-error) l c h / 0.2)', borderRadius: 'var(--radius-md)' }}>
                      <AlertCircle size={14} style={{ color: 'var(--color-error)', flexShrink: 0, marginTop: 2 }} />
                      <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-error)' }}>{err}</span>
                    </div>
                  ))}
                </div>
              )}

              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', maxHeight: 300, overflowY: 'auto' }}>
                <p style={{ margin: 0, fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--color-text-muted)', textTransform: 'uppercase' }}>
                  Detalhes das linhas
                </p>
                {result.rows.map(row => (
                  <div
                    key={row.row_num}
                    style={{
                      padding: '0.5rem 0.75rem',
                      borderRadius: 'var(--radius-md)',
                      background:
                        row.status === 'imported'
                          ? 'oklch(from var(--color-success) l c h / 0.1)'
                          : row.status === 'error'
                            ? 'oklch(from var(--color-error) l c h / 0.1)'
                            : 'oklch(from var(--color-warning) l c h / 0.1)',
                      border:
                        row.status === 'imported'
                          ? '1px solid oklch(from var(--color-success) l c h / 0.2)'
                          : row.status === 'error'
                            ? '1px solid oklch(from var(--color-error) l c h / 0.2)'
                            : '1px solid oklch(from var(--color-warning) l c h / 0.2)',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: 4 }}>
                      {row.status === 'imported' && <CheckCircle size={12} style={{ color: 'var(--color-success)' }} />}
                      {row.status === 'error' && <AlertCircle size={12} style={{ color: 'var(--color-error)' }} />}
                      {row.status !== 'imported' && row.status !== 'error' && (
                        <AlertTriangle size={12} style={{ color: 'var(--color-warning)' }} />
                      )}
                      <span style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: row.status === 'imported' ? 'var(--color-success)' : row.status === 'error' ? 'var(--color-error)' : 'var(--color-warning)' }}>
                        Linha {row.row_num}{row.ticker && ` — ${row.ticker} ${row.operation}`}
                      </span>
                    </div>
                    {row.errors.length > 0 && (
                      <ul style={{ margin: '0.25rem 0 0 1.5rem', fontSize: 'var(--text-xs)', color: 'var(--color-error)', paddingLeft: 0 }}>
                        {row.errors.map((err, idx) => <li key={idx}>{err}</li>)}
                      </ul>
                    )}
                    {row.warnings.length > 0 && (
                      <ul style={{ margin: '0.25rem 0 0 1.5rem', fontSize: 'var(--text-xs)', color: 'var(--color-warning)', paddingLeft: 0 }}>
                        {row.warnings.map((warn, idx) => <li key={idx}>{warn}</li>)}
                      </ul>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end', padding: '1rem 1.5rem', borderTop: '1px solid oklch(from var(--color-text) l c h / 0.07)' }}>
          {step !== 'results' && (
            <button onClick={onClose} style={{ padding: '0.5rem 1rem', borderRadius: 'var(--radius-md)', border: '1px solid oklch(from var(--color-text) l c h / 0.12)', background: 'transparent', color: 'var(--color-text-muted)', fontSize: 'var(--text-sm)', cursor: 'pointer' }}>
              Cancelar
            </button>
          )}

          {step === 'upload' && (
            <button disabled={!file || isLoading} onClick={() => setStep('preview')} style={{ padding: '0.5rem 1.25rem', borderRadius: 'var(--radius-md)', border: 'none', background: !file || isLoading ? 'oklch(from var(--color-primary) l c h / 0.6)' : 'var(--color-primary)', color: 'var(--color-text-inverse)', fontSize: 'var(--text-sm)', fontWeight: 600, cursor: !file || isLoading ? 'not-allowed' : 'pointer' }}>
              Próximo
            </button>
          )}

          {step === 'preview' && (
            <>
              <button onClick={() => setStep('upload')} style={{ padding: '0.5rem 1rem', borderRadius: 'var(--radius-md)', border: '1px solid oklch(from var(--color-text) l c h / 0.12)', background: 'transparent', color: 'var(--color-text-muted)', fontSize: 'var(--text-sm)', cursor: 'pointer' }}>
                Voltar
              </button>
              <button disabled={isLoading || !result || hasBlockingErrors} onClick={handleImport} style={{ padding: '0.5rem 1.25rem', borderRadius: 'var(--radius-md)', border: 'none', background: isLoading || !result || hasBlockingErrors ? 'oklch(from var(--color-primary) l c h / 0.6)' : 'var(--color-primary)', color: 'var(--color-text-inverse)', fontSize: 'var(--text-sm)', fontWeight: 600, cursor: isLoading || !result || hasBlockingErrors ? 'not-allowed' : 'pointer', display: 'flex', alignItems: 'center', gap: '0.375rem' }}>
                {isLoading ? 'Processando...' : 'Confirmar importação'}
              </button>
            </>
          )}

          {step === 'results' && (
            <button onClick={onClose} style={{ padding: '0.5rem 1.25rem', borderRadius: 'var(--radius-md)', border: 'none', background: 'var(--color-primary)', color: 'var(--color-text-inverse)', fontSize: 'var(--text-sm)', fontWeight: 600, cursor: 'pointer' }}>
              Fechar
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
