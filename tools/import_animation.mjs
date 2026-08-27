#!/usr/bin/env node
/* Convert a chroma-key AI animation sheet into the exact atlas contract used by the game.

   Example (the model returned nine columns, so column 3 is reused as the second passing pose):
   node tools/import_animation.mjs art_raw/hero_blob_jelly_anim_v1.png \
     web/art/anim/hero/blob.png --src-cols 9 --map 0,1,2,3,4,3,5,6,7,8 \
     --palette hero --static-out web/art/hero/blob.png

   Boss example (48px cells, 480x144 output and 64 KB budget):
   node tools/import_animation.mjs art_raw/boss_b_warden_anim_v1.png \
     web/art/anim/boss/b_warden.png --cell 48 --palette game

   Hat overlay example (the static icon supplies the exact on-head size and anchor):
   node tools/import_animation.mjs art_raw/hat_helm_anim_v1.png \
     web/art/anim/hat/helm.png --src-cols 9 --map 0,1,2,3,4,3,5,6,7,8 \
     --overlay hat --static-ref web/art/hat/helm.png --palette game

   No npm packages are required. Input must be an 8-bit, non-interlaced RGB/RGBA PNG. */
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';

const argv=process.argv.slice(2), input=argv[0], output=argv[1];
if(!input || !output) throw new Error('usage: import_animation.mjs <input.png> <output.png> [options]');
const opt=(name,fallback)=>{ const i=argv.indexOf('--'+name); return i>=0 ? argv[i+1] : fallback; };
const srcCols=Number(opt('src-cols','10')), srcRows=Number(opt('src-rows','3'));
const map=opt('map',Array.from({length:10},(_,i)=>i).join(',')).split(',').map(Number);
const staticOut=opt('static-out',''), paletteName=opt('palette','game');
const overlay=opt('overlay','');
const staticRef=opt('static-ref','');
const hatBoxSpec=opt('hat-box','');
const clearHatEyes=opt('hat-clear-eyes','0')==='1';
const previewBody=opt('preview-body',''),previewOut=opt('preview-out','');
const bodyRef=opt('body-ref',previewBody);
const outCell=Number(opt('cell','32'));
if(![32,48].includes(outCell)) throw new Error('--cell must be 32 or 48');
if(overlay && !['weapon','shield','hat'].includes(overlay))
  throw new Error('--overlay currently supports weapon, shield, or hat');
if(overlay==='hat' && !staticRef)
  throw new Error('--overlay hat requires --static-ref <32px static hat>');
if(Boolean(previewBody)!==Boolean(previewOut))
  throw new Error('--preview-body and --preview-out must be supplied together');
if(clearHatEyes && (overlay!=='hat'||!bodyRef))
  throw new Error('--hat-clear-eyes requires --overlay hat and --body-ref (or --preview-body)');
if(map.length!==10 || map.some(n=>!Number.isInteger(n)||n<0||n>=srcCols))
  throw new Error('--map must contain ten valid zero-based source columns');

const PALETTES={
  /* 主角不是一塊橘色剪影：十色保留球面由左上亮面到右下暗面的
     連續色階，也保留四腳彼此遮擋時需要的深色。舊版只有五色，
     高解析原稿裡的體積資訊在縮成 32px 時幾乎全部被合併掉了。 */
  hero:['0d0d12','6b2618','a8452c','c95b31','d97757',
        'e87a4a','f5a95e','eaa88c','f6c4a2','f2efe7'],
  game:['0d0d12','1a1a24','2b2b38','3d3d4d','565668','757589','c8c8d4','e8edf4','f7f5eb',
        '2a1d14','43301f','5e442c','7d5c3c','9c7850','bb9668','ecd3ae',
        '6b1a1e','9c2b2b','c94a3a','e87a4a','f5a95e','1e5230','2f7d45','4aa85e','79c97a',
        '101c3a','1d3468','2f57a0','4a86cf','7cb8ea',
        '382044','573060','75407f','a85aaa','d978c4','f2b2df',
        '1d6475','2f90a6','58c2cf','a5ebeb',
        '6b4a12','a87a1e','dcae35','f5dc7a']
};
const palette=(PALETTES[paletteName]||PALETTES.game).map(h=>[
  parseInt(h.slice(0,2),16),parseInt(h.slice(2,4),16),parseInt(h.slice(4,6),16),255]);

