// 對話分頁回歸：長句必須真的拆頁，A 鍵提示與白色向下三角也必須接上。
const { api } = require('./simcore.js');
const assert = require('assert');
const fs = require('fs');

let pass=0,fail=0;
function t(name,fn){
  try{fn();console.log('✓ '+name);pass++;}
  catch(e){console.log('✗ '+name+'\n    '+e.message);fail++;}
}

t('短對話維持一頁',()=>{
  assert.strictEqual(api.splitTalk('這是哪裡？我得先站起來。').length,1);
});

t('長對話會依句尾拆成多頁',()=>{
  const body='很久以前，兩河之間的人把星辰與數字刻進泥板。'+
    '他們建起一座想抵達天空的塔，卻在塔完成之前失去了共同的語言。'+
    '千年之後，封閉的神殿再次亮起藍光，而你在最深處醒來。';
  const pages=api.splitTalk(body);
  assert(pages.length>=2,'長文仍只有一頁');
  assert.strictEqual(pages.join(''),body,'分頁遺失了文字');
});

t('畫面有向下三角，A／Enter 會呼叫翻頁',()=>{
  const html=fs.readFileSync(__dirname+'/index.html','utf8');
  assert(/id="talkmore"/.test(html),'缺少向下三角元素');
  assert(/border-top:8px solid #fff/.test(html),'提示不是白色向下三角');
  assert(/k==='a'\|\|k==='A'\)\{ advanceTalk\(\)/.test(html),'鍵盤 A 沒有翻頁');
  assert(/if\(talkOpen\(\)\)\{ advanceTalk\(\); return; \}/.test(html),'手機 A 沒有翻頁');
});

t('長文提供框內翻頁按鈕，且觸控手把不被對話遮罩蓋住',()=>{
  const html=fs.readFileSync(__dirname+'/index.html','utf8');
  assert(/id="talknext"[^>]*><span id="talknextlabel"><\/span><i id="talkmore"/.test(html),
    '白色三角必須跟著可點的翻頁按鈕');
  assert(html.includes("$('talknext').onclick = ()=> advanceTalk();"),'翻頁按鈕未接線');
  assert(html.includes('next.hidden=!wait'),'最後一頁仍保留翻頁按鈕，可能誤接任務');
  assert(/#screenwrap:has\(#talk.on\) #pad\{z-index:31\}/.test(html),'A/B 仍被 z-index:30 遮罩擋住');
  assert(html.includes("t.closest('#talk')"),'對話點擊可能漏進地圖觸控');
});

console.log('\n對話檢查：通過 %d，失敗 %d',pass,fail);
process.exit(fail?1:0);
