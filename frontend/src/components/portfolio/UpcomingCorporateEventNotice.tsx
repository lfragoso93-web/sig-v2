import { useEffect, useMemo, useState } from 'react'
import { CalendarDays } from 'lucide-react'
import { useAppStore } from '@/store/appStore'
import { useUpcomingCorporateEvents } from '@/hooks/useUpcomingCorporateEvents'
import Modal from '@/components/ui/Modal'

export default function UpcomingCorporateEventNotice() {
  const portfolioId = useAppStore(state => state.selectedPortfolioId)
  const { data: events = [] } = useUpcomingCorporateEvents(portfolioId)
  const storageKey = 'sgi:seen-upcoming-corporate-events'
  const [dismissed, setDismissed] = useState<{
    portfolioId: number | null
    eventIds: number[]
  }>({ portfolioId: null, eventIds: [] })

  useEffect(() => {
    try {
      const value: unknown = JSON.parse(sessionStorage.getItem(storageKey) ?? '{}')
      const portfolioEvents = (
        value && typeof value === 'object' && !Array.isArray(value)
          ? (value as Record<string, unknown>)[String(portfolioId ?? 'none')]
          : []
      )
      setDismissed({
        portfolioId,
        eventIds: Array.isArray(portfolioEvents)
          ? portfolioEvents.filter((item): item is number => (
            typeof item === 'number' && Number.isInteger(item)
          ))
          : [],
      })
    } catch {
      setDismissed({ portfolioId, eventIds: [] })
    }
  }, [storageKey, portfolioId])

  const dismissedEventIds = dismissed.portfolioId === portfolioId
    ? dismissed.eventIds
    : null

  const nextEvent = useMemo(
    () => dismissedEventIds === null
      ? null
      : events.find(event => !dismissedEventIds.includes(event.event_id)) ?? null,
    [dismissedEventIds, events],
  )

  const close = () => {
    if (!nextEvent) return
    const updated = [...new Set([...(dismissedEventIds ?? []), nextEvent.event_id])]
    setDismissed({ portfolioId, eventIds: updated })
    try {
      const value: unknown = JSON.parse(sessionStorage.getItem(storageKey) ?? '{}')
      const allDismissed = value && typeof value === 'object' && !Array.isArray(value)
        ? value as Record<string, unknown>
        : {}
      sessionStorage.setItem(storageKey, JSON.stringify({
        ...allDismissed,
        [String(portfolioId ?? 'none')]: updated,
      }))
    } catch {
      // The notice remains dismissible when session storage is unavailable.
    }
  }

  const eventDate = nextEvent
    ? new Intl.DateTimeFormat('pt-BR', { dateStyle: 'long' })
      .format(new Date(`${nextEvent.event_date}T00:00:00`))
    : ''

  return (
    <Modal
      open={!!nextEvent}
      onClose={close}
      title="Evento futuro na sua carteira"
      size="sm"
    >
      {nextEvent && (
        <div style={{ display: 'grid', gap: 'var(--space-3)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
            <CalendarDays size={18} aria-hidden="true" />
            <strong>{nextEvent.ticker}</strong>
            <span>{nextEvent.event_type.replace(/_/g, ' ')}</span>
          </div>
          <p style={{ margin: 0, color: 'var(--color-text-muted)' }}>
            Data do evento: <strong>{eventDate}</strong>
          </p>
          {nextEvent.description && (
            <p style={{ margin: 0 }}>{nextEvent.description}</p>
          )}
          <p style={{ margin: 0, fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)' }}>
            Aviso baseado em evento confirmado no cadastro do SGI.
          </p>
          <button className="btn" onClick={close} style={{ justifySelf: 'end' }}>
            Entendi
          </button>
        </div>
      )}
    </Modal>
  )
}
