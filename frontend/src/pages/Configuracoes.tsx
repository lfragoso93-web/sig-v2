import { useState } from 'react'
import { usePortfolios, useCreatePortfolio } from '@/hooks/usePortfolios'
import { Trash2, Plus } from 'lucide-react'
import api from '@/services/api'

export default function Configuracoes() {
  const { data: portfolios = [], refetch } = usePortfolios()
  const { mutate: createPortfolio, isPending } = useCreatePortfolio()
  const [newName, setNewName] = useState('')

  const handleCreate = () => {
    if (!newName.trim()) return
    createPortfolio({ name: newName.trim() }, {
      onSuccess: () => { setNewName(''); refetch() },
    })
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Excluir carteira? Esta ação não pode ser desfeita.')) return
    try {
      await api.delete(`/portfolios/${id}`)
      refetch()
    } catch {
      alert('Erro ao excluir carteira.')
    }
  }

  return (
    <div className="p-6 max-w-lg space-y-6">
      <h1 className="text-xl font-bold text-white">Configurações</h1>

      <section className="bg-gray-900 rounded-xl p-4 space-y-3">
        <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wide">Carteiras</h2>

        <ul className="space-y-2">
          {portfolios.map((p: { id: number; name: string }) => (
            <li key={p.id} className="flex items-center justify-between bg-gray-800 rounded-lg px-3 py-2">
              <span className="text-white text-sm">{p.name}</span>
              <button onClick={() => handleDelete(p.id)} className="text-gray-500 hover:text-red-400 transition">
                <Trash2 size={16} />
              </button>
            </li>
          ))}
        </ul>

        <div className="flex gap-2">
          <input
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder="Nome da nova carteira"
            className="flex-1 bg-gray-800 text-white text-sm rounded-lg px-3 py-2 border border-gray-700 focus:outline-none focus:border-teal-500"
            onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
          />
          <button
            onClick={handleCreate}
            disabled={isPending}
            className="bg-teal-600 hover:bg-teal-500 text-white px-3 py-2 rounded-lg transition"
          >
            <Plus size={16} />
          </button>
        </div>
      </section>
    </div>
  )
}
