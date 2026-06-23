import React from 'react'
import ReactDOM from 'react-dom/client'
import { createBrowserRouter, RouterProvider, Navigate, Outlet } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ThemeProvider } from '@/contexts/ThemeContext'
import { AuthProvider } from '@/contexts/AuthContext'
import '@/index.css'

// Layouts
import AppLayout  from '@/components/layout/AppLayout'
import AuthLayout from '@/components/layout/AuthLayout'
import ProtectedRoute from '@/router/ProtectedRoute'

// Pages auth
import LoginPage    from '@/pages/auth/LoginPage'
import RegisterPage from '@/pages/auth/RegisterPage'
import EsqueceuSenha from '@/pages/EsqueceuSenha'

// Pages app
import Landing           from '@/pages/Landing'
import ResumePage        from '@/pages/ResumePage'
import RentabilidadePage from '@/pages/RentabilidadePage'
import Transacoes        from '@/pages/Transacoes'
import Configuracoes     from '@/pages/Configuracoes'
import ProventosPage     from '@/pages/ProventosPage'
import IRPFPage          from '@/pages/IRPFPage'
import WelcomePage       from '@/pages/WelcomePage'

// Patrimônio
import PatrimonioPage    from '@/pages/patrimonio/PatrimonioPage'
import RendaVariavelPage from '@/pages/patrimonio/RendaVariavelPage'
import TesouroDiretoPage from '@/pages/patrimonio/TesouroDiretoPage'
import RendaFixaPage     from '@/pages/patrimonio/RendaFixaPage'

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
          { path: 'esqueceu-senha', element: <EsqueceuSenha /> },
        ],
      },

      // Atalhos legados
      { path: '/login',    element: <Navigate to="/auth/login"    replace /> },
      { path: '/register', element: <Navigate to="/auth/registro" replace /> },

      // Welcome — onboarding (protegido, fora do AppLayout)
      {
        path: '/welcome',
        element: <ProtectedRoute><WelcomePage /></ProtectedRoute>,
      },

      // App protegido
      {
        path: '/carteira',
        element: <ProtectedRoute><AppLayout /></ProtectedRoute>,
        children: [
          { index: true,           element: <ResumePage /> },
          { path: 'rentabilidade', element: <RentabilidadePage /> },
          { path: 'transacoes',    element: <Transacoes /> },
          { path: 'proventos',     element: <ProventosPage /> },
          { path: 'irpf',          element: <IRPFPage /> },
          { path: 'configuracoes', element: <Configuracoes /> },
          {
            path: 'patrimonio',
            element: <PatrimonioPage />,
            children: [
              { index: true,            element: <Navigate to="renda-variavel" replace /> },
              { path: 'renda-variavel', element: <RendaVariavelPage /> },
              { path: 'tesouro',        element: <TesouroDiretoPage /> },
              { path: 'renda-fixa',     element: <RendaFixaPage /> },
            ],
          },
        ],
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
