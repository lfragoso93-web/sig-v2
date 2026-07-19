import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'

import { ProventosMonthDetail } from '@/services/proventosService'
import { formatBRL } from '@/utils/format'

const MONTH_NAMES = [
  'janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho',
  'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro',
]

const WIDTH = 288
const GAP = 8
const VIEWPORT_MARGIN = 8

interface Position {
  left: number
  top: number
  ready: boolean
}

interface Props {
  anchor: HTMLElement
  detail: ProventosMonthDetail
  id: string
  year: number
  onClose: () => void
  onMouseEnter: () => void
  onMouseLeave: () => void
}

export default function ProventosMonthPopover({
  anchor,
  detail,
  id,
  year,
  onClose,
  onMouseEnter,
  onMouseLeave,
}: Props) {
  const popoverRef = useRef<HTMLDivElement>(null)
  const [position, setPosition] = useState<Position>({ left: 0, top: 0, ready: false })

  useLayoutEffect(() => {
    const updatePosition = () => {
      const anchorRect = anchor.getBoundingClientRect()
      const height = popoverRef.current?.offsetHeight ?? 0
      const centeredLeft = anchorRect.left + anchorRect.width / 2 - WIDTH / 2
      const left = Math.min(
        Math.max(centeredLeft, VIEWPORT_MARGIN),
        Math.max(VIEWPORT_MARGIN, window.innerWidth - WIDTH - VIEWPORT_MARGIN),
      )
      const below = anchorRect.bottom + GAP
      const top = below + height <= window.innerHeight - VIEWPORT_MARGIN
        ? below
        : Math.max(VIEWPORT_MARGIN, anchorRect.top - height - GAP)

      setPosition({ left, top, ready: true })
    }

    updatePosition()
    window.addEventListener('resize', updatePosition)
    window.addEventListener('scroll', updatePosition, true)
    return () => {
      window.removeEventListener('resize', updatePosition)
      window.removeEventListener('scroll', updatePosition, true)
    }
  }, [anchor, detail])

  useEffect(() => {
    const handlePointerDown = (event: PointerEvent) => {
      const target = event.target as Node
      if (!anchor.contains(target) && !popoverRef.current?.contains(target)) onClose()
    }
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault()
        onClose()
        anchor.focus()
      }
    }

    document.addEventListener('pointerdown', handlePointerDown)
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('pointerdown', handlePointerDown)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [anchor, onClose])

  return createPortal(
    <div
      ref={popoverRef}
      id={id}
      role="dialog"
      aria-label={`Proventos de ${MONTH_NAMES[detail.month - 1]} de ${year}`}
      className="fixed z-50 rounded-lg border p-3 text-xs shadow-xl"
      style={{
        background: 'var(--color-surface)',
        borderColor: 'var(--color-divider)',
        color: 'var(--color-text)',
        left: position.left,
        top: position.top,
        visibility: position.ready ? 'visible' : 'hidden',
        width: WIDTH,
      }}
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
    >
      <p className="mb-3 font-semibold capitalize">
        {MONTH_NAMES[detail.month - 1]} de {year}
      </p>
      <ul className="space-y-2">
        {detail.by_asset_class.map(item => (
          <li key={item.asset_type} className="flex items-center justify-between gap-4">
            <span className="flex min-w-0 items-center gap-2">
              <span
                aria-hidden="true"
                className="h-2 w-2 shrink-0 rounded-full"
                style={{ background: 'var(--color-primary)' }}
              />
              <span className="truncate">{item.label}</span>
            </span>
            <span className="shrink-0 tabular-nums font-medium">{formatBRL(item.value)}</span>
          </li>
        ))}
      </ul>
      <div
        className="mt-3 flex items-center justify-between border-t pt-2 font-semibold"
        style={{ borderColor: 'var(--color-divider)' }}
      >
        <span>Total</span>
        <span className="tabular-nums" style={{ color: 'var(--color-success)' }}>
          {formatBRL(detail.total)}
        </span>
      </div>
    </div>,
    document.body,
  )
}
