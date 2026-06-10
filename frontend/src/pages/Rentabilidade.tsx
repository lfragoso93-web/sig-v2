// DEPRECATED — substituída por RentabilidadePage.tsx
// Topbar agora aponta /carteira/rentabilidade → RentabilidadePage
import { Navigate } from 'react-router-dom'
export default function Rentabilidade() {
  return <Navigate to="/carteira/rentabilidade" replace />
}
