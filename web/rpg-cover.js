/* One protagonist, three real equipment silhouettes. Preview never grants equipment. */
(() => {
  const root=document.getElementById('cover'),poster=document.getElementById('coverposter');
  const url=id=>{const f=HD_ASSETS[id];return f?globalThis.BABEL_HD_DATA?.[f]||'art-hd/'+f:'';};
  root.classList.add('party-cover');
  // Existing temple artwork has blue glazed panels, golden lions and rosettes.
  if(HD_MODE)poster.style.backgroundImage='url("'+url('hd:prologue-3')+'")';
  const glaze=document.createElement('div');glaze.id='cover-glaze';glaze.setAttribute('aria-hidden','true');
  glaze.style.setProperty('--glaze-art','url("'+url('hd:prologue-3')+'")');glaze.innerHTML='<i></i><i></i>';root.append(glaze);
  const party=document.createElement('div');party.id='cover-party';party.setAttribute('role','img');party.setAttribute('aria-label','同一位主角的三種裝備與帽子穿戴展示');
  const outfits=[
    {id:'cover-mage',hat:'cone',weapon:4,shield:-1,face:[-1,0]},
    {id:'cover-ranger',hat:'plume',weapon:2,shield:1,face:[1,0]},
    {id:'cover-knight',hat:'helm',weapon:3,shield:2,face:[0,1]}
  ];
  for(const outfit of outfits){const c=document.createElement('canvas');c.id=outfit.id;c.width=c.height=256;c.setAttribute('aria-hidden','true');party.append(c);}
  const note=document.createElement('p');note.id='cover-equipment-note';party.append(note);
  root.insertBefore(party,document.getElementById('coverfoot'));
  const status=document.createElement('div');status.id='cover-color-status';status.setAttribute('aria-live','polite');document.getElementById('cols').before(status);
  let queued=false;
  function labels(){
    const words=LANG==='en'?['Choose your colour','Equipment and hats are found during your journey']:LANG==='ja'?['主人公の色を選ぶ','装備と帽子は冒険の中で手に入ります']:['選擇主角色彩','穿戴示意 · 裝備與帽子在冒險中取得'];
    note.textContent=words[1];status.textContent=words[0]+' · '+coverColorLabel(VILLAGE.col);
    for(const b of document.querySelectorAll('#cols button')){const label=coverColorLabel(b.dataset.color);b.title=label;b.setAttribute('aria-label',label);b.querySelector('span').textContent=label;}
  }
  function paint(){
    for(const o of outfits){
      const c=document.getElementById(o.id),x=c.getContext('2d');x.clearRect(0,0,256,256);
      const img=hdHeroSprite(o.weapon,o.shield,o.hat,VILLAGE.skin,VILLAGE.col,o.face)||heroSprite(o.weapon,o.shield,o.hat,VILLAGE.skin,VILLAGE.col);
      if(img){x.imageSmoothingEnabled=true;x.imageSmoothingQuality='high';x.drawImage(img,0,0,256,256);}
    }
    labels();
  }
  function redraw(){if(queued)return;queued=true;requestAnimationFrame(()=>{queued=false;paint();});}
  new MutationObserver(redraw).observe(document.documentElement,{attributes:true,attributeFilter:['lang']});
  globalThis.RPG_COVER={paint,announce:labels};heroArtHooks.push(redraw);paint();
})();
