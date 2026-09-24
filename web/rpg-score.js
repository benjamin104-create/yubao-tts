/* Original v23 arrangements. Instrument-inspired synthesis, not historical recordings.
   Eight-bar harmony; A / developed A / contrasting B / return. All pitches are
   authored or deterministically voiced, independent of combat RNG and save data. */
(() => {
  const T=BGM.TRACKS;
  const minor=[[0,0],[8,1],[3,1],[10,1],[5,0],[8,1],[7,1],[0,0]];
  const minorB=[[3,1],[10,1],[8,1],[5,0],[0,0],[8,1],[7,1],[7,1]];
  const major=[[0,1],[7,1],[9,0],[4,0],[5,1],[0,1],[2,0],[7,1]];
  const majorB=[[5,1],[7,1],[4,0],[9,0],[2,0],[5,1],[7,1],[7,1]];
  const hero=[
    [[0,2],[7,2],[12,4],[10,2],[7,2],[3,4]],
    [[8,3],[12,1],[15,4],[14,2],[12,2],[8,4]],
    [[7,2],[10,2],[15,4],[14,2],[10,2],[7,4]],
    [[10,3],[14,1],[17,4],[15,2],[14,2],[10,4]],
    [[5,2],[8,2],[12,4],[10,2],[8,2],[5,4]],
    [[8,2],[12,2],[15,4],[19,2],[15,2],[12,4]],
    [[11,2],[14,2],[19,4],[17,2],[14,2],[11,4]],
    [[12,4],[7,2],[3,2],[2,2],[0,6]]
  ];
  const defiance=[
    [[0,3],[0,1],[7,2],[10,2],[12,4],[7,4]],
    [[12,4],[15,2],[14,2],[12,4],[8,4]],
    [[10,3],[7,1],[3,2],[7,2],[15,6],[14,2]],
    [[14,4],[10,2],[5,2],[10,4],[14,4]],
    [[8,3],[5,1],[0,2],[5,2],[12,4],[8,4]],
    [[15,4],[12,2],[8,2],[12,6],[15,2]],
    [[14,3],[11,1],[7,2],[11,2],[19,4],[14,4]],
    [[12,6],[7,2],[3,4],[0,4]]
  ];
  const nearest=(n,pcs)=>{let best=n,dist=99;for(let v=n-6;v<=n+6;v++)if(pcs.includes((v%12+12)%12)&&Math.abs(v-n)<dist){best=v;dist=Math.abs(v-n);}return best;};
  function voicing(root,quality,previous){
    const pcs=[root,root+(quality?4:3),root+7].map(n=>n%12),out=[];
    // Smooth inner voices, no simultaneous doubled bass muddying the low register.
    for(let j=0;j<3;j++){
      const choices=[];for(let n=50;n<=72;n++)if(pcs.includes(n%12)&&!out.some(x=>x%12===n%12))choices.push(n);
      choices.sort((a,b)=>Math.abs(a-(previous?.[j]||[55,60,65][j]))-Math.abs(b-(previous?.[j]||[55,60,65][j])));
      out.push(choices[0]);
    }
    return out.sort((a,b)=>a-b);
  }
  function arrange(id,opt={}){
    const old=T[id];if(!old)return;
    const mode=opt.major?'major':'minor',tonic=opt.tonic??62,battle=!!opt.battle,boss=!!opt.boss;
    const prog=opt.major?major:minor,bridge=opt.major?majorB:minorB;
    const source=opt.motif||old.answer||old.lead,score=[];let previous=null;
    for(let section=0;section<4;section++)for(let b=0;b<8;b++){
      const [degree,quality]=(section===2?bridge:prog)[b],root=tonic-24+degree;
      const chord=voicing(root,quality,previous);previous=chord;
      const pcs=[root,root+(quality?4:3),root+7].map(n=>n%12);
      const scale=(opt.major?[0,2,4,5,7,9,11]:[0,2,3,5,7,8,10]).map(n=>(n+tonic)%12);
      let lead;
      if(opt.motif){let s=0;lead=source[b].map(([n,d])=>{const event=[s,tonic+n,d];s+=d;return event;});}
      else lead=source[b%source.length].map(([s,n,d])=>[s,n,d]);
      if(section===2){
        // A singing B phrase leaves air between the driving A figures.
        lead=[[0,chord[2]+12,6],[6,chord[1]+12,2],[8,chord[0]+12,4],[12,chord[1]+12,4]];
      }
      lead=lead.map(([s,n,d],i)=>{
        n=nearest(n,(s%4===0||i===lead.length-1)?pcs:scale);
        while(n>84)n-=12;while(n<60)n+=12;
        return [s,n,Math.min(d,16-s)];
      });
      if(section===3&&b===7)lead=[[0,tonic+12,8],[8,tonic+7,4],[12,tonic,4]];
      const energy=(battle?[.87,.98,1,.84]:[.84,.94,1,.82])[section];
      const bassSteps=battle?[0,3,6,8,11,14]:[0,8];
      const bass=bassSteps.map((s,i)=>[s,root+(i%3===2?7:0),Math.min(16-s,battle?2.6:7.2)]);
      const arpSteps=section===0&&!battle?[0,8]:section===3?[0,4,8,12]:[0,2,4,6,8,10,12,14];
      const arp=arpSteps.map((s,i)=>[s,chord[[0,1,2,1][i%4]]+12,Math.min(16-s,battle?1.7:2.6)]);
      const counter=section===1||section===2?[[4,chord[1]+12,4],[12,chord[2]+12,3.7]]:[];
      const busy=section===1||section===2,quiet=opt.quiet;
      const drums={kick:quiet?[]:battle?(boss?[0,6,8,14]:[0,8]):[0],
        snare:battle?[4,12]:[],hat:quiet?[]:battle?(busy?[2,6,10,14]:[6,14]):[],
        tom:quiet?[]:battle?(b===7?[10,12,14,15]:boss?[3,11]:[14]):b%2?[10]:[]};
      // A low-drum guardian, a syncopated hunter and ritual bells remain distinct.
      if(opt.drums==='heavy'){drums.snare=[];drums.kick=[0,7,10];drums.tom=b===7?[9,12,14,15]:[4,12];}
      if(opt.drums==='chase'){drums.kick=[0,6,11];drums.snare=[3,10];}
      if(opt.drums==='ritual'){drums.snare=[];drums.tom=[3,10,14];}
      score.push({chord,root,lead,bass,arp,counter,drums,energy,double:boss&&busy});
    }
    Object.assign(old,{score,scoreVersion:23,bars:32,bpm:opt.bpm||old.bpm,
      instrument:opt.instrument||old.instrument||'flute',pluck:old.pluck||'lyre',
      cut:opt.instrument==='horn'?2100:2500,lvol:battle?.070:.067,avol:battle?.025:.031,
      padvol:battle?.031:.035,mvol:opt.volume||.78,tonic,mode});
  }
  // The two themes are composed in full, with different motifs and harmonic rhythm.
  arrange('combat',{bpm:132,tonic:62,battle:true,instrument:'horn',motif:hero});
  arrange('boss',{bpm:142,tonic:60,battle:true,boss:true,instrument:'horn',motif:defiance});
  arrange('boss_guardian',{bpm:106,tonic:62,battle:true,boss:true,instrument:'horn',motif:defiance,drums:'heavy'});
  arrange('boss_trickster',{bpm:146,tonic:64,battle:true,boss:true,instrument:'flute',motif:hero,drums:'chase',volume:.61});
  arrange('boss_arcane',{bpm:120,tonic:60,battle:true,boss:true,instrument:'bell',motif:defiance,drums:'ritual',volume:.65});
  arrange('boss_warlord',{bpm:124,tonic:57,battle:true,boss:true,instrument:'bowed',motif:hero,drums:'heavy'});
  arrange('mind_gaze',{bpm:84,tonic:62,boss:true,instrument:'flute',quiet:true});
  arrange('mind_echo',{bpm:128,tonic:62,battle:true,boss:true,instrument:'bell',motif:defiance,drums:'ritual',volume:.59});
  arrange('mind_unity',{bpm:150,tonic:62,battle:true,boss:true,instrument:'horn',motif:hero});
  arrange('hall',{bpm:126,tonic:60,battle:true,instrument:'bowed',motif:defiance,drums:'chase'});
  arrange('title',{bpm:88,tonic:62,instrument:'horn',motif:hero});
  arrange('village',{bpm:78,tonic:67,major:true,instrument:'flute',quiet:true});
  const keys={temple:62,mine:62,forest:67,trial:62,ordeal:57,briar:60,lake:62,beast:67,ninja:62,heian:64,gaol:57,mirror:60,crystal:59,hall:62,tower:62,final:60,chaos:57,vault:57};
  for(const [id,tonic]of Object.entries(keys))arrange('chapter_'+id,{tonic,major:['forest','lake','heian','crystal'].includes(id),quiet:['mine','lake','heian','gaol','final','chaos'].includes(id)});
  arrange('terrace',{bpm:68,tonic:62,major:true,instrument:'flute',quiet:true});
  for(const id of ['ending_afterglow','ending_home','ending_horizon'])arrange(id,{tonic:id==='ending_home'?67:62,major:true,quiet:true});
})();
