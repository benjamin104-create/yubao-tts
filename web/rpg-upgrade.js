/* Original chapter scores: A / A with accompaniment / B / quiet reprise.
   Instrument-inspired synthesis is not a historical music reconstruction. */
(() => {
  const profiles=[
    ['temple',76,'reed','lyre','門廊的微光',[69,67,64,62,65,64,62,57,62,64,67,69,67,64,62,62]],
    ['mine',68,'flute','lyre','石層之下',[62,57,60,59,57,55,54,57,60,62,64,60,59,57,54,50]],
    ['forest',82,'flute','lyre','根系與微光',[76,74,71,69,67,71,74,76,79,76,74,71,69,67,64,67]],
    ['trial',96,'reed','lyre','山腹迴聲',[74,72,69,67,65,67,69,72,77,74,72,69,67,65,62,62]],
    ['ordeal',110,'bowed','lyre','四面石門',[69,70,69,64,65,64,62,61,64,65,69,70,73,70,69,64]],
    ['briar',94,'reed','lyre','灰燼中的枝蔓',[72,71,68,65,64,65,68,71,76,74,72,71,68,65,64,65]],
    ['lake',72,'bell','lyre','穹頂下的水鏡',[74,77,81,79,77,74,72,69,72,74,77,81,79,77,74,74]],
    ['beast',88,'flute','lyre','沉睡的幻獸',[67,70,72,74,77,74,72,70,67,65,62,65,67,70,74,67]],
    ['ninja',92,'flute','koto','岩窟暗徑',[74,72,69,67,62,67,69,72,74,79,74,72,69,67,62,62]],
    ['heian',66,'reed','koto','三橋夜燈',[76,74,69,67,64,67,69,74,76,81,79,76,74,69,67,64]],
    ['gaol',62,'bowed','lyre','深牢的名字',[57,56,52,50,49,50,52,56,57,61,59,57,56,52,49,45]],
    ['mirror',84,'bell','lyre','反向的走廊',[79,76,74,71,72,74,76,79,71,74,76,79,76,74,72,71]],
    ['crystal',78,'bell','lyre','晶脈折光',[81,78,76,73,71,73,76,78,83,81,78,76,73,71,69,71]],
    ['hall',70,'reed','lyre','地底塔門',[62,65,67,69,74,72,69,67,65,67,69,74,77,74,69,62]],
    ['tower',98,'reed','lyre','向上的石階',[74,76,79,81,83,81,79,76,74,79,81,86,83,81,79,74]],
    ['final',74,'bowed','bell','時間的內室',[72,73,77,78,80,78,77,73,72,68,65,61,60,61,65,72]],
    ['chaos',58,'bell','lyre','意識之環',[81,76,72,69,68,72,76,80,84,81,80,76,72,68,64,69]],
    ['vault',90,'bowed','lyre','祕匠的爐心',[69,72,74,76,79,76,74,72,69,67,64,67,69,72,76,69]],
  ];
  for(const [id,bpm,instrument,pluck,title,notes] of profiles){
    const src=BGM.TRACKS[ACT_THEME[id]]||BGM.TRACKS.stone,t=JSON.parse(JSON.stringify(src));
    Object.assign(t,{bpm,instrument,pluck,title,bars:16,lvol:.075,avol:.043,cut:instrument==='bell'?3800:2600});
    t.answer=Array.from({length:4},(_,b)=>[0,3,6,10].map((s,i)=>[s,notes[b*4+i],[3,3,4,6][i]]));
    // Chapters sharing a terrain also receive an independent opening phrase.
    if(['gaol','heian','ordeal','chaos','vault'].includes(id)){
      t.lead=t.answer.map((bar,b)=>bar.map(([s,n,d],i)=>[s,n+(i===3&&b%2===0?-12:0),d]));
      t.answer=t.answer.map(bar=>bar.map(([s,n,d])=>[s,n,d]));
    }
    if(id==='chaos'){t.lvol*=1.3;t.avol*=1.3;}
    BGM.TRACKS['chapter_'+id]=t;
  }
  for(const [id,t]of Object.entries(BGM.TRACKS))if(!id.startsWith('chapter_')&&!id.includes('diva')){
    t.instrument=t.instrument||(id==='village'?'flute':id.startsWith('boss')?'bowed':'reed');t.pluck=t.pluck||'lyre';
  }
  BGM.TRACKS.terrace={...JSON.parse(JSON.stringify(BGM.TRACKS.chapter_tower)),title:'門外的天空',bpm:68,instrument:'flute',avol:.026,lvol:.066,kick:[],hat:[],tom:[],bass:[0,8]};
})();

/* Walkable towns share the game's art, economy, saves and sound bus. */
(() => {
  const bar=document.createElement('div');bar.id='pressure-status';bar.hidden=true;bar.setAttribute('role','status');
  document.getElementById('body').before(bar);
  const fade=document.createElement('div');fade.id='floor-collapse';fade.hidden=true;fade.textContent='地層崩落 · 墜入下一層';document.getElementById('screenwrap').append(fade);
  let timer;
  globalThis.RPG_PRESSURE={update(){const p=pressureInfo(),changed=bar.hidden!==!p;bar.hidden=!p;if(changed)requestAnimationFrame(()=>fitViewport());if(!p)return;bar.dataset.stage=p.stage;bar.textContent=p.turns>=720?'怪潮已抵達 · 儘速前往樓梯':p.label+' '+p.left+' 行動 ｜ 選單與閱讀暫停';},fall(){clearTimeout(timer);fade.hidden=false;timer=setTimeout(()=>fade.hidden=true,1100);}};
  globalThis.RPG_PRESSURE.drawGround=(c,ox,oy)=>{
    const info=pressureInfo();if(!info||!info.fall||info.turns<540)return;
    c.save();c.lineWidth=.7;c.strokeStyle=info.turns>=660?'#d89864aa':'#302015bb';
    for(let y=G.p.y-5;y<=G.p.y+5;y++)for(let x=G.p.x-6;x<=G.p.x+6;x++){
      if(!walkable(x,y)||G.seen[key(x,y)]!==2||(x*7+y*11)%5!==0)continue;
      const px=ox+x*T,py=oy+y*T;c.beginPath();c.moveTo(px+1,py+3);c.lineTo(px+7,py+8);c.lineTo(px+5,py+12);c.lineTo(px+12,py+15);c.moveTo(px+7,py+8);c.lineTo(px+14,py+5);c.stroke();
    }c.restore();
  };
})();

(() => {
  const visual=document.getElementById('prologuevisual'),art=document.getElementById('prologueart'),hero=document.getElementById('chapterhero');
  let lastScene='';
  const url=id=>{const file=HD_ASSETS[id];return file?((globalThis.BABEL_HD_DATA||{})[file]||'art-hd/'+file):null;};
  function sync(){
    const chapter=visual.className.match(/chapter-(\d+)/),scene=visual.className.match(/scene-(\d+)/);
    const signature=chapter?'chapter'+chapter[1]:scene?'scene'+scene[1]:'';if(signature===lastScene)return;lastScene=signature;
    const id=chapter?'hd:chapter-'+ACTS[Number(chapter[1])-1].id:scene?'hd:prologue-'+scene[1]:null,src=id&&url(id);
    art.style.backgroundImage=src?'url("'+src+'")':'';
    visual.classList.toggle('cinema-hd',!!src);
    if(chapter&&BGM.TRACKS['chapter_'+ACTS[Number(chapter[1])-1].id])BGM.force('chapter_'+ACTS[Number(chapter[1])-1].id);
    const showHero=chapter||(scene&&Number(scene[1])>=2);
    hero.style.backgroundImage=showHero&&HD_MODE?'url("'+heroNow().toDataURL('image/png')+'")':'';
    hero.style.display=showHero&&src?'block':'';
    hero.classList.toggle('awakening',!!scene&&Number(scene[1])===2);
    hero.classList.toggle('awakened',!!scene&&Number(scene[1])===3);
  }
  // Restrict the observer to scene/class changes; style updates do not recurse.
  let queued=false;new MutationObserver(()=>{if(queued)return;queued=true;queueMicrotask(()=>{queued=false;if(!visual.dataset.syncing){visual.dataset.syncing='1';sync();queueMicrotask(()=>delete visual.dataset.syncing);}});}).observe(visual,{attributes:true,attributeFilter:['class']});
  sync();
  const tabs=document.createElement('nav');tabs.id='panel-tabs';tabs.setAttribute('aria-label','道具欄分類');
  for(const [mode,label]of [['inv','背包'],['ground','腳下'],['magic','技能']]){const b=document.createElement('button');b.dataset.mode=mode;b.textContent=label;b.onclick=()=>{SFX.play('move');openPanel(mode);};tabs.append(b);}
  document.getElementById('panel').insertBefore(tabs,document.getElementById('list'));
  const tabLabels=()=>{for(const b of tabs.children)b.textContent=b.dataset.mode==='inv'?locUI('背包','Bag','もちもの'):b.dataset.mode==='ground'?locUI('腳下','Ground','あしもと'):locUI('技能','Skills','スキル');};
  new MutationObserver(tabLabels).observe(document.documentElement,{attributes:true,attributeFilter:['lang']});tabLabels();
})();

