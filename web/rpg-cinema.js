/* Full viewport cinematics. All animation is presentation-only; no game turns advance. */
(() => {
  const url=id=>{const f=HD_ASSETS[id];return f?globalThis.BABEL_HD_DATA?.[f]||'art-hd/'+f:'';};
  const reduced=matchMedia('(prefers-reduced-motion:reduce)').matches;
  const cover=document.getElementById('coverposter');
  if(cover&&HD_MODE)cover.style.backgroundImage='url("'+url('hd:prologue-2')+'")';
  if(LANG==='zh'){
    document.querySelector('#cover h1').innerHTML='<small>深度學習</small><span>通天之塔</span>';
    document.querySelector('#cover .lede').innerHTML='在神廟甦醒，向地底尋找塔門。<br><b>每一次重來，都帶著學會的勇氣。</b>';
  }
  for(const id of ['prologuevisual','cover']){
    const el=document.createElement('div');el.className='cinema-dust';el.setAttribute('aria-hidden','true');document.getElementById(id).append(el);
  }
  // The epilogue answers the opening motif in a slower, open register.
  for(const [id,src,title,bpm,notes,instrument]of [
    ['ending_afterglow','chapter_temple','塔安靜下來了',60,[62,65,69,74,72,69,65,62,64,67,71,76,74,71,67,62],'bell'],
    ['ending_home','village','有人等你回來',72,[67,69,71,74,76,74,71,69,67,64,62,64,67,71,69,67],'flute'],
    ['ending_horizon','terrace','下一個問題',58,[74,76,79,81,83,81,79,76,74,71,67,69,74,79,76,74],'bell']
  ]){
    const t=JSON.parse(JSON.stringify(BGM.TRACKS[src]));Object.assign(t,{title,bpm,bars:16,instrument,pluck:'lyre',lvol:.063,avol:.026,kick:[],hat:[],tom:[]});
    t.lead=Array.from({length:4},(_,b)=>[0,4,8,12].map((step,i)=>[step,notes[b*4+i],4]));
    t.answer=t.lead.map((bar,b)=>bar.map(([s,n,d],i)=>[s,n+(b===3&&i===3?0:12),d]));BGM.TRACKS[id]=t;
  }
  const overlay=document.createElement('section');overlay.id='ending-cinema';overlay.hidden=true;overlay.setAttribute('role','dialog');overlay.setAttribute('aria-modal','true');overlay.setAttribute('aria-labelledby','ending-title');
  overlay.innerHTML='<div id="ending-stage" aria-hidden="true"><div class="ending-plate"></div><div class="ending-plate"></div><div id="ending-cast"></div><div class="ending-light"></div><div class="cinema-dust"></div></div><div id="ending-caption"><div id="ending-kicker"></div><h2 id="ending-title"></h2><div id="ending-body" aria-live="polite"></div></div><nav id="ending-controls" aria-label="結局播放控制"><button id="ending-prev">上一幕</button><button id="ending-pause">暫停閱讀</button><button id="ending-next">下一幕</button><button id="ending-replay" hidden>重播結局</button><button id="ending-return" hidden>返回村莊</button><span id="ending-count"></span></nav>';
  document.body.append(overlay);
  const $=id=>document.getElementById(id),plates=[...overlay.querySelectorAll('.ending-plate')];
  const shots=[
    ['hd:chapter-final','塔安靜下來了','ending_afterglow','aftermath'],
    ['hd:chapter-beast','旅程仍有人接續','ending_afterglow','cavern'],
    ['hd:chapter-hall','有人等你回來','ending_home','home'],
    ['hd:prologue-2','每一步，都留了下來','ending_home','memory'],
    ['hd:chapter-chaos','虛空最深處','ending_horizon','void'],
    ['hd:chapter-chaos','意識成為光','ending_horizon','light'],
    ['hd:terrace','向著下一次黎明','ending_horizon','dawn'],
    ['hd:terrace','下一個問題','ending_horizon','horizon'],
    ['hd:terrace','深度學習：通天之塔','ending_horizon','end']
  ];
  let parts=[],index=0,timer=0,paused=reduced,finished=false,plate=0;
  function clear(){clearTimeout(timer);timer=0;}
  function schedule(){clear();if(paused||finished||document.hidden)return;timer=setTimeout(next,Math.max(9500,Math.min(20000,$('ending-body').textContent.length*140)));}
  function controls(){
    $('ending-prev').textContent=locUI('上一幕','Previous','まえへ');$('ending-next').textContent=locUI('下一幕','Next','つぎへ');$('ending-replay').textContent=locUI('重播結局','Replay','もう一度');$('ending-return').textContent=locUI('返回村莊','Return to village','村にもどる');$('ending-prev').disabled=index===0;$('ending-pause').textContent=paused?locUI('自動播放','Auto-play','自動再生する'):locUI('暫停閱讀','Pause','一時停止する');$('ending-pause').setAttribute('aria-pressed',String(paused));
    for(const id of ['ending-pause','ending-next'])$(id).hidden=finished;
    for(const id of ['ending-replay','ending-return'])$(id).hidden=!finished;
    $('ending-count').textContent=String(index+1).padStart(2,'0')+' / '+parts.length;overlay.classList.toggle('paused',paused);
  }
  function sprite(src,cls){const im=document.createElement('img');im.src=src;im.className=cls;im.alt='';$('ending-cast').append(im);}
  function show(){
    clear();finished=index===parts.length-1;const shot=shots[Math.min(index,8)];overlay.dataset.shot=shot[3];
    plate=1-plate;plates[plate].style.backgroundImage='url("'+url(shot[0])+'")';plates[plate].classList.remove('visible');void plates[plate].offsetWidth;
    plates[plate].classList.add('visible');plates[1-plate].classList.remove('visible');
    $('ending-kicker').textContent=finished?'THE JOURNEY CONTINUES':'EPILOGUE · '+String(index+1).padStart(2,'0');
    $('ending-title').textContent=LANG==='zh'?shot[1]:TX('end.title','你成為了「意識」');
    $('ending-body').innerHTML=parts[index];$('ending-caption').scrollTop=0;
    $('ending-cast').replaceChildren();
    if(index===2){
      sprite(url('hd:town-cave-forge'),'end-forge');sprite(url('hd:town-cave-inn'),'end-inn');sprite(url('npc#smith'),'end-smith');sprite(url('npc#child'),'end-child');
    }
    if(index===0||index===3||index>=6)sprite(heroNow().toDataURL('image/png'),'end-hero');
    if(finished){const p=document.createElement('p');p.className='ending-record';p.textContent='通關 '+VILLAGE.cleared+' 次 · '+(VILLAGE.relicForged?'四像封印已融合 · 諸神的黃昏':'四像封印 '+Object.keys(VILLAGE.relicSeals||{}).length+'/4');$('ending-body').append(p);const c=document.createElement('p');c.className='ending-credit';c.textContent='潔米爸 × 小潔米株式會社　出品';$('ending-body').append(c);}
    BGM.force(shot[2]);controls();schedule();
  }
  function next(){if(index<parts.length-1){index++;show();}}
  function previous(){if(index>0){index--;show();}}
  function pause(){paused=!paused;controls();schedule();}
  $('ending-next').onclick=next;$('ending-prev').onclick=previous;$('ending-pause').onclick=pause;
  $('ending-replay').onclick=()=>{index=0;paused=reduced;show();$('ending-next').focus();};
  $('ending-return').onclick=()=>{clear();overlay.hidden=true;$('over').classList.remove('show','roll');openVillage();};
  document.addEventListener('visibilitychange',()=>{if(document.hidden&&!overlay.hidden){paused=true;controls();clear();}});
  window.addEventListener('keydown',e=>{
    if(overlay.hidden)return;
    if(e.key==='Tab'){
      const bs=[...overlay.querySelectorAll('button')].filter(b=>!b.hidden&&!b.disabled),first=bs[0],last=bs[bs.length-1];
      if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus();}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus();}return;
    }
    if(e.key==='ArrowRight'){e.preventDefault();next();}else if(e.key==='ArrowLeft'){e.preventDefault();previous();}else if(e.key==='Escape'){e.preventDefault();paused=true;controls();clear();}
    e.stopImmediatePropagation();
  },true);
  globalThis.RPG_ENDING={start(text){parts=text.slice();index=0;paused=reduced;overlay.hidden=false;show();$('ending-next').focus({preventScroll:true});},get active(){return !overlay.hidden;},get index(){return index;}};

  // Warn before anything leaves the wall; the same turn countdown drives art and combat.
  const oldGround=RPG_PRESSURE.drawGround,oldUpdate=RPG_PRESSURE.update;
  RPG_PRESSURE.update=()=>{oldUpdate();const bar=$('pressure-status'),s=G?.f?.pursuit,m=G?.mons.find(m=>m.hp>0&&m.d.hunter&&!m.d.relic);
    if(s?.pending)bar.textContent=(s.pending.kind==='lion'?'石爪聲逼近':'牆面浮雕碎裂')+' · '+s.pending.left+' 行動後甦醒 ｜ 閱讀暫停';
    else if(m)bar.textContent=m.d.nm+' 正在追獵 ｜ 找樓梯撤離，或閃過重擊後反擊';};
  RPG_PRESSURE.drawGround=(c,ox,oy)=>{
    oldGround(c,ox,oy);const q=G?.f?.pursuit?.pending,tm=performance.now()/1000;
    if(q&&G.seen[key(q.x,q.y)]===2){
      const emerge=q.kind==='wall'?Math.max(0,Math.min(1,(4-q.left)/3)):1;
      const x=ox+((q.wx??q.x)+((q.x-(q.wx??q.x))*emerge)+.5)*T,y=oy+((q.wy??q.y)+((q.y-(q.wy??q.y))*emerge)+.8)*T;c.save();
      if(q.kind==='wall'){
        const img=HD_LOADED['hd:hunter-wall-'+(q.left>2?'relief':'emerge')];
        if(img){c.globalAlpha=q.left>2?.6:.92;c.drawImage(img,x-T*1.5,y-T*2.6,T*3,T*3);}
        c.globalAlpha=1;c.strokeStyle='#f2d695';c.lineWidth=.8;c.beginPath();c.moveTo(x-T*.5,y-T*2);c.lineTo(x,y-T*1.4);c.lineTo(x-T*.2,y-T);c.lineTo(x+T*.4,y);c.stroke();
      }
      c.fillStyle='#ffe5b1';c.font='bold 5px sans-serif';c.textAlign='center';c.fillText(q.left+' 行動後甦醒',x,y+T*.7);c.restore();
    }
    for(const m of G?.mons||[]){if(!m.d.relic||m.hp<=0||G.seen[key(m.x,m.y)]!==2)continue;
      c.save();c.strokeStyle=m.d.color;c.lineWidth=.8;c.globalAlpha=reduced?.7:.65+.2*Math.sin(tm*2);c.beginPath();c.ellipse(ox+(m.x+.5)*T,oy+(m.y+.8)*T,T*1.1,T*.5,0,0,Math.PI*2);c.stroke();
      c.globalAlpha=1;c.fillStyle=m.d.color;c.font='bold 5px sans-serif';c.textAlign='center';c.fillText(m.awake?'四像封印':m.d.nm+' · 攻擊挑戰',ox+(m.x+.5)*T,oy+(m.y+1.6)*T);c.restore();
    }
  };
  // Code-native weapon detail follows the established layered equipment renderer.
  const sword=document.createElement('canvas');sword.width=sword.height=256;const c=sword.getContext('2d');
  c.translate(128,125);c.rotate(.38);const steel=c.createLinearGradient(-16,0,18,0);steel.addColorStop(0,'#5f6684');steel.addColorStop(.48,'#ecf4ff');steel.addColorStop(.55,'#ffffff');steel.addColorStop(1,'#8b779b');
  c.fillStyle=steel;c.strokeStyle='#ead6a6';c.lineWidth=3;c.beginPath();c.moveTo(0,-113);c.lineTo(18,-78);c.lineTo(11,55);c.lineTo(-11,55);c.lineTo(-18,-78);c.closePath();c.fill();c.stroke();
  c.strokeStyle='#b78463';c.lineWidth=2;for(let y=-65;y<35;y+=19){c.beginPath();c.moveTo(0,y-7);c.lineTo(5,y);c.lineTo(0,y+7);c.lineTo(-5,y);c.closePath();c.stroke();}
  c.fillStyle='#bb914d';c.beginPath();c.moveTo(-48,35);c.lineTo(-37,58);c.lineTo(-12,65);c.lineTo(12,65);c.lineTo(37,58);c.lineTo(48,35);c.lineTo(22,47);c.lineTo(-22,47);c.closePath();c.fill();
  for(const [i,color]of ['#e4a064','#77d0e4','#c4a6fb','#ffeab1'].entries()){c.fillStyle=color;c.beginPath();c.arc(-27+i*18,53,4,0,Math.PI*2);c.fill();}
  c.fillStyle='#302d44';c.fillRect(-7,65,14,32);c.strokeStyle='#c0a163';for(let y=67;y<98;y+=7){c.beginPath();c.moveTo(-7,y);c.lineTo(7,y+4);c.stroke();}c.fillStyle='#d9b867';c.beginPath();c.arc(0,101,9,0,Math.PI*2);c.fill();
  sword._hd=true;HD_LOADED['weap#10']=sword;atlas['weap#10']=sword;
})();
