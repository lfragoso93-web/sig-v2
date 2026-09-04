import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import ImportCSVModal from './ImportCSVModal'

const mocks = vi.hoisted(() => ({
  post: vi.fn(),
  invalidateQueries: vi.fn(),
}))

vi.mock('@/services/api', () => ({
  default: {
    post: mocks.post,
    get: vi.fn(),
  },
}))

vi.mock('@tanstack/react-query', () => ({
  useQueryClient: () => ({ invalidateQueries: mocks.invalidateQueries }),
}))

const CSV = [
  'ticker,asset_type,operation,quantity,price,date,fees,currency,notes',
  'PETR4,ACAO,buy,10,30.00,2024-01-10,0,BRL,teste',
].join('\n')

function selectCsv(container: HTMLElement) {
  const file = new File([CSV], 'synthetic.csv', { type: 'text/csv' })
  Object.defineProperty(file, 'text', {
    value: vi.fn().mockResolvedValue(CSV),
  })
  const input = container.querySelector<HTMLInputElement>('#file-input')
  if (!input) throw new Error('file input not found')
  fireEvent.change(input, { target: { files: [file] } })
}

describe('ImportCSVModal behavior', () => {
  beforeEach(() => {
    mocks.post.mockReset()
    mocks.invalidateQueries.mockReset()
  })

  it('blocks real import when dry-run returns warnings', async () => {
    mocks.post.mockResolvedValueOnce({
      data: {
        success: false,
        imported_count: 0,
        skipped_count: 1,
        error_count: 0,
        global_errors: [],
        rows: [
          {
            row_num: 2,
            errors: [],
            warnings: ['duplicate transaction skipped'],
            status: 'warning',
            ticker: 'PETR4',
            operation: 'buy',
          },
        ],
      },
    })

    const { container } = render(
      <ImportCSVModal portfolioId={5} onClose={vi.fn()} onSuccess={vi.fn()} />,
    )

    selectCsv(container)

    const confirm = await screen.findByRole('button', { name: 'Confirmar importação' })
    expect((confirm as HTMLButtonElement).disabled).toBe(true)
    expect(screen.getByText(/Nenhuma linha será importada parcialmente/)).toBeTruthy()
    expect(mocks.post).toHaveBeenCalledTimes(1)
    expect(mocks.post.mock.calls[0][2]).toMatchObject({ params: { dry_run: true } })
  })

  it('blocks real import when dry-run returns errors', async () => {
    const onSuccess = vi.fn()
    mocks.post.mockResolvedValueOnce({
      data: {
        success: false,
        imported_count: 0,
        skipped_count: 0,
        error_count: 1,
        global_errors: ['CSV invalido para importacao sintetica'],
        rows: [
          {
            row_num: 2,
            errors: ['ticker obrigatorio'],
            warnings: [],
            status: 'error',
            operation: 'buy',
          },
        ],
      },
    })

    const { container } = render(
      <ImportCSVModal portfolioId={5} onClose={vi.fn()} onSuccess={onSuccess} />,
    )

    selectCsv(container)

    await screen.findByText('CSV invalido para importacao sintetica')
    const confirm = screen.getByRole('button', { name: /Confirmar/ })
    expect((confirm as HTMLButtonElement).disabled).toBe(true)
    expect(screen.getByText('ticker obrigatorio')).toBeTruthy()
    fireEvent.click(confirm)

    expect(mocks.post).toHaveBeenCalledTimes(1)
    expect(mocks.post.mock.calls[0][2]).toMatchObject({ params: { dry_run: true } })
    expect(onSuccess).not.toHaveBeenCalled()
    expect(mocks.invalidateQueries).not.toHaveBeenCalled()
  })

  it('imports validated CSV and refreshes queries only after persisted rows', async () => {
    const onSuccess = vi.fn()
    mocks.post
      .mockResolvedValueOnce({
        data: {
          success: true,
          imported_count: 0,
          skipped_count: 0,
          error_count: 0,
          global_errors: [],
          rows: [
            {
              row_num: 2,
              errors: [],
              warnings: [],
              status: 'valid',
              ticker: 'PETR4',
              operation: 'buy',
            },
          ],
        },
      })
      .mockResolvedValueOnce({
        data: {
          success: true,
          imported_count: 1,
          skipped_count: 0,
          error_count: 0,
          global_errors: [],
          rows: [
            {
              row_num: 2,
              errors: [],
              warnings: [],
              status: 'imported',
              ticker: 'PETR4',
              operation: 'buy',
            },
          ],
        },
      })

    const { container } = render(
      <ImportCSVModal portfolioId={5} onClose={vi.fn()} onSuccess={onSuccess} />,
    )

    selectCsv(container)

    const confirm = await screen.findByRole('button', { name: 'Confirmar importação' })
    await waitFor(() => expect((confirm as HTMLButtonElement).disabled).toBe(false))
    fireEvent.click(confirm)

    await waitFor(() => expect(mocks.post).toHaveBeenCalledTimes(2))
    expect(mocks.post.mock.calls[0][2]).toMatchObject({ params: { dry_run: true } })
    expect(mocks.post.mock.calls[1][2]).toMatchObject({ params: { dry_run: false } })
    await waitFor(() => expect(onSuccess).toHaveBeenCalledTimes(1))
    expect(mocks.invalidateQueries).toHaveBeenCalledWith({
      queryKey: ['portfolio-summary', 5],
    })
    expect(mocks.invalidateQueries).toHaveBeenCalledWith({
      queryKey: ['positions', 5],
    })
    expect(mocks.invalidateQueries).toHaveBeenCalledWith({
      queryKey: ['rentabilidade-kpis', 5],
    })
  })
})
