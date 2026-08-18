import axios from 'axios'

interface ApiErrorBody {
  detail?: unknown
}

export function getApiErrorDetail(error: unknown): string | null {
  if (axios.isAxiosError<ApiErrorBody>(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string' && detail.trim()) return detail
  }
  return null
}

export function getApiErrorMessage(error: unknown, fallback: string): string {
  const detail = getApiErrorDetail(error)
  if (detail) return detail
  if (error instanceof Error && error.message.trim()) return error.message
  return fallback
}

export function getApiValidationErrorMessage(error: unknown, fallback: string): string {
  if (axios.isAxiosError<ApiErrorBody>(error)) {
    const detail = error.response?.data?.detail
    if (Array.isArray(detail)) {
      const messages = detail.flatMap((item) => {
        if (typeof item !== 'object' || item === null || !('msg' in item)) return []
        return typeof item.msg === 'string' && item.msg.trim() ? [item.msg] : []
      })
      if (messages.length) return messages.join(', ')
    }
  }
  return getApiErrorMessage(error, fallback)
}
