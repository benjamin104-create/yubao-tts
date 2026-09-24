/* World-space boss magic. Presentation never writes HP, turns, RNG or terrain. */
(() => {
  let owner=null,events=[],banner=null,notice='',noticeUntil=0;
  const colors={earth:['#f1be71','#fff5ce'],root:['#66dba1','#e4ffd1'],fire:['#ff7845','#fff1b5'],water:['#61cfe8','#e6ffff'],crystal:['#b9a0ff','#f9eaff'],void:['#c583fa','#fff0ff']};
  const themes={b_keeper:'earth',b_warden:'earth',b_treant:'root',b_ballista:'earth',b_pyro:'fire',b_lord:'water',b_mermaid:'water',b_phoenix:'fire',b_hanzo:'void',b_oni:'fire',b_queen:'crystal',b_prism:'crystal',b_hallking:'earth',b_gate:'void',b_mind:'void',b_mind2:'void',b_mind1:'void',b_artisan:'crystal'};
  const titles={earth:{quake:'地脈崩裂',slam:'封印重槌',beam:'神殿裁光',charge:'石門衝陣'},root:{quake:'古根怒濤',beam:'翠脈穿心'},fire:{quake:'焚界炎環',beam:'赤焰天柱',charge:'灼魂突進'},water:{quake:'深潮迴響',beam:'滄海詠嘆'},crystal:{quake:'稜鏡碎界',beam:'萬象晶光',charge:'鏡界穿梭'},void:{quake:'虛空震盪',beam:'歸一凝視',charge:'裂隙突襲'}};
  const profile=m=>{const theme=themes[m.d.id]||(m.d.mind?'void':m.d.turret?'crystal':'earth');return {theme,col:colors[theme][0],core:colors[theme][1]};};
  const clear=()=>{if(owner!==G){owner=G;events=[];notice='';noticeUntil=0;}};
  function release(m,kind,aim){
    if(!(m?.d?.boss||m?.d?.hunter)||!G)return;clear();
    kind=kind==='bossSlam'?'slam':kind==='shoot'?'beam':kind;
    if(!['slam','quake','beam','charge'].includes(kind))return;
    const stamp=m.id+':'+G.turn+':'+kind;if(events.some(e=>e.stamp===stamp))return;
    const v=profile(m),now=performance.now()/1000;
    events.push({...v,stamp,kind,x:m.x,y:m.y,ax:aim?.x??G.p.x,ay:aim?.y??G.p.y,start:now,dur:REDUCED?.5:1.55,radius:kind==='slam'?1:3});
    events=events.slice(-5);notice=locName('mon',m.d)+' · '+(titles[v.theme][kind]||titles.earth[kind]);noticeUntil=now+1.65;
    SFX.play(kind==='quake'||kind==='slam'?'slam':'cast',180);
  }
  function circle(c,x,y,r,col,width=1,flat=1){c.strokeStyle=col;c.lineWidth=width;c.beginPath();c.ellipse(x,y,r,r*flat,0,0,Math.PI*2);c.stroke();}
  function rune(c,x,y,r,col,rot){
    circle(c,x,y,r,col,.65,.53);circle(c,x,y,r*.78,col,.4,.53);
    c.save();c.translate(x,y);c.scale(1,.53);c.rotate(rot);c.strokeStyle=col;c.lineWidth=.6;
    for(let i=0;i<12;i++){const a=i*Math.PI/6;c.save();c.rotate(a);c.beginPath();c.moveTo(r*.83,0);c.lineTo(r*.93,0);c.lineTo(r*.9,-2);c.stroke();c.restore();}
    c.beginPath();for(let i=0;i<=8;i++){const a=i*Math.PI/4,z=i===0?'moveTo':'lineTo';c[z](Math.cos(a)*r*.63,Math.sin(a)*r*.63);}c.stroke();c.restore();
  }
  function cells(m){
    const w=m.warn,rad=m.qWarn?3:w?.kind==='slam'?1:0,out=[];
    const cx=w?.cx??m.x,cy=w?.cy??m.y;
    if(rad){for(let y=cy-rad;y<=cy+rad;y++)for(let x=cx-rad;x<=cx+rad;x++)if(x>=0&&y>=0&&x<MW&&y<MH&&walkable(x,y)&&G.seen[key(x,y)]===2)out.push([x,y]);}
    else if(w){for(let y=0;y<MH;y++)for(let x=0;x<MW;x++)if((x===w.x||y===w.y)&&walkable(x,y)&&G.seen[key(x,y)]===2)out.push([x,y]);}
    return out;
  }
  function drawGround(c,ox,oy){
    if(!G)return;clear();const time=performance.now()/1000;
    for(const m of G.mons){if(!(m.d.boss||m.d.hunter)||(!m.warn&&!m.qWarn)||G.seen[key(m.x,m.y)]!==2)continue;
      const p=profile(m),x=ox+(m.x+.5)*T,y=oy+(m.y+.6)*T,list=cells(m);
      c.save();c.globalAlpha=REDUCED?.25:.21+.07*Math.sin(time*3);c.fillStyle=p.col;
      for(const [gx,gy]of list)c.fillRect(ox+gx*T+1,oy+gy*T+1,T-2,T-2);
      c.globalAlpha=.8;c.strokeStyle=p.core;c.lineWidth=.65;
      const set=new Set(list.map(q=>q.join(',')));
      for(const [gx,gy]of list){const xx=ox+gx*T,yy=oy+gy*T;c.beginPath();if(!set.has(gx+','+(gy-1))){c.moveTo(xx,yy);c.lineTo(xx+T,yy);}if(!set.has((gx+1)+','+gy)){c.moveTo(xx+T,yy);c.lineTo(xx+T,yy+T);}if(!set.has(gx+','+(gy+1))){c.moveTo(xx,yy+T);c.lineTo(xx+T,yy+T);}if(!set.has((gx-1)+','+gy)){c.moveTo(xx,yy);c.lineTo(xx,yy+T);}c.stroke();}
      c.globalAlpha=.8;rune(c,x,y,T*(m.qWarn?3.6:2),p.col,REDUCED?0:time*.18);c.restore();
    }
  }
  function draw(c,ox,oy){
    if(!G)return;clear();const now=performance.now()/1000;events=events.filter(e=>now-e.start<e.dur);
    for(const e of events){const t=(now-e.start)/e.dur,fade=Math.sin(Math.PI*Math.min(1,t))*.8,x=ox+(e.x+.5)*T,y=oy+(e.y+.6)*T;
      c.save();c.globalCompositeOperation='screen';c.globalAlpha=fade;
      if(REDUCED){rune(c,x,y,T*(e.radius+.6),e.col,0);c.restore();continue;}
      const r=T*(e.radius+.6)*(1-Math.pow(1-t,3));
      // Three staggered shock fronts carry the weight of the release.
      if(e.kind==='quake'||e.kind==='slam'){
        for(let i=0;i<3;i++){const k=Math.max(0,t-i*.10),rr=T*(e.radius+.7)*(1-Math.pow(1-k,3));circle(c,x,y,rr,e.col,Math.max(.5,2.5-i*.5),.65);}
        rune(c,x,y,T*(e.radius+.4),e.col,t*.3);
        for(let i=0;i<20;i++){
          const a=i*Math.PI*2/20,dist=r*(.55+(i%3)*.17),xx=x+Math.cos(a)*dist,yy=y+Math.sin(a)*dist*.68,up=Math.sin(t*Math.PI)*(6+i%4*4);
          c.strokeStyle=e.col;c.lineWidth=i%3===0?1.3:.6;c.beginPath();c.moveTo(x+Math.cos(a)*T*.45,y+Math.sin(a)*T*.3);c.lineTo(xx-Math.sin(a)*3,yy+2);c.lineTo(xx,yy);c.stroke();
          if(e.theme==='root'){c.lineWidth=2;c.beginPath();c.moveTo(xx,yy);c.quadraticCurveTo(xx+8,yy-up-8,xx-3,yy-up-14);c.stroke();}
          else if(e.theme==='fire'){const g=c.createLinearGradient(xx,yy,xx,yy-up-16);g.addColorStop(0,e.col);g.addColorStop(1,e.col+'00');c.fillStyle=g;c.beginPath();c.moveTo(xx-3,yy);c.quadraticCurveTo(xx+6,yy-up-8,xx,yy-up-18);c.lineTo(xx+3,yy);c.fill();}
          else if(e.theme==='water'){circle(c,xx,yy-up,3,e.core,.7,.5);}
          else{c.fillStyle=i%2?e.col:e.core;c.save();c.translate(xx,yy-up);c.rotate(a+t*2);c.fillRect(-1.5,-2,3,4);c.restore();}
        }
      }else{
        const ax=ox+(e.ax+.5)*T,ay=oy+(e.ay+.5)*T;
        // The beam follows the same cross as its warning. Only visible floor
        // tiles glow; walls and unseen rooms stay intact.
        c.lineCap='round';for(let pass=0;pass<3;pass++){c.strokeStyle=pass===2?e.core:e.col;c.globalAlpha=fade*(pass===0?.20:pass===1?.45:.9);c.lineWidth=[T*.86,T*.30,T*.065][pass]*(1-t*.5);
          c.beginPath();for(let yy=0;yy<MH;yy++)if(walkable(e.ax,yy)&&G.seen[key(e.ax,yy)]===2){c.moveTo(ax,oy+yy*T);c.lineTo(ax,oy+(yy+1)*T);}for(let xx=0;xx<MW;xx++)if(walkable(xx,e.ay)&&G.seen[key(xx,e.ay)]===2){c.moveTo(ox+xx*T,ay);c.lineTo(ox+(xx+1)*T,ay);}c.stroke();}
        c.globalAlpha=fade;rune(c,x,y,T*2.2,e.col,t*.7);
        for(let i=0;i<12;i++){const a=i*Math.PI/6;circle(c,ax+Math.cos(a)*T*(.3+t*2),ay+Math.sin(a)*T*(.3+t*2),1.1,e.core,.8);}
      }
      // Keep the player silhouette readable even at the effect's peak.
      c.globalCompositeOperation='source-over';c.globalAlpha=.75;c.strokeStyle='#fff0c6';c.lineWidth=.7;circle(c,ox+(G.p.x+.5)*T,oy+(G.p.y+.8)*T,T*.42,'#fff0c6',.7,.4);c.restore();
    }
    updateBanner(now);
  }
  function updateBanner(now){
    if(!banner){banner=document.createElement('aside');banner.id='boss-art-banner';banner.setAttribute('aria-live','polite');document.getElementById('main').append(banner);}
    const m=G.mons.find(m=>m.d.boss&&(m.warn||m.qWarn)&&G.seen[key(m.x,m.y)]===2),text=noticeUntil>now?notice:m?locName('mon',m.d)+' · '+(m.qWarn?'地脈蓄力：離開標示區域':m.warn.kind==='slam'?'重槌蓄力：退離身邊一格':'術式蓄力：離開交叉光線'):'';
    if(banner.textContent!==text)banner.textContent=text;banner.hidden=!text;banner.dataset.phase=noticeUntil>now?'impact':'charge';
  }
  function focus(){
    if(!G||REDUCED)return null;clear();const now=performance.now()/1000;
    const m=G.mons.find(m=>m.d.boss&&(m.warn||m.qWarn)&&G.seen[key(m.x,m.y)]===2),e=events.find(e=>now-e.start<e.dur);
    const o=m||e;if(!o)return null;
    const scale=m?bossVisualScale(m.d):3,r=m?.qWarn||e?.kind==='quake'?3:1;
    const left=Math.min(G.p.x-1,o.x-r-1),right=Math.max(G.p.x+1,o.x+r+1),top=Math.min(G.p.y-1,o.y-Math.max(scale,r)-1),bottom=Math.max(G.p.y+1,o.y+r+1);
    return {x:Math.max(G.p.x-VW/2+1.5,Math.min(G.p.x+VW/2-1.5,(left+right)/2)),y:Math.max(G.p.y-VH/2+1.5,Math.min(G.p.y+VH/2-1.5,(top+bottom)/2))};
  }
  globalThis.RPG_BOSS_FX={release,drawGround,draw,cells,focus,get active(){return QA_MODE?events.map(e=>({...e})):undefined;}};
})();

