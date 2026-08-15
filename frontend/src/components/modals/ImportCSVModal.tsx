import { ChangeEvent, DragEvent, MouseEvent, useMemo, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { X, Upload, Download, AlertCircle, CheckCircle, AlertTriangle } from 'lucide-react'
import api from '@/services/api'
import { getApiValidationErrorMessage } from '@/utils/apiError'

interface Props {
  portfolioId: number
  onClose: () => void
  onSuccess?: () => void
}

type ValidationStatus = 'valid' | 'imported' | 'error' | 'warning' | 'skipped'
type RowFilter = 'valid' | 'warning' | 'error' | null

interface ValidationRow {
  row_num: number
  errors: string[]
  warnings: string[]
  status: ValidationStatus
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

const buttonStyle = {
  padding: '0.5rem 1rem',
  borderRadius: 'var(--radius-md)',
  fontSize: 'var(--text-sm)',
} as const

function rowKind(row: ValidationRow): Exclude<RowFilter, null> {
  if (row.status === 'valid' || row.status === 'imported') return 'valid'
  if (row.status === 'error') return 'error'
  return 'warning'
}

export default function ImportCSVModal({ portfolioId, onClose, onSuccess }: Props) {
  const queryClient = useQueryClient()
  const [step, setStep] = useState<'upload' | 'preview' | 'results'>('upload')
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<string[][]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState<ImportResult | null>(null)
  const [rowFilter, setRowFilter] = useState<RowFilter>(null)

  const hasBlockingErrors = !!result && (
    !result.success ||
    result.error_count > 0 ||
    result.skipped_count > 0 ||
    result.global_errors.length > 0
  )

  const filteredRows = useMemo(() => {
    if (!result || rowFilter === null) return result?.rows ?? []
    return result.rows.filter(row => rowKind(row) === rowFilter)
  }, [result, rowFilter])

  const counts = useMemo(() => {
    const rows = result?.rows ?? []
    return {
      valid: rows.filter(row => rowKind(row) === 'valid').length,
      warning: rows.filter(row => rowKind(row) === 'warning').length,
      error: rows.filter(row => rowKind(row) === 'error').length,
    }
  }, [result])

  const invalidateImportedData = () => {
    const keys = [
      'transactions',
      'portfolio-summary',
      'positions',
      'asset-distribution',
      'patrimonio-history',
      'summary',
      'rentabilidade-kpis',
      'rentabilidade-ativos',
      'rentabilidade-classes',
      'goals',
    ]
    keys.forEach(key => queryClient.invalidateQueries({ queryKey: [key, portfolioId] }))
  }

  const validateFile = async (selectedFile: File) => {
    setIsLoading(true)
    setResult(null)
    setRowFilter(null)
    setError('')

    try {
      const formData = new FormData()
      formData.append('file', selectedFile)
      const response = await api.post(`/portfolios/${portfolioId}/import-csv`, formData, {
        params: { dry_run: true },
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setResult(response.data)
    } catch (error: unknown) {
      setError('Erro ao validar: ' + getApiValidationErrorMessage(error, 'Erro desconhecido'))
    } finally {
      setIsLoading(false)
    }
  }

  const prepareFile = async (selectedFile: File) => {
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
    setRowFilter(null)
    setError('')

    try {
      const text = await selectedFile.text()
      const rows = text
        .split('\n')
        .filter(line => line.trim())
        .slice(0, 11)
        .map(line => line.split(',').map(value => value.trim()))
      setPreview(rows)
      setStep('preview')
      await validateFile(selectedFile)
    } catch (err) {
      setError('Erro ao ler arquivo: ' + (err instanceof Error ? err.message : 'Erro desconhecido'))
    }
  }

  const handleFileSelect = async (event: ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0]
    if (selectedFile) await prepareFile(selectedFile)
  }

  const handleDrop = async (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault()
    const selectedFile = event.dataTransfer.files?.[0]
    if (selectedFile) await prepareFile(selectedFile)
  }

  const handleDownloadTemplate = async () => {
    try {
      const response = await api.get('/assets/csv-template', { responseType: 'blob' })
      const blob = new Blob([response.data], { type: 'text/csv;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = 'portfolio_import_template.csv'
      document.body.appendChild(anchor)
      anchor.click()
      anchor.remove()
      URL.revokeObjectURL(url)
    } catch (err) {
      setError('Erro ao baixar modelo: ' + (err instanceof Error ? err.message : 'Erro desconhecido'))
    }
  }

  const handleImport = async () => {
    if (!file || !result || hasBlockingErrors) return
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
      setRowFilter(null)
      setStep('results')
      if (importResult.success) {
        invalidateImportedData()
        onSuccess?.()
      }
    } catch (error: unknown) {
      setError('Erro ao importar: ' + getApiValidationErrorMessage(error, 'Erro desconhecido'))
    } finally {
      setIsLoading(false)
    }
  }

  const toggleFilter = (filter: Exclude<RowFilter, null>, event: MouseEvent<HTMLButtonElement>) => {
    event.stopPropagation()
    setRowFilter(current => current === filter ? null : filter)
  }

  const renderFilterCard = (
    filter: Exclude<RowFilter, null>,
    label: string,
    value: number,
    color: string,
  ) => {
    const active = rowFilter === filter
    return (
      <button
        type="button"
        onClick={event => toggleFilter(filter, event)}
        aria-pressed={active}
        style={{
          padding: '0.75rem',
          borderRadius: 'var(--radius-md)',
          background: `oklch(from ${color} l c h / ${active ? '0.18' : '0.1'})`,
          border: `1px solid oklch(from ${color} l c h / ${active ? '0.55' : '0.2'})`,
          textAlign: 'center',
          cursor: 'pointer',
          outline: active ? `2px solid oklch(from ${color} l c h / 0.35)` : 'none',
          outlineOffset: 2,
        }}
      >
        <p style={{ margin: '0 0 0.25rem', fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>{label}</p>
        <p style={{ margin: 0, fontSize: 'var(--text-lg)', fontWeight: 700, color }}>{value}</p>
      </button>
    )
  }

  const renderRows = (rows: ValidationRow[]) => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', maxHeight: step === 'results' ? 300 : 220, overflowY: 'auto' }}>
      {rows.length === 0 && (
        <div style={{ padding: '0.75rem', color: 'var(--color-text-muted)', fontSize: 'var(--text-xs)', textAlign: 'center' }}>
          Nenhuma linha neste filtro.
        </div>
      )}
      {rows.map(row => {
        const kind = rowKind(row)
        const color = kind === 'valid' ? 'var(--color-success)' : kind === 'error' ? 'var(--color-error)' : 'var(--color-warning)'
        const Icon = kind === 'valid' ? CheckCircle : kind === 'error' ? AlertCircle : AlertTriangle
        return (
          <div key={row.row_num} style={{ padding: '0.5rem 0.75rem', borderRadius: 'var(--radius-md)', background: `oklch(from ${color} l c h / 0.08)`, border: `1px solid oklch(from ${color} l c h / 0.18)` }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: row.errors.length || row.warnings.length ? 4 : 0 }}>
              <Icon size={12} style={{ color }} />
              <span style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color }}>
                Linha {row.row_num}{row.ticker && ` — ${row.ticker} ${row.operation ?? ''}`}
              </span>
            </div>
            {row.errors.length > 0 && (
              <ul style={{ margin: '0.25rem 0 0 1.5rem', fontSize: 'var(--text-xs)', color: 'var(--color-error)', paddingLeft: 0 }}>
                {row.errors.map((message, index) => <li key={index}>{message}</li>)}
              </ul>
            )}
            {row.warnings.length > 0 && (
              <ul style={{ margin: '0.25rem 0 0 1.5rem', fontSize: 'var(--text-xs)', color: 'var(--color-warning)', paddingLeft: 0 }}>
                {row.warnings.map((message, index) => <li key={index}>{message}</li>)}
              </ul>
            )}
          </div>
        )
      })}
    </div>
  )

  return (
    <div
      style={{ position: 'fixed', inset: 0, zIndex: 50, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '1rem', background: 'oklch(0.12 0.01 240 / 0.7)', backdropFilter: 'blur(4px)' }}
      onClick={event => {
        if (event.target === event.currentTarget) onClose()
      }}
    >
      <div style={{ width: '100%', maxWidth: step === 'results' ? 900 : 520, background: 'var(--color-surface)', border: '1px solid oklch(from var(--color-text) l c h / 0.08)', borderRadius: 'var(--radius-xl)', boxShadow: 'var(--shadow-lg)', overflow: 'hidden', display: 'flex', flexDirection: 'column', maxHeight: '90vh' }}>
        <header style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '1.125rem 1.5rem', borderBottom: '1px solid oklch(from var(--color-text) l c h / 0.07)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <div style={{ width: 32, height: 32, borderRadius: 'var(--radius-lg)', background: 'oklch(from var(--color-primary) l c h / 0.12)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Upload size={15} style={{ color: 'var(--color-primary)' }} />
            </div>
            <div>
              <span style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--color-text)', display: 'block' }}>Importar Transações</span>
              <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>Use o modelo CSV para garantir compatibilidade</span>
            </div>
          </div>
          <button onClick={onClose} aria-label="Fechar" style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 4, color: 'var(--color-text-muted)', display: 'flex' }}>
            <X size={16} />
          </button>
        </header>

        <main style={{ flex: 1, overflow: 'auto', padding: '1.5rem' }}>
          {error && (
            <div style={{ display: 'flex', gap: '0.75rem', padding: '0.75rem 1rem', borderRadius: 'var(--radius-md)', background: 'oklch(from var(--color-error) l c h / 0.1)', border: '1px solid oklch(from var(--color-error) l c h / 0.3)', marginBottom: '1rem' }}>
              <AlertCircle size={16} style={{ color: 'var(--color-error)', flexShrink: 0 }} />
              <span style={{ fontSize: 'var(--text-sm)', color: 'var(--color-error)' }}>{error}</span>
            </div>
          )}

          {step === 'upload' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
              <div
                onClick={() => document.getElementById('file-input')?.click()}
                onDragOver={event => event.preventDefault()}
                onDrop={handleDrop}
                style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '2rem', border: '2px dashed oklch(from var(--color-text) l c h / 0.2)', borderRadius: 'var(--radius-lg)', background: 'oklch(from var(--color-text) l c h / 0.02)', cursor: 'pointer' }}
              >
                <Upload size={32} style={{ color: 'var(--color-primary)', marginBottom: '0.5rem' }} />
                <p style={{ margin: '0.25rem 0 0', fontSize: 'var(--text-sm)', fontWeight: 500 }}>Arraste seu arquivo CSV aqui</p>
                <p style={{ margin: '0.25rem 0 0', fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>ou clique para selecionar</p>
              </div>
              <input id="file-input" type="file" accept=".csv" onChange={handleFileSelect} style={{ display: 'none' }} />
              <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', lineHeight: 1.5 }}>
                Colunas obrigatórias: <strong>{REQUIRED_COLUMNS.join(', ')}</strong>. Operações aceitas: <strong>buy</strong> e <strong>sell</strong>. Data em <strong>YYYY-MM-DD</strong>.
              </div>
              <button onClick={handleDownloadTemplate} style={{ ...buttonStyle, alignSelf: 'flex-start', display: 'flex', alignItems: 'center', gap: '0.375rem', border: '1px solid oklch(from var(--color-text) l c h / 0.12)', background: 'transparent', color: 'var(--color-text-muted)', cursor: 'pointer' }}>
                <Download size={14} /> Baixar modelo CSV
              </button>
            </div>
          )}

          {step === 'preview' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div style={{ overflowX: 'auto', border: '1px solid oklch(from var(--color-text) l c h / 0.08)', borderRadius: 'var(--radius-md)' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 'var(--text-xs)' }}>
                  <tbody>
                    {preview.map((row, rowIndex) => (
                      <tr key={rowIndex} style={{ background: rowIndex === 0 ? 'oklch(from var(--color-text) l c h / 0.05)' : 'transparent' }}>
                        {row.map((cell, cellIndex) => (
                          <td key={cellIndex} style={{ padding: '0.5rem 0.75rem', whiteSpace: 'nowrap', color: rowIndex === 0 ? 'var(--color-text-muted)' : 'var(--color-text)', fontWeight: rowIndex === 0 ? 600 : 400 }}>{cell || '—'}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {isLoading && <div style={{ color: 'var(--color-primary)', fontSize: 'var(--text-sm)' }}>Validando arquivo...</div>}

              {result && (
                <section onClick={() => setRowFilter(null)} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: '0.75rem' }}>
                    {renderFilterCard('valid', 'Válidas', counts.valid, 'var(--color-success)')}
                    {renderFilterCard('warning', 'Avisos', counts.warning, 'var(--color-warning)')}
                    {renderFilterCard('error', 'Erros', counts.error, 'var(--color-error)')}
                  </div>

                  {rowFilter && (
                    <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', textAlign: 'center' }}>
                      Filtro ativo. Clique fora dos cards para mostrar todas as linhas.
                    </div>
                  )}

                  {hasBlockingErrors ? (
                    <div style={{ display: 'flex', gap: '0.5rem', padding: '0.75rem 1rem', background: 'oklch(from var(--color-error) l c h / 0.1)', border: '1px solid oklch(from var(--color-error) l c h / 0.2)', borderRadius: 'var(--radius-md)' }}>
                      <AlertCircle size={14} style={{ color: 'var(--color-error)', flexShrink: 0 }} />
                      <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-error)' }}>Corrija os erros ou avisos do CSV antes de confirmar. Nenhuma linha será importada parcialmente.</span>
                    </div>
                  ) : (
                    <div style={{ display: 'flex', gap: '0.5rem', padding: '0.75rem 1rem', background: 'oklch(from var(--color-success) l c h / 0.1)', border: '1px solid oklch(from var(--color-success) l c h / 0.2)', borderRadius: 'var(--radius-md)' }}>
                      <CheckCircle size={14} style={{ color: 'var(--color-success)', flexShrink: 0 }} />
                      <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-success)' }}>Arquivo validado. A importação será aplicada em lote único.</span>
                    </div>
                  )}

                  {result.global_errors.map((message, index) => (
                    <div key={index} style={{ color: 'var(--color-error)', fontSize: 'var(--text-xs)' }}>{message}</div>
                  ))}
                  {renderRows(filteredRows)}
                </section>
              )}
            </div>
          )}

          {step === 'results' && result && (
            <section onClick={() => setRowFilter(null)} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: '0.75rem' }}>
                {renderFilterCard('valid', 'Importadas', counts.valid, 'var(--color-success)')}
                {renderFilterCard('warning', 'Avisos', counts.warning, 'var(--color-warning)')}
                {renderFilterCard('error', 'Erros', counts.error, 'var(--color-error)')}
              </div>
              {renderRows(filteredRows)}
            </section>
          )}
        </main>

        <footer style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end', padding: '1rem 1.5rem', borderTop: '1px solid oklch(from var(--color-text) l c h / 0.07)' }}>
          {step !== 'results' && <button onClick={onClose} style={{ ...buttonStyle, border: '1px solid oklch(from var(--color-text) l c h / 0.12)', background: 'transparent', color: 'var(--color-text-muted)', cursor: 'pointer' }}>Cancelar</button>}
          {step === 'upload' && <button disabled={!file || isLoading} onClick={() => setStep('preview')} style={{ ...buttonStyle, border: 'none', background: 'var(--color-primary)', color: 'var(--color-text-inverse)', fontWeight: 600, cursor: !file || isLoading ? 'not-allowed' : 'pointer', opacity: !file || isLoading ? 0.6 : 1 }}>Próximo</button>}
          {step === 'preview' && (
            <>
              <button onClick={() => setStep('upload')} style={{ ...buttonStyle, border: '1px solid oklch(from var(--color-text) l c h / 0.12)', background: 'transparent', color: 'var(--color-text-muted)', cursor: 'pointer' }}>Voltar</button>
              <button disabled={isLoading || !result || hasBlockingErrors} onClick={handleImport} style={{ ...buttonStyle, border: 'none', background: 'var(--color-primary)', color: 'var(--color-text-inverse)', fontWeight: 600, cursor: isLoading || !result || hasBlockingErrors ? 'not-allowed' : 'pointer', opacity: isLoading || !result || hasBlockingErrors ? 0.6 : 1 }}>{isLoading ? 'Processando...' : 'Confirmar importação'}</button>
            </>
          )}
          {step === 'results' && <button onClick={onClose} style={{ ...buttonStyle, border: 'none', background: 'var(--color-primary)', color: 'var(--color-text-inverse)', fontWeight: 600, cursor: 'pointer' }}>Fechar</button>}
        </footer>
      </div>
    </div>
  )
}
