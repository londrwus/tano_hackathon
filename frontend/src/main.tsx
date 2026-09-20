import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'

import App from './App'
// Self-hosted, NOT a Google Fonts link. The venue wifi is not something we are
// willing to bet the typeface on, and the approved Pen mockups are all set in Inter.
import '@fontsource-variable/inter'
import './styles/tokens.css'
import './index.css'

createRoot(document.getElementById('root') as HTMLElement).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>,
)
