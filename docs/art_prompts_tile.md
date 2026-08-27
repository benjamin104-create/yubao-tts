# 地磚生成提示詞

給影像模型用的提示詞。跟 `art_prompts_mon.md`／`art_prompts_boss.md` 同一份規矩，
規格本體在 `docs/art_tile_spec.md`，這一份只負責「怎麼叫模型畫出來」。

> **關於參考**：下面 A 段描述的是 1990 年代家用主機 RPG 地牢圖磚的**技法**——
> 每磚十六色的限制、單一左上光源、硬邊色塊、無抗鋸齒、四邊不畫框。
> 那一段就是那個年代畫面好看的全部原因，照著做就會是那個味道。
> 提示詞裡不寫遊戲名、不指名畫師：模型看到遊戲名會把構圖、角色、UI
> 一起腦補進來，而你要的只是一塊地板 —— 寫技法比寫名字**更準**。

---

## 三步流程（缺一不可）

```bash
# 1) 用下面的提示詞生一張大圖（模型不會給你 32x32，會給 1024x1024）

# 2) 轉成真正的像素圖：切格、降取樣、統一色盤
python3 tools/pixelize.py sheet.png --grid 4x3 --size 32 \
        --keep-bg --no-trim --out-dir web/art/tile/stone

#    地磚一定要加 --keep-bg --no-trim：
#    預設會去背並「裁到主體」，那是給角色用的，
#    地磚被裁掉邊緣就再也接不起來了。
#
#    色盤會依輸出路徑自動選（會印出「地貌 stone：用地形色盤」）。
#    地形用的是自己的材質色，不是角色那 32 色 —— 兩者一個都沒重疊，
#    所以走錯色盤的磚會整批偏色。地貌名打錯會直接中止，不會安靜生錯。

# 3) 驗收
python3 tools/check_tile.py
```

第 2 步不能跳過。影像模型產出的「像素風」每個色塊裡其實有幾十種相近色、
邊緣還帶半透明——直接丟進遊戲會糊掉，而且色數會爆掉被 `check_tile.py` 擋下。

---

## A. 共用前綴（每一張都要貼）

```
16-bit console RPG dungeon tileset, single square terrain tile, top-down
three-quarter view. Authentic 1993-era pixel art discipline:

- Hard-edged flat color clusters. NO anti-aliasing, NO soft gradients,
  NO airbrush blur, NO outer glow, NO bloom.
- Strictly limited palette, roughly 12-24 colors total, organized as
  3-4 value steps per material plus a dark base.
- Single light source from the TOP-LEFT: top and left edges catch the light,
  bottom and right edges fall into shadow. Every tile obeys this.
- Detail is made of deliberate 3-8 pixel SHAPES (a chip, a crack, a stain,
  a tuft), never per-pixel speckle or random noise.
- Matte, low-saturation surface. This is a floor, not a jewel.
- SEAMLESS TILING: the tile repeats edge-to-edge in all four directions.
  Do NOT draw a border, frame, outline or dark edge around the tile.
  The four edges must flow into a neighbouring copy invisibly.
- Flat even lighting across the whole tile: no vignette, no spotlight,
  no shadow of an off-screen object.
- Square 1:1 composition, no text, no watermark, no character, no props
  beyond what is described.
```

**三條救命的**（現有畫面就是敗在這裡，量測見 `docs/art_gap_terrain.md`）：

- `Do NOT draw a border` —— 目前地磚四邊有深色框，鋪起來變成一張網格。
- `Detail is ... SHAPES, never per-pixel speckle` —— 目前地板灑滿單像素亮點。
- 每張都寫的 **MID-DARK** —— 目前神殿、水晶、通天塔的地板比主角還亮，
  玩家會找不到自己。**亮色只准當高光，不准當地板主體。**
---

## A2. 亮度校準（**這一段是第二批才加的，用第一批的實測結果校準**）

第一批交了四個地貌，量出來成功與失敗的差別只有一個數字 —— **地板的平均亮度**：

| 地貌 | 地板平均亮度 | 主角與地板的差 | 結果 |
|---|---|---|---|
| `forest` 迷霧森林 | **33.5** | +77.5 | ✓ 最好 |
| `stone` 礦坑 | **44.5** | +66.5 | ✓ |
| `crystal` 水晶礦坑 | **80.5** | +30.5 | ✓ 及格邊緣 |
| `temple` 巴比倫神殿 | **92.9** | +18.1 | ✗ 主角認不出來 |

