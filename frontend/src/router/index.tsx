import { createBrowserRouter, Navigate } from 'react-router-dom'
import { ThemeProvider } from '@/contexts/ThemeContext'
import { AuthProvider } from '@/contexts/AuthContext'
import AppLayout     from '@/components/layout/AppLayout'
import AuthLayout    from '@/components/layout/AuthLayout'
import ProtectedRoute from './ProtectedRoute'

// Pages de autenticação
import LoginPage    from '@/pages/auth/LoginPage'
import RegisterPage from '@/pages/auth/RegisterPage'
import EsqueceuSenha from '@/pages/EsqueceuSenha'

// Pages do app
import Landing           from '@/pages/Landing'
import ResumePage        from '@/pages/ResumePage'
import RentabilidadePage from '@/pages/RentabilidadePage'
import Transacoes        from '@/pages/Transacoes'
import Configuracoes     from '@/pages/Configuracoes'
import ProventosPage     from '@/pages/ProventosPage'
import IRPFPage          from '@/pages/IRPFPage'

// Patrimônio
import PatrimonioPage    from '@/pages/patrimonio/PatrimonioPage'
import RendaVariavelPage from '@/pages/patrimonio/RendaVariavelPage'
import TesouroDiretoPage from '@/pages/patrimonio/TesouroDiretoPage'
import RendaFixaPage     from '@/pages/patrimonio/RendaFixaPage'

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
    // Componente raiz que envolve tudo com providers
    element: <Root><AppLayout /></Root>,
    // Rotas filhas SEM AppLayout — auth
    children: [
      // Precisamos de uma estrutura flat; usamos dois níveis
    ]
  },
])

// Router correto com layout separado para auth e app
export const routerV2 = createBrowserRouter([
  {
    path: '/',
    element: (
      <ThemeProvider>
        <AuthProvider>
          {/* Outlet é renderizado pelos filhos */}
          <Landing />
        </AuthProvider>
      </ThemeProvider>
    ),
  },
  // Catch-all
  { path: '*', element: <Navigate to="/" replace /> },
])
