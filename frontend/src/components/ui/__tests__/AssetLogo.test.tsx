import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import AssetLogo from '../AssetLogo'
import { formatTreasuryName } from '@/utils/treasury'

describe('AssetLogo canonical iconography (#351)', () => {
  it('renders persisted logoUrl when provided and falls back to canonical icon on error without calling external providers', () => {
    const { container } = render(
      <AssetLogo ticker="PETR4" assetType="ACAO" logoUrl="/static/logos/petr4.png" />,
    )

    const img = screen.getByRole('img', { name: 'PETR4' }) as HTMLImageElement
    expect(img.getAttribute('src')).toBe('/static/logos/petr4.png')

    fireEvent.error(img)

    expect(screen.queryByRole('img')).toBeNull()
    expect(screen.getByTestId('asset-logo-class-ACAO')).toBeTruthy()
    expect(container.innerHTML).not.toContain('brapi.dev')
  })

  it.each([
    ['BTC', 'BTC'],
    ['BTC-USD', 'BTC'],
    ['ETH', 'ETH'],
    ['ETH-BRL', 'ETH'],
    ['SOL', 'SOL'],
    ['USDT', 'USDT'],
  ])('renders canonical vector icon for supported crypto %s (%s)', (ticker, expectedSymbol) => {
    const { container } = render(<AssetLogo ticker={ticker} assetType="CRIPTO" />)
    expect(screen.getByTestId(`asset-logo-crypto-${expectedSymbol}`)).toBeTruthy()
    expect(container.querySelector('svg')).toBeTruthy()
    expect(container.innerHTML).not.toContain('brapi.dev')
  })

  it.each([
    'TESOURO_DIRETO',
    'RENDA_FIXA',
    'FII',
    'ACAO',
    'ETF_NACIONAL',
    'BDR',
    'STOCK',
    'CRIPTO',
  ])('renders class fallback visual for %s when no specific logo exists', (assetType) => {
    const { container } = render(<AssetLogo ticker="CUSTOM99" assetType={assetType} />)
    expect(screen.getByTestId(`asset-logo-class-${assetType}`)).toBeTruthy()
    expect(container.querySelector('svg')).toBeTruthy()
  })
})

describe('formatTreasuryName commercial nomenclature (#351)', () => {
  it('formats RendA+ commercial display name', () => {
    expect(formatTreasuryName('TESOURO-RENDA-PLUS-01032065')).toBe(
      'Tesouro RendA+ Aposentadoria Extra 2065',
    )
    expect(formatTreasuryName('TESOURO-RENDA-MAIS-2065', 'Tesouro RENDA MAIS 2065')).toBe(
      'Tesouro RendA+ Aposentadoria Extra 2065',
    )
  })

  it('preserves canonical Educa+ product year when provided in metadata', () => {
    expect(formatTreasuryName('TESOURO-EDUCA-MAIS-15122030', 'Tesouro Educa+ 2026')).toBe(
      'Tesouro Educa+ 2026',
    )
  })
})
