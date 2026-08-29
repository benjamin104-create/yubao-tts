// 手機像素清晰度回歸：來源像素經 CSS 縮放後，必須剛好落在整數裝置像素。
// 只關掉 imageSmoothing 還不夠；3x 手機把 352px 畫布塞進 393px 寬時，
// 每一來源像素會變成 3.349... 個裝置像素，硬邊仍然會忽粗忽細。
const { api } = require('./simcore.js');
const assert = require('assert');
const fs = require('fs');

let pass = 0, fail = 0;
function t(name, fn){
  try { fn(); console.log('✓ ' + name); pass++; }
  catch(e){ console.log('✗ ' + name + '\n    ' + e.message); fail++; }
}

function phone(dpr, width){
  global.window = {devicePixelRatio:dpr};
  const pick = api.crispPortraitGrid(width);
  const source = pick.cols * 16 * 2;
  return {...pick, source, scale:pick.width*dpr/source};
}

t('正式遊戲沒有永久的 1.12 倍分數縮放', ()=>{
  assert.strictEqual(api.FIELD_ZOOM, 1);
});

t('一般 1x 手機仍是來源像素 1:1', ()=>{
  const q=phone(1,393);
  assert.strictEqual(q.cols,11);
  assert.strictEqual(q.width,352);
  assert.strictEqual(q.scale,1);
});

t('2x Retina 手機的每個來源像素正好佔 2 個裝置像素', ()=>{
  const q=phone(2,393);
  assert(Number.isInteger(q.scale), `實際倍率 ${q.scale}`);
  assert.strictEqual(q.scale,2);
});

t('3x Retina 手機自動改為九欄，來源像素正好放大 4 倍', ()=>{
  const q=phone(3,393);
  assert.strictEqual(q.cols,9);
  assert.strictEqual(q.width,384);
  assert.strictEqual(q.scale,4);
});

t('Canvas 與像素圖都明確關閉平滑插值', ()=>{
  const html=fs.readFileSync(__dirname+'/index.html','utf8');
  assert(/imageSmoothingEnabled\s*=\s*false/.test(html));
  assert(/image-rendering:\s*pixelated/.test(html));
});

t('樓梯是原生 32px 成品，不是 16px 粗圖硬放大', ()=>{
  assert.strictEqual(api.TILE_ART.stairs.width,32);
  assert.strictEqual(api.TILE_ART.stairs.height,32);
});

t('迷路村民與主角使用相同場上倍率', ()=>{
  const html=fs.readFileSync(__dirname+'/index.html','utf8');
  assert(/shadow\(nx2,\s*ny2,\s*ACTOR_SCALE/.test(html));
  assert(/drawEnt\(n2,\s*art,\s*'npc',\s*7,\s*ACTOR_SCALE\)/.test(html));
});

t('手機主方向鍵加大、斜向鍵的實際觸控區縮小', ()=>{
  const html=fs.readFileSync(__dirname+'/index.html','utf8');
  assert(/padding-bottom:186px/.test(html),'手機手把區沒有增高');
  assert(/Math\.min\(58,/.test(html),'主方向鍵上限仍是舊尺寸');
  assert(/#cross \.dg\{[\s\S]*?width:72%;\s*height:72%/.test(html),'斜向鍵沒有縮小觸控區');
});

t('升級拉遠完成後會依目前 viewport 與角色位置重新鎖定鏡頭', ()=>{
  const html=fs.readFileSync(__dirname+'/index.html','utf8');
  assert(/function cameraTarget\(\)[\s\S]*?G\.p\.x\s*-\s*VW\/2[\s\S]*?G\.p\.y\s*-\s*VH\/2/.test(html),
    '鏡頭中心沒有共用目前格數與玩家位置');
  assert(/cameraSettle\s*=\s*G\.zoomTo/.test(html), '升級結束沒有排入拉遠後校正');
  assert(/Math\.abs\(G\.zoom\s*-\s*cameraSettle\)[\s\S]*?snapCameraToPlayer\(\)/.test(html),
    '拉遠抵達原倍率後沒有鎖回玩家中心');
  assert(/if\(G\)\s*snapCameraToPlayer\(\)/.test(html),
    '旋轉或改變 viewport 時沒有使用同一套中心公式');
});

console.log('\n手機畫質檢查：通過 %d，失敗 %d', pass, fail);
process.exit(fail ? 1 : 0);
