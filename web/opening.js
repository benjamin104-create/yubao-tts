/* Release checks for the cinematic opening, level-up presentation and boss art.
   Run with: node web/opening.js */
const fs = require('fs');
const path = require('path');

const ROOT = __dirname;
const html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');
let pass = 0;

function ok(condition, message){
  if(!condition) throw new Error(`FAIL: ${message}`);
  pass++;
  console.log(`PASS ${message}`);
}

function pngSize(file){
  const b = fs.readFileSync(file);
  ok(b.toString('ascii', 1, 4) === 'PNG', `${path.basename(file)} is a PNG`);
  return { width:b.readUInt32BE(16), height:b.readUInt32BE(20) };
}

const bossIds = [
  'b_keeper','b_warden','b_treant','b_ballista','b_pyro','b_lord',
  'b_phoenix','b_hanzo','b_oni','b_gaoler','b_queen','b_prism',
  'b_artisan','b_hallking','b_mermaid','b_gate','b_mind1','b_mind2','b_mind'
];

ok(/TRACKS\.title\s*=\s*T_\(\{\s*bpm:112/.test(html), 'original title theme is registered at 112 BPM');
ok(/levelup:\(\)=>\{/.test(html), 'dedicated level-up fanfare is registered');
ok(/LEVEL_FANFARE_DUR\s*=\s*1\.72/.test(html), 'level-up camera timing follows the fanfare');
ok(/startLevelUpCelebration/.test(html) && /G\.zoomTo\s*=\s*Math\.max\(1\.43/.test(html), 'level-up action and focus zoom are wired');
const prologueSource = html.slice(html.indexOf('const PROLOGUE ='), html.indexOf("const pro=$('prologue')"));
ok((prologueSource.match(/\{title:/g) || []).length === 12, 'four prologue pages exist in all three languages');
ok(/art\/promo\/deep-learning-tower-cover-landscape\.jpg/.test(html), 'landscape poster is used by the title screen');
ok(/art\/promo\/deep-learning-tower-cover-square\.jpg/.test(html), 'mobile square poster is used by the title screen');

for(const rel of [
  'art/promo/deep-learning-tower-cover-landscape.jpg',
  'art/promo/deep-learning-tower-cover-square.jpg'
]){
  const file = path.join(ROOT, rel);
  ok(fs.existsSync(file), `${rel} exists`);
  ok(fs.statSync(file).size < 600000, `${rel} stays below 600 KB`);
}

for(const id of bossIds){
  const still = path.join(ROOT, 'art', 'boss', `${id}.png`);
  const sheet = path.join(ROOT, 'art', 'anim', 'boss', `${id}.png`);
  ok(fs.existsSync(still), `${id} still exists`);
  ok(fs.existsSync(sheet), `${id} animation exists`);
  const a = pngSize(still), b = pngSize(sheet);
  ok(a.width === 48 && a.height === 48, `${id} still is 48x48`);
  ok(b.width === 480 && b.height === 144, `${id} animation sheet is 10x3 cells`);
  ok(html.includes(`'${id}'`), `${id} is registered in the runtime`);
}

console.log(`\nOpening/boss release checks: ${pass} passed, 0 failed.`);