（亮度 = 0～255 的感知明度；主角本體是 111。）

**所以規則是**：地板四張的平均亮度要落在 **35～75**，**絕對不要超過 85**。
神殿就是唯一超過的那一個，也是唯一失敗的那一個。

反過來，「鄰格對比」不是預測因子 —— `stone` 高達 13.8 卻很好看，
因為那是石板的結構邊緣，不是雜訊。所以**不要**為了壓對比而把地板畫平；
要壓的是**亮度**，不是細節。

把這一句直接放進每一張 floor 的提示詞：

```
The finished tile must be DARK: its average perceived brightness should land
around 40-70 on a 0-255 scale, and must never exceed 85. A bright character
sprite (brightness ~111) stands on this tile and must read instantly against
it. Bright colors from the palette are for narrow highlight lines only,
never for the body of the tile.
```

---

## B. 通用結構（每個地貌四張，換的只有材質名詞）

```
[A 共用前綴]
[該地貌的 Palette 那一行]
[下面四種之一]
```

| 檔名 | 講什麼 | 固定要求 |
|---|---|---|
| `floor0`~`floor3` | 房間地板 | MID-DARK，內部安靜，四張是同一材質的四種磨損 |
| `corr0`~`corr2` | 走道地板 | 比房間**暗一階、粗一階**（玩家分辨房間／走廊的唯一線索）|
| `wall` | 牆的頂面 | 比地板**再暗**（「不能走」要用明度讀，不能只靠花紋）|
| `wallface` | 牆的正面 | 垂直面，上緣受光、下半沉入陰影，要讀得出牆有高度 |

四張 floor 的尾綴固定這樣加（**不要**換成四種不同材質）：

| | 尾綴 |
|---|---|
| `floor0` | `Variant 1: the plainest, almost featureless. This is the base tile.` |
| `floor1` | `Variant 2: one chipped corner and a short hairline crack.` |
| `floor2` | `Variant 3: a faint dark stain across one third of the tile.` |
| `floor3` | `Variant 4: a scatter of small grit and two small fragments in the seams.` |

三張 corr 的尾綴：`Variant 1: plain.` / `Variant 2: a diagonal crack.` /
`Variant 3: loose rubble along one edge.`

> `floor0` 會鋪掉最多面積，所以它是**最平的那張**。它越安靜，角色越跳得出來。

---

## C. 十三個地貌

每一段的 `Palette anchored to:` 就是 `pixelize.py` 會量化過去的那一組，
所以照著寫，轉檔時幾乎不會掉色。

---

### 1. `temple` —— 巴比倫神殿（第 1 章）

```
Palette anchored to: #211e1b #615b50 #928977 #d0c8b9 #0e2b5d #1d58a0
#5793c8 #c58b2a #f0ce68 #0d0d12 #1a1a24 #2b2b38 — weathered limestone,
lapis blue glaze, ochre gold.
```

- **floor**：`A temple floor tile of weathered limestone slabs, precisely cut and tightly fitted, edges softened by centuries of feet. Keep the stone body MID-DARK (use #615b50 as the main body, NOT the pale #d0c8b9) — the pale tones are for narrow highlights on the top-left edge only. Rare, sparse fragments of lapis-blue glazed brick set flush into the stone.`
- **corr**：`Same limestone one step darker and rougher, slabs smaller and more broken, sand drifted into the joints.`
- **wall**：`The TOP surface of a temple wall: packed rubble and broken limestone core, clearly coarser than the finished floor, and darker in overall value.`
- **wallface**：`The FRONT FACE of a temple wall: horizontal courses of dressed limestone blocks with a single band of lapis-blue glazed brick and a thin ochre relief line near the top. Top edge catches light, lower half in deep shadow.`

> 這一章目前地板是**全畫面最亮**的東西（量到 151.9，主角才 111）。
> 主體色一定要壓在 `#615b50`，不要用 `#d0c8b9`。

---

### 2. `stone` —— 礦坑洞穴（第 2 章）、深淵牢獄（第 11 章）

```
Palette anchored to: #17100d #2b1c13 #432a1a #654127 #8a6240 #b4895a
#d4ad75 #34231d #0d0d12 #1a1a24 #2b2b38 — damp brown earth and cut stone.
```

