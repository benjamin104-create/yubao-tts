// 音樂資料檢查：十五章各自該有一首，而且資料要長得對。
//
// 曲子聽不聽得出來要靠耳朵，但「這一章根本沒配到曲子」「第三小節少了旋律」
// 這種錯不需要耳朵 —— 而且它不會報錯，只會安靜地退回礦坑主題。
// 這正是這個專案一路上最常踩的那種坑：加了東西，但沒有接上。
const { api } = require('./simcore.js');
const assert = require('assert');

const TRACKS = api.BGM.TRACKS;
const ACT_THEME = api.ACT_THEME;
let pass = 0, fail = 0;
function t(name, fn){
  try { fn(); console.log('✓ ' + name); pass++; }
  catch(e){ console.log('✗ ' + name + '\n    ' + e.message); fail++; }
}

t('每一章都對應得到一首曲子', ()=>{
  for(const a of api.ACTS){
    const theme = ACT_THEME[a.id];
    assert(theme, a.nm + ' 沒有地貌');
    assert(TRACKS[theme], a.nm + '（' + theme + '）沒有曲子');
  }
});

t('每一首曲子的四個小節都寫滿了', ()=>{
  for(const id in TRACKS){
    const tr = TRACKS[id];
    assert.strictEqual(tr.root.length, 4, id + ' 的低音不是四小節');
    assert.strictEqual(tr.chord.length, 4, id + ' 的和弦不是四小節');
    assert.strictEqual(tr.lead.length, 4, id + ' 的旋律不是四小節');
    for(const bar of tr.lead)
      assert(bar.length > 0, id + ' 有一小節沒有旋律');
    for(const bar of tr.chord)
      assert(bar.length >= 3, id + ' 有一個和弦少於三個音');
  }
});

t('所有音符都落在一小節之內、音高在可聽範圍', ()=>{
  for(const id in TRACKS){
    const tr = TRACKS[id];
    for(const bar of tr.lead) for(const [s, n, d] of bar){
      assert(s >= 0 && s < 16, id + ' 有音符起點在小節外：' + s);
      assert(d >= 1 && s + d <= 24, id + ' 有音符長度異常：' + s + '+' + d);
      assert(n >= 36 && n <= 96, id + ' 的音高離譜：' + n);
    }
    for(const k of tr.bass.concat(tr.hat, tr.kick))
      assert(k >= 0 && k < 16, id + ' 有鼓點落在小節外：' + k);
    assert(tr.bpm >= 60 && tr.bpm <= 160, id + ' 的速度異常：' + tr.bpm);
  }
});

t('十五章至少聽得到五首不同的曲子', ()=>{
  const used = new Set(api.ACTS.map(a => ACT_THEME[a.id]));
  assert(used.size >= 5, '只有 ' + used.size + ' 首 —— 整趟聽起來會像同一首');
});

t('鏡像世界的曲子真的是礦坑主題的倒影', ()=>{
  const st = TRACKS.stone.lead, mi = TRACKS.mirror.lead;
  for(let b = 0; b < 4; b++){
    assert.strictEqual(mi[b].length, st[b].length, '第 ' + b + ' 小節音數對不上');
    // 音高集合要是原曲以 A4 為軸的倒影（順序會因為節奏翻轉而改變）
    const a = st[b].map(x => 138 - x[1]).sort((x,y)=>x-y);
    const c = mi[b].map(x => x[1]).sort((x,y)=>x-y);
    assert.deepStrictEqual(c, a, '第 ' + b + ' 小節的音高不是倒影');
    // 節奏也要翻：第 k 步的音變成第 (16-k-長度) 步
    const ra = st[b].map(x => 16 - x[0] - x[2]).sort((x,y)=>x-y);
    const rc = mi[b].map(x => x[0]).sort((x,y)=>x-y);
    assert.deepStrictEqual(rc, ra, '第 ' + b + ' 小節的節奏沒有翻過來');
  }
  // 倒影之後方向要真的相反：原曲往上走的地方，鏡像要往下走
  const dir = bars => Math.sign(bars[0][1][1] - bars[0][0][1]);
  assert.strictEqual(dir(mi), -dir(st), '倒影之後旋律的方向沒有反過來');
});

t('每一首的鼓組編排都不一樣（不然只是換了音高的同一首）', ()=>{
  const sig = id => {
    const tr = TRACKS[id];
    return [tr.bpm, tr.bass.join(','), tr.hat.join(','), tr.kick.join(',')].join('|');
  };
  const seen = new Map();
  for(const id in TRACKS){
    const s = sig(id);
    if(seen.has(s)) throw new Error(id + ' 跟 ' + seen.get(s) + ' 的速度與鼓組完全一樣');
    seen.set(s, id);
  }
});

console.log('\n通過 %d，失敗 %d', pass, fail);
process.exit(fail ? 1 : 0);
