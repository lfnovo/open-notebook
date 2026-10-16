import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/postcss'
import { playwright } from '@vitest/browser-playwright'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  optimizeDeps: {
    entries: ['src/**/*.browser.test.tsx'],
  },
  resolve: { alias: { '@': path.resolve(__dirname, './src') } },
  css: { postcss: { plugins: [tailwindcss()] } },
  test: {
    globals: true,
    include: ['src/**/*.browser.test.tsx'],
    browser: {
      enabled: true,
      headless: true,
      provider: playwright(),
      instances: [{ browser: 'chromium' }],
    },
  },
})