- **floor**：`A dungeon room floor tile: large irregular flagstones of damp brown stone, tightly fitted, mortar lines worn shallow. MID-DARK overall, clearly darker than any character standing on it. Keep the interior quiet — most of the tile is flat mid-tone stone.`
- **corr**：`Same stone, one step darker and rougher: smaller broken slabs, more grit, heavy foot wear. Cramped and utilitarian.`
- **wall**：`The TOP surface of a dungeon wall: rough packed earth with embedded stone rubble, obviously a different material from the walkable floor and darker in value.`
- **wallface**：`The FRONT FACE of a dungeon wall: horizontal courses of rough-cut stone blocks, damp at the base, top edge catching light, lower part sinking into deep shadow.`

---

### 3. `forest` —— 迷霧森林（第 3 章）

```
Palette anchored to: #07130d #241b14 #45311e #2d2117 #5b4027 #8b6841
#173820 #2c6b3c #58a05b #9abd73 #0d0d12 #1a1a24 — wet soil, bark, moss.
```

- **floor**：`A forest floor tile of packed wet dark soil with pressed-in bark fragments and flat roots. MID-DARK and matte. Moss appears as a FEW deliberate clumps of 4-8 pixels at the edges, never as scattered green dots across the whole tile.`
- **corr**：`Same soil one step darker and rougher, deeper leaf litter, exposed root ridges.`
- **wall**：`The TOP surface of a forest wall: a dense mass of fallen logs and root tangle packed with dark earth, darker than the floor.`
- **wallface**：`The FRONT FACE of a forest wall: a muddy earth bank held by horizontal fallen logs, moss along the lit top edge, deep shadow at the base.`

> 這一章目前是**做得最好的**（接縫 1.41×，全遊戲最低）。手繪版要守住這個水準。

---

### 4. `mountain` —— 試煉的山道（第 4 章）

```
Palette anchored to: #0d0d12 #1a1a24 #2b2b38 #3d3d4d #565668 #757589
#c8c8d4 #08172b #123557 #28648c #5798bd — cold grey rock and thin snow.
```

- **floor**：`A mountain path tile of cold grey fractured rock with thin wind-packed snow caught in the low seams. MID-DARK: the rock body sits at #3d3d4d–#565668, and the pale #c8c8d4 is used ONLY for thin snow lines on top-left edges.`
- **corr**：`Same rock one step darker and rougher, loose scree and gravel, less snow.`
- **wall**：`The TOP surface of a cliff wall: raw broken grey rock, angular fracture planes, darker than the path.`
- **wallface**：`The FRONT FACE of a cliff: near-vertical strata of grey stone in horizontal bands, a rim of snow catching light along the top edge, deep cold shadow below.`

---

### 5. `briar` —— 魔王的考驗（第 5 章）、荊棘城堡（第 6 章）

```
Palette anchored to: #6b1a1e #9c2b2b #c94a3a #2a1d14 #43301f #5e442c
#7d5c3c #9c7850 #bb9668 #ecd3ae #0d0d12 #1a1a24 — dark red brick and wood.
```

- **floor**：`A castle hall floor tile of dark red-brown brick laid in a tight running bond, worn smooth at the centre. MID-DARK and matte — deep oxblood reds, not bright scarlet. Keep the interior quiet.`
- **corr**：`Same brick one step darker and rougher, more chipped edges, dried briar thorns drifted into the joints.`
- **wall**：`The TOP surface of a castle wall: dark red masonry core matted with dry thorny briar, darker than the floor.`
- **wallface**：`The FRONT FACE of a castle wall: courses of dark red brick with a wooden beam band, dry briar creeping up from the base, top edge lit.`

---

### 6. `lake` —— 南湖畔（第 7 章）

```
Palette anchored to: #08172b #123557 #28648c #5798bd #9ed0e3 #e5f5f7
#c5ddea #79b5d2 #101c3a #1d3468 #2f57a0 #4a86cf #7cb8ea — wet stone and
shallow water.
```

- **floor**：`A lakeside temple floor tile of wet dark blue-grey stone, a thin film of water pooling in the low seams. MID-DARK: body at #123557–#28648c. The pale #e5f5f7 is used ONLY as a few short highlight glints on the top-left edge of wet spots, never as a large area.`
- **corr**：`Same stone one step darker and rougher, silt and small pebbles, more standing water.`
- **wall**：`The TOP surface of a lakeside wall: dark waterlogged stone rubble with algae in the cracks, darker than the floor.`
- **wallface**：`The FRONT FACE of a lakeside wall: courses of wet blue-grey stone with a darker waterline stain across the lower third, lit top edge.`

---

### 7. `beast` —— 幻獸洞窟（第 8 章）

