import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ThemeProvider } from 'hg_ui_kit'
import 'hg_ui_kit/tokens.css'
import 'hg_ui_kit/components.css'
import App from './app.jsx'
import './styles.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 30_000, retry: 1 },
  },
})

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <ThemeProvider defaultMode="dark" defaultDensity="comfortable">
        <App />
      </ThemeProvider>
    </QueryClientProvider>
  </React.StrictMode>
)


