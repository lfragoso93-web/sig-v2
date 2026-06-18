import { createBrowserRouter, Navigate } from 'react-router-dom'
import AppLayout    from '@/components/layout/AppLayout'
import AuthLayout   from '@/components/layout/AuthLayout'
import ProtectedRoute from './ProtectedRoute'

// Pages de autenticação (corretas)
import LoginPage    from '@/pages/auth/LoginPage'
import RegisterPage from '@/pages/auth/RegisterPage'
import EsqueceuSenha from '@/pages/EsqueceuSenha'

// Pages do app
import ResumePage        from '@/pages/ResumePage'
import RentabilidadePage from '@/pages/RentabilidadePage'
import Transacoes        from '@/pages/Transacoes'
import Configuracoes     from '@/pages/Configuracoes'
import ProventosPage     from '@/pages/ProventosPage'
import IRPFPage          from '@/pages/IRPFPage'
import Landing           from '@/pages/Landing'

// Patrimônio
import PatrimonioPage    from '@/pages/patrimonio/PatrimonioPage'
import RendaVariavelPage from '@/pages/patrimonio/RendaVariavelPage'
import TesouroDiretoPage from '@/pages/patrimonio/TesouroDiretoPage'
import RendaFixaPage     from '@/pages/patrimonio/RendaFixaPage'

export const router = createBrowserRouter([
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

      // Módulo Patrimônio
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

  // Catch-all → landing
  { path: '*', element: <Navigate to="/" replace /> },
])
