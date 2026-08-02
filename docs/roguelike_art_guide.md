# 美術導入指南

用影像生成模型（GPT / Firefly / Midjourney 等）為這款回合制網格 roguelike
產製美術的完整流程：需求清單、風格規格、提示詞模板、轉換管線、驗收標準。

配套工具：`tools/pixelize.py`
配套資源：`docs/art/palette.png`、`docs/art/sheet_template_4x4.png`

---

## 0. 先講三件會踩到的事

**1. 影像模型不會給你 24x24 的圖。**
你要「24x24 像素風草藥」，它會給你一張 1024x1024、看起來像像素風但每個
「像素」其實是 42x42 一團、邊緣帶抗鋸齒與雜色的圖。直接縮小會糊掉。
必須走 `tools/pixelize.py`：區域平均降取樣 → 硬邊重建 → 色盤量化。

**2. 分次生成的圖不會像同一款遊戲。**
今天生成的草藥和明天生成的卷軸，色溫、飽和度、線條粗細都會不一樣。
解法有兩層：**固定 32 色色盤**（量化階段強制統一），以及
**用 sheet 一次生成一整類**（同一次推論內的一致性遠高於跨次）。

**3. 數量不是「道具有幾種」。**
未鑑定道具顯示的是**外觀**，所以圖的數量由外觀池決定。草藥只有 14 種，
但外觀池有 16 個（含 2 個防排除法的假外觀），所以要 16 張圖。
四類加起來 60 張而不是 52 張 —— 這種差異晚發現會直接爆預算。

---

## 1. 需求清單（由資料表推算，不是估的）

重算指令：`python3 tools/pixelize.py --check godot/assets`（驗收用）
清單由 `godot/data/items.json` 與 `monsters.json` 決定。

### 1.1 道具圖示 —— 81 張，每張 24x24

放在 `godot/assets/items/`。

| 類別 | 張數 | 檔名 | 說明 |
|---|---|---|---|
| 草藥 | **16** | `herb_00.png` ~ `herb_15.png` | 檔名對應**外觀池索引**，不是道具 ID |
| 卷軸 | **18** | `scroll_00.png` ~ `scroll_17.png` | 同上 |
| 杖 | **14** | `wand_00.png` ~ `wand_13.png` | 同上 |
| 壺 | **12** | `pot_00.png` ~ `pot_11.png` | 同上 |
| 食物 | 5 | `food_big_bread.png` 等 | 檔名 = def_id |
| 武器 | 10 | `wpn_club.png` 等 | 檔名 = def_id |
| 盾牌 | 6 | `shd_leather.png` 等 | 檔名 = def_id |

> **為什麼外觀類用索引而不是 def_id**：外觀映射每局重洗，`herb_03` 這一局
> 可能是回復草、下一局是睡眠草。圖跟著**外觀**走，不跟著效果走 ——
> 鑑定揭露的是名字，不是外形。一瓶紅色的草不會因為你知道它是回復草就變樣。
> 程式端見 `IdentificationTable.art_key()`。

外觀名（決定每張圖該長什麼樣）在 `items.json` 的 `appearance_pools`：

```
herb_00 赤紅的草   herb_01 靛藍的草   herb_02 嫩黃的草   herb_03 灰白的草
herb_04 墨綠的草   herb_05 斑點的草   herb_06 捲曲的草   herb_07 焦黑的草
herb_08 半透明的草 herb_09 帶刺的草   herb_10 毛絨的草   herb_11 泛紫的草
herb_12 濕黏的草   herb_13 乾枯的草   herb_14 蜜色的草   herb_15 鏽色的草
```

> ⚠ **外觀不可暗示效果。** 「焦黑的草」不該畫得比「嫩黃的草」更像毒草。
> 一旦外觀能被聯想推測，整套隨機映射就失效了。這是美術驗收的硬性項目。

### 1.2 實體 —— 13 種 x 2 影格，每格 24x24

放在 `godot/assets/`：`player.png`、`monsters/<def_id>.png`。
2 影格橫向並排，所以檔案是 48x24。

| def_id | 名稱 | AI | 視覺要點 |
|---|---|---|---|
| `mon_cave_rat` | 洞穴鼠 | CHASER | 小、低威脅，教學怪 |
| `mon_blue_slime` | 藍史萊姆 | WANDERER | 無方向感，呆滯 |
| `mon_green_goblin` | 綠哥布林 | CHASER | 手上要有袋子（牠會撿走你的道具） |
| `mon_drunk_shroom` | 醉步蕈 | WANDERER | 孢子、迷幻色 |
| `mon_pebble_imp` | 投石妖精 | RANGED | 手上有石頭，一看就知道會丟東西 |
| `mon_rot_grub` | 食腐蟲 | WANDERER | 蠕動、口器明顯（牠吸的是飽足度） |
| `mon_skeleton` | 骷髏兵 | CHASER | 不死族，免疫睡眠 |
| `mon_gale_wolf` | 疾風狼 | CHASER | 速度感，成群出現 |
| `mon_hex_mage` | 詛咒法師 | RANGED | 兜帽 + 法器 |
| `mon_wander_golem` | 徘徊石像 | WANDERER | 巨大厚重，明顯打不動 |
| `mon_crystal_turret` | 水晶砲台 | RANGED | 不會動，像地形的一部分 |
| `mon_abyss_knight` | 深淵騎士 | CHASER | 重甲，終盤壓迫感 |

