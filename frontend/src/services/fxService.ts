import api from './api'

export const fxService = {
  getUsdBrl: (): Promise<{ rate: number; pair: string }> =>
    api.get('/api/v1/fx/usd-brl').then(r => r.data),
}
