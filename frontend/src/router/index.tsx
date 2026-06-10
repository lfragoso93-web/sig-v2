import { createBrowserRouter, Navigate } from 'react-router-dom'
import AppLayout    from '@/components/layout/AppLayout'
import AuthLayout   from '@/components/layout/AuthLayout'
import ProtectedRoute from './ProtectedRoute'

// Pages
import Landing          from '@/pages/Landing'
import Login            from '@/pages/Login'
import Register         from '@/pages/Register'
import EsqueceuSenha    from '@/pages/EsqueceuSenha'
import ResumePage       from '@/pages/ResumePage'
import RentabilidadePage from '@/pages/RentabilidadePage'
import Transacoes        from '@/pages/Transacoes'
import Configuracoes     from '@/pages/Configuracoes'

// Lazy stubs — ainda não implementados
import ProventosPage    from '@/pages/ProventosPage'

export const router = createBrowserRouter([
  // Landing pública
  { path: '/', element: <Landing /> },

  // Auth
  {
    path: '/auth',
    element: <AuthLayout />,
    children: [
      { index: true,              element: <Navigate to="login" replace /> },
      { path: 'login',            element: <Login /> },
      { path: 'registro',         element: <Register /> },
      { path: 'esqueceu-senha',   element: <EsqueceuSenha /> },
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
      { index: true,                    element: <ResumePage /> },
      { path: 'rentabilidade',          element: <RentabilidadePage /> },
      { path: 'transacoes',             element: <Transacoes /> },
      { path: 'proventos',              element: <ProventosPage /> },
      { path: 'configuracoes',          element: <Configuracoes /> },
    ],
  },

  // Catch-all → landing
  { path: '*', element: <Navigate to="/" replace /> },
])
