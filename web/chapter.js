// 章節炭筆分鏡回歸：十八章、四腳主角、流程鉤子與離線包缺一不可。
const assert = require('assert');
const fs = require('fs');
const path = require('path');

const html = fs.readFileSync(path.join(__dirname,'index.html'),'utf8');
let pass=0, fail=0;
function t(name,fn){
  try{fn();console.log('✓ '+name);pass++;}
  catch(e){console.log('✗ '+name+'\n    '+e.message);fail++;}
}

t('十八章炭筆背景都存在並有實際內容',()=>{
  for(let i=1;i<=18;i++){
    const n=String(i).padStart(2,'0');
    const f=path.join(__dirname,'art','promo',`chapter-charcoal-${n}-v1.jpg`);
    assert(fs.existsSync(f),`缺少第 ${n} 章`);
    assert(fs.statSync(f).size>70000,`第 ${n} 章疑似空白或過度壓縮`);
    assert(html.includes(`url("art/promo/chapter-charcoal-${n}-v1.jpg")`),`第 ${n} 章未接入 CSS`);
  }
});

t('四腳主角透明層有接入章節舞台',()=>{
  const f=path.join(__dirname,'art','promo','chapter-charcoal-hero-v1.png');
  assert(fs.existsSync(f),'缺少章節主角');
  assert(fs.statSync(f).size>100000,'章節主角疑似被換成低品質暫存圖');
  assert(/id="chapterhero"/.test(html),'舞台沒有主角層');
  assert(/chapter-charcoal-hero-v1\.png/.test(html),'主角圖沒有被引用');
});

t('村莊出發會播放章節分鏡，死亡重試不強制重播',()=>{
  assert((html.match(/restart\(true\)/g)||[]).length>=2,'主線或副本出發沒有接上分鏡');
  assert(/function restart\(withChapterPrelude\)/.test(html),'重開流程沒有分鏡參數');
  assert(/chapterSeen/.test(html),'沒有記住已看過的章節');
});

t('章節分鏡是輕量 CSS 動畫並有手機驗收入口',()=>{
  assert(/@keyframes chapterDrift/.test(html),'背景沒有分鏡動畫');
  assert(/@keyframes chapterHeroIn/.test(html),'四腳主角沒有進場動畫');
  assert(/kind==='chapter'/.test(html),'缺少直接測試章節動畫的網址');
  assert(/prefers-reduced-motion:reduce/.test(html),'沒有尊重減少動態設定');
});

console.log('\n章節分鏡檢查：通過 %d，失敗 %d',pass,fail);
process.exit(fail?1:0);
