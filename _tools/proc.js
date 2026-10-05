window.__run=(async()=>{const K=window.__P.k,STORE=window.__P.s,TOL=window.__P.t;
const blob=await fetch(location.href).then(r=>r.blob());const bm=await createImageBitmap(blob);
let W=bm.width,H=bm.height;const c=document.createElement('canvas');c.width=W;c.height=H;const x=c.getContext('2d');x.drawImage(bm,0,0);
let d=x.getImageData(0,0,W,H),p=d.data;
const corners=[0,(W-1)*4,((H-1)*W)*4,((H-1)*W+W-1)*4];const hasAlpha=corners.some(i=>p[i+3]<200);
let note='alpha';
if(!hasAlpha&&TOL>0){
 const br=[];for(let i=0;i<W;i+=3){br.push(i*4,((H-1)*W+i)*4)}for(let j=0;j<H;j+=3){br.push(j*W*4,(j*W+W-1)*4)}
 const ch=k=>{const a=br.map(i=>p[i+k]).sort((m,n)=>m-n);return a[a.length>>1]};const bg=[ch(0),ch(1),ch(2)];
 const near=i=>Math.abs(p[i]-bg[0])<=TOL&&Math.abs(p[i+1]-bg[1])<=TOL&&Math.abs(p[i+2]-bg[2])<=TOL;
 const m=new Uint8Array(W*H),q=new Int32Array(W*H);let h=0,t=0;
 const push=k=>{if(!m[k]&&near(k*4)){m[k]=1;q[t++]=k}};
 for(let i=0;i<W;i++){push(i);push((H-1)*W+i)}for(let j=0;j<H;j++){push(j*W);push(j*W+W-1)}
 while(h<t){const k=q[h++],xx=k%W,yy=(k/W)|0;if(xx>0)push(k-1);if(xx<W-1)push(k+1);if(yy>0)push(k-W);if(yy<H-1)push(k+W)}
 let n=0;for(let k=0;k<W*H;k++){if(m[k]){p[k*4+3]=0;n++}}
 for(let k=0;k<W*H;k++){if(m[k])continue;const xx=k%W,yy=(k/W)|0;if((xx>0&&m[k-1])||(xx<W-1&&m[k+1])||(yy>0&&m[k-W])||(yy<H-1&&m[k+W])){const i=k*4,dd=Math.max(Math.abs(p[i]-bg[0]),Math.abs(p[i+1]-bg[1]),Math.abs(p[i+2]-bg[2]));p[i+3]=Math.min(255,Math.round(255*dd/(TOL*3)))}}
 note='bg '+bg.join(',')+' removed '+Math.round(100*n/(W*H))+'%';x.putImageData(d,0,0)}
let x0=W,y0=H,x1=0,y1=0;for(let j=0;j<H;j++)for(let i=0;i<W;i++){if(p[(j*W+i)*4+3]>12){if(i<x0)x0=i;if(i>x1)x1=i;if(j<y0)y0=j;if(j>y1)y1=j}}
const pad=Math.round(Math.max(x1-x0,y1-y0)*0.03);x0=Math.max(0,x0-pad);y0=Math.max(0,y0-pad);x1=Math.min(W-1,x1+pad);y1=Math.min(H-1,y1+pad);
const cw=x1-x0+1,chh=y1-y0+1,s=Math.min(1,800/Math.max(cw,chh));const o=document.createElement('canvas');o.width=Math.round(cw*s);o.height=Math.round(chh*s);
const ox=o.getContext('2d');ox.imageSmoothingQuality='high';ox.drawImage(c,x0,y0,cw,chh,0,0,o.width,o.height);
const url=o.toDataURL('image/webp',0.9);let S={};try{S=JSON.parse(window.name||'{}')}catch(e){}S[K]=url;window.name=JSON.stringify(S);
document.body.innerHTML='<div style="display:flex;gap:8px;background:#ccc;padding:8px"><img src="'+STORE+'" style="height:420px;max-width:45%;object-fit:contain;background:#fff"><img src="'+url+'" style="height:420px;max-width:50%;object-fit:contain;background-image:conic-gradient(#f9c 25%,#9cf 0 50%,#f9c 0 75%,#9cf 0);background-size:24px 24px"></div><p style="font:16px sans-serif">'+K+' '+o.width+'x'+o.height+' '+Math.round(url.length/1024)+'KB '+note+' keys:'+Object.keys(S).length+'</p>';
document.body.style.margin=0;window.__r=K+' '+note+' '+Object.keys(S).length;});
