import { useEffect, useRef, useState } from 'react'

import { ProventosHistoricoMes } from '@/services/proventosService'
import { formatBRL } from '@/utils/format'
import ProventosMonthPopover from './ProventosMonthPopover'

const MONTHS = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez']

const cellText  = { color: 'var(--color-text)' }
const cellMuted = { color: 'var(--color-text-muted)' }
const cellFaint = { color: 'var(--color-text-faint)' }

interface OpenMonth {
  anchor: HTMLButtonElement
  detail: ProventosHistoricoMes['month_details'][number]
  year: number
}

export default function ProventosHistoricoTable({ data }: { data: ProventosHistoricoMes[] }) {
  const [openMonth, setOpenMonth] = useState<OpenMonth | null>(null)
  const closeTimer = useRef<number | null>(null)

  const cancelClose = () => {
    if (closeTimer.current !== null) window.clearTimeout(closeTimer.current)
    closeTimer.current = null
  }
  const close = () => {
    cancelClose()
    setOpenMonth(null)
  }
  const scheduleClose = () => {
    cancelClose()
    closeTimer.current = window.setTimeout(() => setOpenMonth(null), 120)
  }
  const show = (
    anchor: HTMLButtonElement,
    row: ProventosHistoricoMes,
    month: number,
  ) => {
    const detail = row.month_details.find(item => item.month === month)
    if (!detail) return
    cancelClose()
    setOpenMonth({ anchor, detail, year: row.year })
  }

  useEffect(() => () => cancelClose(), [])

  if (!data.length) return (
    <p className="text-xs p-4" style={cellMuted}>Sem dados</p>
  )

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[800px] text-xs" style={{ borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ borderBottom: '1px solid var(--color-divider)' }}>
            <th className="px-3 py-2 text-left font-medium w-12" style={cellMuted}>Ano</th>
            {MONTHS.map(m => (
              <th key={m} className="px-2 py-2 text-right font-medium" style={cellMuted}>{m}</th>
            ))}
            <th className="px-3 py-2 text-right font-medium" style={cellMuted}>Média</th>
            <th className="px-3 py-2 text-right font-medium" style={cellMuted}>Total</th>
          </tr>
        </thead>
        <tbody>
          {data.map((row, rowIdx) => (
            <tr
              key={row.year}
              style={{
                borderBottom: '1px solid oklch(from var(--color-text) l c h / 0.05)',
                background: rowIdx % 2 !== 0 ? 'var(--color-surface-offset)' : 'transparent',
              }}
              onMouseEnter={e => (e.currentTarget.style.background = 'oklch(from var(--color-primary) l c h / 0.04)')}
              onMouseLeave={e => (e.currentTarget.style.background = rowIdx % 2 !== 0 ? 'var(--color-surface-offset)' : 'transparent')}
            >
              <td className="px-3 py-2 font-semibold" style={cellText}>{row.year}</td>
              {row.months.map((val, idx) => {
                const month = idx + 1
                const detail = row.month_details.find(item => item.month === month)
                const isOpen = openMonth?.year === row.year && openMonth.detail.month === month

                return (
                  <td key={idx} className="px-1 py-1 text-right tabular-nums" style={val && val > 0 ? cellText : cellFaint}>
                    {val != null && val > 0 && detail ? (
                      <button
                        type="button"
                        className="min-h-9 min-w-14 rounded px-1 text-right tabular-nums underline decoration-dotted underline-offset-2"
                        style={{ color: 'inherit' }}
                        aria-label={`Detalhar ${MONTHS[idx]} de ${row.year}`}
                        aria-haspopup="dialog"
                        aria-expanded={isOpen}
                        aria-controls={isOpen ? `proventos-month-${row.year}-${month}` : undefined}
                        onMouseEnter={event => show(event.currentTarget, row, month)}
                        onMouseLeave={scheduleClose}
                        onFocus={event => show(event.currentTarget, row, month)}
                        onBlur={scheduleClose}
                        onClick={event => {
                          if (isOpen) close()
                          else show(event.currentTarget, row, month)
                        }}
                      >
                        {formatBRL(val).replace('R$\u00a0', '')}
                      </button>
                    ) : val != null && val > 0 ? (
                      formatBRL(val).replace('R$\u00a0', '')
                    ) : '—'}
                  </td>
                )
              })}
              <td className="px-3 py-2 text-right tabular-nums font-medium" style={{ color: 'var(--color-primary)' }}>
                {formatBRL(row.media).replace('R$\u00a0', '')}
              </td>
              <td className="px-3 py-2 text-right tabular-nums font-semibold" style={{ color: 'var(--color-success)' }}>
                {formatBRL(row.total)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {openMonth && (
        <ProventosMonthPopover
          anchor={openMonth.anchor}
          detail={openMonth.detail}
          id={`proventos-month-${openMonth.year}-${openMonth.detail.month}`}
          year={openMonth.year}
          onClose={close}
          onMouseEnter={cancelClose}
          onMouseLeave={scheduleClose}
        />
      )}
    </div>
  )
}
