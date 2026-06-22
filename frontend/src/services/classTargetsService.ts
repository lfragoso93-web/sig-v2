import api from './api'

export interface ClassTarget {
  asset_type: string
  target_pct: number
}

export const classTargetsService = {
  list: (portfolioId: number) =>
    api.get<ClassTarget[]>(`/portfolios/${portfolioId}/class-targets`).then(r => r.data),

  upsert: (portfolioId: number, asset_type: string, target_pct: number) =>
    api
      .put<ClassTarget>(`/portfolios/${portfolioId}/class-targets/${asset_type}`, { target_pct })
      .then(r => r.data),

  remove: (portfolioId: number, asset_type: string) =>
    api.delete(`/portfolios/${portfolioId}/class-targets/${asset_type}`),
}