function decodePng(file){
  const b=fs.readFileSync(file);
  if(b.subarray(0,8).toString('hex')!=='89504e470d0a1a0a') throw new Error('not a PNG: '+file);
  let p=8,w=0,h=0,depth=0,type=0,interlace=0; const idat=[];
  while(p<b.length){
    const n=b.readUInt32BE(p), name=b.subarray(p+4,p+8).toString('ascii'), data=b.subarray(p+8,p+8+n);
    if(name==='IHDR'){ w=data.readUInt32BE(0); h=data.readUInt32BE(4); depth=data[8]; type=data[9]; interlace=data[12]; }
    if(name==='IDAT') idat.push(data);
    p+=12+n;
    if(name==='IEND') break;
  }
  if(depth!==8 || ![2,6].includes(type) || interlace!==0)
    throw new Error(`unsupported PNG (need 8-bit non-interlaced RGB/RGBA): depth=${depth} type=${type} interlace=${interlace}`);
  const channels=type===6?4:3, stride=w*channels, raw=zlib.inflateSync(Buffer.concat(idat));
  const out=new Uint8Array(w*h*4), prev=new Uint8Array(stride), row=new Uint8Array(stride);
  let rp=0;
  const paeth=(a,b,c)=>{ const q=a+b-c,pa=Math.abs(q-a),pb=Math.abs(q-b),pc=Math.abs(q-c); return pa<=pb&&pa<=pc?a:pb<=pc?b:c; };
  for(let y=0;y<h;y++){
    const filter=raw[rp++];
    for(let x=0;x<stride;x++){
      const a=x>=channels?row[x-channels]:0, up=prev[x], ul=x>=channels?prev[x-channels]:0, v=raw[rp++];
      row[x]=(v+(filter===0?0:filter===1?a:filter===2?up:filter===3?Math.floor((a+up)/2):paeth(a,up,ul)))&255;
    }
    for(let x=0;x<w;x++){
      const si=x*channels,di=(y*w+x)*4;
      out[di]=row[si]; out[di+1]=row[si+1]; out[di+2]=row[si+2]; out[di+3]=channels===4?row[si+3]:255;
    }
    prev.set(row);
  }
  return {w,h,data:out};
}

