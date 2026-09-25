import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // The browser only reaches the Vite port; the dev server forwards API calls on this machine.
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
})
