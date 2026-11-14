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

  it('ignores the generic BRAPI placeholder logo and shows the class icon instead', () => {
    render(
      <AssetLogo ticker="MXRF11" assetType="FII" logoUrl="https://icons.brapi.dev/icons/BRAPI.svg" />,
    )
    expect(screen.queryByRole('img')).toBeNull()
    expect(screen.getByTestId('asset-logo-class-FII')).toBeTruthy()
  })

  it.each(['DOGE', 'DOT', 'AVAX', 'POL', 'LTC', 'ADA'])(
    'renders dedicated icon for crypto %s',
    (ticker) => {
      render(<AssetLogo ticker={ticker} assetType="CRIPTO" />)
      expect(screen.getByTestId(`asset-logo-crypto-${ticker}`)).toBeTruthy()
    },
  )

  it('does not treat a non-crypto asset with a crypto-like ticker as crypto', () => {
    render(<AssetLogo ticker="BTC" assetType="ACAO" />)
    expect(screen.getByTestId('asset-logo-class-ACAO')).toBeTruthy()
  })

  it.each([
    ['POMO4', 'ACAO', 'https://icons.brapi.dev/icons/POMO4.svg'],
    ['PETR4', 'ACAO', 'https://icons.brapi.dev/icons/PETR4.svg'],
    ['VALE3', 'ACAO', 'https://icons.brapi.dev/icons/VALE3.svg'],
    ['AAPL34', 'BDR', 'https://icons.brapi.dev/icons/AAPL34.svg'],
    ['NVDC34', 'BDR', 'https://icons.brapi.dev/icons/NVDC34.svg'],
    ['NVDA', 'STOCK', 'https://icons.brapi.dev/icons/NVDC34.svg'],
    ['AAPL', 'STOCK', 'https://icons.brapi.dev/icons/AAPL.svg'],
  ])('derives company logo for %s (%s) when logoUrl is not passed and falls back to icon on error', (ticker, assetType, expectedUrl) => {
    render(<AssetLogo ticker={ticker} assetType={assetType} />)
    const img = screen.getByRole('img', { name: ticker }) as HTMLImageElement
    expect(img.getAttribute('src')).toBe(expectedUrl)

    fireEvent.error(img)
    expect(screen.queryByRole('img')).toBeNull()
    expect(screen.getByTestId(`asset-logo-class-${assetType}`)).toBeTruthy()
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
