import { it, expect } from 'vitest'
import { normalizedBox } from '@/features/evidence/composables/pdf-coordinates'
it.each([
  [0,{left:20,top:30,width:80,height:90}],
  [90,{left:180,top:20,width:90,height:80}],
  [180,{left:100,top:180,width:80,height:90}],
  [270,{left:30,top:100,width:90,height:80}],
] as const)('归一化左上角bbox按%d度旋转，缩放保留落点',(angle,expected)=>{
  for(const [key,value] of Object.entries(expected)) {
    expect(normalizedBox([.1,.1,.5,.4],200,300,angle)[key as keyof typeof expected]).toBeCloseTo(value,8)
    expect(normalizedBox([.1,.1,.5,.4],400,600,angle)[key as keyof typeof expected]).toBeCloseTo(value*2,8)
  }
})
it.each([[0,0,0,1],[-.1,0,.3,.5],[0,0,2,1],[0,0,1], [0,0,NaN,1]].map(box=>({box})))('拒绝未知或无效坐标，不伪造高亮 $box',({box})=>{
  expect(()=>normalizedBox(box,200,300,0)).toThrow()
})
