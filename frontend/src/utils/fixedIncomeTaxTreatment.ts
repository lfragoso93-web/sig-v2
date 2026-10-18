export type FixedIncomeProductType =
  | 'CDB' | 'RDB' | 'LCI' | 'LCA' | 'LC' | 'LIG' | 'CRI' | 'CRA'
  | 'DEBENTURE' | 'DEBENTURE_INCENTIVADA' | 'LETRA_FINANCEIRA' | 'OUTRO'

const EXEMPT_PRODUCT_TYPES = new Set<FixedIncomeProductType>([
  'LCI', 'LCA', 'LIG', 'CRI', 'CRA', 'DEBENTURE_INCENTIVADA',
])

export type FixedIncomeTaxTreatment = 'EXEMPT' | 'TAXABLE'

export function fixedIncomeTaxTreatment(productType: string): FixedIncomeTaxTreatment {
  return EXEMPT_PRODUCT_TYPES.has(productType as FixedIncomeProductType) ? 'EXEMPT' : 'TAXABLE'
}

export function isFixedIncomeProductTaxExempt(productType: string): boolean {
  return fixedIncomeTaxTreatment(productType) === 'EXEMPT'
}