```
Palette anchored to: #07130d #241b14 #45311e #2d2117 #5b4027 #8b6841
#173820 #2c6b3c #58a05b #9abd73 #0d0d12 #1a1a24 — cave soil, root, lichen.
```

- **floor**：`A beast-den cave floor tile of trodden dark earth mixed with bone fragments and dry bedding straw. MID-DARK and matte. Lichen appears as a FEW deliberate 4-8 pixel patches, not scattered dots.`
- **corr**：`Same earth one step darker and rougher, deep claw-scored ruts.`
- **wall**：`The TOP surface of a cave wall: dark earth packed with thick roots pushing through, darker than the floor.`
- **wallface**：`The FRONT FACE of a cave wall: a raw earth bank with exposed root ends and a few embedded bones, lit along the top edge.`

---

### 8. `wood` —— 幻忍之里（第 9 章）、平安京三橋（第 10 章）

```
Palette anchored to: #2a1d14 #43301f #5e442c #7d5c3c #9c7850 #bb9668
#ecd3ae #0d0d12 #1a1a24 #2b2b38 — aged timber.
```

- **floor**：`An interior floor tile of aged wooden planks laid parallel, tight joints, visible straight grain, worn darker along the walking line. MID-DARK: body at #5e442c–#7d5c3c, the pale #ecd3ae only as a thin lit edge on the top-left of each plank. The plank direction must continue across tile edges so the floor reads continuous.`
- **corr**：`Same planks one step darker and rougher, narrower boards, a few cupped and splintered.`
- **wall**：`The TOP surface of a wooden wall: the cut top of a timber frame packed with dark plaster, darker than the floor.`
- **wallface**：`The FRONT FACE of a wooden wall: a lattice of dark timber posts over pale plaster panels, lit along the top edge, shadow pooling at the base.`

---

### 9. `mirror` —— 鏡像世界（第 12 章）

```
Palette anchored to: #0d0d12 #1a1a24 #2b2b38 #3d3d4d #565668 #757589
#c8c8d4 #101c3a #1d3468 #2f57a0 #4a86cf #7cb8ea — dark polished stone
and cold blue reflection.
```

- **floor**：`A hall floor tile of dark polished stone in a diamond-set pattern, faintly reflective. MID-DARK: body at #2b2b38–#3d3d4d. Reflection is suggested by a FEW straight, hard-edged pale streaks along the top-left of each panel — NOT by making the whole tile bright, and NOT by a soft gradient.`
- **corr**：`Same stone one step darker, the polish dulled and scuffed, hairline fractures.`
- **wall**：`The TOP surface of a mirror-hall wall: dark stone core with embedded shard fragments, darker than the floor.`
- **wallface**：`The FRONT FACE of a mirror-hall wall: tall dark panels with narrow vertical mirror strips catching a single cold blue highlight at the top.`

---

### 10. `crystal` —— 水晶礦坑（第 13 章）

```
Palette anchored to: #08172b #123557 #28648c #5798bd #9ed0e3 #e5f5f7
#c5ddea #79b5d2 #0d0d12 #1a1a24 #2b2b38 — blue ice and packed snow.
```

- **floor**：`An ice-cavern floor tile of thick blue glacial ice, smooth but not glassy, with faint frozen strata visible under the surface. MID-DARK — this is the single most important instruction here: the body must sit at #123557–#28648c, deep blue, NOT white. The pale #e5f5f7 and #9ed0e3 are used ONLY as thin highlight lines on the top-left edge and a couple of small glints. The tile must read clearly DARKER than a character standing on it.`
- **corr**：`Same ice one step darker and rougher: wind-scoured, matte, packed snow gritted into the surface.`
- **wall**：`The TOP surface of an ice wall: fractured blue ice and packed snow, darker than the floor.`
- **wallface**：`The FRONT FACE of an ice cliff: a clean vertical cut through blue ice showing horizontal strata, a rim of bright frost catching light along the very top edge, deep blue shadow below.`

> 這一章目前**最吵**（鄰格對比 7.00，是最好那幾章的三倍），而且地板比主角亮。
> 生完務必做 D 段的第 2 項檢查。

---

### 11. `greathall` —— 地下大廣間（第 14 章）

```
Palette anchored to: #2a1d14 #43301f #5e442c #7d5c3c #9c7850 #bb9668
#ecd3ae #0e2b5d #1d58a0 #5793c8 #c58b2a #f0ce68 #0d0d12 #1a1a24 —
sandstone with lapis and gold inlay.
```

