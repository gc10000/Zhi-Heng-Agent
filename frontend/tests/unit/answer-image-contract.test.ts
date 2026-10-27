import { describe,it,expect } from 'vitest'
import cases from '../../../tests/fixtures/answer-image-markdown.json'
import { renderEvidence } from '../../src/features/evidence/markdown'

describe('与后端共享的答案图片可见性契约',()=>{
  for(const c of cases)it(c.id,()=>{
    const div=document.createElement('div')
    div.innerHTML=renderEvidence(c.body,[],['diagram'])
    expect([...div.querySelectorAll('img')].map(i=>i.getAttribute('src')?.split('/').at(-1))).toEqual(c.assets)
  })
})