function crc32(buf){
  let c=0xffffffff;
  for(const n of buf){ c^=n; for(let k=0;k<8;k++) c=(c>>>1)^((c&1)?0xedb88320:0); }
  return (c^0xffffffff)>>>0;
}
function chunk(name,data){
  const n=Buffer.from(name), out=Buffer.alloc(12+data.length);
  out.writeUInt32BE(data.length,0); n.copy(out,4); data.copy(out,8);
  out.writeUInt32BE(crc32(Buffer.concat([n,data])),8+data.length); return out;
}
function encodePng(w,h,rgba,file){
  const rows=Buffer.alloc(h*(1+w*4));
  for(let y=0;y<h;y++){ const p=y*(1+w*4); rows[p]=0; Buffer.from(rgba.buffer,rgba.byteOffset+y*w*4,w*4).copy(rows,p+1); }
  const ihdr=Buffer.alloc(13); ihdr.writeUInt32BE(w,0); ihdr.writeUInt32BE(h,4); ihdr[8]=8; ihdr[9]=6;
  const png=Buffer.concat([Buffer.from('89504e470d0a1a0a','hex'),chunk('IHDR',ihdr),
                           chunk('IDAT',zlib.deflateSync(rows,{level:9})),chunk('IEND',Buffer.alloc(0))]);
  fs.mkdirSync(path.dirname(file),{recursive:true}); fs.writeFileSync(file,png);
}
function isKey(r,g,b,a){ return a<16 || (r>165 && b>145 && g<150 && r+b>g*2+210); }
function nearest(r,g,b){
  let best=palette[0],score=Infinity;
  for(const c of palette){ const d=(r-c[0])**2+(g-c[1])**2+(b-c[2])**2; if(d<score){score=d;best=c;} }
  return best;
}
function boundsFor(im,x0,y0,x1,y1){
  const w=x1-x0,h=y1-y0,n=w*h,mask=new Uint8Array(n),seen=new Uint8Array(n);
  for(let y=0;y<h;y++) for(let x=0;x<w;x++){
    const i=((y0+y)*im.w+x0+x)*4,d=im.data;
    if(!isKey(d[i],d[i+1],d[i+2],d[i+3])) mask[y*w+x]=1;
  }
  /* A generated pose can slightly cross an imagined cell boundary.  Finding the
     connected subject nearest the cell centre prevents a neighbour's stray paw or
     weapon tip from making this pose tiny after downsampling. */
  const q=new Int32Array(n),comps=[];
  for(let seed=0;seed<n;seed++){
    if(!mask[seed]||seen[seed]) continue;
    let head=0,tail=0,count=0,l=w,t=h,r=-1,b=-1; q[tail++]=seed;seen[seed]=1;
    while(head<tail){
      const p=q[head++],px=p%w,py=Math.floor(p/w); count++;
      if(px<l)l=px;if(px>r)r=px;if(py<t)t=py;if(py>b)b=py;
      for(let yy=Math.max(0,py-1);yy<=Math.min(h-1,py+1);yy++)
        for(let xx=Math.max(0,px-1);xx<=Math.min(w-1,px+1);xx++){
          const z=yy*w+xx;if(mask[z]&&!seen[z]){seen[z]=1;q[tail++]=z;}
        }
    }
    if(count>=4) comps.push({l,t,r,b,count,cx:(l+r)/2,cy:(t+b)/2});
  }
  if(!comps.length) return null;
  const midX=(w-1)/2,midY=(h-1)/2;
  let main=comps[0],mainScore=-1;
  for(const c of comps){
    const dist=Math.hypot((c.cx-midX)/w,(c.cy-midY)/h);
    const score=c.count/(1+dist*1.5);
    if(score>mainScore){main=c;mainScore=score;}
  }
  let l=main.l,t=main.t,r=main.r,b=main.b;
  for(const c of comps){
    if(c===main || c.count<Math.max(12,main.count*.015)) continue;
    const gx=Math.max(0,Math.max(l,c.l)-Math.min(r,c.r)-1);
    const gy=Math.max(0,Math.max(t,c.t)-Math.min(b,c.b)-1);
    if(gx<=w*.18 && gy<=h*.18){ l=Math.min(l,c.l);t=Math.min(t,c.t);r=Math.max(r,c.r);b=Math.max(b,c.b); }
  }
  l+=x0;r+=x0;t+=y0;b+=y0;
  return {l,t,r,b,w:r-l+1,h:b-t+1};
}

const src=decodePng(input), cells=[];
for(let row=0;row<srcRows;row++) for(let col=0;col<srcCols;col++){
  const x0=Math.floor(col*src.w/srcCols),x1=Math.floor((col+1)*src.w/srcCols);
  const y0=Math.floor(row*src.h/srcRows),y1=Math.floor((row+1)*src.h/srcRows);
  const box=boundsFor(src,x0,y0,x1,y1);
  if(!box) throw new Error(`empty source cell ${col},${row}`);
  cells.push({row,col,box});
}
const used=cells.filter(c=>map.includes(c.col));
if(opt('debug','0')==='1') for(const c of used) console.log(`cell ${c.col},${c.row}: ${c.box.l},${c.box.t}..${c.box.r},${c.box.b} (${c.box.w}x${c.box.h})`);
const maxW=Math.max(...used.map(c=>c.box.w)),maxH=Math.max(...used.map(c=>c.box.h));
const widest=used.find(c=>c.box.w===maxW),tallest=used.find(c=>c.box.h===maxH);
const outW=outCell*10,outH=outCell*3;
const scale=Math.min((outCell-6)/maxW,(outCell-5)/maxH), out=new Uint8Array(outW*outH*4);

