import React from 'react'
import ReactDOM from 'react-dom/client'
import { RouterProvider } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { router } from '@/router'
import '@/styles/tokens.css'
import '@/styles/base.css'
import '@/styles/components.css'
import '@/index.css'

// Aplica o tema salvo ANTES do primeiro render para evitar flash branco
;(function applyTheme() {
  try {
    const stored = JSON.parse(localStorage.getItem('sig-app') ?? '{}')
    const theme = stored?.state?.theme ?? 'dark'
    document.documentElement.setAttribute('data-theme', theme)
  } catch {
    document.documentElement.setAttribute('data-theme', 'dark')
  }
})()

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 2, // 2 min
      retry: 1,
    },
  },
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  </React.StrictMode>,
)
