import { it,expect,vi,afterEach } from 'vitest'
import { mount,flushPromises } from '@vue/test-utils'
import { usePdfDocument } from '@/features/evidence/composables/usePdfDocument'
const runtime=vi.hoisted(()=>({pdfRuntime:vi.fn()}))
vi.mock('@/lib/pdf',()=>runtime)
afterEach(()=>vi.restoreAllMocks())
it('取消后迟到的文本层渲染不能返回旧页坐标',async()=>{
  let finishText!:()=>void
  const text=new Promise<void>(r=>{finishText=r})
  const page={rotate:0,getViewport:()=>({width:100,height:200}),render:()=>({promise:Promise.resolve(),cancel:vi.fn()}),getTextContent:async()=>({items:[]})}
  const doc={getPage:async()=>page,destroy:async()=>{}}
  runtime.pdfRuntime.mockResolvedValue({getDocument:()=>({promise:Promise.resolve(doc),destroy:async()=>{}}),TextLayer:class{render=()=>text;cancel=vi.fn()}})
  let pdf!:ReturnType<typeof usePdfDocument>
  const wrapper=mount({setup(){pdf=usePdfDocument();return()=>null}})
  await pdf.load('/api/v1/assets/a')
  const canvas=document.createElement('canvas');vi.spyOn(canvas,'getContext').mockReturnValue({} as CanvasRenderingContext2D)
  const result=pdf.draw(1,1,0,canvas,document.createElement('div'))
  await flushPromises();await pdf.close();finishText()
  expect(await result).toBeUndefined()
  expect(pdf.document.value).toBeUndefined();wrapper.unmount()
})
