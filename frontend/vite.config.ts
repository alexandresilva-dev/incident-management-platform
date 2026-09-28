import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: true, // necessário para o servidor de dev ser acessível a partir do Docker
    port: 5173,
  },
  test: {
    environment: 'node',
  },
})
