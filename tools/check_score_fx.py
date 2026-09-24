"""Render complete musical forms, and every player effect through a real canvas."""
import base64
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parent.parent
BASE=os.environ.get('GAME_URL',(ROOT/'web/index.html').as_uri()).split('?')[0]
OUT=ROOT/'work/rpg-v23'
OUT.mkdir(parents=True,exist_ok=True)


def main():
    with sync_playwright() as pw:
        browser=pw.chromium.launch(args=['--allow-file-access-from-files'])
        page=browser.new_page(viewport={'width':390,'height':844},device_scale_factor=2)
        errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(BASE+'?qa=floor&act=temple&seed=81291')
        page.wait_for_function('()=>G&&globalThis.RPG_PLAYER_FX&&BGM.TRACKS.combat.score')
        page.locator('body').click(position={'x':5,'y':5})
        page.evaluate('()=>{SFX.unlock();BGM.stop();}')
        ids=page.evaluate('()=>Object.keys(BGM.TRACKS).filter(id=>BGM.TRACKS[id].score)')
        if os.environ.get('SCORE_IDS'):ids=os.environ['SCORE_IDS'].split(',')
        if os.environ.get('SKIP_SCORE'):ids=[]
        report={}
        for tid in ids:
            result=page.evaluate('''async id=>{
              const t=BGM.TRACKS[id];
              if(t.score.length!==32)throw Error('Incomplete form: '+id);
              for(const b of t.score)for(const part of ['lead','bass','arp','counter'])for(const [s,n,d]of b[part])
                if(s<0||s+d>16.01||d<=0||!Number.isFinite(n))throw Error('Invalid note '+id);
              const audio=await BGM.qaRender(id);let peak=0,sum=0,count=0;
              for(let ch=0;ch<audio.numberOfChannels;ch++)for(const v of audio.getChannelData(ch)){
                peak=Math.max(peak,Math.abs(v));sum+=v*v;count++;
              }
              window.scoreSample=audio;
              const db=x=>Math.round(200*Math.log10(x||1e-9))/10;
              return {rms:db(Math.sqrt(sum/count)),peak:db(peak),seconds:audio.duration};
            }''',tid)
            print(tid,result,flush=True)
            report[tid]=result
            if os.environ.get('SAVE_AUDIO') and tid in ['combat','boss_guardian','chapter_temple']:
                data=page.evaluate('''()=>{
                  const a=window.scoreSample,len=Math.min(a.length,a.sampleRate*24),out=new ArrayBuffer(44+len*4),v=new DataView(out);
                  const str=(o,s)=>[...s].forEach((c,i)=>v.setUint8(o+i,c.charCodeAt(0)));
                  str(0,'RIFF');v.setUint32(4,36+len*4,true);str(8,'WAVE');str(12,'fmt ');v.setUint32(16,16,true);
                  v.setUint16(20,1,true);v.setUint16(22,2,true);v.setUint32(24,a.sampleRate,true);v.setUint32(28,a.sampleRate*4,true);
                  v.setUint16(32,4,true);v.setUint16(34,16,true);str(36,'data');v.setUint32(40,len*4,true);
                  for(let i=0;i<len;i++)for(let ch=0;ch<2;ch++)v.setInt16(44+i*4+ch*2,Math.max(-1,Math.min(1,a.getChannelData(ch)[i]))*32767,true);
                  let s='';for(const byte of new Uint8Array(out))s+=String.fromCharCode(byte);return btoa(s);
                }''')
                (OUT/(tid+'.wav')).write_bytes(base64.b64decode(data))
        if report:(OUT/'score-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        for tid,result in report.items():
            assert -30<=result['rms']<=-14,(tid,result)
            assert result['peak']<=-2,(tid,result)
        # Freeze the presentation clock only within this synchronous draw check.
        count=page.evaluate('''()=>{
          const before=JSON.stringify({p:G.p,mons:G.mons,turn:G.turn,rng:G.rng,f:G.f});
          const c=document.createElement('canvas');c.width=640;c.height=480;const x=c.getContext('2d');
          const orig=performance.now.bind(performance);let time=orig();performance.now=()=>time;
          const defs=[...SPELLS,...ABIL.filter(a=>a.t!=='pass'),...MASTER];
          try{for(const d of defs){RPG_PLAYER_FX.cast(d,1,0);for(const dt of [80,240,400]){time+=dt;RPG_PLAYER_FX.draw(x,160-G.p.x*T,240-G.p.y*T);}time+=2000;RPG_PLAYER_FX.draw(x,0,0);}}
          finally{delete performance.now;}
          if(before!==JSON.stringify({p:G.p,mons:G.mons,turn:G.turn,rng:G.rng,f:G.f}))throw Error('FX modified gameplay');
          return defs.length;
        }''')
        for name in ['flame','spark','gust','cure']:
            page.evaluate('id=>RPG_PLAYER_FX.cast(SPELLS.find(s=>s.id===id),1,0)',name)
            page.wait_for_timeout(570)
            page.screenshot(path=str(OUT/('effect-'+name+'.png')))
            page.wait_for_timeout(1100)
        assert not errors,errors
        print('PASS complete scores:',len(ids),'player effects:',count,flush=True)
        browser.close()


if __name__=='__main__':main()
