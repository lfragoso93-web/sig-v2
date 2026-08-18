import { describe, expect, it } from 'vitest'
import { getApiErrorDetail, getApiErrorMessage, getApiValidationErrorMessage } from '../apiError'

describe('getApiErrorMessage', () => {
  it('returns the API detail from an Axios error', () => {
    const error = {
      isAxiosError: true,
      response: { data: { detail: 'Carteira indisponível' } },
    }
    expect(getApiErrorMessage(error, 'Falha padrão')).toBe('Carteira indisponível')
    expect(getApiErrorDetail(error)).toBe('Carteira indisponível')
  })

  it('uses a native error message when no API detail exists', () => {
    expect(getApiErrorMessage(new Error('Falha de rede'), 'Falha padrão')).toBe('Falha de rede')
  })

  it('uses the fallback for unknown values and structured details', () => {
    expect(getApiErrorMessage({ reason: 'unknown' }, 'Falha padrão')).toBe('Falha padrão')
    expect(getApiErrorMessage({
      isAxiosError: true,
      response: { data: { detail: [{ msg: 'inválido' }] } },
    }, 'Falha padrão')).toBe('Falha padrão')
    expect(getApiErrorDetail({ reason: 'unknown' })).toBeNull()
  })

  it('joins structured FastAPI validation messages explicitly', () => {
    const error = {
      isAxiosError: true,
      response: { data: { detail: [{ msg: 'ticker inválido' }, { msg: 'data ausente' }] } },
    }
    expect(getApiValidationErrorMessage(error, 'Falha padrão')).toBe(
      'ticker inválido, data ausente',
    )
  })
})
