import { defineConfig } from '@playwright/test'
if (!process.env.M7_BROWSER_CONFIG || !process.env.M7_BROWSER_OUTPUT) throw new Error('须显式提供本轮隔离配置及私有输出目录')
export default defineConfig({
  testDir: './tests/e2e', testMatch: 'operational-readonly.spec.ts', workers: 1, retries: 0, timeout: 90000,
  outputDir: process.env.M7_BROWSER_OUTPUT,
  reporter: [['list']],
  use: { baseURL: process.env.M7_UI_BASE, browserName: 'chromium', channel: 'msedge',
    viewport: { width: 1500, height: 960 }, screenshot: 'only-on-failure', trace: 'on', video: 'on' },
})
