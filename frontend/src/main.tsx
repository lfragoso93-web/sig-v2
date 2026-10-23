import React, { Suspense, lazy } from 'react'
import ReactDOM from 'react-dom/client'
import { createBrowserRouter, RouterProvider, Navigate, Outlet } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ThemeProvider } from '@/contexts/ThemeContext'
import { AuthProvider } from '@/contexts/AuthContext'
import '@/index.css'
import '@/styles/entry-fixes.css'

// Layouts
import AppLayout  from '@/components/layout/AppLayout'
import AuthLayout from '@/components/layout/AuthLayout'
import ProtectedRoute, { OnboardingRoute } from '@/router/ProtectedRoute'
import { LEGACY_PORTFOLIO_ROUTE_REDIRECTS } from '@/router/portfolioRoutes'

// Critical-path pages (carregamento imediato)
import LoginPage    from '@/pages/auth/LoginPage'
import RegisterPage from '@/pages/auth/RegisterPage'
import Landing      from '@/pages/Landing'
import ResumePage   from '@/pages/ResumePage'

// Lazy-loaded pages (code splitting por rota para carregamento inicial rápido)
const EsqueceuSenha             = lazy(() => import('@/pages/EsqueceuSenha'))
const GoogleCallbackPage        = lazy(() => import('@/pages/auth/GoogleCallbackPage'))
const RentabilidadePage         = lazy(() => import('@/pages/RentabilidadePage'))
const Transacoes                = lazy(() => import('@/pages/Transacoes'))
const Configuracoes             = lazy(() => import('@/pages/Configuracoes'))
const ProventosPage             = lazy(() => import('@/pages/ProventosPage'))
const IRPFPage                  = lazy(() => import('@/pages/IRPFPage'))
const MetasPage                 = lazy(() => import('@/pages/MetasPage'))
const AnalisePage               = lazy(() => import('@/pages/AnalisePage'))
const IncomeCalculatorPage      = lazy(() => import('@/pages/IncomeCalculatorPage'))
const FixedIncomeCalculatorPage = lazy(() => import('@/pages/FixedIncomeCalculatorPage'))
const WelcomePage               = lazy(() => import('@/pages/WelcomePage'))
const PatrimonioPage            = lazy(() => import('@/pages/PatrimonioPage'))
const RendaVariavelPage         = lazy(() => import('@/pages/patrimonio/RendaVariavelPage'))
const TesouroDiretoPage         = lazy(() => import('@/pages/patrimonio/TesouroDiretoPage'))
const RendaFixaPage             = lazy(() => import('@/pages/patrimonio/RendaFixaPage'))

function RouteSuspense({ children }: { children: React.ReactNode }) {
  return (
    <Suspense
      fallback={
        <div className="page-container">
          <div className="skeleton" style={{ height: 120, borderRadius: 'var(--radius-lg)' }} />
        </div>
      }
    >
      {children}
    </Suspense>
  )
}

// Aplica o tema salvo ANTES do primeiro render para evitar flash
;(function applyTheme() {
  try {
    const stored = JSON.parse(localStorage.getItem('sig-app') ?? '{}')
    const theme = stored?.state?.theme ?? 'dark'
    document.documentElement.setAttribute('data-theme', theme)
  } catch {
    document.documentElement.setAttribute('data-theme', 'dark')
  }
})()

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 1000 * 60 * 2, retry: 1 },
  },
})

/** Wrapper raiz com todos os providers */
function Providers() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <Outlet />
      </AuthProvider>
    </ThemeProvider>
  )
}

const router = createBrowserRouter([
  {
    element: <Providers />,
    children: [
      // Landing pública
      { path: '/', element: <Landing /> },

      // Auth
      {
        path: '/auth',
        element: <AuthLayout />,
        children: [
          { index: true,            element: <Navigate to="login" replace /> },
          { path: 'login',          element: <LoginPage /> },
          { path: 'registro',       element: <RegisterPage /> },
          { path: 'esqueceu-senha', element: <RouteSuspense><EsqueceuSenha /></RouteSuspense> },
          { path: 'redefinir-senha', element: <RouteSuspense><EsqueceuSenha /></RouteSuspense> },
          { path: 'google/callback', element: <RouteSuspense><GoogleCallbackPage /></RouteSuspense> },
        ],
      },

      // Atalhos legados
      { path: '/login',    element: <Navigate to="/auth/login"    replace /> },
      { path: '/register', element: <Navigate to="/auth/registro" replace /> },

      // Welcome — onboarding (protegido, sem verificar onboarding para evitar loop)
      {
        path: '/welcome',
        element: <OnboardingRoute><RouteSuspense><WelcomePage /></RouteSuspense></OnboardingRoute>,
      },

      // App protegido (redireciona para /welcome se onboarding incompleto)
      {
        path: '/carteira',
        element: <ProtectedRoute><AppLayout /></ProtectedRoute>,
        children: [
          { index: true,           element: <ResumePage /> },
          { path: 'rentabilidade', element: <RouteSuspense><RentabilidadePage /></RouteSuspense> },
          { path: 'transacoes',    element: <RouteSuspense><Transacoes /></RouteSuspense> },
          { path: 'proventos',     element: <RouteSuspense><ProventosPage /></RouteSuspense> },
          { path: 'metas',         element: <RouteSuspense><MetasPage /></RouteSuspense> },
          { path: 'analise',       element: <RouteSuspense><AnalisePage /></RouteSuspense> },
          { path: 'ferramentas/rendimentos', element: <RouteSuspense><IncomeCalculatorPage /></RouteSuspense> },
          { path: 'ferramentas/renda-fixa', element: <RouteSuspense><FixedIncomeCalculatorPage /></RouteSuspense> },
          { path: 'irpf',          element: <RouteSuspense><IRPFPage /></RouteSuspense> },
          { path: 'configuracoes', element: <RouteSuspense><Configuracoes /></RouteSuspense> },
          { path: 'patrimonio',                element: <RouteSuspense><PatrimonioPage /></RouteSuspense> },
          { path: 'patrimonio/renda-variavel', element: <RouteSuspense><RendaVariavelPage /></RouteSuspense> },
          { path: 'patrimonio/tesouro',        element: <RouteSuspense><TesouroDiretoPage /></RouteSuspense> },
          { path: 'patrimonio/renda-fixa',     element: <RouteSuspense><RendaFixaPage /></RouteSuspense> },
        ],
      },

      // Compatibilidade com URLs antigas fora do contexto da carteira.
      {
        path: '/metas',
        element: <Navigate to={LEGACY_PORTFOLIO_ROUTE_REDIRECTS['/metas']} replace />,
      },
      {
        path: '/irpf',
        element: <Navigate to={LEGACY_PORTFOLIO_ROUTE_REDIRECTS['/irpf']} replace />,
      },

      // Catch-all
      { path: '*', element: <Navigate to="/" replace /> },
    ],
  },
])

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  </React.StrictMode>,
)
