import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  publicDir: 'public',
  server: {
    host: '0.0.0.0',
    port: 10000,
    strictPort: true,
    allowedHosts: ['https://taipei-lens.onrender.com', 'localhost']
  }
})