function opaqueBounds(im){
  let l=im.w,t=im.h,r=-1,b=-1;
  for(let y=0;y<im.h;y++) for(let x=0;x<im.w;x++){
    if(im.data[(y*im.w+x)*4+3]<16) continue;
    if(x<l)l=x;if(x>r)r=x;if(y<t)t=y;if(y>b)b=y;
  }
  return r>=l&&b>=t ? {l,t,r,b,w:r-l+1,h:b-t+1} : null;
}

function drawCell(dstCol,row,srcCol){
  const cell=cells[row*srcCols+srcCol],box=cell.box;
  const dw=Math.max(1,Math.round(box.w*scale)),dh=Math.max(1,Math.round(box.h*scale));
  const dx=dstCol*outCell+Math.floor((outCell-dw)/2),dy=row*outCell+(outCell-dh);
  for(let ty=0;ty<dh;ty++) for(let tx=0;tx<dw;tx++){
    const sx0=box.l+Math.floor(tx*box.w/dw),sx1=box.l+Math.max(1,Math.floor((tx+1)*box.w/dw));
    const sy0=box.t+Math.floor(ty*box.h/dh),sy1=box.t+Math.max(1,Math.floor((ty+1)*box.h/dh));
    const votes=new Array(palette.length).fill(0); let fg=0,total=0;
    for(let sy=sy0;sy<Math.min(sy1,box.b+1);sy++) for(let sx=sx0;sx<Math.min(sx1,box.r+1);sx++){
      total++; const i=(sy*src.w+sx)*4,d=src.data;
      if(isKey(d[i],d[i+1],d[i+2],d[i+3])) continue;
      fg++; const c=nearest(d[i],d[i+1],d[i+2]); votes[palette.indexOf(c)]++;
    }
    if(!total || fg/total<0.12) continue;
    let pi=0; for(let i=1;i<votes.length;i++) if(votes[i]>votes[pi]) pi=i;
    const oi=((dy+ty)*outW+dx+tx)*4,c=palette[pi]; out[oi]=c[0];out[oi+1]=c[1];out[oi+2]=c[2];out[oi+3]=255;
  }
}

/* Equipment layers cannot be centred like a whole character: the weapon's grip must
   stay attached to the owner's hand while its tip is free to swing.  ImageGen source
   sheets use a tiny invisible-owner hand patch, so we treat a stable point on the
   weapon silhouette as the grip and move that point to a per-pose 32px hand anchor.
   The attack anchors deliberately sit farther inside the body.  Otherwise a full
   weapon has only 6-8 pixels before it hits the cell edge and the strike reads as a
   twitch instead of a swing. */