- **floor**：`A great hall floor tile of large sandstone slabs, precisely cut, with a thin inlaid line of lapis blue and gold running along one edge as a repeating border motif. MID-DARK sandstone body at #5e442c–#7d5c3c; gold #f0ce68 only as a 1-2 pixel inlay line, never as a filled area.`
- **corr**：`Same sandstone one step darker and rougher, no inlay, sand drifted into the joints.`
- **wall**：`The TOP surface of a great hall wall: sandstone rubble core, darker than the floor.`
- **wallface**：`The FRONT FACE of a great hall wall: dressed sandstone courses with a lapis-and-gold banded frieze near the top, lit top edge, deep shadow at the base.`

---

### 12. `spire` —— 通天塔（第 15 章）、祕匠的副本

```
Palette anchored to: #101c3a #1d3468 #2f57a0 #4a86cf #7cb8ea #5798bd
#9ed0e3 #e5f5f7 #c5ddea #79b5d2 #2a1d14 #43301f #5e442c #7d5c3c
#9c7850 #c58b2a #f0ce68 #0d0d12 #1a1a24 — lapis-glazed brick, exposed
raw clay, and a narrow ochre-gold relief band.
```

- **floor**：`A tower floor tile of lapis-blue glazed brick laid in a tight grid, the glaze slightly uneven from firing. MID-DARK: body at #1d3468–#2f57a0. The pale #e5f5f7 is used ONLY as a thin specular line on the top-left of a few bricks — the glaze reads as glossy through hard-edged highlights, never through overall brightness.`
- **corr**：`Same brick one step darker, the glaze worn away in patches showing the raw clay beneath.`
- **wall**：`The TOP surface of a tower wall: unglazed clay brick core, matte and darker than the glazed floor.`
- **wallface**：`The FRONT FACE of a tower wall: courses of lapis-glazed brick with a gold relief band, top edge catching a hard specular line, deep shadow below.`

> 這一章目前主角與地板的亮度差只有 **+5.9**，等於沒有對比。務必壓暗。

> **神像（`blocker0` / `blocker1`）**：這一章的簡介是「往上二十層，塔頂有一道門，
> 門後不是一個地方，而是一個時間」，而終章是「只有意識，而你即將成為它」。
> 兩尊神像各說一句話 ——
> `blocker0` **未完成**：上半身還是粗胚，綁著木鷹架。他們在造神，而且沒造完。
> `blocker1` **已傾倒**：巨大的頭側躺著、半埋進地板，閉著眼、面容安詳。
> 他們要去見的神，早就倒了。
> 兩尊都要跟第一章神殿的有翼守衛（lamassu）明顯不同 —— 那是門口的守衛，
> 這是神本身。

---

### 13. `void` —— 最後的迷宮（第 16 章）、混沌之間（第 17 章）

```
Palette anchored to: #0d0d12 #1a1a24 #2b2b38 #3d3d4d #565668 #757589
#c8c8d4 #101c3a #1d3468 #2f57a0 #4a86cf — near-black substrate with a
single cold-blue light running through it.
```

- **floor**：`A void floor tile: nested hard-edged geometric panels of near-black material, each step recessed deeper than the last, so the tile reads as looking DOWN into depth rather than at a flat surface. Running straight across it is a single cold-blue light thread, 1-2 pixels wide, that continues off BOTH opposite edges so neighbouring tiles link into one continuous web of light across the whole room. The substrate stays very dark and matte — the blue is a thread, never a glow, never a halo, never a lit pool.`
- **corr**：`Same substrate one step darker and tighter, panels smaller, the blue thread thinner and broken in a place or two, as if the current is failing.`
- **wall**：`The TOP surface of a void wall: solid near-black material with a faint panel grid and NO blue thread at all — the light does not run through the walls. Darker still than the floor.`
- **wallface**：`The FRONT FACE of a void wall: tall dark panels receding into black, a single cold-blue line tracing the very top edge like a distant horizon, everything below falling to near-black.`

> 這一章目前的圖地分離是全遊戲最好的（**+67.5**）。手繪版守住「很暗」就對了。

