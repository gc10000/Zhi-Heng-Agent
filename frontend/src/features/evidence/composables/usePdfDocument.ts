import { shallowRef, ref, onBeforeUnmount } from 'vue'
import { pdfRuntime } from '@/lib/pdf'
import type { PDFDocumentProxy, PDFDocumentLoadingTask, RenderTask, TextLayer } from 'pdfjs-dist'

export function usePdfDocument() {
  const document=shallowRef<PDFDocumentProxy>(),error=ref(''),loading=ref(false)
  let generation=0,task: PDFDocumentLoadingTask | undefined,render:RenderTask|undefined,text:TextLayer|undefined
  function cancelRender() { render?.cancel(); render=undefined;text?.cancel();text=undefined }
  async function close() { generation++;cancelRender();const old=task;task=undefined;document.value=undefined;await old?.destroy().catch(()=>{}) }
  async function load(url:string) {
    const previous=close();const current=generation;loading.value=true;error.value=''
    try {
      await previous
      const pdf=await pdfRuntime();if(current!==generation)return
      task=pdf.getDocument({url,withCredentials:true,rangeChunkSize:65536,disableAutoFetch:true,
        cMapUrl:'/pdfjs/cmaps/',cMapPacked:true,standardFontDataUrl:'/pdfjs/standard_fonts/',wasmUrl:'/pdfjs/wasm/'})
      const value=await task.promise
      if(current!==generation){await value.destroy();return}
      document.value=value
    } catch(e){if(current===generation)error.value='PDF读取失败，请核对授权或重试。'}
    finally{if(current===generation)loading.value=false}
  }
  let renderVersion=0
  async function draw(pageNumber:number,scale:number,rotation:number,canvas:HTMLCanvasElement,layer:HTMLElement) {
    cancelRender();const version=++renderVersion,current=generation,doc=document.value
    if(!doc)return
    try {
      const page=await doc.getPage(pageNumber)
      if(current!==generation||version!==renderVersion)return
      const viewport=page.getViewport({scale,rotation:(page.rotate+rotation)%360}),ratio=window.devicePixelRatio||1
      canvas.width=Math.floor(viewport.width*ratio);canvas.height=Math.floor(viewport.height*ratio);canvas.style.width=viewport.width+'px';canvas.style.height=viewport.height+'px'
      layer.replaceChildren();layer.style.setProperty('--scale-factor',String(scale));layer.style.width=viewport.width+'px';layer.style.height=viewport.height+'px'
      render=page.render({canvas,canvasContext:canvas.getContext('2d')!,viewport,transform:ratio===1?undefined:[ratio,0,0,ratio,0,0]})
      await render.promise
      if(current!==generation||version!==renderVersion)return
      const pdf=await pdfRuntime(),content=await page.getTextContent()
      if(current!==generation||version!==renderVersion)return
      text=new pdf.TextLayer({textContentSource:content,container:layer,viewport});await text.render()
      if(current!==generation||version!==renderVersion)return
      return { width:viewport.width,height:viewport.height,baseWidth:page.getViewport({scale,rotation:0}).width,baseHeight:page.getViewport({scale,rotation:0}).height,rotation:(page.rotate+rotation)%360 }
    }catch(e){if(current===generation&&version===renderVersion&&(e as Error).name!=='RenderingCancelledException')error.value='PDF页面渲染失败，请重试。'}
  }
  onBeforeUnmount(()=>{void close()})
  return {document,error,loading,load,draw,close,cancelRender}
}
