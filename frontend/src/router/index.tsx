import { createBrowserRouter, Navigate } from 'react-router-dom'
import { ThemeProvider } from '@/contexts/ThemeContext'
import { AuthProvider } from '@/contexts/AuthContext'
import AppLayout      from '@/components/layout/AppLayout'
import _AuthLayout    from '@/components/layout/AuthLayout'
import _ProtectedRoute from './ProtectedRoute'

// Pages de autenticação
import _LoginPage    from '@/pages/auth/LoginPage'
import _RegisterPage from '@/pages/auth/RegisterPage'
import _EsqueceuSenha from '@/pages/EsqueceuSenha'

// Pages do app
import Landing            from '@/pages/Landing'
import _ResumePage        from '@/pages/ResumePage'
import _RentabilidadePage from '@/pages/RentabilidadePage'
import _Transacoes        from '@/pages/Transacoes'
import _Configuracoes     from '@/pages/Configuracoes'
import _ProventosPage     from '@/pages/ProventosPage'
import _IRPFPage          from '@/pages/IRPFPage'

// Patrimônio
import _PatrimonioPage    from '@/pages/patrimonio/PatrimonioPage'
import _RendaVariavelPage from '@/pages/patrimonio/RendaVariavelPage'
import _TesouroDiretoPage from '@/pages/patrimonio/TesouroDiretoPage'
import _RendaFixaPage     from '@/pages/patrimonio/RendaFixaPage'

/** Wrapper raiz: injeta ThemeProvider e AuthProvider em toda a árvore */
function Root({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider>
      <AuthProvider>{children}</AuthProvider>
    </ThemeProvider>
  )
}

export const router = createBrowserRouter([
  {
    element: <Root><AppLayout /></Root>,
    children: []
  },
])

export const routerV2 = createBrowserRouter([
  {
    path: '/',
    element: (
      <ThemeProvider>
        <AuthProvider>
          <Landing />
        </AuthProvider>
      </ThemeProvider>
    ),
  },
  { path: '*', element: <Navigate to="/" replace /> },
])
