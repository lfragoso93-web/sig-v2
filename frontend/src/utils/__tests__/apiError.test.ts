import { describe, expect, it } from 'vitest'
import { getApiErrorMessage } from '../apiError'

describe('getApiErrorMessage', () => {
  it('returns the API detail from an Axios error', () => {
    const error = {
      isAxiosError: true,
      response: { data: { detail: 'Carteira indisponível' } },
    }
    expect(getApiErrorMessage(error, 'Falha padrão')).toBe('Carteira indisponível')
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
  })
})
