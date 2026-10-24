import { spawnSync } from 'node:child_process'
const result = spawnSync(process.execPath, ['node_modules/vitest/vitest.mjs', 'run', ...process.argv.slice(2).filter(x => x !== '--')], { stdio: 'inherit' })
process.exit(result.status ?? 1)
