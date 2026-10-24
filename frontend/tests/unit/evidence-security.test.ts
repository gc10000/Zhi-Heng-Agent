import { it, expect } from 'vitest'
import { renderEvidence } from '@/features/evidence/markdown'
import type { Citation } from '@/lib/api/types'
const c: Citation = {citation_id:'c-one',document_id:'d',revision_id:'v',text:'原文',source_refs:[],asset_ids:['asset-one']}
it('未知HTML、脚本、SVG和事件属性不作为DOM执行', () => {
  const div=document.createElement('div');div.innerHTML=renderEvidence('<script>alert(1)</script><img src=x onerror=alert(1)><svg onload=alert(1)></svg>')
  expect(div.querySelector('script,img,svg')).toBeNull()
})
it('拒绝危险/协议相对链接与所有未登记远程/同源图像', () => {
  const html=renderEvidence('[危险](javascript:alert(1)) [远程](//evil.test) ![跟踪](https://evil.test/pixel) ![跨引用](/api/v1/assets/private)')
  const div=document.createElement('div');div.innerHTML=html
  expect(div.querySelector('img')).toBeNull();expect(div.querySelector('a[href^="//"]')).toBeNull();expect(div.querySelector('a[href^="javascript:"]')).toBeNull()
})
it('只有入选证据的登记资产可加载，编号绑定稳定citation_id', () => {
  const div=document.createElement('div');div.innerHTML=renderEvidence('参数[1]，未知[2]。![图](asset://asset-one)',[c],['asset-one'])
  expect(div.querySelector('img')?.getAttribute('src')).toBe('/api/v1/assets/asset-one')
  expect(div.querySelector('button')?.getAttribute('data-citation-id')).toBe('c-one')
  expect(div.querySelectorAll('button')).toHaveLength(1)
})
it('代码内的编号不转换，安全链接保留且阻止opener', () => {
  const div=document.createElement('div');div.innerHTML=renderEvidence('`[1]` [厂商](https://example.com/manual)',[c])
  expect(div.querySelector('code')?.textContent).toBe('[1]');expect(div.querySelector('button')).toBeNull();expect(div.querySelector('a')?.getAttribute('rel')).toContain('noopener')
})
