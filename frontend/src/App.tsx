import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from '@/contexts/AuthContext'
import { ThemeProvider } from '@/contexts/ThemeContext'
import ProtectedRoute from '@/components/ProtectedRoute'
import AppLayout from '@/components/layout/AppLayout'
import LoginPage from '@/pages/auth/LoginPage'
import RegisterPage from '@/pages/auth/RegisterPage'
import WelcomePage from '@/pages/WelcomePage'
import ResumePage from '@/pages/ResumePage'
import ProventosPage from '@/pages/ProventosPage'
import PatrimonioPage from '@/pages/PatrimonioPage'
import RentabilidadePage from '@/pages/RentabilidadePage'
import MetasPage from '@/pages/MetasPage'
import AnalisePage from '@/pages/AnalisePage'
import LancamentosPage from '@/pages/LancamentosPage'
import IRPFPage from '@/pages/IRPFPage'
import Transacoes from '@/pages/Transacoes'
import Configuracoes from '@/pages/Configuracoes'
import TesouroDiretoPage from '@/pages/patrimonio/TesouroDiretoPage'
import AssetsPage from '@/pages/AssetsPage'

export default function App() {
  return (
    <ThemeProvider>
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            {/* Public */}
            <Route path="/login"    element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />

            {/* Protected */}
            <Route element={<ProtectedRoute />}>

              {/* Welcome / Onboarding — fora do AppLayout (tela cheia) */}
              <Route path="/welcome" element={<WelcomePage />} />

              <Route element={<AppLayout />}>
                {/* Raíz -> /carteira */}
                <Route path="/"        element={<Navigate to="/carteira" replace />} />
                <Route path="/resumo"  element={<Navigate to="/carteira" replace />} />

                {/* Rotas principais */}
                <Route path="/carteira"                    element={<ResumePage />} />
                <Route path="/carteira/transacoes"         element={<Transacoes />} />
                <Route path="/carteira/lancamentos"        element={<LancamentosPage />} />
                <Route path="/carteira/proventos"          element={<ProventosPage />} />
                <Route path="/carteira/rentabilidade"      element={<RentabilidadePage />} />
                <Route path="/carteira/configuracoes"      element={<Configuracoes />} />
                <Route path="/carteira/metas"              element={<MetasPage />} />
                <Route path="/carteira/analise"            element={<AnalisePage />} />
                <Route path="/carteira/irpf"               element={<IRPFPage />} />
                <Route path="/carteira/ativos"             element={<AssetsPage />} />

                {/* Patrimonio e sub-rotas */}
                <Route path="/carteira/patrimonio"         element={<PatrimonioPage />} />
                <Route path="/carteira/patrimonio/tesouro" element={<TesouroDiretoPage />} />
              </Route>
            </Route>

            <Route path="*" element={<Navigate to="/carteira" replace />} />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </ThemeProvider>
  )
}
