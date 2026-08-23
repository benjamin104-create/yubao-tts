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
  'b_artisan','b_hallking','b_mermaid','b_gate','b_mind1','b_mind'
];

ok(/TRACKS\.title\s*=\s*T_\(\{\s*bpm:112/.test(html), 'original title theme is registered at 112 BPM');
ok(/levelup:\(\)=>\{/.test(html), 'dedicated level-up fanfare is registered');
ok(/LEVEL_FANFARE_DUR\s*=\s*1\.72/.test(html), 'level-up camera timing follows the fanfare');
ok(/startLevelUpCelebration/.test(html) && /G\.zoomTo\s*=\s*Math\.max\(1\.43/.test(html), 'level-up action and focus zoom are wired');
const prologueSource = html.slice(html.indexOf('const PROLOGUE ='), html.indexOf("const pro=$('prologue')"));
ok((prologueSource.match(/\{title:/g) || []).length === 12, 'four prologue pages exist in all three languages');
ok(/PROLOGUE_SCENE_MS=\[6500,5200,5200,7000\]/.test(html) && /setTimeout\(nextPrologue/.test(html),
   'four charcoal scenes auto-advance before gameplay');
ok(/@keyframes towerBuild/.test(html) && /@keyframes transportDrop/.test(html) &&
   /@keyframes impactSettle/.test(html) && /@keyframes charcoalAwake/.test(html),
   'each prologue scene has its own motion language');
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

for(let i=1;i<=4;i++){
  const rel = `art/promo/prologue-charcoal-${i}-v1.jpg`;
  const file = path.join(ROOT, rel);
  ok(html.includes(rel), `${rel} is wired into the prologue`);
  ok(fs.existsSync(file), `${rel} exists`);
  ok(fs.statSync(file).size < 400000, `${rel} stays below 400 KB for mobile`);
}

const bossRatio = Number((html.match(/const BOSS_SCALE\s*=\s*ACTOR_SCALE\s*\*\s*([\d.]+)/)||[])[1]);
const gateRatio = Number((html.match(/const GATE_BOSS_SCALE\s*=\s*ACTOR_SCALE\s*\*\s*([\d.]+)/)||[])[1]);
ok(bossRatio * bossRatio >= 4, 'every standard boss occupies at least four times the hero area');
ok(gateRatio > bossRatio, 'Gate Watcher is larger than the already-giant standard bosses');
ok(/const msc = bossVisualScale\(m\.d\)/.test(html), 'runtime rendering uses the enforced boss scale');

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

ok(/m\.d\.mind\s*===\s*2\s*\?\s*heroAnimNow/.test(html), 'Mind Echo reuses the current animated hero by design');
ok(!fs.existsSync(path.join(ROOT, 'art', 'boss', 'b_mind2.png')), 'Mind Echo has no dedicated still that could break the mimic puzzle');
ok(!fs.existsSync(path.join(ROOT, 'art', 'anim', 'boss', 'b_mind2.png')), 'Mind Echo has no dedicated animation that could break the mimic puzzle');

console.log(`\nOpening/boss release checks: ${pass} passed, 0 failed.`);
