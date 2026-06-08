import { X } from 'lucide-react'

interface Props {
  onClose: () => void
}

export default function AddTransactionModal({ onClose }: Props) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />
      {/* Modal */}
      <div className="relative z-10 w-full max-w-lg card p-6 shadow-xl">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-base font-semibold text-gray-900 dark:text-gray-100">
            Adicionar Lançamento
          </h2>
          <button onClick={onClose} className="btn-ghost p-1">
            <X size={18} />
          </button>
        </div>
        {/* Formulário será implementado no bloco de lançamentos */}
        <div className="flex flex-col items-center justify-center py-10 text-muted gap-3">
          <span className="text-sm">Formulário completo no próximo bloco.</span>
        </div>
      </div>
    </div>
  )
}
