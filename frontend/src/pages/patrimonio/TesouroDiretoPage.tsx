import { useTreasury, TreasuryItem } from '../../hooks/useTreasury'
import { useAppStore } from '../../store/appStore'

// ── helpers ────────────────────────────────────────────────────────────────
const fmtBRL = (v: number | null | undefined) =>
  v == null ? '—' : v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })

const fmtDate = (s: string | null | undefined) => {
  if (!s) return '—'
  const [y, m, d] = s.split('-')
  return `${d}/${m}/${y}`
}

// ── TesouroDiretoPage ────────────────────────────────────────────────────────
export default function TesouroDiretoPage() {
  const portfolioId        = useAppStore((s) => s.selectedPortfolioId)
  const openTransactionModal = useAppStore((s) => s.openTransactionModal)
  const { items, loading, error } = useTreasury()

  if (!portfolioId) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-gray-400">
        <p className="text-base">Selecione uma carteira para ver o Tesouro Direto.</p>
      </div>
    )
  }

  // Abre o AddTransactionModal global já existente, pré-preenchido com os dados do título
  const handleEdit = (item: TreasuryItem) => {
    const canonicalTicker = item.brapi_symbol || item.ticker || item.brapi_name
    openTransactionModal({
      tab:       'tesouro',
      ticker:    canonicalTicker,
      assetName: item.brapi_name,
      treasurySlug: canonicalTicker,
    })
  }

  return (
    <div className="p-4 md:p-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-bold text-gray-800 dark:text-white">Tesouro Direto</h1>
      </div>

      {loading && (
        <div className="flex justify-center py-12">
          <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
        </div>
      )}

      {!loading && error && (
        <div className="bg-red-50 border border-red-200 text-red-600 rounded-lg px-4 py-3 text-sm">{error}</div>
      )}

      {!loading && !error && items.length === 0 && (
        <div className="flex flex-col items-center justify-center h-48 text-gray-400">
          <p>Nenhum investimento em Tesouro Direto cadastrado.</p>
          <p className="text-sm mt-1">
            Utilize o botão <strong>+ Novo Lançamento</strong> do topo da aplicação para adicionar.</p>
        </div>
      )}

      {!loading && items.length > 0 && (
        <div className="overflow-x-auto rounded-xl border border-gray-200 dark:border-gray-700">
          <table className="min-w-full text-sm">
            <thead className="bg-gray-50 dark:bg-gray-800 text-gray-500 dark:text-gray-400 uppercase text-xs">
              <tr>
                <th className="px-4 py-3 text-left">Título</th>
                <th className="px-4 py-3 text-right">Valor Investido</th>
                <th className="px-4 py-3 text-right">Preço Atual</th>
                <th className="px-4 py-3 text-center hidden md:table-cell">Compra</th>
                <th className="px-4 py-3 text-center hidden md:table-cell">Vencimento</th>
                <th className="px-4 py-3 text-center">Status</th>
                <th className="px-4 py-3 text-center">Ações</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-700 bg-white dark:bg-gray-900">
              {items.map((item) => (
                <tr key={item.id} className="hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
                  <td className="px-4 py-3 font-medium text-gray-800 dark:text-white max-w-[200px] truncate">
                    {item.brapi_name}
                  </td>
                  <td className="px-4 py-3 text-right text-gray-700 dark:text-gray-300">
                    {fmtBRL(item.invested_value)}
                  </td>
                  <td className="px-4 py-3 text-right text-gray-700 dark:text-gray-300">
                    {fmtBRL(item.current_price)}
                  </td>
                  <td className="px-4 py-3 text-center text-gray-500 hidden md:table-cell">
                    {fmtDate(item.purchase_date)}
                  </td>
                  <td className="px-4 py-3 text-center text-gray-500 hidden md:table-cell">
                    {fmtDate(item.maturity_date)}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      item.is_active
                        ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                        : 'bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400'
                    }`}>
                      {item.is_active ? 'Ativo' : 'Encerrado'}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <div className="flex items-center justify-center gap-2">
                      {/* Lápis: abre AddTransactionModal já na aba Tesouro pré-preenchido */}
                      <button
                        onClick={() => handleEdit(item)}
                        title="Adicionar novo lançamento para este título"
                        className="text-blue-500 hover:text-blue-700 p-1 rounded hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors"
                      >
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                            d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                        </svg>
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

    </div>
  )
}