function warmGrip(box){
  const target=[[217,119,87],[234,168,140],[232,122,74]], cand=[];
  for(let y=box.t;y<=box.b;y++) for(let x=box.l;x<=box.r;x++){
    const i=(y*src.w+x)*4,d=src.data;
    if(isKey(d[i],d[i+1],d[i+2],d[i+3])) continue;
    let score=Infinity;
    for(const c of target) score=Math.min(score,(d[i]-c[0])**2+(d[i+1]-c[1])**2+(d[i+2]-c[2])**2);
    cand.push({x,y,score});
  }
  cand.sort((a,b)=>a.score-b.score);
  const take=Math.max(4,Math.min(cand.length,Math.round(cand.length*.035)));
  let x=0,y=0,w=0;
  for(let i=0;i<take;i++){
    const q=cand[i],weight=1/(1+Math.sqrt(q.score)); x+=q.x*weight;y+=q.y*weight;w+=weight;
  }
  return w ? {x:x/w,y:y/w} : {x:box.l+box.w/2,y:box.b};
}
function drawWeaponCell(dstCol,row,srcCol){
  const cell=cells[row*srcCols+srcCol],box=cell.box;
  const dw=Math.max(1,Math.round(box.w*scale)),dh=Math.max(1,Math.round(box.h*scale));
  const attack=dstCol>=6&&dstCol<=8, hurt=dstCol===9;
  const horizontal=box.w>box.h*1.25;
  // Four walking frames alternate lean/neutral.  On the lean frames the heavy
  // tip shears two pixels inward while the grip moves one pixel outward.
  const walkLean=dstCol===2||dstCol===4;
  const grip=warmGrip(box);
  let sgx=grip.x,sgy=grip.y;
  // Anatomical right hand: viewer-left in the front row, viewer-right in the back row.
  let tx=row===0?6:26,ty=27;
  if(attack){
    if(horizontal){
      // A horizontal impact crosses the body.  Put the detected grip at the edge it
      // already occupies so the full blade or shaft remains inside the 32px cell.
      tx=sgx<box.l+box.w/2?5:27; ty=23;
    } else { tx=row===0?13:row===1?16:19; ty=26; }
  } else if(hurt){
    tx=row===0?7:row===1?24:25; ty=27;
  } else if(row===1&&horizontal){
    tx=sgx<box.l+box.w/2?5:27; ty=23;
  }
  const inward=row===0?1:-1;
  if(walkLean){
    if(horizontal) ty++;    // side view: grip drops out while the tip tucks upward
    else tx-=inward;        // front/back: grip moves outward, opposite the tip
  }
  const dx=Math.round(tx-(sgx-box.l)*scale),dy=Math.round(ty-(sgy-box.t)*scale);
  for(let oy=0;oy<dh;oy++) for(let ox=0;ox<dw;ox++){
    const leanX=walkLean&&!horizontal ? inward*Math.round(2*(1-oy/Math.max(1,dh-1))) : 0;
    const fromGrip=sgx<box.l+box.w/2 ? ox/Math.max(1,dw-1) : 1-ox/Math.max(1,dw-1);
    const leanY=walkLean&&horizontal ? -Math.round(2*fromGrip) : 0;
    const px=dx+ox+leanX,py=dy+oy+leanY;
    if(px<0||px>=outCell||py<0||py>=outCell) continue;
    const sx0=box.l+Math.floor(ox*box.w/dw),sx1=box.l+Math.max(1,Math.floor((ox+1)*box.w/dw));
    const sy0=box.t+Math.floor(oy*box.h/dh),sy1=box.t+Math.max(1,Math.floor((oy+1)*box.h/dh));
    const votes=new Array(palette.length).fill(0); let fg=0,total=0;
    for(let sy=sy0;sy<Math.min(sy1,box.b+1);sy++) for(let sx=sx0;sx<Math.min(sx1,box.r+1);sx++){
      total++; const i=(sy*src.w+sx)*4,d=src.data;
      if(isKey(d[i],d[i+1],d[i+2],d[i+3])) continue;
      fg++; const c=nearest(d[i],d[i+1],d[i+2]); votes[palette.indexOf(c)]++;
    }
    if(!total||fg/total<.12) continue;
    let pi=0; for(let i=1;i<votes.length;i++) if(votes[i]>votes[pi]) pi=i;
    const oi=((row*outCell+py)*outW+dstCol*outCell+px)*4,c=palette[pi];
    out[oi]=c[0];out[oi+1]=c[1];out[oi+2]=c[2];out[oi+3]=255;
  }
}
/* Shields attach by their visual centre rather than the hidden wrist.  Round, tower
   and kite shields put their straps in different places; using that strap as an
   anchor makes the six silhouettes jump when equipment changes. */
