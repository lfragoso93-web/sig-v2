import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { transactionService, TransactionCreate } from '@/services/transactionService'
import toast from 'react-hot-toast'

export function useTransactionList(
  portfolioId: number,
  params?: { ticker?: string; asset_type?: string; tx_type?: string; year?: number }
) {
  return useQuery({
    queryKey: ['transactions', portfolioId, params],
    queryFn: () => transactionService.list(portfolioId, params),
    enabled: !!portfolioId,
  })
}

export function useCreateTransaction(portfolioId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: TransactionCreate) => transactionService.create(portfolioId, data),
    onSuccess: (tx) => {
      qc.invalidateQueries({ queryKey: ['transactions', portfolioId] })
      qc.invalidateQueries({ queryKey: ['portfolio-summary', portfolioId] })
      qc.invalidateQueries({ queryKey: ['portfolio-positions', portfolioId] })
      toast.success(
        `${tx.transaction_type === 'COMPRA' ? 'Compra' : 'Venda'} de ${tx.ticker} registrada!`
      )
    },
    onError: () => toast.error('Erro ao registrar transação'),
  })
}

export function useDeleteTransaction(portfolioId: number) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (txId: number) => transactionService.delete(txId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['transactions', portfolioId] })
      qc.invalidateQueries({ queryKey: ['portfolio-summary', portfolioId] })
      qc.invalidateQueries({ queryKey: ['portfolio-positions', portfolioId] })
      toast.success('Transação removida')
    },
    onError: () => toast.error('Erro ao remover transação'),
  })
}