/* Player spells have distinct silhouettes and three visual beats. Pure presentation:
   no combat RNG, costs, damage, targeting or turn scheduling is changed here. */
(() => {
  let owner=null,floor=null,events=[];
  const palettes={fire:['#ff7745','#fff3c2'],aqua:['#67cbff','#efffff'],bolt:['#b5abff','#fffbdc'],wind:['#64dfba','#e6fff3'],heal:['#8ce5a4','#fff0b5'],blade:['#efc481','#fff9e8'],shadow:['#b9a1ef','#ebe8ff']};
  const types={smash:'blade',duplex:'blade',onicut:'shadow',pyro:'fire',deluge:'aqua',pierce:'wind',m_gale:'wind',m_smite:'bolt',m_mail:'bolt',m_pyre:'fire',m_core:'fire',m_zero:'aqua',m_mirror:'aqua',m_judge:'heal',m_revive:'heal',mend:'heal',ward:'heal',guard:'blade',veil:'shadow',reflect:'aqua',clone:'shadow',foresee:'shadow',m_shift:'wind',lull:'aqua',anthem:'heal',circle:'shadow',survey:'wind'};
  const reset=()=>{if(owner!==G||floor!==G?.f){owner=G;floor=G?.f;events=[];}};
  types.meditate='heal';types.sageward='heal';
  function cast(def,dx,dy){
    if(!G)return;reset();const p=G.p,theme=def.sc||types[def.id]||'blade',k=def.k||'self',hits=[];
    let end={x:p.x,y:p.y};
    if(def.id==='m_gale'){
      for(const [vx,vy]of DIRS)for(let n=1;n<=7;n++){const x=p.x+vx*n,y=p.y+vy*n;if(!walkable(x,y)||G.seen[key(x,y)]!==2)break;if(monAt(x,y))hits.push({x,y});}
    }else if(k==='beam'||k==='blast'){
      const range=def.id==='m_smite'?12:def.id==='gust'?8:def.sc?9:10;
      for(let n=1;n<=range;n++){const x=p.x+dx*n,y=p.y+dy*n;if(!walkable(x,y)||G.seen[key(x,y)]!==2)break;end={x,y};const m=monAt(x,y);if(m){hits.push({x,y});if(k==='blast')break;}}
      if(!hits.length)hits.push(end);
    }else if(k==='room'||k==='around'){
      for(const m of G.mons)if(m.hp>0&&G.seen[key(m.x,m.y)]===2&&(k==='room'||Math.max(Math.abs(m.x-p.x),Math.abs(m.y-p.y))<=1))hits.push({x:m.x,y:m.y});
    }else if(k==='melee'){end={x:p.x+dx,y:p.y+dy};if(walkable(end.x,end.y))hits.push(end);}
    else hits.push({x:p.x,y:p.y});
    const melee=['smash','duplex','onicut','m_gale'].includes(def.id);
    events.push({id:def.id,theme,k,melee,dx,dy,x:p.x,y:p.y,end,hits:hits.slice(0,12),start:performance.now()/1000,dur:REDUCED?.5:melee?.95:1.45,master:def.id.startsWith('m_')});
    events=events.slice(-4);
  }
  function ellipse(c,x,y,r,flat,col,width){c.strokeStyle=col;c.lineWidth=width;c.beginPath();c.ellipse(x,y,r,r*flat,0,0,Math.PI*2);c.stroke();}
  function rune(c,x,y,r,col,t){
    ellipse(c,x,y,r,.5,col,.65);ellipse(c,x,y,r*.76,.5,col,.35);
    c.strokeStyle=col;c.lineWidth=.7;
    for(let i=0;i<8;i++){const a=i*Math.PI/4+t,xx=x+Math.cos(a)*r*.87,yy=y+Math.sin(a)*r*.44;c.beginPath();c.moveTo(xx-1,yy-2);c.lineTo(xx+1,yy+2);c.moveTo(xx-2,yy);c.lineTo(xx+2,yy);c.stroke();}
  }
  function bloom(c,x,y,r,col){const g=c.createRadialGradient(x,y,0,x,y,r);g.addColorStop(0,col+'80');g.addColorStop(.4,col+'30');g.addColorStop(1,col+'00');c.fillStyle=g;c.fillRect(x-r,y-r,r*2,r*2);}
  function lightning(c,x,y,xx,yy,col,core,phase){
    const dx=xx-x,dy=yy-y,n=Math.hypot(dx,dy)||1,points=[];
    for(let i=0;i<=10;i++){const t=i/10,j=i===0||i===10?0:Math.sin(i*12.7+Math.floor(phase*9))*T*.23;points.push([x+dx*t-dy/n*j,y+dy*t+dx/n*j]);}
    for(const [w,a,color]of [[4,.22,col],[1.5,.8,col],[.5,1,core]]){c.save();c.globalAlpha*=a;c.strokeStyle=color;c.lineWidth=w;c.beginPath();points.forEach(([px,py],i)=>i?c.lineTo(px,py):c.moveTo(px,py));c.stroke();c.restore();}
  }
  function impact(c,e,x,y,t,col,core){
    const rise=Math.sin(Math.PI*t),r=T*(.35+t*(e.master?1.7:1.1));
    bloom(c,x,y,T*(e.master?1.6:1.1)*rise,col);
    if(e.theme==='fire'&&e.k!=='self'){
      ellipse(c,x,y,r,.45,col,1.3*(1-t)+.3);
      for(let i=0;i<7;i++){const a=i*2.4,xx=x+Math.cos(a)*r*.6,base=y+Math.sin(a)*r*.22,h=T*(.7+(i%3)*.35)*rise;
        const g=c.createLinearGradient(xx,base,xx,base-h);g.addColorStop(0,col);g.addColorStop(.55,core);g.addColorStop(1,col+'00');c.fillStyle=g;c.beginPath();c.moveTo(xx-3,base);c.quadraticCurveTo(xx-5,base-h*.45,xx+Math.sin(t*9+i)*4,base-h);c.quadraticCurveTo(xx+5,base-h*.3,xx+3,base);c.fill();}
    }else if(e.theme==='aqua'&&e.k!=='self'){
      ellipse(c,x,y,r,.5,col,.7);
      for(let i=0;i<6;i++){const a=i*Math.PI/3,xx=x+Math.cos(a)*T*.5,yy=y+Math.sin(a)*T*.25,h=T*(.7+(i%2)*.5)*rise;c.fillStyle=col+'66';c.strokeStyle=core;c.lineWidth=.65;c.beginPath();c.moveTo(xx-3,yy);c.lineTo(xx-1,yy-h);c.lineTo(xx+4,yy-h*.5);c.lineTo(xx+3,yy);c.closePath();c.fill();c.stroke();}
    }else if(e.theme==='bolt'&&e.k!=='self'){
      lightning(c,x+T*.3,y-T*2*rise,x,y,col,core,t);ellipse(c,x,y,r,.5,col,.7);
      for(let i=0;i<4;i++){const a=i*Math.PI/2+t;lightning(c,x,y,x+Math.cos(a)*r,y+Math.sin(a)*r*.5,col,core,t+i);}
    }else if(e.theme==='wind'&&e.k!=='self'){
      for(let i=0;i<4;i++){const yy=y-i*T*.27*rise,rr=r*(1-i*.13);c.strokeStyle=i%2?core:col;c.lineWidth=1.1;c.beginPath();c.ellipse(x,yy,rr,rr*.32,0,t*6+i,t*6+i+Math.PI*1.5);c.stroke();}
    }else if(e.k==='self'){
      rune(c,x,y,r,col,t*.3);
      if(['guard','ward','veil','reflect','m_mirror','m_mail','sageward'].includes(e.id)){c.strokeStyle=core;c.lineWidth=1;c.fillStyle=col+'18';c.beginPath();c.moveTo(x,y-T*1.7*rise);c.lineTo(x+T*.7,y-T*.95);c.lineTo(x+T*.55,y);c.lineTo(x,y+T*.35);c.lineTo(x-T*.55,y);c.lineTo(x-T*.7,y-T*.95);c.closePath();c.fill();c.stroke();}
      for(let i=0;i<8;i++){const a=i*Math.PI/4+t*2,xx=x+Math.cos(a)*T*.7,yy=y+Math.sin(a)*T*.3-T*t*1.6;c.strokeStyle=i%2?col:core;c.lineWidth=.9;c.beginPath();c.moveTo(xx-1.5,yy);c.lineTo(xx+1.5,yy);c.moveTo(xx,yy-2);c.lineTo(xx,yy+2);c.stroke();}
    }else{
      rune(c,x,y,r,col,t);for(let i=0;i<8;i++){const a=i*Math.PI/4;c.strokeStyle=core;c.lineWidth=.9;c.beginPath();c.moveTo(x+Math.cos(a)*r*.4,y+Math.sin(a)*r*.2);c.lineTo(x+Math.cos(a)*r,y+Math.sin(a)*r*.5);c.stroke();}
    }
  }
  function draw(c,ox,oy){
    if(!G)return;reset();const now=performance.now()/1000;events=events.filter(e=>now-e.start<e.dur);if(!events.length)return;
    c.save();c.beginPath();for(let y=0;y<MH;y++)for(let x=0;x<MW;x++)if(G.seen[key(x,y)]===2)c.rect(ox+x*T,oy+y*T,T,T);c.clip();
    for(const e of events){const t=(now-e.start)/e.dur,[col,core]=palettes[e.theme]||palettes.blade,x=ox+(e.x+.5)*T,y=oy+(e.y+.75)*T,fade=Math.min(1,t*9,Math.max(0,(1-t)*2.4));
      c.save();c.globalCompositeOperation='screen';c.globalAlpha=fade*.78;
      if(REDUCED){rune(c,x,y,T*.9,col,0);for(const hit of e.hits)ellipse(c,ox+(hit.x+.5)*T,oy+(hit.y+.65)*T,T*.5,.5,core,.8);c.restore();continue;}
      rune(c,x,y,T*(.7+Math.min(t,.25)*1.2),col,t*.4);
      if(e.melee){
        const a=Math.atan2(e.dy,e.dx),count=e.id==='duplex'?2:e.id==='m_gale'?4:1;
        for(let i=0;i<count;i++){const q=Math.max(0,Math.min(1,(t-i*.13)*1.8)),angle=a+(i%2?-1:1)*(-1.6+q*2.5);c.save();c.translate(x,y-T*.2);c.rotate(angle);c.globalAlpha*=Math.sin(Math.PI*q);const r=T*(e.master?2.3:1.6);c.fillStyle=col+'70';c.beginPath();c.arc(0,0,r,-.65,.65);c.quadraticCurveTo(r*.35,0,r*Math.cos(-.65),r*Math.sin(-.65));c.fill();c.strokeStyle=core;c.lineWidth=1.2;c.beginPath();c.arc(0,0,r,-.65,.65);c.stroke();c.restore();}
      }else if(e.k==='beam'||e.k==='blast'){
        const q=Math.max(0,Math.min(1,(t-.08)/.28)),xx=x+(e.end.x-e.x)*T*q,yy=y+(e.end.y-e.y)*T*q;
        if(t<.55){if(e.theme==='bolt')lightning(c,x,y,xx,yy,col,core,t);
          else{const grad=c.createLinearGradient(x,y,xx+0.01,yy+0.01);grad.addColorStop(0,col+'00');grad.addColorStop(1,col);c.strokeStyle=grad;c.lineWidth=e.theme==='wind'?2:3;c.beginPath();c.moveTo(x,y);c.lineTo(xx,yy);c.stroke();bloom(c,xx,yy,T*.8,col);c.fillStyle=core;c.beginPath();c.ellipse(xx,yy,e.theme==='aqua'?5:3,e.theme==='aqua'?1.5:3,Math.atan2(e.dy,e.dx),0,Math.PI*2);c.fill();}}
      }
      const start=e.melee?.18:.28;
      if(t>start)for(const [i,hit]of e.hits.entries()){const q=(t-start-i*.008)/(1-start);if(q<0||q>1)continue;c.save();c.globalAlpha*=Math.sin(Math.PI*q);impact(c,e,ox+(hit.x+.5)*T,oy+(hit.y+.75)*T,q,col,core);c.restore();}
      c.restore();
    }c.restore();
  }
  globalThis.RPG_PLAYER_FX={cast,draw,get active(){return QA_MODE?events.map(e=>({...e})):undefined;}};
})();