> **時空感與「混沌中的光明」**（使用者指定的方向）：
> 這一章的簡介是「沒有地圖、沒有商店，你不再需要它們」與
> 「這裡沒有牆，也沒有天花板，只有意識，而你即將成為它」。
>
> 兩個要求跟「無縫鋪貼＋地板要暗」會打架，解法是：
> · **時空感** 靠**層層內縮的幾何板** —— 讀起來是「往下看進一個很深的東西」，
>   而不是看著一個平面。不要用光暈或霧來做深度，那會破壞平鋪。
> · **光明** 做成**貫穿整塊磚的細光線**（1～2 像素），而且要從對邊接出去，
>   鋪起來會在整個房間連成一張光網。**不能做成光暈** —— 每塊磚中央一團光
>   會讓地板變成一格一格的光點陣，那正是我們花了半天在修的網格感。
> · 牆上**沒有**光線：光只走地板。玩家因此讀得出「可以走的地方有光」。
>
> 色盤為此補了 `#2f57a0` `#4a86cf` 兩個亮一階的藍（原本只有兩個暗藍，
> 沒有任何一個能當光）。那兩個色**只給光線用**，不是給地板主體。

---

## D. 生完之後怎麼判斷「有沒有到位」

硬性的 `tools/check_tile.py` 會擋（尺寸、色數、登記）。軟性的自己看三件事：

1. **把 `floor0` 複製九份排成 3×3** —— 看得到格線就是四邊畫了框，重生。
2. **把主角圖疊上去** —— 要找一下才看得到主角，就是地板太亮或太吵，重生。
   （水晶、通天塔、神殿這三章特別容易犯。）
3. **四張 floor 並排** —— 看起來像四種不同材質而不是同一種的四塊，重生。

---

## E. 已知的坑

| 症狀 | 原因 | 修法 |
|---|---|---|
| 色數爆掉（幾百色） | 沒跑 `pixelize.py` | 一定要跑第 2 步 |
| 邊緣一圈雜點 | 模型加了抗鋸齒 | 提示詞已寫 NO anti-aliasing；仍發生就靠 pixelize 量化 |
| 鋪起來像磁磚牆 | 四邊有深色框 | `Do NOT draw a border` 那一條要留著 |
| 地板搶走視線 | 太亮或細節太碎 | 加強 `MID-DARK`，並明講「亮色只准當高光」 |
| 地磚被裁掉一圈 | 少了 `--no-trim` | 地磚一定要 `--keep-bg --no-trim` |
| 整批偏色 | 地貌名打錯 | 會直接中止，照訊息改路徑 |

---

## F. `blocker0`、`blocker1` —— 房間裡的柱子／巨石

這兩張跟地磚不同：**背景要透明**，而且**要有落地陰影**。

```
[A 共用前綴（把 SEAMLESS TILING 那一條拿掉）] + [該地貌的 Palette 那一行] +

A single free-standing obstacle resting on the ground, centered, on a fully
TRANSPARENT background. Solid volume with a clear lit top-left and shaded
bottom-right, plus a soft dark contact shadow pooled at its base so it sits
on the floor instead of floating. It must not touch the edges of the image.
```

各地貌的物件：

| 地貌 | `blocker0` | `blocker1` |
|---|---|---|
| `temple` | a broken fluted limestone column stump | a heap of fallen carved masonry |
| `stone` | a broken stone pillar stump | a heap of fallen boulders |
| `forest` | a mossy tree stump | a tangle of fallen logs |
| `mountain` | a jagged standing rock | a cairn of stacked stones |
| `briar` | a scorched wooden post | a dense ball of dry briar |
| `lake` | a worn stone bollard | a pile of wet river boulders |
| `beast` | a great rib bone arch | a mound of bones and bedding |
| `wood` | a thick timber post | a stack of crates and barrels |
| `mirror` | a tall dark mirror panel | a heap of angular shards |
| `crystal` | a jagged ice pillar | a mound of broken ice blocks |
| `greathall` | a squared sandstone column stump | a pile of inlaid rubble |
| `spire` | an unfinished standing deity statue, its upper half still rough-hewn, wooden scaffolding lashed around it | a colossal toppled statue head lying on its side, half sunk into the floor, its face serene and eyes closed |
| `void` | a tall black monolith standing upright, a single cold-blue seam of light running down its centre | a broken arch of dark panels with cold-blue light spilling out through the fracture |

生這兩張時 `pixelize.py` **不要**加 `--keep-bg`（要去背），照角色的規矩走。

---

## G. 順序建議

先做 `stone` 一整套 11 張（礦坑洞穴＋深淵牢獄，全戰役出現最久的地貌），
在遊戲裡看過效果、確認流程走得通，再照量測到的嚴重度往下推：

`crystal` → `temple` → `spire` → 其餘。
