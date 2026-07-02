/// <reference types="vitest/config" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Served from https://<user>.github.io/building-code-verifier-app/
export default defineConfig({
  base: '/building-code-verifier-app/',
  plugins: [react()],
  test: {
    environment: 'node',
  },
})
