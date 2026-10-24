import { test, expect } from '@playwright/test'
import { readFileSync } from 'node:fs'
test('固定PDF.js和本地worker解码合成PDF', async ({ page }) => {
  await page.goto('/')
  const data = readFileSync('tests/fixtures/one-page.base64.txt', 'utf8')
  const result = await page.evaluate(async base64 => {
    const modulePath = '/src/lib/pdf.ts'
    const pdf = await (await import(modulePath)).pdfRuntime()
    const task = pdf.getDocument({ data: Uint8Array.from(atob(base64), c => c.charCodeAt(0)) })
    const doc = await task.promise
    const text = await (await doc.getPage(1)).getTextContent()
    const value = { version: pdf.version, pages: doc.numPages, text: text.items.map((x: { str: string }) => x.str).join(''), worker: pdf.GlobalWorkerOptions.workerSrc }
    await doc.destroy()
    return value
  }, data)
  expect(result.version).toBe('5.4.296'); expect(result.pages).toBe(1)
  expect(result.text).toContain('M3 local PDF'); expect(result.worker).not.toMatch(/^https?:\/\//)
})
