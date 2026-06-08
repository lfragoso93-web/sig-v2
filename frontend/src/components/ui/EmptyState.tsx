import { LucideIcon } from 'lucide-react'

interface EmptyStateProps {
  icon: LucideIcon
  title: string
  description?: string
  action?: { label: string; onClick: () => void }
}

export default function EmptyState({ icon: Icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-8 text-center">
      <Icon size={40} className="text-gray-300 dark:text-dark-400 mb-4" strokeWidth={1.5} />
      <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-1">{title}</h3>
      {description && <p className="text-xs text-muted max-w-xs">{description}</p>}
      {action && (
        <button onClick={action.onClick} className="btn-primary mt-4 text-xs">
          {action.label}
        </button>
      )}
    </div>
  )
}
