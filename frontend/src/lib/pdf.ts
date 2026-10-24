// PDF.js及worker来自同一锁定包；按需加载，不在登录/聊天首屏加载PDF代码。
export async function pdfRuntime() {
  const pdf = await import('pdfjs-dist')
  pdf.GlobalWorkerOptions.workerSrc = (await import('pdfjs-dist/build/pdf.worker.min.mjs?url')).default
  return pdf
}
