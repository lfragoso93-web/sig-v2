import { createBrowserRouter, Navigate } from 'react-router-dom'
import AppLayout from '@/components/layout/AppLayout'
import AuthLayout from '@/components/layout/AuthLayout'
import Login from '@/pages/Login'
import Register from '@/pages/Register'
import Resumo from '@/pages/Resumo'
import Rentabilidade from '@/pages/Rentabilidade'
import Transacoes from '@/pages/Transacoes'
import Proventos from '@/pages/Proventos'
import ProtectedRoute from './ProtectedRoute'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <Navigate to="/carteira" replace />,
  },
  {
    path: '/auth',
    element: <AuthLayout />,
    children: [
      { index: true, element: <Navigate to="login" replace /> },
      { path: 'login',   element: <Login /> },
      { path: 'registro', element: <Register /> },
    ],
  },
  {
    path: '/carteira',
    element: <ProtectedRoute><AppLayout /></ProtectedRoute>,
    children: [
      { index: true, element: <Resumo /> },
      {
        path: ':portfolioId',
        children: [
          { index: true,             element: <Resumo /> },
          { path: 'rentabilidade',   element: <Rentabilidade /> },
          { path: 'transacoes',      element: <Transacoes /> },
          { path: 'proventos',       element: <Proventos /> },
        ],
      },
    ],
  },
])
