// DEPRECATED — esta page foi substituída por ResumePage.tsx
// Mantida apenas para evitar erros de import residuais.
// O App.tsx já redireciona /resumo -> /carteira (ResumePage).
import { Navigate } from 'react-router-dom'
export default function Resumo() {
  return <Navigate to="/carteira" replace />
}
