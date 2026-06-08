import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from '@/contexts/AuthContext'
import { ThemeProvider } from '@/contexts/ThemeContext'
import ProtectedRoute from '@/components/ProtectedRoute'
import AppLayout from '@/layouts/AppLayout'
import LoginPage from '@/pages/auth/LoginPage'
import RegisterPage from '@/pages/auth/RegisterPage'
import ResumePage from '@/pages/ResumePage'
import ProventosPage from '@/pages/ProventosPage'
import PatrimonioPage from '@/pages/PatrimonioPage'
import RentabilidadePage from '@/pages/RentabilidadePage'
import MetasPage from '@/pages/MetasPage'
import AnalisePage from '@/pages/AnalisePage'
import LancamentosPage from '@/pages/LancamentosPage'
import IRPFPage from '@/pages/IRPFPage'

export default function App() {
  return (
    <ThemeProvider>
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            {/* Public */}
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />

            {/* Protected */}
            <Route element={<ProtectedRoute />}>
              <Route element={<AppLayout />}>
                <Route path="/" element={<Navigate to="/resumo" replace />} />
                <Route path="/resumo" element={<ResumePage />} />
                <Route path="/proventos" element={<ProventosPage />} />
                <Route path="/patrimonio" element={<PatrimonioPage />} />
                <Route path="/rentabilidade" element={<RentabilidadePage />} />
                <Route path="/metas" element={<MetasPage />} />
                <Route path="/analise" element={<AnalisePage />} />
                <Route path="/lancamentos" element={<LancamentosPage />} />
                <Route path="/irpf" element={<IRPFPage />} />
              </Route>
            </Route>

            <Route path="*" element={<Navigate to="/resumo" replace />} />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </ThemeProvider>
  )
}
