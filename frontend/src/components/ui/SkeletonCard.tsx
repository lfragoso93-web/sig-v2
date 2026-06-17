export default function SkeletonCard() {
  return (
    <div
      className="rounded-xl p-4 flex flex-col gap-2 animate-pulse"
      style={{
        background: 'var(--color-surface)',
        border: '1px solid var(--color-border)',
      }}
    >
      <div className="h-3 w-20 rounded skeleton" />
      <div className="h-7 w-32 rounded skeleton" />
      <div className="h-3 w-16 rounded skeleton" />
      <div className="h-3 w-24 rounded skeleton" />
    </div>
  )
}
