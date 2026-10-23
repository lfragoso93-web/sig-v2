import { useCallback, useEffect, useId, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { CircleHelp } from 'lucide-react'

export const TWR_HELP_TITLE = 'O que é TWR?'
export const TWR_HELP_DESCRIPTION =
  'O TWR (Time-Weighted Return) mede a rentabilidade dos investimentos sem a influência de aportes e retiradas. Ele permite avaliar o desempenho da carteira ao longo do tempo.'

interface TwrHelpPopoverProps {
  className?: string
  size?: number
}

interface PopoverCoords {
  top: number
  left: number
  placement: 'top' | 'bottom'
}

export default function TwrHelpPopover({ className = '', size = 13 }: TwrHelpPopoverProps) {
  const [open, setOpen] = useState(false)
  const [pinnedByClick, setPinnedByClick] = useState(false)
  const [coords, setCoords] = useState<PopoverCoords | null>(null)
  const triggerRef = useRef<HTMLButtonElement>(null)
  const popoverRef = useRef<HTMLDivElement>(null)
  const suppressFocusOpenRef = useRef(false)
  const tooltipId = useId()

  const updatePosition = useCallback(() => {
    const trigger = triggerRef.current
    if (!trigger) return
    const rect = trigger.getBoundingClientRect()
    const popoverWidth = Math.min(288, Math.max(220, window.innerWidth - 24))
    const estimatedHeight = 112
    const margin = 12

    const spaceAbove = rect.top - margin
    const spaceBelow = window.innerHeight - rect.bottom - margin
    const placement: 'top' | 'bottom' =
      spaceAbove >= estimatedHeight || spaceAbove >= spaceBelow ? 'top' : 'bottom'

    const centeredLeft = rect.left + rect.width / 2 - popoverWidth / 2
    const left = Math.min(
      Math.max(margin, centeredLeft),
      Math.max(margin, window.innerWidth - popoverWidth - margin),
    )

    const top =
      placement === 'top'
        ? Math.max(margin, rect.top - 8)
        : Math.min(window.innerHeight - margin, rect.bottom + 8)

    setCoords({ top, left, placement })
  }, [])

  useEffect(() => {
    if (!open) return
    updatePosition()

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        suppressFocusOpenRef.current = true
        setOpen(false)
        setPinnedByClick(false)
      }
    }

    const handlePointerDown = (event: MouseEvent | TouchEvent) => {
      const target = event.target as Node | null
      if (!target) return
      if (triggerRef.current?.contains(target) || popoverRef.current?.contains(target)) {
        return
      }
      setOpen(false)
      setPinnedByClick(false)
    }

    window.addEventListener('resize', updatePosition)
    window.addEventListener('scroll', updatePosition, true)
    document.addEventListener('keydown', handleKeyDown)
    document.addEventListener('mousedown', handlePointerDown)
    document.addEventListener('touchstart', handlePointerDown)

    return () => {
      window.removeEventListener('resize', updatePosition)
      window.removeEventListener('scroll', updatePosition, true)
      document.removeEventListener('keydown', handleKeyDown)
      document.removeEventListener('mousedown', handlePointerDown)
      document.removeEventListener('touchstart', handlePointerDown)
    }
  }, [open, updatePosition])

  const handleMouseEnter = () => {
    setOpen(true)
  }

  const handleMouseLeave = () => {
    if (!pinnedByClick) {
      setOpen(false)
    }
  }

  const handleFocus = () => {
    if (suppressFocusOpenRef.current) {
      suppressFocusOpenRef.current = false
      return
    }
    setOpen(true)
  }

  const handleBlur = (event: React.FocusEvent<HTMLButtonElement>) => {
    const nextFocused = event.relatedTarget as Node | null
    if (nextFocused && popoverRef.current?.contains(nextFocused)) {
      return
    }
    if (!pinnedByClick) {
      setOpen(false)
    }
  }

  const handleClick = (event: React.MouseEvent<HTMLButtonElement>) => {
    event.stopPropagation()
    setPinnedByClick(prev => {
      const nextPinned = !prev
      setOpen(nextPinned || !open)
      return nextPinned
    })
  }

  return (
    <span className={`inline-flex items-center ${className}`}>
      <button
        ref={triggerRef}
        type="button"
        aria-label="Ajuda sobre TWR"
        aria-expanded={open}
        aria-describedby={open ? tooltipId : undefined}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
        onFocus={handleFocus}
        onBlur={handleBlur}
        onClick={handleClick}
        className="inline-flex items-center justify-center rounded-full transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1"
        style={{
          width: Math.max(size + 6, 18),
          height: Math.max(size + 6, 18),
          color: open ? 'var(--color-primary)' : 'var(--color-text-faint)',
          background: open ? 'oklch(from var(--color-primary) l c h / 0.12)' : 'transparent',
          border: 'none',
          padding: 0,
          cursor: 'pointer',
          flexShrink: 0,
        }}
      >
        <CircleHelp size={size} aria-hidden="true" />
      </button>

      {open &&
        typeof document !== 'undefined' &&
        createPortal(
          <div
            ref={popoverRef}
            id={tooltipId}
            role="tooltip"
            onMouseEnter={handleMouseEnter}
            onMouseLeave={handleMouseLeave}
            style={{
              position: 'fixed',
              top: coords?.top ?? 0,
              left: coords?.left ?? 0,
              transform: coords?.placement === 'top' ? 'translateY(-100%)' : 'none',
              width: 'min(288px, calc(100vw - 24px))',
              zIndex: 9999,
              background: 'var(--color-surface-2)',
              color: 'var(--color-text)',
              border: '1px solid var(--color-border)',
              borderRadius: 'var(--radius-lg)',
              boxShadow: 'var(--shadow-lg)',
              padding: '0.75rem 0.875rem',
              textTransform: 'none',
              letterSpacing: 'normal',
              fontWeight: 400,
              pointerEvents: 'auto',
            }}
          >
            <div
              style={{
                fontSize: 'var(--text-xs)',
                fontWeight: 650,
                color: 'var(--color-text)',
                marginBottom: 4,
                lineHeight: 1.3,
              }}
            >
              {TWR_HELP_TITLE}
            </div>
            <p
              style={{
                fontSize: 'var(--text-xs)',
                color: 'var(--color-text-muted)',
                lineHeight: 1.45,
                margin: 0,
              }}
            >
              {TWR_HELP_DESCRIPTION}
            </p>
          </div>,
          document.body,
        )}
    </span>
  )
}
