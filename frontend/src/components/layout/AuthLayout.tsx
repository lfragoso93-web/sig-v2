import { Outlet, Navigate } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'

function SigLogoLarge() {
  return (
    <svg viewBox="0 0 48 48" fill="none" aria-label="SIG v2" className="w-12 h-12">
      <rect width="48" height="48" rx="13" fill="var(--color-primary)" />
      <polyline
        points="8,34 19,21 26,27 40,13"
        stroke="white"
        strokeWidth="3.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        fill="none"
      />
      <circle cx="40" cy="13" r="3" fill="white" />
    </svg>
  )
}

export default function AuthLayout() {
  const token = useAuthStore((s) => s.token)
  if (token) return <Navigate to="/carteira" replace />

  return (
    <div
      className="flex flex-col items-center justify-center px-4 py-10"
      style={{
        minHeight: '100dvh',
        background: 'var(--color-bg)',
      }}
    >
      <div className="w-full max-w-sm">
        {/* Header */}
        <div className="flex flex-col items-center gap-3 mb-8">
          <SigLogoLarge />
          <div className="text-center">
            <h1 className="text-xl font-bold" style={{ color: 'var(--color-text)' }}>SIG v2</h1>
            <p className="text-sm" style={{ color: 'var(--color-text-muted)' }}>Sistema de Gestão de Investimentos</p>
          </div>
        </div>

        {/* Card */}
        <div
          className="rounded-xl shadow-md"
          style={{
            background: 'var(--color-surface)',
            border: '1px solid var(--color-border)',
            padding: 'clamp(1.5rem, 5vw, 2rem)',
          }}
        >
          <Outlet />
        </div>
      </div>
    </div>
  )
}
