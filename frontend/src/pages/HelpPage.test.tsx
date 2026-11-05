import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import HelpPage from './HelpPage'

const mocks = vi.hoisted(() => ({ post: vi.fn() }))

vi.mock('@/services/api', () => ({ default: { post: mocks.post } }))

describe('HelpPage', () => {
  beforeEach(() => vi.clearAllMocks())

  it('mostra respostas e atalhos para as páginas principais', () => {
    render(<MemoryRouter><HelpPage /></MemoryRouter>)

    expect(screen.getByRole('heading', { name: 'Como podemos ajudar?' })).toBeTruthy()
    expect(screen.getByRole('link', { name: 'Rentabilidade', exact: true })).toBeTruthy()
    expect(screen.getByText('O que significa TWR?')).toBeTruthy()
  })

  it('filtra perguntas sem diferenciar acentos e apresenta o estado vazio', () => {
    render(<MemoryRouter><HelpPage /></MemoryRouter>)
    const search = screen.getByRole('searchbox', { name: 'Buscar na ajuda' })

    fireEvent.change(search, { target: { value: 'autenticacao multifator' } })
    expect(screen.getByText('Como funciona a autenticação de dois fatores?')).toBeTruthy()
    expect(screen.queryByText('O que significa TWR?')).toBeNull()

    fireEvent.change(search, { target: { value: 'termo inexistente' } })
    expect(screen.getByText('Não encontramos essa resposta')).toBeTruthy()
  })

  it('filtra por categoria e permite abrir a resposta correspondente', () => {
    render(<MemoryRouter><HelpPage /></MemoryRouter>)

    fireEvent.click(screen.getByRole('button', { name: 'Rentabilidade' }))
    expect(screen.getByText('Como o sistema calcula “No Ano” na matriz?')).toBeTruthy()
    expect(screen.queryByText('Como funcionam os proventos?')).toBeNull()

    fireEvent.click(screen.getByText('Como o sistema calcula “No Ano” na matriz?'))
    expect(screen.getByText(/compõe os retornos mensais do ano-calendário/)).toBeTruthy()
  })

  it('envia a pergunta ao assistente e apresenta as fontes retornadas', async () => {
    mocks.post.mockResolvedValue({
      data: {
        answer: 'Encontrei estes trechos na documentação do sistema.',
        sources: [{ document: 'Rentabilidade', section: 'Composição', excerpt: 'Os retornos são compostos.' }],
        suggested_routes: [{ label: 'Rentabilidade', path: '/carteira/rentabilidade' }],
        mode: 'llm',
      },
    })
    render(<MemoryRouter><HelpPage /></MemoryRouter>)

    fireEvent.change(screen.getByRole('textbox', { name: 'Pergunta sobre a documentação' }), {
      target: { value: 'Como é calculado o TWR?' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Perguntar' }))

    await waitFor(() => expect(mocks.post).toHaveBeenCalledWith('/help/ask', { question: 'Como é calculado o TWR?' }))
    expect(await screen.findByText('Os retornos são compostos.')).toBeTruthy()
    expect(screen.getByText('Rentabilidade · Composição')).toBeTruthy()
    expect(screen.getByText('Resposta sintetizada por IA (Grounded)')).toBeTruthy()
    expect(screen.getAllByRole('link', { name: 'Rentabilidade' }).length).toBeGreaterThanOrEqual(2)
  })

  it('permite clicar em pergunta sugerida e preencher busca por tópicos rápidos', async () => {
    mocks.post.mockResolvedValue({
      data: {
        answer: 'O TWR composto reflete a multiplicação dos fatores periódicos.',
        sources: [],
      },
    })
    render(<MemoryRouter><HelpPage /></MemoryRouter>)

    // Click starter question button
    const starterBtn = screen.getByRole('button', { name: 'Como é calculado o TWR acumulado?' })
    fireEvent.click(starterBtn)

    await waitFor(() =>
      expect(mocks.post).toHaveBeenCalledWith('/help/ask', {
        question: 'Como é calculado o TWR acumulado?',
      })
    )

    // Click quick pill
    fireEvent.click(screen.getByRole('button', { name: 'Snapshot 21h' }))
    const search = screen.getByRole('searchbox', { name: 'Buscar na ajuda' }) as HTMLInputElement
    expect(search.value).toBe('Snapshot 21h')
  })
})
