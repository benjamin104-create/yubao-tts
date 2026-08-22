// 靜態掃描：有沒有中文**直接**送到玩家眼前，沒有經過 TX() / M()。
//
// 為什麼還要第五支多語言檢查：前面四支都是「跑起來才掃得到」的 ——
//   · web/i18n.js    逐條丟進轉譯函式，掃得到每一張資料表
//   · web/msgs.js    攔 say()，自動玩幾十場，掃得到「機器人玩得到」的句子
//   · tools/check_tags.py    掃得到畫布上的名牌
//   · tools/check_screens.py 掃得到打得開的覆蓋畫面
//
// 它們合起來的涵蓋率是「執行得到的路徑」。但有一整類文字執行不到：
//   · 只有施法、發動技能才會出現的句子（機器人不施法）
//   · 只有錢不夠、只有餓到 0 才會出現的句子
//   · 只有按下「顯示名稱」「音效」開關才會出現的句子
//
// 這一支從**原始碼**下手，所以不管跑不跑得到都掃得到。
// 它跟前面四支互補：靜態掃得到「沒接上」，動態掃得到「接錯了」。
//
//     node web/strings.js
const fs = require('fs');

const HAN = /[㐀-鿿]/;
const src = fs.readFileSync(__dirname + '/index.html', 'utf8');
const m = src.match(/<script>\n"use strict";([\s\S]*)<\/script>/);
if(!m){ console.error('index.html 裡找不到遊戲腳本'); process.exit(2); }

/* 字典本身整段拿掉。它就是中文與譯文並排的地方，掃它只會得到一堆假警報。 */
let code = m[1].replace(/const DICT_RAW = `[\s\S]*?`;/, 'const DICT_RAW = ``;');

// 行號還原用：把拿掉的部分補回等量的換行，回報的行號才對得上原始檔
{
  const cut = m[1].match(/const DICT_RAW = `[\s\S]*?`;/);
  if(cut){
    const nl = (cut[0].match(/\n/g) || []).length;
    code = code.replace('const DICT_RAW = ``;', 'const DICT_RAW = ``;' + '\n'.repeat(nl));
  }
}
/* 美術驗收入口（?qa=...）整段拿掉。那一段是**開發用的工具頁** ——
   只有帶著 ?qa= 參數才進得去，玩家永遠看不到它，而它的標籤
   （「頭目美術驗收」「回快速測試總表」）是給做美術的人看的。
   把工具的字也算成漏翻，等於逼人替一個沒有玩家的畫面寫三種語言。

   拿掉的是**一段明確標好邊界的區域**，不是「含有 qa 的行」——
   後者會在別人把某個玩家看得到的函式取名成 qaSomething 的時候
   悄悄地少掃一塊。邊界找不到就整段不切（寧可誤報，不可漏掉）。 */
{
  const a = m[1].indexOf('/* ═══ 美術驗收入口（?qa=...）');
  const b = m[1].indexOf('/* ─── 啟動 ───', a + 1);
  if(a >= 0 && b > a){
    const cutQa = m[1].slice(a, b);
    const nl = (cutQa.match(/\n/g) || []).length;
    code = code.replace(cutQa, '\n'.repeat(nl));
  } else {
    console.log('※ 找不到美術驗收頁的邊界 —— 這一段照樣掃（可能是註解被改過）');
  }
}
const head = src.slice(0, src.indexOf(m[1]));
const baseLine = (head.match(/\n/g) || []).length;
const lineOf = i => baseLine + (code.slice(0, i).match(/\n/g) || []).length;

/* 從 open 這個左括號往後找到配對的右括號。
   字串與樣板字面值裡的括號不算 —— 不處理的話，
   say('（腳下購買）') 這種句子會讓整個掃描從中間斷掉。 */
function balanced(s, open){
  let d = 0, q = null;
  for(let i = open; i < s.length; i++){
    const c = s[i];
    if(q){
      if(c === '\\'){ i++; continue; }
      if(c === q) q = null;
      continue;
    }
    if(c === "'" || c === '"' || c === '`'){ q = c; continue; }
    if(c === '(') d++;
    else if(c === ')'){ d--; if(!d) return i; }
  }
  return -1;
}

// 玩家看得到的出口。少一個就是少掃一塊。
const SINKS = /\b(say|keeperSay|btn|float|prompt|alert)\s*\(|\.(textContent|innerHTML|placeholder|value)\s*=/g;
// 已經翻好的東西：TX/M 是轉譯函式，loc* 回傳的是當下語言的名字
const WRAPPED = /\b(TX|M|loc[A-Z]\w*|nameOf|defNm|jobRank|costLabel|keepLine)\s*\(/;

/* 允許清單。跟 tools/check_screens.py 同一條規矩：**刻意留短**，
   每多一條就少一分保護，所以每一條都要說得出理由。
   狀態鍵是遊戲內部的識別字（`p.st['睡']`），拿來比對而不是顯示；
   「中文」是語言鈕的後備字串，那顆鈕本來就永遠顯示自己的語言。 */
const OK = new Set(['睡','麻','亂','盲','燒','毒','速','守','歌','熔','影','鏡','界','雷','怒','中文']);

const leaks = [];
let mm;
while((mm = SINKS.exec(code))){
  // 取這個出口後面那一整段（呼叫的引數，或指派的右手邊）
  let seg;
  const at = mm.index + mm[0].length - 1;
  if(mm[0].endsWith('(')){
    const close = balanced(code, at);
    if(close < 0) continue;
    seg = code.slice(at + 1, close);
  } else {
    /* 指派：預設吃到行尾，但如果這一行有沒收掉的左括號就一路吃到配對為止。
       不這樣做的話，跨行的 M('key', '中文預設', {...}) 只被看到第一行，
       挖掉「已翻好的呼叫」那一步會因為括號不成對而放棄 ——
       於是**每一個跨行的 M() 都會被誤報成漏翻**。
       這是掃描器自己的 bug，先修它，才有辦法相信它報的東西。 */
    const from = mm.index + mm[0].length;
    let nl = code.indexOf('\n', from);
    if(nl < 0) nl = code.length;
    seg = code.slice(from, nl);
    const open = seg.indexOf('(');
    if(open >= 0 && balanced(seg, open) < 0){
      const close = balanced(code, from + open);
      if(close > 0) seg = code.slice(from, close + 1);
    }
  }
  // 把所有「已經翻好」的呼叫連同引數整段挖掉，剩下的才是裸露的東西
  let bare = seg;
  for(let pass = 0; pass < 12; pass++){
    const w = bare.search(WRAPPED);
    if(w < 0) break;
    const open = bare.indexOf('(', w);
    const close = balanced(bare, open);
    if(close < 0) break;
    bare = bare.slice(0, w) + 'Ⓣ' + bare.slice(close + 1);
  }
  const lits = bare.match(/'(?:[^'\\]|\\.)*'|"(?:[^"\\]|\\.)*"|`(?:[^`\\]|\\.)*`/g) || [];
  const bad = lits.filter(s => HAN.test(s) && !OK.has(s.slice(1, -1)));
  if(bad.length) leaks.push({ line: lineOf(mm.index), what: mm[0], lits: bad });
}

console.log('=== 原始碼掃描：沒有經過 TX() / M() 的中文 ===\n');
for(const l of leaks){
  console.log('✗ 第 %d 行　%s', l.line, l.what.trim());
  for(const s of l.lits.slice(0, 3)) console.log('     ' + s.slice(0, 90));
}
console.log(leaks.length ? '\n共 %d 處' : '\n沒有裸露的中文', leaks.length);
process.exit(leaks.length ? 1 : 0);
