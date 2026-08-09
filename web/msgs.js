// 訊息簿的多語言檢查：真的玩幾十場，把每一句出現過的訊息攔下來看。
//
// 為什麼不是掃畫面：戰鬥、陷阱、詛咒、鑑定、店員、休息、召喚 ——
// 這些訊息只在特定情況才出現，把畫面一個一個打開是掃不到的。
// 使用者最後一次回報的就是這種：日文模式下打完一場，訊息簿冒出
// 「★ 看清楚了 —— 那是「麻痺草」。」
//
// 做法：把 say() 攔下來，用跟 sim.js 一樣的自動遊玩跑幾十場，
// 收集所有實際發生過的句子，再檢查裡面有沒有中文。
// 涵蓋率因此等於「機器人玩得到的範圍」，而不是「我想得到的範圍」。
const { api } = require('./simcore.js');

const HAN = /[㐀-鿿]/;
const KANA = /[぀-ゟ゠-ヿ]/;
const GAMES = 24;
const TURNS = 1500;

// 本來就是漢字的日文。跟 tools/check_screens.py 同一份理由：清單要短。
const OK_JA = /^[攻防]\s*[+＋]?\d*$/;

function play(G){
  let t = 0;
  while(!G.over && t < TURNS){
    const p = G.p;
    const food = p.inv.find(i => i.cat === 'food');
    if(p.sat < 25000 && food){ api.useItem(food, false); api.endTurn(); t++; continue; }
    // 什麼都用一點，才碰得到「喝到毒草」「杖沒效力了」那些句子
    if(p.hp === p.mhp){
      const any = p.inv.find(i => i.cat === 'herb' || i.cat === 'scroll');
      if(any){ api.useItem(any, false); api.endTurn(); t++; continue; }
    }
    if(p.hp * 2 < p.mhp){
      const h = p.inv.find(i => i.cat === 'herb' && i.id === 'heal');
      if(h){ api.useItem(h, false); api.endTurn(); t++; continue; }
    }
    let hit = false;
    for(const d of api.DIRS){
      const m = api.monAt(p.x + d[0], p.y + d[1]);
      if(m && api.cornerOK(p.x, p.y, p.x + d[0], p.y + d[1])){
        api.tryMove(d[0], d[1]); hit = true; break;
      }
    }
    if(hit){ t++; continue; }
    const k = api.key(p.x, p.y), here = G.items[k];
    if(here && !here.shop && p.inv.length < 20){
      p.inv.push(here); delete G.items[k]; api.endTurn(); t++; continue;
    }
    if(api.tileAt(p.x, p.y) === api.DOWN && !G.f.bossLock){ api.descend(); t++; continue; }
    let goal = G.f.stairs;
    if(G.f.bossLock && G.mons.length) goal = {x:G.mons[0].x, y:G.mons[0].y};
    const step = api.nextStep(G, {x:p.x, y:p.y}, goal);
    if(!step){ api.endTurn(); t++; continue; }
    api.tryMove(step[0], step[1]);
    t++;
  }
}

const V = api.VILLAGE();
const seen = { en: new Set(), ja: new Set() };
const hooked = api.hookSay(txt => {
  const L = api.i18n.LANG();
  if(seen[L]) seen[L].add(txt);
});

for(const lang of ['en', 'ja']){
  api.i18n.setLang(lang);
  // 每一章都走一遍：章節專屬的訊息（頭目台詞、獎勵、增援）才碰得到
  for(let g = 0; g < GAMES; g++){
    V.act = g % api.ACTS.length;
    api.newGame(2000 + g * 37);
    play(api.G());
  }
}
api.i18n.setLang('zh');
hooked();

console.log('=== 訊息簿多語言（自動遊玩 %d 場 x 2 語言）===\n', GAMES);
let bad = 0;
for(const lang of ['en', 'ja']){
  const leak = [];
  for(const t of seen[lang]){
    if(!HAN.test(t)) continue;
    if(lang === 'ja' && KANA.test(t)) continue;
    if(lang === 'ja' && OK_JA.test(t.trim())) continue;
    leak.push(t);
  }
  console.log('%s　收集 %d 句，殘留 %d 句', lang.toUpperCase(), seen[lang].size, leak.length);
  for(const l of leak.slice(0, 20)) console.log('   ' + l);
  bad += leak.length;
}
process.exit(bad ? 1 : 0);
