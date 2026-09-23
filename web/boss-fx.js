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
