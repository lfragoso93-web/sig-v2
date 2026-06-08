export default function SkeletonCard({ className = '' }: { className?: string }) {
  return (
    <div className={`card p-4 animate-pulse ${className}`}>
      <div className="h-3 w-24 bg-gray-200 dark:bg-dark-400 rounded mb-3" />
      <div className="h-7 w-32 bg-gray-200 dark:bg-dark-400 rounded mb-2" />
      <div className="h-3 w-20 bg-gray-200 dark:bg-dark-400 rounded" />
    </div>
  )
}