const shieldScale=Math.min((outCell-12)/maxW,(outCell-12)/maxH);
function drawShieldCell(dstCol,row,srcCol){
  const cell=cells[row*srcCols+srcCol],box=cell.box;
  const dw=Math.max(1,Math.round(box.w*shieldScale)),dh=Math.max(1,Math.round(box.h*shieldScale));
  const attack=dstCol>=6&&dstCol<=8,hurt=dstCol===9,walkOut=dstCol===2||dstCol===4;
  // Anatomical left hand: viewer-right in front, viewer-left from behind.
  let cx=row===0?24:row===1?8:8,cy=24;
  if(attack){ cx=row===0?21:11; cy=25; }
  else if(hurt){ cx=row===0?22:10; cy=18; }
  const outward=row===0?1:-1;
  if(walkOut) cx+=outward;
  const dx=Math.round(cx-dw/2),dy=Math.round(cy-dh/2);
  for(let oy=0;oy<dh;oy++) for(let ox=0;ox<dw;ox++){
    const topWeight=1-oy/Math.max(1,dh-1);
    const lean=walkOut ? outward*Math.round(topWeight) :
               hurt ? -outward*Math.round(2*topWeight) : 0;
    const px=dx+ox+lean,py=dy+oy;
    if(px<0||px>=outCell||py<0||py>=outCell) continue;
    const sx0=box.l+Math.floor(ox*box.w/dw),sx1=box.l+Math.max(1,Math.floor((ox+1)*box.w/dw));
    const sy0=box.t+Math.floor(oy*box.h/dh),sy1=box.t+Math.max(1,Math.floor((oy+1)*box.h/dh));
    const votes=new Array(palette.length).fill(0); let fg=0,total=0;
    for(let sy=sy0;sy<Math.min(sy1,box.b+1);sy++) for(let sx=sx0;sx<Math.min(sx1,box.r+1);sx++){
      total++; const i=(sy*src.w+sx)*4,d=src.data;
      if(isKey(d[i],d[i+1],d[i+2],d[i+3])) continue;
      fg++; const c=nearest(d[i],d[i+1],d[i+2]); votes[palette.indexOf(c)]++;
    }
    if(!total||fg/total<.12) continue;
    let pi=0; for(let i=1;i<votes.length;i++) if(votes[i]>votes[pi]) pi=i;
    const oi=((row*outCell+py)*outW+dstCol*outCell+px)*4,c=palette[pi];
    out[oi]=c[0];out[oi+1]=c[1];out[oi+2]=c[2];out[oi+3]=255;
  }
}

/* Hats are keyed to the already-approved 32px static icon.  Its alpha box is the
   exact resting size and forehead position; ImageGen supplies the side/back views
   and the tiny pose changes.  This keeps wide brims, low headbands, and tall cones
   consistent with the inventory icon while preventing any frame from floating.

   Walking alternates a single-pixel delayed sway.  Attack frames follow the body's
   lunge by at most one pixel, and the final source pose carries the visible hurt
   tilt.  The shifts are deliberately smaller than weapon/shield motion. */
const staticHat=overlay==='hat'?decodePng(staticRef):null;
const staticHatBox=staticHat&&opaqueBounds(staticHat);
if(overlay==='hat' && (!staticHatBox||staticHat.w!==outCell||staticHat.h!==outCell))
  throw new Error('--static-ref for a hat must be a non-empty '+outCell+'x'+outCell+' PNG');