/* Walkable towns share the game's art, economy, saves and sound bus. */
(() => {
  'use strict';
  const W=20,H=20, $id=id=>document.getElementById(id);
  const buildings=[{x:2,y:2,w:5,h:4,art:'forge'},{x:12,y:2,w:6,h:4,art:'inn'}];
  const trees=[[1,7],[18,7],[2,12],[17,12],[5,1],[10,1],[18,1]];
  const names={smith:'鐵匠',merchant:'旅行商人',elder:'守火長老',child:'尋物的孩子',chief:'村長',mason:'石匠',innkeeper:'旅店老闆娘',healer:'草藥師',archivist:'碑文學者'};
  const portraitOf=id=>HD_LOADED['hd:town-'+id]||HD_LOADED['npc#'+id]||atlas['npc#'+({innkeeper:'merchant',healer:'elder',archivist:'chief'}[id]||id)];
  const sites=[{id:'board',x:7,y:8,label:'委託告示板',art:'noticeboard'},{id:'archive',x:9,y:2,label:'古老石碑',art:'stele'},{id:'well',x:10,y:8,label:'地下蓄水池',art:'valves'},
    {id:'save',x:6,y:10,label:'旅程紀錄台',art:'save-desk',size:1.8},
    {id:'alchemy',x:14,y:7,label:'魔法調合工房',art:'alchemy-bench',size:2},
    {id:'elder-home',x:4,y:15,label:'長老之家 · 初心者',art:'elder-house',size:3.3},
    {id:'camp',x:15,y:16,label:'行商帳篷',art:'yurt',size:3.3},
    {id:'shrine',x:16,y:12,label:'驅魔小祠',art:'shrine',size:2.5},
    {id:'dungeon',x:10,y:18,label:'主線／副本入口',art:'route-map',size:1.6}];
  const visibleSites=()=>sites.filter(s=>s.id!=='shrine'||exorcismAvailable());
  let state=null,canvas,ctx,hud,hint,modal,modalBody,modalActions,dir=[0,0],last=0,phase=0,camera={x:0,y:0},openKind=null;
  const active=()=>$id('village').classList.contains('show');
  const blocked=(x,y)=>x<1||y<1||x>=W-1||y>=H-1||buildings.some(b=>x>=b.x&&x<b.x+b.w&&y>=b.y&&y<b.y+b.h)||visibleSites().some(s=>s.y===y&&Math.abs(s.x-x)<(s.size>=2.5?2:1))||trees.some(t=>t[0]===x&&t[1]===y);
  const cell=o=>[Math.round(o.x),Math.round(o.y)];
  const near=(a,b)=>Math.hypot(a.x-b.x,a.y-b.y)<1.65;
  const persist=()=>{saveVillage();updateHud();};
  const quest=()=>((VILLAGE.townQuest||{})[villageStyle()]||0);
  const story=k=>(VILLAGE.townStory||{})[villageStyle()+':'+k]||0;
  function setStory(k,v){VILLAGE.townStory=VILLAGE.townStory||{};VILLAGE.townStory[villageStyle()+':'+k]=v;persist();}
  const supplies=()=>VILLAGE.travelSupplies||(VILLAGE.travelSupplies=[]);
  function takeSupplies(){
    if(!G||G.over)return;
    while(supplies().length&&G.p.inv.length<20){const q=supplies().shift();G.p.inv.push(mk(q.cat,q.id,{known:1}));G.known[q.cat+'/'+q.id]=1;}
    persist();
  }
  function setQuest(q){VILLAGE.townQuest=VILLAGE.townQuest||{};VILLAGE.townQuest[villageStyle()]=q;persist();}
  function note(id,text){
    VILLAGE.townJournal=VILLAGE.townJournal||[];
    if(!VILLAGE.townJournal.some(n=>n.id===id)){VILLAGE.townJournal.push({id,text});VILLAGE.townJournal=VILLAGE.townJournal.slice(-60);persist();}
  }
  function reset(){
    state={style:villageStyle(),p:{x:10,y:12,face:[0,-1],moving:false},path:[],target:null,npcs:[
      ['smith',5,7],['merchant',14,9],['elder',9,6],['child',7,11],['chief',16,9],['mason',4,10],['innkeeper',15,6],['healer',14,12],['archivist',9,4]
    ].map(([id,x,y],i)=>({id,x,y,home:[x,y],face:[0,1],next:1+i*.6,goal:null,moving:false})),stepAt:0};
  }
  function route(tx,ty){
    const [sx,sy]=cell(state.p),todo=[[sx,sy]],seen=new Map([[sx+','+sy,null]]);
    for(let i=0;i<todo.length;i++){
      const [x,y]=todo[i];if(x===tx&&y===ty)break;
      for(const [dx,dy]of [[0,-1],[1,0],[0,1],[-1,0]]){const nx=x+dx,ny=y+dy,k=nx+','+ny;
        if(!blocked(nx,ny)&&!state.npcs.some(n=>Math.hypot(n.x-nx,n.y-ny)<.65)&&!seen.has(k)){seen.set(k,[x,y]);todo.push([nx,ny]);}}
    }
    let k=tx+','+ty;if(!seen.has(k))return [];
    const out=[];while(seen.get(k)){const [x,y]=k.split(',').map(Number);out.unshift([x,y]);k=seen.get(k).join(',');}return out;
  }
  function move(o,dx,dy,dt,speed){
    const n=Math.hypot(dx,dy);if(!n){o.moving=false;return;}
    dx/=n;dy/=n;const nx=o.x+dx*dt*speed,ny=o.y+dy*dt*speed;
    const free=(x,y)=>!blocked(Math.round(x),Math.round(y))&&!state.npcs.some(p=>p!==o&&Math.hypot(p.x-x,p.y-y)<.58);
    let did=false;if(free(nx,o.y)){did=Math.abs(nx-o.x)>.001;o.x=nx;}if(free(o.x,ny)){did=did||Math.abs(ny-o.y)>.001;o.y=ny;}
    if(Math.abs(dx)>Math.abs(dy))o.face=[Math.sign(dx),0];else o.face=[0,Math.sign(dy)];o.moving=did;
  }
  function conditionText(){const c=VILLAGE.condition||{hp:1,mp:1,sat:1};return 'HP '+Math.round(c.hp*100)+'% · MP '+Math.round(c.mp*100)+'% · '+locUI('飽足','Food','まんぷく')+' '+Math.round(c.sat*100)+'%';}
  function updateHud(){if(hud)hud.textContent=TX('v.name.'+villageStyle(),VNAME[villageStyle()])+'　·　'+VILLAGE.gold+' G';const b=$id('town-status');if(b)b.textContent=conditionText()+' ｜ '+locUI('補給','Supplies','もちこみ')+' '+supplies().length+'/4 · '+locUI('精礦','Ore','こうせき')+' '+(VILLAGE.forgeOre|0);}
  function closeModal(){modal.hidden=true;openKind=null;dir=[0,0];canvas.focus({preventScroll:true});}
  function dialog(title,text,actions=[],portrait){
    for(const id of ['vstock','vowned']){const el=$id(id);if(el&&modalBody.contains(el))$id('village').append(el);}
    dir=[0,0];state.path=[];openKind='talk';modal.hidden=false;modalBody.replaceChildren();modalActions.replaceChildren();
    modalBody.scrollTop=0;
    const h=document.createElement('h2');h.textContent=title;modalBody.append(h);
    if(portrait){const c=document.createElement('canvas');c.width=c.height=128;c.className='town-face';const art=portraitOf(portrait);if(art)c.getContext('2d').drawImage(art,0,0,128,128);modalBody.append(c);}
    const p=document.createElement('p');p.textContent=text;modalBody.append(p);
    for(const [label,fn]of actions){const b=document.createElement('button');b.dataset.mode=mode;b.textContent=label;b.onclick=()=>{SFX.play('open');fn();};modalActions.append(b);}
    const back=document.createElement('button');back.textContent='返回村莊';back.onclick=closeModal;modalActions.append(back);
    SFX.play('talk');modal.querySelector('button').focus({preventScroll:true});
  }
  function shop(){
    renderVillage();
    dialog('鐵匠鋪','永久裝備不因死亡消失。工坊目前可鍛至 +'+forgeCap({up:8})+'；持有 '+VILLAGE.gold+' G、'+(VILLAGE.forgeOre|0)+' 塊精礦。高階鍛造需使用通關或村莊委託取得的精礦。',[['工坊進度與換裝',forgeGuide]]);openKind='shop';
    const relic=document.createElement('button');relic.textContent='四像封印 · 諸神的黃昏';relic.onclick=relicForge;modalActions.prepend(relic);
    modalBody.append($id('vstock'),$id('vowned'));
  }
  function relicForge(){
    const ready=RELIC_GUARDS.every(r=>VILLAGE.relicSeals?.[r.id]);
    dialog('究極鍛造 · 諸神的黃昏',
      '四尊守護像，四件跨章節的封印。集齊後在此合成永久武器。\n\n'+
      RELIC_GUARDS.map(r=>(VILLAGE.relicForged?'✦ 已融合':VILLAGE.relicSeals?.[r.id]?'◆ 已取得':'◇ 未取得')+'　'+r.item+'\n'+locAct(ACTS.find(a=>a.id===r.act))+' · '+r.nm).join('\n\n')+
      '\n\n雕像從對應章節的第二層開始出現，主動攻擊才會甦醒。錯過的封印會在後續章節的普通樓層補現。\n材料不佔背包；合成消耗四件封印，不另收金幣。\n成品：攻擊 38、強化上限 +5、相鄰橫掃，可破巴比倫獅的封印。',
      VILLAGE.relicForged?[['查看永久裝備',shop]]:ready?[['融合四印 · 鑄成究極之劍',()=>{if(!forgeRagnarok())return;updateHud();dialog('諸神的黃昏 · 鑄成','四道光沿劍脊匯流，爐火終於安靜下來。\n\n究極之劍已加入永久裝備，下次出發可攜帶。它能破除獅身封印，但仍需閃避重擊，等待反擊的時機。',[['查看永久裝備',shop]],'smith');}]]:[], 'smith');
  }
  function journal(){dialog('旅人手記',(VILLAGE.townJournal||[]).map(n=>'• '+n.text).join('\n\n')||'還沒有記錄。走近村人交談，線索會留在這裡。');}
  function forgeGuide(){
    const upcoming=VILLAGE_STOCK.filter(g=>(g.from||0)>(VILLAGE.act|0)).sort((a,b)=>a.from-b.from).slice(0,3);
    dialog('工坊進度','村莊比迷宮更早取得新一階的裝備，永久鍛造上限也更高。\n\n下一批貨：\n'+upcoming.map(g=>locAct(ACTS[g.from])+'：'+defNm(g)).join('\n')+'\n\n已取得的舊裝備與強化值會保留。可回收不再使用的永久裝備，取回四成基礎價格。',VILLAGE.stock.map(g=>['回收 '+defNm(g)+' · '+Math.floor(defOf(g.cat,g.id).price*.4)+' G',()=>{
      dialog('確認回收',defNm(g)+'會從永久裝備中移除，鍛造值也一併放棄。',[['確認回收',()=>{const i=VILLAGE.stock.indexOf(g);if(i<0)return;VILLAGE.stock.splice(i,1);VILLAGE.gold+=Math.floor(defOf(g.cat,g.id).price*.4);persist();SFX.play('coin');forgeGuide();}]]);
    }]));
  }
  function supplyShop(){
    const discount=story('well')===3?.9:1;
    const goods=[['food','bread',150],['food','fruit',80],['herb','heal',100],['herb','cure',270],...(story('caravan')>=2?[['scroll','map',450],['scroll','ident',450]]:[])];
    dialog('補給與草藥','最多準備 4 件，下次出發會放入背包。消耗品使用後不會再次發放。'+(discount<1?'\n水路修復後，村莊補給享九折。':'')+'\n\n已打包：'+(supplies().map(defNm).join('、')||'無'),[['魔法調合與素材寄存',alchemy]], 'healer');
    const grid=document.createElement('div');grid.className='town-goods';
    for(const [cat,id,base]of goods){const cost=Math.round(base*discount),b=document.createElement('button');b.textContent=defNm({cat,id})+' · '+cost+' G';b.disabled=VILLAGE.gold<cost||supplies().length>=4;b.onclick=()=>{if(VILLAGE.gold<cost||supplies().length>=4)return;VILLAGE.gold-=cost;supplies().push({cat,id});persist();SFX.play('coin');supplyShop();};grid.append(b);}modalBody.append(grid);
  }
  function alchemy(){
    const bank=VILLAGE.reagents||{},stock=VILLAGE.alchemyStock||[];
    dialog('草藥師的魔法調合','活著返村時，最多寄存 12 件已鑑定的普通草藥、卷軸與空法杖。保存壺與珍稀成長藥不會自動提煉。\n先選擇要提煉的物品，再選配方；成品放入 4 格出發補給。\n\n'+Object.entries(ALCHEMY_MATERIAL).map(([k,n])=>n+' '+(bank[k]||0)).join(' · ')+'\n出發補給 '+supplies().length+'/4 · '+VILLAGE.gold+' G',[], 'healer');
    const cards=document.createElement('div');cards.className='alchemy-recipes';
    for(const r of ALCHEMY_RECIPES){
      const unlocked=alchemyUnlocked(r),card=document.createElement('article'),title=document.createElement('b'),desc=document.createElement('p'),cost=document.createElement('p'),b=document.createElement('button');
      title.textContent=defNm({cat:r.cat,id:r.out});desc.textContent=r.effect;
      const req={well:'修復蓄水池',archive:'請碑文學者解讀石碑',caravan:'完成商隊貨箱委託'}[r.gate];
      cost.textContent=(unlocked?'配方：':'尚未學會：'+req+'\n')+Object.entries(r.cost).map(([k,n])=>ALCHEMY_MATERIAL[k]+' '+(bank[k]||0)+'/'+n).join('、')+' · '+r.gold+' G';
      b.textContent=!unlocked?'等待配方':supplies().length>=4?'出發補給已滿':'調合 1 份';
      b.disabled=!unlocked||supplies().length>=4||VILLAGE.gold<r.gold||Object.entries(r.cost).some(([k,n])=>(bank[k]||0)<n);
      b.onclick=()=>{if(craftAlchemy(r.id)){SFX.play('ident');updateHud();alchemy();}};card.append(title,desc,cost,b);cards.append(card);
    }modalBody.append(cards);
    const h=document.createElement('h3');h.textContent='寄存物品 '+stock.length+'/12 · 提煉後會消耗原物品';modalBody.append(h);
    const grid=document.createElement('div');grid.className='town-goods';
    stock.forEach((it,i)=>{const b=document.createElement('button'),key=ALCHEMY_INPUT[it.cat+'/'+it.id];b.textContent='提煉 '+defNm(it)+' → '+ALCHEMY_MATERIAL[key]+' ×1';b.disabled=(bank[key]||0)>=99;b.onclick=()=>{if(distillAlchemy(i)){SFX.play('quaff');alchemy();}};grid.append(b);if(it.cat!=='wand'){const take=document.createElement('button');take.textContent='保留原用途：打包 '+defNm(it);take.disabled=supplies().length>=4;take.onclick=()=>{if(supplies().length>=4||stock[i]!==it)return;stock.splice(i,1);supplies().push({...it});persist();alchemy();};grid.append(take);}});modalBody.append(grid);
    if(!stock.length){const p=document.createElement('p');p.textContent='寄存箱目前是空的。把探索中收集的物品帶回來；進迷宮時，先決定哪些藥草要急救、哪些要留給下一次調合。';modalBody.append(p);}
  }
  function inn(){
    const rumor=story('well')===3?'水聲回來了，草藥師終於有乾淨的水配藥。':story('well')===2?'石匠說：先止水，再清淤，最後引水。千萬別反過來。':'最近蓄水池不再流水。告示板貼了委託，石匠似乎知道原因。';
    dialog('宿屋 · 旅人歇腳處',conditionText()+'\n\n返村不會自動恢復。住宿補滿體力、魔力與飽足；不解除裝備詛咒。\n'+rumor+'\n每章可領一份野果。',[
      ['住宿 · '+innCost()+' G',()=>{const ok=restAtInn();updateHud();dialog(ok?'一夜好眠':'暫時無法住宿',ok?'體力、魔力與飽足已恢復。':VILLAGE.gold<innCost()?'旅費不足，可以請老闆娘提供基本救護。':'你目前精神與體力充足，不需要付費。',[['返回宿屋',inn]],'innkeeper');}],
      ...(VILLAGE.gold<innCost()?[['請求基本救護',()=>{const ok=restAtInn(true);updateHud();dialog('火爐旁的救護',ok?'免費止血與熱湯：體力至少五成、魔力至少四分之一、飽足至少四成。':'你已能繼續旅行。完整恢復需要住宿。',[['返回宿屋',inn]],'innkeeper');}]]:[]),
      ['歇腳與準備乾糧',()=>{if(story('rest')===(VILLAGE.act|0)+1){dialog('火爐旁','這一章的乾糧已經領過了。坐一會兒吧，村裡的消息又多了些。',[['查看委託',noticeboard]],'innkeeper');return;}if(supplies().length>=4){dialog('行囊已滿','先使用已準備的補給，再來領乾糧。');return;}supplies().push({cat:'food',id:'fruit'});setStory('rest',(VILLAGE.act|0)+1);SFX.play('pick');dialog('一盞燈等著你','你在火爐旁歇了片刻。老闆娘把一份野果包進了行囊。',[['聽村裡的消息',noticeboard]],'innkeeper');}],
      ['採買補給',supplyShop],['聽說地下塔門……',()=>{note('inn-route','神廟門衛後是向下的迷宮；最低處的大廣間藏著向上的塔門。村莊的燈火，是回來時的路標。');dialog('火爐邊的傳聞','「別追著頭頂的光走。要先抵達最深的大廣間，才能找到塔真正的入口。」\n老闆娘把這句話託你記下。',[],'innkeeper');}]
    ],'innkeeper');
  }
  function facilityArt(id){const img=HD_LOADED['hd:town-'+id];if(!img)return;const c=document.createElement('canvas');c.width=c.height=384;c.className='town-facility-art';c.getContext('2d').drawImage(img,0,0,384,384);modalBody.insertBefore(c,modalBody.children[1]);}
  function elderHome(){
    const chapter=ACTS[Math.min(VILLAGE.act|0,LAST_MAIN)];
    dialog('長老之家 · 初心者相談',locAct(chapter)+'\n'+TX('acti.'+chapter.id,chapter.intro)+'\n\n先穿戴武器盾牌、準備急救草，再找入口。地底迷宮的沙漏以行動計時；閱讀、選單與停留村莊不消耗回合。',[
      ['詢問設施與路線',directory],['技能與素材的取捨',()=>dialog('長老的提醒','技能點數來自首次里程碑，不可重複刷取。普通草藥可保留急救，也可活著帶回工房提煉；珍稀成長藥不自動拆解。\n\n一般迷宮：420 行動預警、540 行動怪潮、720 行動崩落。序章、王層與特殊戰場不觸發。塔內以增援取代崩落。',[['返回長老之家',elderHome]],'elder')],['查看旅人手記',journal]
    ],'elder');
  }
  function recordPoint(){
    dialog('旅程紀錄台','記錄章節、永久裝備、村莊事件、寄存素材與返村傷勢。這是目前裝置的本機紀錄，不會回復體力，也不會把已結束的迷宮變成可重讀的戰鬥。',[
      ['記錄目前旅程',()=>{VILLAGE.recordedAt=Date.now();const ok=saveVillage();dialog('旅程紀錄',QA_MODE?'測試模式：紀錄流程已演示，未覆寫正式存檔。':ok?'已記錄目前旅程，可安心關閉遊戲。':'此瀏覽器無法儲存。請保持此頁開啟，勿清除瀏覽資料。',[['查看旅人手記',journal]]);}],['查看冒險紀錄',()=>{closeModal();$id('vboard').click();}]
    ]);facilityArt('save-desk');
  }
  function shrine(){
    if(!exorcismAvailable())return;
    const count=townCursedItems().length,cost=120+count*80;
    dialog('驅魔小祠','只有和風聚落與塔前中繼村設有驅魔師。\n可淨化永久裝備、寄存保存壺與萬用口袋內的詛咒物品，不改變強化值。\n\n詛咒物品 '+count+' 件'+(count?' · 儀式費 '+cost+' G':' · 無須儀式'),count?[['舉行淨化儀式 · '+cost+' G',()=>{const ok=purifyAtShrine();updateHud();dialog(ok?'咒印散去':'尚無法舉行',ok?'寄存物品的詛咒已解除。':'金幣不足或已沒有需要淨化的物品。',[['返回小祠',shrine]]);}]]:[]);facilityArt('shrine');
  }
  function dungeonGate(){dialog('地下通道 · 出發處','主線：'+locAct(ACTS[Math.min(VILLAGE.act|0,LAST_MAIN)])+'\n'+(VILLAGE.sideKey&&!VILLAGE.sideDone?'祕匠副本：已開啟，可挑戰。':'祕匠副本：探索途中協助受困石匠，取得入口線索。')+'\n\n'+conditionText(),[['主線出發',depart],...(VILLAGE.sideKey&&!VILLAGE.sideDone?[['進入祕匠副本',()=>{closeModal();$id('vside').click();}]]:[])]);}
  function directory(){
    const stops=[['鐵匠鋪','smith'],['宿屋','innkeeper'],['魔法藥草店','healer'],...visibleSites().filter(s=>!['well','archive','board'].includes(s.id)).map(s=>[s.label,s.id])];
    dialog('村落導覽','選擇地點後，主角會沿路走過去。也能點地面移動，靠近設施後按 A 調查。',stops.map(([name,id])=>[name,()=>{
      const target=visibleSites().find(s=>s.id===id)||state.npcs.find(n=>n.id===id);if(!target)return;
      const [x,y]=cell(target),opts=[[x,y+1],[x-1,y],[x+1,y],[x,y-1]].filter(c=>!blocked(...c)).map(c=>({c,path:route(...c)})).filter(o=>o.path.length||Math.hypot(state.p.x-o.c[0],state.p.y-o.c[1])<.2).sort((a,b)=>a.path.length-b.path.length);
      if(!opts.length)return;closeModal();state.path=opts[0].path;state.target=target;
    }]));
  }
  function noticeboard(){
    const lines=[['遺失的鈴鐺',quest()===3?'完成':quest()?'尋找中':'與孩子交談'],['停水的蓄水池',story('well')===3?'完成 · 補給九折':story('well')===2?'工具已備妥 · 調整水閥':story('well')===1?'向石匠請教':'未承接'],['走散的商隊',story('caravan')>=2?'完成 · 卷軸到貨':story('caravan')?'尋找西南與東南貨箱':'未承接']];
    const actions=[];if(!story('well'))actions.push(['承接：修復蓄水池',()=>{setStory('well',1);note('well:'+state.style,'蓄水池停水：先找西側石匠取得工具與操作順序，再調整水閥。');dialog('委託已承接','找到西側石匠，問清楚操作水閥的順序。報酬：180 G、2 塊精礦，以及補給九折。');}]);
    if(!story('caravan'))actions.push(['承接：尋找商隊貨箱',()=>{setStory('caravan',1);note('caravan:'+state.style,'商隊貨箱散落在聚落西南與東南角。兩箱都找到後交給旅行商人，或送給傷患。');closeModal();}]);
    if(quest()===3&&story('well')===3&&story('caravan')>=2&&!story('festival'))actions.push(['與大家一起點燈',()=>{setStory('festival',1);VILLAGE.forgeOre=(VILLAGE.forgeOre|0)+2;persist();note('festival:'+state.style,'聚落的水與補給恢復，村民在廣場點起感謝的燈。鐵匠送來 2 塊精礦。');SFX.play('victory');dialog('地底的燈火','孩子搖著鈴鐺，老闆娘端出熱湯。你帶回的東西成了整個村子的晚餐。\n\n村民送你 2 塊精礦；廣場會留下這晚的燈火。',[],'chief');}]);
    dialog('委託告示板',lines.map(([a,b])=>a+'　—　'+b).join('\n\n')+'\n\n委託各可完成一次，成果與解鎖會保留。',actions);
  }
  function well(){
    if(story('well')===3){dialog('流動的水','乾淨的地下水重新流進蓄水池。草藥師的補給價格已降低。');return;}
    if(story('well')<2){dialog('停止轉動的水閥','三道閥門鏽住了。需要石匠的工具與操作提示。',[['查看委託',noticeboard]]);return;}
    const step=story('valve'),seq=['止水閥','清淤閥','引水閥'];
    dialog('修復蓄水池','已完成 '+step+'/3 道程序。\n'+(step===0?'哪一道閥門要先處理？':step===1?'水流止住了，管底仍塞著泥沙。':'管底清乾淨了，可以讓水重新流動。'),seq.map((label,i)=>[label,()=>{
      if(i!==step){setStory('valve',0);SFX.play('wall');dialog('水壓不穩','你鬆開閥門，避免把管道扭裂。先回想石匠說的順序。',[['重新調整',well]]);return;}
      if(step<2){setStory('valve',step+1);SFX.play('door');well();return;}
      if(story('well')===3)return;VILLAGE.gold+=180;VILLAGE.forgeOre=(VILLAGE.forgeOre|0)+2;setStory('well',3);setStory('valve',0);SFX.play('victory');note('well-done:'+state.style,'水路已修復：獲得 180 G、2 塊精礦，村莊補給永久九折。');dialog('水聲回來了','水從牆內的銅管流出。你獲得 180 G、2 塊精礦；草藥師將以九折供應補給。');
    }]));
  }
  function caravan(){
    if(story('caravan')>=2){dialog('商隊重新出發','貨箱找回後，商隊恢復了卷軸供應。'+(story('caravan')===3?'你把物資先送給傷患，村民一直記得這件事。':''),[['採買補給',supplyShop]],'merchant');return;}
    if(!story('caravan')){noticeboard();return;}
    if(story('parcels')!==3){dialog('遺落的貨箱','西南角與東南角各有一箱。已找到 '+((story('parcels')&1?1:0)+(story('parcels')&2?1:0))+'/2 箱。',[],'merchant');return;}
    dialog('兩箱物資的去向','商人說這批補給可換來 240 G；草藥師則希望先照顧受困的傷患。兩種選擇都會恢復商隊供貨。',[
      ['交給商隊 · 240 G',()=>{if(story('caravan')!==1)return;VILLAGE.gold+=240;setStory('caravan',2);note('caravan-done:'+state.style,'貨箱交還商隊：獲得 240 G，補給店開始供應地圖與鑑定卷軸。');SFX.play('coin');caravan();}],
      ['送給傷患 · 3 塊精礦',()=>{if(story('caravan')!==1)return;VILLAGE.forgeOre=(VILLAGE.forgeOre|0)+3;setStory('caravan',3);note('caravan-done:'+state.style,'把貨箱送給傷患：村民以 3 塊精礦答謝，商隊仍恢復了卷軸供應。');SFX.play('ident');caravan();}]
    ],'merchant');
  }
  function inspectSite(id){const handlers={board:noticeboard,well,save:recordPoint,alchemy,'elder-home':elderHome,camp:()=>talk(state.npcs.find(n=>n.id==='merchant')),shrine,dungeon:dungeonGate};if(handlers[id]){handlers[id]();return;}setStory('archive',1);note('archive:'+state.style,'石碑記著：門衛守的是向下的路，塔的根基藏在最深的大廣間。');dialog('石碑上的舊路線','碑文畫著向下的階梯、橫展的大廳，以及一道向上的塔門。旁邊刻著：\n「先尋其根，方能登其頂。」',[],'archivist');}
  function talk(n){
    const chapter=ACTS[Math.min(VILLAGE.act|0,LAST_MAIN)],key=chapter.id+':'+n.id;
    n.face=[0,1];
    if(n.id==='innkeeper'){inn();return;}
    if(n.id==='healer'){supplyShop();return;}
    if(n.id==='archivist'){inspectSite('archive');return;}
    if(n.id==='smith'){shop();return;}
    if(n.id==='elder'){
      elderHome();return;
    }
    if(n.id==='merchant'){
      dialog(names[n.id],story('caravan')>=2?'商隊已經恢復供貨。村民記得你替大家帶回的物資。':'商隊在村子南邊弄丟了兩箱物資。若找回來，卷軸也能重新上架。',[['購買旅途補給',supplyShop],['關於遺落的貨箱',caravan]],n.id);return;
    }
    if(n.id==='child'){
      if(quest()===0)dialog(names[n.id],'我把鈴鐺掉在南邊的樹下了。你能替我找回來嗎？',[['幫忙找鈴鐺',()=>{setQuest(1);note('bell:'+state.style,'孩子遺失的鈴鐺：到村莊西南方的樹旁尋找亮光。');closeModal();}]],n.id);
      else if(quest()===1)dialog(names[n.id],'我記得在西南邊的樹下玩過。鈴鐺應該還在附近。',[],n.id);
      else if(quest()===2)dialog(names[n.id],'你找到了！這是我存下的謝禮，請收下。',[['交還鈴鐺，領取 80 G',()=>{if(quest()!==2)return;VILLAGE.gold+=80;setQuest(3);note('bell-done:'+state.style,'已找回鈴鐺。孩子說：長老知道下一章的消息，村長守著通往冒險的路。');SFX.play('coin');closeModal();}]],n.id);
      else dialog(names[n.id],'鈴鐺已經繫牢了。謝謝你！旅途中也記得找人聊聊。',[],n.id);return;
    }
    if(n.id==='mason'){
      if(story('well')===1){dialog(names[n.id],'蓄水池不是枯了，是管底塞住了。順序要記好：先止水，再清淤，最後引水。',[['接過扳手與操作提示',()=>{setStory('well',2);note('valves:'+state.style,'石匠的提示：止水閥 → 清淤閥 → 引水閥。到廣場中央蓄水池操作。');closeModal();}]],n.id);return;}
      const text=VILLAGE.sideKey&&!VILLAGE.sideDone?'祕匠的入口已替你打開。準備好再出發吧。':'古牆上的浮雕能辨認通道年代。探索時留意石碑、機關，以及受困的旅人。';
      note(key,text);dialog(names[n.id],text,VILLAGE.sideKey&&!VILLAGE.sideDone?[['前往祕匠副本',()=>{closeModal();$id('vside').click();}]]:[],n.id);return;
    }
    dialog(names[n.id],'石門後的通道通往'+locAct(chapter)+'。確認裝備與手記後，我會替你開門。',[['前往下一章',depart],['查看紀錄碑',()=>{closeModal();$id('vboard').click();}]],n.id);
  }
  function depart(){dialog('準備出發','前往'+locAct(ACTS[Math.min(VILLAGE.act|0,LAST_MAIN)])+'？永久裝備會隨你同行。\n\n'+conditionText()+'\n返村傷勢會帶入下一趟，住宿才能完整恢復。',[['出發',()=>{closeModal();$id('vgo').click();}],['先去宿屋',inn]]);}
  function interact(){
    if(!state||!modal.hidden)return;
    const nearby=[...state.npcs,...visibleSites()].filter(s=>near(state.p,s)).sort((a,b)=>Math.hypot(a.x-state.p.x,a.y-state.p.y)-Math.hypot(b.x-state.p.x,b.y-state.p.y));
    if(nearby.length){const target=nearby[0];if(target.art)inspectSite(target.id);else talk(target);return;}
    if(story('caravan')===1){for(const [x,y,bit]of [[4,13,1],[16,13,2]])if(!(story('parcels')&bit)&&near(state.p,{x,y})){setStory('parcels',story('parcels')|bit);SFX.play('pick');dialog('找到了商隊貨箱',story('parcels')===3?'兩箱都找到了。帶回給旅行商人，決定物資的去向。':'收好第一箱。另一箱在聚落南邊的另一側。');return;}}
    if(quest()===1&&near(state.p,{x:3,y:13})){setQuest(2);SFX.play('pick');dialog('找到了鈴鐺','把鈴鐺帶回給廣場旁的孩子。');return;}
    if(state.p.y>17&&Math.abs(state.p.x-10)<2){dungeonGate();return;}
    SFX.play('wall',200);
  }
  function drawSprite(art,x,y,size,face,moving){
    if(!art)return;const bob=moving?Math.sin(phase*12)*2:Math.sin(phase*2+x)*.7;
    ctx.save();ctx.translate(x,y+bob);if(face&&face[0]<0)ctx.scale(-1,1);
    ctx.fillStyle='rgba(5,9,8,.28)';ctx.beginPath();ctx.ellipse(0,-3,size*.26,size*.065,0,0,Math.PI*2);ctx.fill();
    ctx.rotate(moving?Math.sin(phase*9)*.025:0);ctx.drawImage(art,-size/2,-size,size,size);ctx.restore();
  }
  function draw(){
    const dpr=Math.min(devicePixelRatio||1,2),box=canvas.getBoundingClientRect();
    if(box.width<1||box.height<1)return;
    if(canvas.width!==Math.round(box.width*dpr)||canvas.height!==Math.round(box.height*dpr)){canvas.width=Math.round(box.width*dpr);canvas.height=Math.round(box.height*dpr);}
    ctx.setTransform(dpr,0,0,dpr,0,0);const vw=box.width,vh=box.height,t=Math.max(38,Math.min(58,vw/13));
    camera={x:W*t<vw?(W*t-vw)/2:Math.max(0,Math.min(W*t-vw,(state.p.x+.5)*t-vw/2)),y:H*t<vh?(H*t-vh)/2:Math.max(0,Math.min(H*t-vh,(state.p.y+.5)*t-vh*.57)),t};
    ctx.fillStyle='#182721';ctx.fillRect(0,0,vw,vh);ctx.save();ctx.translate(-camera.x,-camera.y);
    const st=state.style,earth=HD_LOADED['tile:'+(st==='edo'?'wood':st==='spire'?'temple':st==='cave'?'mountain':'stone')+'#floor0'];
    const paving=HD_LOADED['tile:'+(st==='spire'?'spire':'temple')+'#floor0'];
    for(let y=0;y<H;y++)for(let x=0;x<W;x++){
      const path=(x>=8&&x<=11)||(y>=6&&y<=9)||y===12||y===16||y===17;
      const img=path?paving:earth;if(img)ctx.drawImage(img,x*t,y*t,t,t);else{ctx.fillStyle=path?'#a89a71':'#3c5945';ctx.fillRect(x*t,y*t,t,t);}
      if(!path){ctx.fillStyle='rgba(14,21,24,.18)';ctx.fillRect(x*t,y*t,t,t);}
    }
    // Enclosing masonry and pillars make this a refuge beneath a cavern roof.
    const wall=HD_LOADED['tile:'+(st==='spire'?'spire':st==='edo'?'wood':'stone')+'#wallface'];
    for(let y=0;y<H;y++)for(let x=0;x<W;x++)if(x===0||y===0||x===W-1||y===H-1){
      if(y===H-1&&x>=9&&x<=11)continue;
      if(wall)ctx.drawImage(wall,x*t,y*t,t,t);else{ctx.fillStyle='#333638';ctx.fillRect(x*t,y*t,t,t);}
      ctx.fillStyle='rgba(3,8,10,.35)';ctx.fillRect(x*t,y*t,t,t);
    }
    const actors=[];
    for(const b of buildings)actors.push({y:b.y+b.h,paint:()=>{const img=HD_LOADED['hd:town-'+st+'-'+b.art];if(img)ctx.drawImage(img,b.x*t,(b.y-1)*t,b.w*t,(b.h+1)*t);}});
    for(const [x,y]of trees)actors.push({y:y+.6,paint:()=>{const img=HD_LOADED['hd:town-'+st+'-tree'];ctx.fillStyle='#786b52';ctx.fillRect((x+.05)*t,(y+.1)*t,t*.9,t*.65);if(img)ctx.drawImage(img,(x-.4)*t,(y-1.3)*t,t*1.8,t*2.2);}});
    actors.push({y:8.5,paint:()=>{const img=HD_LOADED['hd:town-'+st+'-well'];if(img)ctx.drawImage(img,9.5*t,7*t,t*2,t*2);const valves=HD_LOADED['hd:town-valves'];if(valves)ctx.drawImage(valves,10.8*t,8.2*t,t*.8,t*.65);}});
    for(const site of visibleSites().filter(s=>s.id!=='well'))actors.push({y:site.y+.7,paint:()=>{const size=site.size||1.8,art=site.id==='elder-home'&&st==='edo'?'edo-inn':site.art,img=HD_LOADED['hd:town-'+art];if(img)ctx.drawImage(img,(site.x+.5-size/2)*t,(site.y+1-size)*t,t*size,t*size);ctx.font='600 12px sans-serif';ctx.textAlign='center';const tw=ctx.measureText(site.label).width;ctx.fillStyle='#102018dd';ctx.fillRect((site.x+.5)*t-tw/2-5,(site.y+1)*t,tw+10,20);ctx.fillStyle='#ffecc7';ctx.fillText(site.label,(site.x+.5)*t,(site.y+1)*t+14);}});
    const decor=[['cauldron',13,10,1.1],['herb-stall',14,12,1.7],['bench',4,11,1.7],['weapon-rack',3,6,1.6],['lamp',8,5,1],['lamp',12,10,1],['carpet',4,16,1.5],['lamp',7,17,1],['crate',17,17,1]];
    for(const [id,x,y,scale]of decor)actors.push({y:y+.3,paint:()=>{const img=HD_LOADED['hd:town-'+id];if(img)ctx.drawImage(img,(x+.5-scale/2)*t,(y+1-scale)*t,t*scale,t*scale);}});
    if(story('caravan')===1)for(const [x,y,bit]of [[4,13,1],[16,13,2]])if(!(story('parcels')&bit))actors.push({y,paint:()=>{const img=HD_LOADED['hd:town-crate'];if(img)ctx.drawImage(img,x*t,(y-.3)*t,t,t);ctx.fillStyle='#ffdf7e';ctx.font='bold 18px serif';ctx.fillText('!',(x+.5)*t,(y-.4)*t);}});
    for(const n of state.npcs)actors.push({y:n.y+.8,paint:()=>{
      drawSprite(portraitOf(n.id),(n.x+.5)*t,(n.y+1)*t,t*1.25,n.face,n.moving);
      if((n.id==='child'&&quest()<3)||(n.id==='mason'&&story('well')===1)||(n.id==='merchant'&&story('caravan')===1&&story('parcels')===3)){ctx.font='bold 18px serif';ctx.textAlign='center';ctx.fillStyle='#ffe09a';ctx.fillText('!',(n.x+.5)*t,(n.y-.5)*t);}
      if(near(state.p,n)){ctx.font='600 12px sans-serif';ctx.textAlign='center';ctx.fillStyle='#161c19';ctx.fillRect((n.x-.35)*t,(n.y-.8)*t,t*1.7,22);ctx.fillStyle='#fff0c9';ctx.fillText(names[n.id]+' · A',(n.x+.5)*t,(n.y-.8)*t+15);}
    }});
    actors.push({y:state.p.y+.8,paint:()=>{const p=state.p,img=hdHeroSprite(-1,-1,null,VILLAGE.skin,VILLAGE.col,p.face)||heroSprite(-1,-1,null,VILLAGE.skin,VILLAGE.col);drawSprite(img,(p.x+.5)*t,(p.y+1)*t,t*1.35,null,p.moving);}});
    actors.sort((a,b)=>a.y-b.y).forEach(a=>a.paint());
    ctx.textAlign='center';ctx.font='600 13px sans-serif';ctx.fillStyle='#fff0cb';ctx.fillText('鐵匠鋪',4.5*t,6.2*t);ctx.fillText('宿屋 · 旅人歇腳處',15*t,6.2*t);
    if(quest()===1){const x=3.5*t,y=13.5*t,g=ctx.createRadialGradient(x,y,0,x,y,t*.6);g.addColorStop(0,'#fff3aecc');g.addColorStop(1,'#ffdc5500');ctx.fillStyle=g;ctx.fillRect(x-t,y-t,t*2,t*2);ctx.fillStyle='#fff7c8';ctx.beginPath();ctx.arc(x,y,3+Math.sin(phase*4),0,Math.PI*2);ctx.fill();}
    if(story('well')===3){ctx.strokeStyle='#89d7e6aa';ctx.lineWidth=2;for(let i=0;i<3;i++){ctx.beginPath();ctx.ellipse(10.5*t,8.4*t,(.18+(phase*.15+i*.12)%.35)*t,t*.07,0,0,Math.PI*2);ctx.stroke();}}
    if(story('festival')){const lamps=HD_LOADED['hd:town-garland'];if(lamps)ctx.drawImage(lamps,6*t,5*t,7*t,2*t);}
    ctx.restore();const glow=ctx.createRadialGradient(vw*.25,0,0,vw*.25,0,vw);glow.addColorStop(0,'rgba(255,211,124,.12)');glow.addColorStop(1,'rgba(4,17,28,.12)');ctx.fillStyle=glow;ctx.fillRect(0,0,vw,vh);
    const site=visibleSites().find(s=>near(state.p,s)),n=state.npcs.find(n=>near(state.p,n));hint.textContent=site?'A 調查 · '+site.label:n?'A 交談 · '+names[n.id]:quest()===1?'尋物：西南邊樹旁的亮光':story('caravan')===1?'商隊貨箱：聚落西南與東南角':locUI('點地面移動 · A 交談 ·「設施」可引路','Tap to walk · A to talk · Services for directions','タップで移動 · Aで話す · しせつで道案内');
  }
  function frame(ts){
    const dt=Math.min(.04,(ts-last)/1000||0);last=ts;phase+=dt;
    if(active()&&state){
      if(modal.hidden){
        const p=state.p;if(dir[0]||dir[1]){state.path=[];state.target=null;move(p,dir[0],dir[1],dt,3.2);}
        else if(state.path.length){const [x,y]=state.path[0],dx=x-p.x,dy=y-p.y;
          if(Math.hypot(dx,dy)<.08){p.x=x;p.y=y;state.path.shift();}else{move(p,dx,dy,dt,3.2);if(!p.moving){const end=state.path[state.path.length-1];state.path=route(...end);}}
        }else{p.moving=false;if(state.target){const target=state.target;state.target=null;if(near(p,target)){if(target.art)inspectSite(target.id);else talk(target);}}}
        if(p.moving&&phase-state.stepAt>.30){state.stepAt=phase;SFX.play('step',230);}
        for(const n of state.npcs){
          n.next-=dt;if(n.next<=0&&!near(p,n)){n.next=2.5+Math.random()*3;const [dx,dy]=[[0,1],[0,-1],[1,0],[-1,0]][Math.floor(Math.random()*4)];const gx=Math.round(n.x)+dx,gy=Math.round(n.y)+dy;if(!blocked(gx,gy)&&Math.abs(gx-n.home[0])+Math.abs(gy-n.home[1])<=3)n.goal=[gx,gy];}
          if(n.goal&&!near(p,n)){const [x,y]=n.goal;if(Math.hypot(x-n.x,y-n.y)<.08){n.x=x;n.y=y;n.goal=null;n.moving=false;}else move(n,x-n.x,y-n.y,dt,1.05);}else n.moving=false;
        }
      }
      draw();
    }
    requestAnimationFrame(frame);
  }
  function mount(){
    const root=$id('village');root.classList.add('rpg-town');
    if(!canvas){
      const shell=document.createElement('div');shell.id='town-shell';shell.innerHTML='<header><b id="town-title"></b><nav><button id="town-journal">手記</button><button id="town-exit">出發</button></nav></header><div id="town-stage"><canvas id="town-world" tabindex="0" role="application" aria-label="可步行村莊：方向鍵移動，Enter 交談"></canvas><p id="town-hint"></p></div><footer><div id="town-dpad"><button data-dir="0,-1" aria-label="向上">▲</button><button data-dir="-1,0" aria-label="向左">◀</button><button data-dir="0,1" aria-label="向下">▼</button><button data-dir="1,0" aria-label="向右">▶</button></div><button id="town-action">A <small>交談 / 調查</small></button></footer>';
      root.append(shell);const quests=document.createElement('button');quests.textContent=locUI('委託','Quests','クエスト');quests.id='town-quests';quests.onclick=noticeboard;shell.querySelector('nav').prepend(quests);const status=document.createElement('div');status.id='town-status';shell.querySelector('header').after(status);canvas=$id('town-world');ctx=canvas.getContext('2d');hud=$id('town-title');hint=$id('town-hint');
      modal=document.createElement('section');modal.id='town-modal';modal.hidden=true;modal.setAttribute('role','dialog');modal.setAttribute('aria-modal','true');modal.innerHTML='<div id="town-modal-body"></div><div id="town-modal-actions"></div>';root.append(modal);modalBody=$id('town-modal-body');modalActions=$id('town-modal-actions');
      $id('town-journal').textContent=locUI('設施','Services','しせつ');$id('town-exit').textContent=locUI('出發','Depart','しゅっぱつ');$id('town-action').innerHTML='A <small>'+locUI('交談 / 調查','Talk / Examine','はなす / しらべる')+'</small>';$id('town-journal').onclick=directory;$id('town-exit').onclick=dungeonGate;$id('town-action').onclick=interact;
      for(const b of root.querySelectorAll('[data-dir]')){b.onpointerdown=e=>{e.preventDefault();b.setPointerCapture(e.pointerId);dir=b.dataset.dir.split(',').map(Number);SFX.unlock();BGM.start();};b.onpointerup=b.onpointercancel=()=>dir=[0,0];}
      canvas.addEventListener('pointerdown',e=>{
        if(!modal.hidden)return;e.preventDefault();canvas.focus({preventScroll:true});SFX.unlock();BGM.start();
        const box=canvas.getBoundingClientRect(),x=(e.clientX-box.left+camera.x)/camera.t-.5,y=(e.clientY-box.top+camera.y)/camera.t-.5;
        const n=visibleSites().find(n=>Math.hypot(n.x-x,n.y-y)<.8)||state.npcs.find(n=>Math.hypot(n.x-x,n.y-y)<.9);
        if(n&&near(state.p,n)){if(n.art)inspectSite(n.id);else talk(n);return;}
        let target=[Math.round(x),Math.round(y)];
        if(n){const [nx,ny]=cell(n);const choices=[[nx,ny+1],[nx-1,ny],[nx+1,ny],[nx,ny-1]].map(c=>({c,p:route(...c)})).filter(a=>a.p.length);choices.sort((a,b)=>a.p.length-b.p.length);if(!choices.length)return;target=choices[0].c;}
        state.path=route(...target);state.target=n||null;
      });
      requestAnimationFrame(frame);
    }
    if(!state||state.style!==villageStyle())reset();updateHud();
  }
  addEventListener('keydown',e=>{
    if(!active()||!state||$id('board').classList.contains('show')||e.target.matches('input,textarea,select'))return;
    if(!modal.hidden){e.stopImmediatePropagation();if(e.key==='Escape'){e.preventDefault();closeModal();}else if(e.key==='Tab'){const items=[...modal.querySelectorAll('button:not(:disabled),input,select,[tabindex="0"]')].filter(b=>b.getClientRects().length),i=items.indexOf(document.activeElement);if(items.length&&(i<0||(!e.shiftKey&&i===items.length-1)||(e.shiftKey&&i===0))){e.preventDefault();items[e.shiftKey?items.length-1:0].focus();}}return;}
    const keys={ArrowUp:[0,-1],ArrowDown:[0,1],ArrowLeft:[-1,0],ArrowRight:[1,0],w:[0,-1],s:[0,1],a:[-1,0],d:[1,0]};
    if(keys[e.key]){dir=keys[e.key];e.preventDefault();e.stopImmediatePropagation();SFX.unlock();BGM.start();}
    else if(['Enter',' ','A'].includes(e.key)){e.preventDefault();e.stopImmediatePropagation();interact();}
    else if(e.key==='Escape'){e.preventDefault();e.stopImmediatePropagation();journal();}
  },true);
  addEventListener('keyup',e=>{if(active()){dir=[0,0];if(['ArrowUp','ArrowDown','ArrowLeft','ArrowRight','w','a','s','d'].includes(e.key))e.stopImmediatePropagation();}},true);
  addEventListener('blur',()=>{dir=[0,0];});document.addEventListener('visibilitychange',()=>{dir=[0,0];});
  globalThis.RPG_TOWN={mount,active,takeSupplies,close:()=>{dir=[0,0];if(modal)closeModal();},get state(){return QA_MODE?state:undefined;}};
  for(const theme of ['stone','temple','mountain','wood','spire'])for(const slot of ['floor0','wallface']){
    const id='tile:'+theme+'#'+slot;if(HD_ASSETS[id]&&!HD_LOADED[id])artImage(id,'',()=>{});
  }
  mount();
  const editable=e=>e.target.closest('input,textarea,select,[contenteditable="true"]');
  $id('cabinet').addEventListener('contextmenu',e=>{if(!editable(e))e.preventDefault();});
  $id('cabinet').addEventListener('selectstart',e=>{if(!editable(e))e.preventDefault();});
})();

