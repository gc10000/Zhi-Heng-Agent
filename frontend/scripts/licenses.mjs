// 随静态资源保留实际安装包许可，不将node_modules或源代码整树公开。
import { readdirSync, readFileSync, existsSync, mkdirSync, copyFileSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'
const output = 'public/licenses'
mkdirSync(output, {recursive:true})
const records = []
function record(folder) {
  const manifest = join(folder, 'package.json')
  if (!existsSync(manifest)) return
  const pkg = JSON.parse(readFileSync(manifest, 'utf8'))
  const destination = join(output, `${pkg.name.replaceAll('/', '__')}@${pkg.version}`)
  const files = readdirSync(folder).filter(name => /^(licen[cs]e|copying|notice)(\.|$)/i.test(name))
  mkdirSync(destination, {recursive:true})
  for (const file of files) copyFileSync(join(folder, file), join(destination, file))
  records.push({name:pkg.name, version:pkg.version, license:pkg.license ?? 'unknown', files})
}
for (const entry of readdirSync('node_modules/.pnpm', {withFileTypes:true})) {
  if (!entry.isDirectory() || entry.name === 'node_modules') continue
  const directory = join('node_modules/.pnpm', entry.name, 'node_modules')
  if (!existsSync(directory)) continue
  for (const item of readdirSync(directory, {withFileTypes:true})) {
    if (!item.isDirectory()) continue
    const path = join(directory, item.name)
    if (item.name.startsWith('@')) {
      for (const child of readdirSync(path, {withFileTypes:true})) if (child.isDirectory()) record(join(path,child.name))
    } else record(path)
  }
}
records.sort((a,b) => a.name.localeCompare(b.name))
if (!records.some(item => item.name === 'pdfjs-dist' && item.files.length)) throw new Error('缺少PDF.js许可')
writeFileSync(join(output,'index.json'), JSON.stringify(records,null,2)+'\n')
console.log(`保留${records.length}个实际安装包许可记录；未核清项仍须发布审阅。`)
