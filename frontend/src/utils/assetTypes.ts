export const ASSET_TYPE_LABELS: Record<string, string> = {
  ACAO: 'Ações',
  ACAO_NACIONAL: 'Ações',
  FII: 'FIIs',
  ETF_NACIONAL: 'ETF Nacional',
  ETF_INTERNACIONAL: 'ETF Internacional',
  STOCK: 'Stocks internacionais',
  BDR: 'BDRs',
  TESOURO_DIRETO: 'Tesouro Direto',
  RENDA_FIXA: 'Renda Fixa',
  CRIPTO: 'Criptomoedas',
  OUTRO: 'Outros',
}

export const ASSET_TYPE_COLORS: Record<string, string> = {
  ACAO: '#01696f',
  ACAO_NACIONAL: '#01696f',
  FII: '#006494',
  ETF_NACIONAL: '#437a22',
  BDR: '#7a39bb',
  TESOURO_DIRETO: '#d19900',
  STOCK: '#da7101',
  ETF_INTERNACIONAL: '#a13544',
  CRIPTO: '#4f98a3',
  RENDA_FIXA: '#6daa45',
  OUTRO: '#64748b',
}

export const ASSET_CLASS_ALL = 'all'

export interface AssetClassOption {
  label: string
  value: string
}

export function assetTypeLabel(assetType: string): string {
  return ASSET_TYPE_LABELS[assetType] ?? assetType
}

export function buildAssetClassOptions(assetTypes: string[]): AssetClassOption[] {
  const uniqueTypes = [...new Set(assetTypes.filter(Boolean))]
    .sort((left, right) => assetTypeLabel(left).localeCompare(assetTypeLabel(right), 'pt-BR'))

  return [
    { label: 'Todas as classes', value: ASSET_CLASS_ALL },
    ...uniqueTypes.map(value => ({ label: assetTypeLabel(value), value })),
  ]
}
