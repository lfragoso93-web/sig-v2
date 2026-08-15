export const PORTFOLIO_ROUTES = {
  root: '/carteira',
  goals: '/carteira/metas',
  irpf: '/carteira/irpf',
} as const

// Compatibilidade unidirecional para favoritos anteriores à hierarquia por
// carteira. Não registrar páginas, loaders ou cálculos nestes caminhos.
export const LEGACY_PORTFOLIO_ROUTE_REDIRECTS = {
  '/metas': PORTFOLIO_ROUTES.goals,
  '/irpf': PORTFOLIO_ROUTES.irpf,
} as const