> **AI 型別要能一眼看出來。** 目前程式用顏色編碼：
> CHASER 紅、WANDERER 綠、RANGED 紫。換成真美術後，這個資訊必須用
> **輪廓與配件**繼續傳達 —— 遠程怪手上要有可投擲物、遊蕩怪要沒有面向感。
> 玩家得先知道那是什麼型別才談得上判斷，這是回合制可推理性的一部分。

### 1.3 地形 —— 單張橫向圖集 `godot/assets/terrain.png`

每格 24x24，欄位順序**必須**對齊 `Tiles` 的 enum：

```
欄位 0  WALL          牆
欄位 1  ROOM_FLOOR    房間地板
欄位 2  CORRIDOR      通道地板（要和房間地板明顯區分）
欄位 3  STAIRS_DOWN   下行樓梯
欄位 4  STAIRS_UP     上行樓梯
```

房間地板與通道地板的區別是**機制性的**，不只是美觀：視野系統靠它切換
「整間房揭露」與「只見 1 格」。玩家必須一眼看出自己在哪一種格子上。

---

## 2. 風格規格

參考《特魯內克大冒險》的視覺**慣例**（不是它的素材）：

| 項目 | 規格 |
|---|---|
| 視角 | 正上方俯視偏 3/4，物件正面朝向鏡頭 |
| 解析度 | 24x24 / 格，無次像素細節 |
| 線條 | 硬邊，**零抗鋸齒**，外框用色盤內的深色而非純黑 |
| 色數 | 每張精靈 4~8 色（含外框），全專案共用 32 色 |
| 光源 | 固定左上打光，右下留暗面 |
| 剪影 | 縮到 24x24 仍可辨識 —— 剪影優先於細節 |
| 背景 | 透明 |

色盤：`docs/art/palette.png`（32 色，hex 標在每格下方）

> 生成時**不要**要求「特魯內克的怪物」或任何具體作品的角色 ——
> 那是他人的美術資產。要求的是視覺慣例：SFC 時代俯視角、有限色盤、
> 厚實輪廓。慣例不受保護，具體素材受保護。

---

## 3. 提示詞模板

### 3.1 一次生成一整類（推薦）

同一次推論內的風格一致性遠高於分開生成。附上
`docs/art/sheet_template_4x4.png` 與 `docs/art/palette.png` 當參考圖。

```
一張 4x4 網格的像素美術素材表，共 16 個獨立圖示，白色背景，格子之間留白。

風格：SNES 時代 16-bit 俯視角地牢探索遊戲的道具圖示。硬邊像素、
無抗鋸齒、有限色盤、厚實深色外框、左上光源。每個圖示縮到 24x24 仍可辨識。

內容：16 種外觀不同的藥草瓶，依序為
01 赤紅  02 靛藍  03 嫩黃  04 灰白  05 墨綠  06 斑點  07 捲曲  08 焦黑
09 半透明  10 帶刺  11 毛絨  12 泛紫  13 濕黏  14 乾枯  15 蜜色  16 鏽色

重要：每一個都要有明確不同的外形輪廓（瓶身、葉形、綁繩），
不可只有換色。所有圖示等大、置中、彼此風格一致。
不要文字、不要編號、不要陰影投射到格線外。
```

生成後：

```bash
python3 tools/pixelize.py sheet_herbs.png --grid 4x4 \
    --out-dir godot/assets/items --prefix herb_ --start 0
```

### 3.2 怪物（單隻 2 影格）

```
一張 2x1 的像素美術精靈表：同一隻生物的 2 個待機動畫影格，
白色背景，兩格等寬。

風格：SNES 時代 16-bit 俯視角地牢遊戲的敵人精靈。正面朝向鏡頭，
硬邊像素、無抗鋸齒、厚實深色外框、左上光源，縮到 24x24 仍可辨識。

生物：<這裡放上表的「視覺要點」，例如：一隻背著布袋的綠色哥布林，
表情狡猾，手上抓著搶來的東西>

第 2 影格只做輕微的呼吸／晃動變化，不要改變剪影。
不要文字、不要背景元素、不要地面陰影。
```

```bash
python3 tools/pixelize.py goblin.png --grid 2x1 \
    --out-dir godot/assets/monsters --prefix mon_green_goblin_ --start 0
# 之後把兩張併成一張 48x24（或直接請模型輸出 2x1 再整張處理）
```