/* An optional exterior reached through a real wall door. Dungeon coordinates,
   combat, inventory and turn counters remain intact while on the terrace. */
(() => {
  let root,canvas,ctx,p={x:2,y:4,face:[0,1]},held=[0,0],goBack=false,opened=false,last=0,time=0,previousMusic=null;
  const door=()=>{
    if(!G||actAt(G.act).id!=='tower')return null;
    if(G.f._terraceDoor!==undefined)return G.f._terraceDoor;
    const candidates=[];
    for(let y=2;y<MH-2;y++)for(let x=2;x<MW-2;x++){
      if(tileAt(x,y)!==WALL||!walkable(x,y+1)||roomRectAt(x,y+1)<0||markCellAt(x,y))continue;
      if((G.f.relics||[]).some(r=>Math.hypot(r.x-x,r.y-y)<2))continue;
      candidates.push({x,y});
    }
    candidates.sort((a,b)=>b.x-a.x||a.y-b.y);
    return G.f._terraceDoor=candidates[0]||null;
  };
  function close(){opened=false;root.hidden=true;held=[0,0];goBack=false;BGM.force(previousMusic);SFX.play('door');}
  function move(dx,dy){p.x=Math.max(1.5,Math.min(10.4,p.x+dx*.18));p.y=Math.max(3.5,Math.min(6.6,p.y+dy*.18));p.face=[dx,dy];}
  function show(){
    if(!root){
      root=document.createElement('section');root.id='tower-terrace';root.hidden=true;root.innerHTML='<header><b id="terrace-title"></b><button id="terrace-return">走回塔門</button></header><canvas id="terrace-canvas" tabindex="0" aria-label="通天塔外側迴廊，方向鍵走動"></canvas><div id="terrace-controls"><button data-terrace="-1,0">◀</button><button data-terrace="0,-1">▲</button><button data-terrace="0,1">▼</button><button data-terrace="1,0">▶</button><span>靠近左側塔門，按 Enter 返回</span></div>';
      document.getElementById('cabinet').append(root);canvas=document.getElementById('terrace-canvas');ctx=canvas.getContext('2d');
      document.getElementById('terrace-return').onclick=()=>goBack=true;
      for(const b of root.querySelectorAll('[data-terrace]')){b.onpointerdown=e=>{e.preventDefault();b.setPointerCapture(e.pointerId);held=b.dataset.terrace.split(',').map(Number);};b.onpointerup=b.onpointercancel=b.onlostpointercapture=()=>held=[0,0];}
      requestAnimationFrame(frame);
    }
    p={x:2,y:4,face:[0,1]};held=[0,0];goBack=false;previousMusic=BGM.forced;BGM.force('terrace');
    root.hidden=false;opened=true;document.getElementById('terrace-title').textContent='通天塔 '+G.floor+'F · 外側迴廊';canvas.focus({preventScroll:true});SFX.play('door');
  }
  function draw(){
    const rect=canvas.getBoundingClientRect(),d=Math.min(devicePixelRatio||1,2),w=rect.width,h=rect.height;
    if(canvas.width!==Math.round(w*d)||canvas.height!==Math.round(h*d)){canvas.width=w*d;canvas.height=h*d;}
    ctx.setTransform(d,0,0,d,0,0);
    ctx.fillStyle='#192534';ctx.fillRect(0,0,w,h);
    const bg=HD_LOADED['hd:terrace'];
    // Fit the entire painted floor into the camera so a narrow phone cannot
    // crop away the return door or turn the walkable area into open sky.
    const scale=Math.min(w/1536,h/1024),bw=1536*scale,bh=1024*scale,ox=(w-bw)/2,oy=(h-bh)/2;
    if(bg)ctx.drawImage(bg,ox,oy,bw,bh);
    const px=ox+bw*(.14+(p.x-2)*.075),py=oy+bh*(.57+(p.y-4)*.09),size=bw*.073;
    const bob=(held[0]||held[1]||goBack)?Math.sin(time*13)*size*.025:Math.sin(time*2)*size*.005;
    ctx.fillStyle='#17202266';ctx.beginPath();ctx.ellipse(px,py,size*.25,size*.07,0,0,Math.PI*2);ctx.fill();
    const worn=hdHeroSprite(G.p.weap?WEAP.findIndex(a=>a.id===G.p.weap.d.id):-1,G.p.shld?SHLD.findIndex(a=>a.id===G.p.shld.d.id):-1,G.p.hat,VILLAGE.skin,VILLAGE.col,p.face)||heroNow();
    ctx.drawImage(worn,px-size/2,py-size+bob,size,size);
    ctx.fillStyle='#fff2cc';ctx.font='13px sans-serif';ctx.textAlign='center';ctx.fillText('塔內',ox+bw*.12,oy+bh*.57);
    // Gentle cloud-light drift, kept above the parapet and away from the floor.
    const glow=ctx.createLinearGradient(ox,oy,ox+bw,oy);glow.addColorStop(0,'#ffe7ac00');glow.addColorStop(.5,'rgba(255,232,176,'+(.018+.012*Math.sin(time*.25))+')');glow.addColorStop(1,'#ffe7ac00');ctx.fillStyle=glow;ctx.fillRect(ox+bw*.29,oy,bw*.71,bh*.4);
  }
  function frame(ts){const dt=Math.min(.04,(ts-last)/1000||0);last=ts;time+=dt;if(opened){
    if(goBack){const dx=2-p.x,dy=4-p.y,n=Math.hypot(dx,dy);if(n<.12)close();else{p.x+=dx/n*dt*3;p.y+=dy/n*dt*3;p.face=[-1,0];}}
    else if(held[0]||held[1]){p.x=Math.max(1.5,Math.min(10.4,p.x+held[0]*dt*3));p.y=Math.max(3.5,Math.min(6.6,p.y+held[1]*dt*3));p.face=held;}
    if((held[0]||held[1]||goBack)&&Math.floor(time*3)!==Math.floor((time-dt)*3))SFX.play('step',230);draw();
  }requestAnimationFrame(frame);}
  addEventListener('keydown',e=>{if(!opened)return;e.stopImmediatePropagation();const dirs={ArrowLeft:[-1,0],ArrowRight:[1,0],ArrowUp:[0,-1],ArrowDown:[0,1],a:[-1,0],d:[1,0],w:[0,-1],s:[0,1]};if(dirs[e.key]){e.preventDefault();goBack=false;held=dirs[e.key];}else if(e.key==='Escape'){e.preventDefault();goBack=true;}else if(e.key==='Enter'&&Math.hypot(p.x-2,p.y-4)<1){e.preventDefault();close();}},true);
  addEventListener('keyup',()=>{held=[0,0];});addEventListener('blur',()=>held=[0,0]);document.addEventListener('visibilitychange',()=>held=[0,0]);
  globalThis.RPG_BALCONY={get active(){return opened;},move,
    enterAt(x,y){const d=door();if(!d||d.x!==x||d.y!==y)return false;if(monInSight()){say('敵人就在附近，先脫離戰鬥再開啟外側門。','bad');return true;}show();return true;},
    drawDoor(c,ox,oy){const d=door();if(!d||!G.seen[key(d.x,d.y+1)])return;const x=ox+d.x*T,y=oy+d.y*T;c.save();c.fillStyle='#182338';c.fillRect(x+2,y-5,T-4,T+5);c.strokeStyle='#c4a366';c.lineWidth=1;c.strokeRect(x+2,y-5,T-4,T+5);c.fillStyle='#7e9ca4';c.fillRect(x+4,y-3,T-8,T+1);c.fillStyle='#ded095';c.fillRect(x+T-5,y+6,1,2);if(Math.hypot(G.p.x-d.x,G.p.y-d.y)<2){c.font='5px sans-serif';c.textAlign='center';c.fillStyle='#fff4cb';c.fillText('外側門 ↑',x+T/2,y-8);}c.restore();},
    get door(){return QA_MODE?door():undefined;}
  };
})();
