# 地磚生成提示詞

給影像模型用的提示詞。跟 `art_prompts_mon.md`／`art_prompts_boss.md` 同一份規矩，
規格本體在 `docs/art_tile_spec.md`，這一份只負責「怎麼叫模型畫出來」。

> **關於參考**：下面描述的是 1990 年代家用主機 RPG 地牢圖磚的**技法**——
> 每磚十六色的限制、單一左上光源、硬邊色塊、無抗鋸齒。技法與風格本來就是
> 公共的作法，照著做完全沒問題；提示詞裡不寫任何一款遊戲的名字、
> 不指名畫師、也不要求模型重現特定素材，因為那樣產出的會是別人的圖，
> 而且反而**不精準**——真正決定質感的是下面那些技法，不是那個名字。

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

## A. 共用前綴（每一張都貼這一段）

```
16-bit console RPG dungeon tileset, single square terrain tile, top-down
three-quarter view. Authentic 1993-era pixel art discipline:

- Hard-edged flat color clusters. NO anti-aliasing, NO soft gradients,
  NO airbrush blur, NO outer glow.
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

**最重要的兩條**（現有畫面就是敗在這裡）：

- `Do NOT draw a border` —— 目前程式畫的地磚四邊有深色框，鋪起來變成一張網格。
- `matte, low-saturation` + 下面每張都指定「比角色暗」—— 目前神殿和水晶礦坑
  的地板比主角還亮，玩家會找不到自己。

---

## B. 色帶（換地貌只換這一段）

貼在共用前綴後面，直接給模型 hex。這幾組**就是遊戲現在正在用的顏色**，
所以生出來的圖跟既有畫面天生同一套色。

| 地貌 | 貼這一段 |
|---|---|
| `stone` 礦坑／牢獄 | `Palette anchored to: #17100d #2b1c13 #432a1a #654127 #8a6240 #b4895a #d4ad75 #34231d — damp brown earth and cut stone.` |
| `forest` 迷霧森林 | `Palette anchored to: #07130d #241b14 #45311e #5b4027 #8b6841 #173820 #2c6b3c #58a05b #9abd73 — wet soil, bark, moss.` |
| `crystal` 水晶礦坑 | `Palette anchored to: #08172b #123557 #28648c #5798bd #9ed0e3 #c5ddea #79b5d2 — blue ice and packed snow.` |
| `temple` 巴比倫神殿 | `Palette anchored to: #211e1b #615b50 #928977 #d0c8b9 #1d58a0 #5793c8 #c58b2a — weathered limestone with lapis and ochre glaze.` |

其餘地貌的四階骨架色見 `docs/art_tile_spec.md` 的表，寫法照抄上面即可。

---

## C. 每個部位的提示詞（以 `stone` 為例）

### `floor0` ~ `floor3` —— 房間地板（面積最大，最先畫）

一次生四張，用同一句加尾綴，**四張必須是同一塊石頭的四種磨損**，
不是四種不同的石頭。

```
[共用前綴] + [stone 色帶] +

A dungeon room floor tile: large irregular cut flagstones of damp brown
stone, tightly fitted, mortar lines worn shallow. The surface is MID-DARK
overall — noticeably darker than any character who will stand on it —
so that a bright character sprite reads instantly against it.
Keep the interior quiet: most of the tile is flat mid-tone stone.
```

四張的尾綴：

| 檔名 | 尾綴 |
|---|---|
| `floor0` | `Variant 1: the plainest, almost featureless. This is the base tile.` |
| `floor1` | `Variant 2: one chipped corner and a short hairline crack.` |
| `floor2` | `Variant 3: a faint dark damp stain across one third of the tile.` |
| `floor3` | `Variant 4: a scatter of small grit and two tiny pebbles in the seams.` |

> 「最平的那張當基準」是刻意的：`floor0` 會鋪掉最多面積，
> 它越安靜，角色越跳得出來。

### `corr0` ~ `corr2` —— 走道地板

```
[共用前綴] + [stone 色帶] +

A dungeon CORRIDOR floor tile, same stone family as the room floor but
one step DARKER and one step ROUGHER: smaller broken slabs, more grit,
more visible wear from foot traffic. Cramped and utilitarian.
```

尾綴：`Variant 1: plain.` / `Variant 2: a diagonal crack.` / `Variant 3: loose rubble along one edge.`

> 走道比房間暗一階，是玩家分辨「我在房間還是走廊」的**唯一**線索，不能省。

### `wall` —— 牆的頂面

```
[共用前綴] + [stone 色帶] +

The TOP surface of a dungeon wall seen from above: rough packed earth and
embedded stone rubble, clearly a different material from the walkable floor.
Darker in overall value than the floor tile — the player must read
"cannot walk here" from BRIGHTNESS alone, not just from pattern.
```

### `wallface` —— 牆的正面

```
[共用前綴] + [stone 色帶] +

The FRONT FACE of a dungeon wall — the vertical band seen below the wall
top, showing that the wall has height. Horizontal courses of cut stone
blocks, top edge catching the light, the lower part falling into deep
shadow. Reads as a vertical surface, not as ground.
```

### `blocker0`、`blocker1` —— 房間裡的柱子／巨石

這兩張跟地磚不同：**背景要透明**，而且**要有落地陰影**。

```
[共用前綴（把 SEAMLESS TILING 那一條拿掉）] + [stone 色帶] +

A single free-standing obstacle resting on the ground, centered, on a fully
TRANSPARENT background. Solid volume with a clear lit top-left and shaded
bottom-right, plus a soft dark contact shadow pooled at its base so it sits
on the floor instead of floating. It must not touch the edges of the image.
```

尾綴：`blocker0: a broken stone pillar stump.` / `blocker1: a heap of fallen boulders.`

生這兩張時，`pixelize.py` **不要**加 `--keep-bg`（要去背），但仍要 `--no-trim`
以外的預設裁切——它們是物件不是地磚，照角色的規矩走。

---

## D. 生完之後怎麼判斷「有沒有到位」

不用靠感覺，`tools/check_tile.py` 會擋掉硬性的（尺寸、色數、登記）。
軟性的自己看三件事：

1. **把 `floor0` 複製九份排成 3×3** —— 看得到格線就是四邊畫了框，重生。
2. **把主角圖疊上去** —— 如果要找一下才看得到主角，地板太亮或太吵，重生。
3. **四張 floor 並排** —— 如果看起來像四種不同的石頭而不是同一種的四塊，重生。

---

## E. 已知的坑

| 症狀 | 原因 | 修法 |
|---|---|---|
| 色數爆掉（幾百色） | 沒跑 `pixelize.py` | 一定要跑第 2 步 |
| 邊緣一圈雜點 | 模型加了抗鋸齒 | 提示詞已寫 NO anti-aliasing；仍發生就靠 pixelize 量化 |
| 鋪起來像磁磚牆 | 四邊有深色框 | 提示詞的 `Do NOT draw a border` 要留著 |
| 地板搶走視線 | 太亮或細節太碎 | 加強 `MID-DARK` 與 `keep the interior quiet` |
| 地磚被裁掉一圈 | `pixelize.py` 少了 `--no-trim` | 地磚一定要 `--keep-bg --no-trim` |

---

## F. 順序建議

先做 `stone` 一整套 11 張（礦坑洞穴＋深淵牢獄，全戰役出現最久的地貌），
在遊戲裡看過效果、確認流程走得通，再推 `crystal` → `temple` → `spire`
（這三個是目前量出來問題最明顯的）。
