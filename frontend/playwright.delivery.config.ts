import { defineConfig } from '@playwright/test'
if (!process.env.M7_BROWSER_CONFIG || !process.env.M7_BROWSER_OUTPUT) throw new Error('须显式提供M7工程合成后台配置及私有输出目录')
export default defineConfig({
  testDir: './tests/e2e', testMatch: 'delivery-live.spec.ts', workers: 1, retries: 0, timeout: 90000,
  outputDir: process.env.M7_BROWSER_OUTPUT,
  reporter: [['list']],
  use: { baseURL: process.env.M7_UI_BASE || 'http://127.0.0.1:18080', browserName: 'chromium', channel: 'msedge',
    viewport: { width: 1500, height: 960 }, screenshot: 'only-on-failure', trace: 'on', video: 'on' },
})
