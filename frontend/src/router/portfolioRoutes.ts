export const PORTFOLIO_ROUTES = {
  root: '/carteira',
  goals: '/carteira/metas',
  irpf: '/carteira/irpf',
} as const

export const LEGACY_PORTFOLIO_ROUTE_REDIRECTS = {
  '/metas': PORTFOLIO_ROUTES.goals,
  '/irpf': PORTFOLIO_ROUTES.irpf,
} as const