let targetHatBox=staticHatBox;
if(overlay==='hat'&&hatBoxSpec){
  const q=hatBoxSpec.split(',').map(Number);
  if(q.length!==4||q.some(n=>!Number.isInteger(n))||q[0]<0||q[1]<0||q[2]>=outCell||q[3]>=outCell||q[2]<q[0]||q[3]<q[1])
    throw new Error('--hat-box must be four inclusive pixel coordinates: left,top,right,bottom');
  targetHatBox={l:q[0],t:q[1],r:q[2],b:q[3],w:q[2]-q[0]+1,h:q[3]-q[1]+1};
}
const hatScale=targetHatBox?Math.min(targetHatBox.w/maxW,targetHatBox.h/maxH):scale;
function drawHatCell(dstCol,row,srcCol){
  const cell=cells[row*srcCols+srcCol],box=cell.box;
  const dw=Math.max(1,Math.round(box.w*hatScale)),dh=Math.max(1,Math.round(box.h*hatScale));
  const walk=dstCol>=2&&dstCol<=5,attack=dstCol>=6&&dstCol<=8,hurt=dstCol===9;
  let shiftX=walk?(dstCol===2?-1:dstCol===4?1:0):0,shiftY=0;
  if(attack){
    if(row===0) shiftY=dstCol===6?1:dstCol===7?1:0;
    else if(row===1) shiftX=dstCol===6?-1:dstCol===7?1:0;
    else shiftY=dstCol===6?1:dstCol===7?-1:0;
  } else if(hurt){
    shiftX=row===1?-1:2;
    shiftY=row===0?-1:row===2?1:0;
  }
  const cx=(targetHatBox.l+targetHatBox.r)/2+shiftX;
  const bottom=targetHatBox.b+shiftY;
  const dx=Math.round(cx-(dw-1)/2),dy=Math.round(bottom-dh+1);
  for(let oy=0;oy<dh;oy++) for(let ox=0;ox<dw;ox++){
    const px=dx+ox,py=dy+oy;
    if(px<0||px>=outCell||py<0||py>=outCell) continue;
    const sx0=box.l+Math.floor(ox*box.w/dw),sx1=box.l+Math.max(1,Math.floor((ox+1)*box.w/dw));
    const sy0=box.t+Math.floor(oy*box.h/dh),sy1=box.t+Math.max(1,Math.floor((oy+1)*box.h/dh));
    const votes=new Array(palette.length).fill(0); let fg=0,total=0;
    for(let sy=sy0;sy<Math.min(sy1,box.b+1);sy++) for(let sx=sx0;sx<Math.min(sx1,box.r+1);sx++){
      total++; const i=(sy*src.w+sx)*4,d=src.data;
      if(isKey(d[i],d[i+1],d[i+2],d[i+3])) continue;
      fg++; const c=nearest(d[i],d[i+1],d[i+2]); votes[palette.indexOf(c)]++;
    }
    if(!total||fg/total<.12) continue;
    let pi=0; for(let i=1;i<votes.length;i++) if(votes[i]>votes[pi]) pi=i;
    const oi=((row*outCell+py)*outW+dstCol*outCell+px)*4,c=palette[pi];
    out[oi]=c[0];out[oi+1]=c[1];out[oi+2]=c[2];out[oi+3]=255;
  }
}

/* A generated face opening can be visually correct at source resolution yet miss
   the real 32px eyes by one or two pixels after downsampling.  For enclosing hats,
   optionally derive the eye boxes from the actual body atlas and punch those boxes
   out of the overlay.  This guarantees that idle, walk, attack, and hurt frames keep
   the character's original eyes rather than painted replacement eyes.

   Bright components are searched only in the face band, so the dome highlight is
   ignored.  The front row keeps the top two components (both eyes); the side row
   keeps the top component (the visible eye).  The lower mouth diamond is later and
   therefore is not selected. */
