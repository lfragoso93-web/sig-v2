import { useState } from 'react'
import { useTransactions } from '@/hooks/useTransactions'
import { formatCurrency, formatDate, formatQuantity } from '@/utils/format'

export default function TransacoesPage() {
  const [page] = useState(1)
  const { data, isLoading } = useTransactions({ page })

  const transactions = data?.items ?? []

  return (
    <div className="p-6 space-y-4">
      <h1 className="text-xl font-bold text-white">Transações</h1>

      {isLoading && (
        <div className="text-gray-400 text-sm">Carregando...</div>
      )}

      <div className="overflow-x-auto">
        <table className="w-full text-sm text-gray-300">
          <thead>
            <tr className="text-gray-500 border-b border-gray-800">
              <th className="text-left py-2">Data</th>
              <th className="text-left py-2">Ticker</th>
              <th className="text-left py-2">Tipo</th>
              <th className="text-right py-2">Qtd</th>
              <th className="text-right py-2">Preço</th>
              <th className="text-right py-2">Total</th>
            </tr>
          </thead>
          <tbody>
            {transactions.map((tx: {
              id: number
              transaction_date: string
              ticker: string
              transaction_type: string
              quantity: number
              price: number
            }) => (
              <tr key={tx.id} className="border-b border-gray-800/50 hover:bg-gray-800/30">
                <td className="py-2">{formatDate(tx.transaction_date)}</td>
                <td className="py-2 font-mono font-semibold">{tx.ticker}</td>
                <td className="py-2">
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                    tx.transaction_type === 'buy' ? 'bg-green-900/40 text-green-400' : 'bg-red-900/40 text-red-400'
                  }`}>
                    {tx.transaction_type === 'buy' ? 'Compra' : 'Venda'}
                  </span>
                </td>
                <td className="py-2 text-right tabular-nums">{formatQuantity(tx.quantity)}</td>
                <td className="py-2 text-right tabular-nums">{formatCurrency(tx.price)}</td>
                <td className="py-2 text-right tabular-nums">{formatCurrency(tx.quantity * tx.price)}</td>
              </tr>
            ))}
            {!isLoading && transactions.length === 0 && (
              <tr>
                <td colSpan={6} className="py-8 text-center text-gray-500">Nenhuma transação encontrada.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
