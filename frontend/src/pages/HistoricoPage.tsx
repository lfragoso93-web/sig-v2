import { Navigate } from 'react-router-dom'

// Historico foi absorvido pela aba Historico dentro de PatrimonioPage.
export default function HistoricoPage() {
  return <Navigate to="/carteira/patrimonio" replace />
}
