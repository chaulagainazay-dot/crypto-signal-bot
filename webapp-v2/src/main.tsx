import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App'

// Force SW update: unregister stale service workers so mobile gets fresh app
const APP_VERSION = '3'
const storedVersion = localStorage.getItem('app_version')
if (storedVersion !== APP_VERSION) {
  localStorage.setItem('app_version', APP_VERSION)
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.getRegistrations().then(regs => {
      regs.forEach(r => r.unregister())
      if (storedVersion !== null) window.location.reload()
    })
  }
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>
)
