export function normalizedBox(box: number[], width: number, height: number, rotation: number) {
  if (box.length!==4 || box.some(x=>!Number.isFinite(x)||x<0||x>1) || box[0]>=box[2] || box[1]>=box[3] || width<=0 || height<=0 || rotation%90!==0) throw new Error('PDF坐标无效。')
  const [x0,y0,x1,y1]=box, angle=((rotation%360)+360)%360
  if(angle===90)return {left:(1-y1)*height,top:x0*width,width:(y1-y0)*height,height:(x1-x0)*width}
  if(angle===180)return {left:(1-x1)*width,top:(1-y1)*height,width:(x1-x0)*width,height:(y1-y0)*height}
  if(angle===270)return {left:y0*height,top:(1-x1)*width,width:(y1-y0)*height,height:(x1-x0)*width}
  return {left:x0*width,top:y0*height,width:(x1-x0)*width,height:(y1-y0)*height}
}