function clearHatEyeWindows(file){
  const body=decodePng(file);
  if(body.w!==outW||body.h!==outH)
    throw new Error(`--body-ref must be ${outW}x${outH}`);
  const n=outCell*outCell,q=new Int32Array(n);
  for(let row=0;row<2;row++) for(let col=0;col<10;col++){
    const mask=new Uint8Array(n),seen=new Uint8Array(n),comps=[];
    for(let y=12;y<=24;y++) for(let x=0;x<outCell;x++){
      const i=((row*outCell+y)*outW+col*outCell+x)*4,d=body.data;
      if(d[i+3]>0&&d[i]>=235&&d[i+1]>=230&&d[i+2]>=220) mask[y*outCell+x]=1;
    }
    for(let seed=0;seed<n;seed++){
      if(!mask[seed]||seen[seed]) continue;
      let head=0,tail=0,count=0,l=outCell,t=outCell,r=-1,b=-1;
      q[tail++]=seed;seen[seed]=1;
      while(head<tail){
        const p=q[head++],x=p%outCell,y=Math.floor(p/outCell);count++;
        if(x<l)l=x;if(x>r)r=x;if(y<t)t=y;if(y>b)b=y;
        for(let yy=Math.max(0,y-1);yy<=Math.min(outCell-1,y+1);yy++)
          for(let xx=Math.max(0,x-1);xx<=Math.min(outCell-1,x+1);xx++){
            const z=yy*outCell+xx;if(mask[z]&&!seen[z]){seen[z]=1;q[tail++]=z;}
          }
      }
      if(count>=2) comps.push({l,t,r,b,count});
    }
    comps.sort((a,b)=>a.t-b.t||b.count-a.count);
    const take=comps.slice(0,row===0?2:1);
    if(!take.length) continue;
    const l=Math.max(0,Math.min(...take.map(c=>c.l))-1);
    const r=Math.min(outCell-1,Math.max(...take.map(c=>c.r))+1);
    const t=Math.max(0,Math.min(...take.map(c=>c.t))-1);
    const b=Math.min(outCell-1,Math.max(...take.map(c=>c.b))+1);
    for(let y=t;y<=b;y++) for(let x=l;x<=r;x++){
      const i=((row*outCell+y)*outW+col*outCell+x)*4;
      out[i]=out[i+1]=out[i+2]=out[i+3]=0;
    }
  }
}
for(let row=0;row<3;row++) for(let col=0;col<10;col++)
  (overlay==='weapon'?drawWeaponCell:
   overlay==='shield'?drawShieldCell:
   overlay==='hat'?drawHatCell:drawCell)(col,row,map[col]);
if(clearHatEyes) clearHatEyeWindows(bodyRef);
encodePng(outW,outH,out,output);
if(previewBody){
  const body=decodePng(previewBody);
  if(body.w!==outW||body.h!==outH)
    throw new Error(`--preview-body must be ${outW}x${outH}`);
  const preview=new Uint8Array(body.data);
  for(let i=0;i<preview.length;i+=4){
    const sa=out[i+3]/255,da=preview[i+3]/255,oa=sa+da*(1-sa);
    if(oa<=0) continue;
    preview[i]=Math.round((out[i]*sa+preview[i]*da*(1-sa))/oa);
    preview[i+1]=Math.round((out[i+1]*sa+preview[i+1]*da*(1-sa))/oa);
    preview[i+2]=Math.round((out[i+2]*sa+preview[i+2]*da*(1-sa))/oa);
    preview[i+3]=Math.round(oa*255);
  }
  encodePng(outW,outH,preview,previewOut);
}
if(staticOut){
  const one=new Uint8Array(outCell*outCell*4);
  for(let y=0;y<outCell;y++) one.set(out.subarray((y*outW)*4,(y*outW+outCell)*4),y*outCell*4);
  encodePng(outCell,outCell,one,staticOut);
}
const bytes=fs.statSync(output).size;
console.log(`wrote ${output} (${(bytes/1024).toFixed(1)} KB), scale=${scale.toFixed(4)}, source=${src.w}x${src.h}, max=${maxW}x${maxH} at ${widest.col},${widest.row}/${tallest.col},${tallest.row}`);
const budget=(outCell===48?64:32)*1024;
if(bytes>budget) throw new Error(`output exceeds ${budget/1024} KB animation budget`);
