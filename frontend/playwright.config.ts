import { defineConfig, devices } from '@playwright/test'

const baseURL = 'http://127.0.0.1:3139'

export default defineConfig({
  testDir: './e2e',
  // Keep browser tests separate from Vitest's colocated *.test / *.spec files.
  testMatch: '**/*.e2e.ts',
  fullyParallel: true,
  workers: 2,
  outputDir: './playwright-results',
  forbidOnly: !!process.env.CI,
  reporter: 'list',
  use: {
    ...devices['Desktop Chrome'],
    channel: 'chromium',
    baseURL,
    locale: 'en-US',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  webServer: {
    command: 'node e2e/server.mjs',
    url: `${baseURL}/config`,
    reuseExistingServer: false,
    env: { API_URL: baseURL, PORT: '3139', HOSTNAME: '127.0.0.1', NEXT_TELEMETRY_DISABLED: '1' },
  },
})
