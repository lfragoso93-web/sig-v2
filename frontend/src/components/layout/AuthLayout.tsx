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
    <div className="min-h-screen flex items-center justify-center bg-bg px-4">
      <div className="w-full max-w-sm">
        {/* Header */}
        <div className="flex flex-col items-center gap-3 mb-8">
          <SigLogoLarge />
          <div className="text-center">
            <h1 className="text-xl font-bold">SIG v2</h1>
            <p className="text-sm text-muted">Sistema de Gestão de Investimentos</p>
          </div>
        </div>

        {/* Card */}
        <div className="bg-surface border border-light-border dark:border-dark-border rounded-xl p-8 shadow-md">
          <Outlet />
        </div>
      </div>
    </div>
  )
}