### 3.3 地形圖集

```
一張 5x1 橫向排列的像素地形圖塊，白色分隔線，每格等寬正方形。

風格：SNES 時代 16-bit 俯視角地牢。硬邊像素、無抗鋸齒、有限色盤。
每格必須可以四方無縫平鋪。

依序為：
01 石牆（深色、厚重、有磚縫）
02 房間地板（暖色調磚地，紋理明顯）
03 通道地板（比房間地板更暗更粗糙，一眼能與房間區分）
04 向下的樓梯（有明確的下沉深度感）
05 向上的樓梯

不要文字、不要角色、不要邊框裝飾。
```

---

## 4. 轉換管線

```bash
# 單張
python3 tools/pixelize.py in.png -o godot/assets/items/wpn_club.png

# sheet 切格 + 批次命名
python3 tools/pixelize.py sheet.png --grid 4x4 \
    --out-dir godot/assets/items --prefix scroll_ --start 0

# 驗收：尺寸、色盤、透明度
python3 tools/pixelize.py --check godot/assets
```

管線做的事：

1. **去背** —— 四角取樣求共同色，容差內轉透明（不是固定色鍵，換底色也不會失效）
2. **降取樣** —— `Image.BOX` 區域平均。**不可用 LANCZOS**：它會製造色盤外的
   中間色與振鈴，量化之後變成髒邊
3. **色盤量化** —— 硬量化到 32 色，`dither=NONE`（抖動在 24x24 上就是雜訊）
4. **Alpha 二值化** —— 半透明像素一律推到全透或全不透，像素美術不要軟邊

實例：`docs/art/pipeline_example.png`（1024x1024 模糊生成圖 → 24x24 / 4 色 / 已去背，放大 8 倍檢視）

---

## 5. 整合

**程式端已經準備好了，不需要再改任何程式碼。**
`TileArt` 會先找資產，找不到才用程式產生的色塊：

```gdscript
static func entity_texture(def_id: String) -> Texture2D:
	var path := ASSET_DIR + ("player.png" if def_id == "" \
		else "monsters/%s.png" % def_id)
	return _load_cached(path)      # 沒有就回 null，呼叫端改用色塊 + 字母
```

所以美術可以**一張一張補**：補一張畫面就多一張真圖，中間任何時刻專案都跑得
起來，也不會因為缺一張圖就 crash。

```
godot/assets/
├── terrain.png              地形圖集（5 格橫排）
├── player.png               玩家（2 影格 = 48x24）
├── monsters/
│   └── mon_cave_rat.png     每隻怪 2 影格
└── items/
    ├── herb_00.png ~ herb_15.png
    ├── scroll_00.png ~ scroll_17.png
    ├── wand_00.png ~ wand_13.png
    ├── pot_00.png ~ pot_11.png
    └── wpn_club.png 等（檔名 = def_id）
```

放進去之後重新匯入並錄一次畫面比對：

```bash
godot --headless --path godot --import
xvfb-run -a --server-args="-screen 0 960x720x24" \
  godot --path godot --script res://tests/play_demo.gd
python3 tools/make_demo_media.py <frames_dir> out/
```

---

## 6. 建議的施工順序

美術是最容易做到一半失去動力的工作。照這個順序做，**每一步都能立刻看到
整體畫面變好**，而不是做完 81 張才看得出效果：

| 順序 | 內容 | 張數 | 為什麼先做這個 |
|---|---|---|---|
| 1 | `terrain.png` | 5 格 | 佔畫面 90% 的面積，一換整個氣氛就變了 |
| 2 | `player.png` | 1 種 | 玩家一直盯著它看 |
| 3 | 前 5 層的怪 | 5 種 | 洞穴鼠／史萊姆／哥布林／醉步蕈／投石妖精，多數試玩只到第 5 層 |
| 4 | 食物 + 武器 + 盾牌 | 21 張 | 種類可見，玩家最常比較的東西 |
| 5 | 草藥 16 張 | 16 張 | 撿到頻率最高的外觀類 |
| 6 | 卷軸／杖／壺 | 44 張 | 量最大，留到最後 |
| 7 | 深層怪 7 種 | 7 種 | 多數玩家還走不到 |

---

## 7. 驗收檢查表

- [ ] `python3 tools/pixelize.py --check godot/assets` 零問題
- [ ] 每張圖尺寸為 24 的倍數 x 24
- [ ] 所有非透明像素都落在 32 色色盤內
- [ ] 背景完全透明（不是白色）
- [ ] 縮到 100% 檢視時，剪影可辨識
- [ ] **外觀類道具的外形不暗示效果**（機制正確性，非美觀）
- [ ] 房間地板與通道地板一眼可分辨（視野系統依賴這個區別）
- [ ] 遠程怪的外形帶有可投擲物，遊蕩怪沒有明確面向
- [ ] 錄一次 `play_demo.gd` 比對，確認沒有圖被錯置或縮放異常
