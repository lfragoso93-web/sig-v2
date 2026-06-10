import type { LucideIcon } from 'lucide-react'

interface Props {
  icon: LucideIcon
  title: string
  description: string
}

export default function EmptyState({ icon: Icon, title, description }: Props) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-6 text-center gap-3">
      <div className="w-12 h-12 rounded-xl bg-brand-600/10 flex items-center justify-center">
        <Icon size={22} className="text-brand-500" />
      </div>
      <div>
        <p className="text-sm font-semibold text-slate-200">{title}</p>
        <p className="text-xs text-slate-500 mt-1 max-w-xs">{description}</p>
      </div>
    </div>
  )
}
