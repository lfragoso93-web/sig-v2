export default function SkeletonCard() {
  return (
    <div className="rounded-xl bg-surface-900 border border-surface-700 p-4 flex flex-col gap-2 animate-pulse">
      <div className="h-3 w-20 bg-surface-700 rounded" />
      <div className="h-7 w-28 bg-surface-700 rounded" />
      <div className="h-3 w-14 bg-surface-700 rounded" />
    </div>
  )
}
