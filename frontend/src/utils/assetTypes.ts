export const ASSET_TYPE_LABELS: Record<string, string> = {
  ACAO_NACIONAL:     'Ações',
  FII:               'FIIs',
  ETF_NACIONAL:      'ETFs Nac.',
  BDR:               'BDRs',
  TESOURO_DIRETO:    'Tesouro Direto',
  STOCK:             'Stocks',
  ETF_INTERNACIONAL: 'ETFs Int.',
  REIT:              'REITs',
  CRIPTO:            'Criptomoedas',
  RENDA_FIXA:        'Renda Fixa',
}

// Paleta por tipo — alinhada com o design system
export const ASSET_TYPE_COLORS: Record<string, string> = {
  ACAO_NACIONAL:     '#01696f',  // primary teal
  FII:               '#006494',  // blue
  ETF_NACIONAL:      '#437a22',  // green
  BDR:               '#7a39bb',  // purple
  TESOURO_DIRETO:    '#d19900',  // gold
  STOCK:             '#da7101',  // orange
  ETF_INTERNACIONAL: '#a13544',  // notification red
  REIT:              '#a12c7b',  // error pink
  CRIPTO:            '#4f98a3',  // primary teal dark mode
  RENDA_FIXA:        '#6daa45',  // success green
}
