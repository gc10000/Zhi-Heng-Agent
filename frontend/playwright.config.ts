import { defineConfig } from '@playwright/test'
export default defineConfig({
  testDir: './tests/e2e', fullyParallel: false, workers: 1, timeout: 45000,
  testIgnore: process.env.M3_LIVE_CONFIG ? [] : ['**/auth-client.spec.ts', '**/support-flow.spec.ts'],
  expect: { timeout: 10000 }, reporter: [['list'], ['json', { outputFile: 'test-results/results.json' }]],
  use: { baseURL: 'http://127.0.0.1:5173', browserName: 'chromium', channel: 'msedge', viewport: { width: 1500, height: 960 }, screenshot: 'only-on-failure', trace: 'retain-on-failure' },
  webServer: process.env.M3_LIVE_CONFIG ? undefined : { command: 'pnpm dev --port 5173 --strictPort', url: 'http://127.0.0.1:5173', reuseExistingServer: !process.env.CI },
})
