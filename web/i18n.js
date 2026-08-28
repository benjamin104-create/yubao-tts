// 多語言覆蓋率檢查：把每一張資料表逐條丟進真正的轉譯函式，
// 看有沒有哪一條在英文／日文模式下還是吐出中文。
//
// 為什麼不是「跑一場遊戲看畫面」：大半的名字只在特定情況才出現 ——
// 隱藏職業的技能、第十三章才有的怪、喝到毒草才會看到的那句話。
// 跑十場也碰不到，但玩家總有一天會碰到，然後畫面上冒出一句中文。
//
// 為什麼不是靜態掃字串：程式裡的中文有兩種，一種是殘留、一種是
// `TX('key','中文')` 的**預設值** —— 後者在切語言時會被詞表蓋掉，
// 完全正常。靜態掃分不出這兩者，只會產生一份沒人想看的假警報。
// 唯一可靠的判準是：呼叫轉譯函式，看它回什麼。
const { api } = require('./simcore.js');

const HAN = /[㐀-鿿]/;                    // 只看漢字；日文模式本來就有假名
const KANA = /[぀-ゟ゠-ヿ]/;

const T = api.i18n;
const miss = { en: [], ja: [] };

function check(lang, label, got, src){
  if(!HAN.test(got)) return;
  // 日文用漢字是正常的 —— 只有「跟中文原文一模一樣」才算沒翻
  if(lang === 'ja' && got !== src) return;
  miss[lang].push(label + '　→ ' + got);
}

for(const lang of ['en', 'ja']){
  T.setLang(lang);

  for(const d of T.MONS)  check(lang, 'mon.'  + d.id, T.locName('mon', d), d.nm);
  for(const d of T.BOSS)  check(lang, 'mon.'  + d.id, T.locName('mon', d), d.nm);
  for(const d of T.BOSS) if(d.line)
                          check(lang, 'bl.'   + d.id, T.TX('bl.' + d.id, d.line), d.line);
  for(const [cat, list] of T.ITEM_TABLES)
    for(const d of list)  check(lang, 'it.'   + d.id, T.locName(cat, d), d.nm);
  for(const d of T.HAT){
                          check(lang, 'hat.'  + d.id, T.locName('hat', d), d.nm);
                          check(lang, 'job.'  + d.job, T.locJob(d.job), d.jobnm);
    /* 練滿職業拿到的永久被動。這張表漏了很久 —— 而且不是「沒翻」，
       是畫面上寫著「只有中文版才顯示這一句」，於是英日文玩家練滿之後
       遊戲一個字都不告訴他拿到了什麼。
       靜態掃描抓不到（中文在變數裡，不在字面值裡），只有這裡驗得到。 */
                          check(lang, 'mp.'   + d.job, T.locPassive(d.job), T.MASTER_PASSIVE[d.job]);
  }
  for(const a of T.ABIL){
                          check(lang, 'ab.'   + a.id, T.locAbil(a), a.nm);
                          check(lang, 'd.'    + a.id, T.TX('d.' + a.id, a.desc), a.desc);
  }
  for(const s of T.SPELLS){
                          check(lang, 'sp.'   + s.id, T.locSpell(s), s.nm);
                          check(lang, 'sd.'   + s.id, T.locSpellD(s), s.desc);
  }
  for(const s of T.SUMMONS) check(lang, 'sm.' + s.id, T.locSummon(s), s.nm);
  for(const s of T.SCHOOLS) check(lang, 'sch.'+ s.id, T.TX('sch.' + s.id, s.nm), s.nm);
  for(const a of T.ACTS){
                          check(lang, 'act.'  + a.id, T.locAct(a), a.nm);
    if(a.intro)           check(lang, 'acti.' + a.id, T.TX('acti.' + a.id, a.intro), a.intro);
    if(a.reward)          check(lang, 'actr.' + a.id, T.TX('actr.' + a.id, a.reward), a.reward);
  }
  for(const st of ['毒','睡','亂','麻','夾','咬','盲','速','燒','怒','守','界','影','雷','鏡'])
                          check(lang, 'st.'   + st, T.TX('st.' + st, st), st);
  // 未鑑定道具的外觀名（「赤紅的草」「螺旋的杖」）
  for(const k in T.LOOK)
    T.LOOK[k].forEach((nm, i) => check(lang, 'lk.' + k + '.' + i, T.TX('lk.' + k + '.' + i, nm), nm));
}
T.setLang('zh');

console.log('=== 多語言覆蓋率 ===\n');
let bad = 0;
for(const lang of ['en', 'ja']){
  const list = miss[lang];
  if(!list.length){ console.log('%s　✓ 全部有翻譯', lang.toUpperCase()); continue; }
  bad += list.length;
  console.log('%s　✗ %d 條沒有翻譯：', lang.toUpperCase(), list.length);
  for(const l of list) console.log('   ' + l);
  console.log('');
}
// 日文如果整份都是漢字沒假名，多半是「詞條抄了中文」——順手提醒一次
if(!bad){
  T.setLang('ja');
  const sample = T.MONS.map(d => T.locName('mon', d)).join('');
  if(!KANA.test(sample)) console.log('（注意：日文怪物名裡沒有任何假名，值得檢查是不是抄了中文）');
  T.setLang('zh');
}
process.exit(bad ? 1 : 0);
