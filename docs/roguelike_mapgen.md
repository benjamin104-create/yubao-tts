# 房間與通道隨機地圖生成演算法

30x30 網格 / 3x3 區域切割 / Z 字形通道 / 保證全連通

參考實作：`docs/roguelike_data/mapgen_reference.py`（引擎無關、可直接執行）
配套：`docs/roguelike_architecture.md` §1 `core/grid`

---

## 0. 演算法總覽

《特魯內克大冒險》系列的地圖之所以「一看就是那個味道」，來自三個結構特徵：

1. **房間大小相近、分佈規律** —— 因為地圖被切成固定區域，每個區域最多一間房。
2. **通道又直又長，常有直角轉折** —— 因為通道是 Z 字形（水平 → 垂直 → 水平），不是隨機遊走。
3. **偶爾有沒有房間的空白區塊，只有通道穿過** —— 因為部分區域被指定為「通道交會點」。

整個流程：

```
Step 1  30x30 全填牆
Step 2  切成 3x3 = 9 個 10x10 區域（Zone）
Step 3  各區域內縮 1 格後隨機生成房間；0~3 個區域改放「通道交會點」
Step 4  在 3x3 區域鄰接圖上取隨機生成樹 → 保證全連通；再注入環路
Step 5  依每條邊挖 Z 字形通道
Step 6  4 向 flood fill 驗證連通性（失敗則重生成）
Step 7  放置出生點、樓梯、道具、金錢、陷阱、怪物
```

**複雜度**：O(W x H)。30x30 在任何平台上都是即時的。

---

## 1. Step 1-2：區域切割

```
CONST MAP_W = 30, MAP_H = 30
CONST ZONE_COLS = 3, ZONE_ROWS = 3
CONST ZONE_W = MAP_W / ZONE_COLS      # 10
CONST ZONE_H = MAP_H / ZONE_ROWS      # 10
CONST MARGIN = 1                       # ★ 區域內縮量，見 §2 的關鍵性質

FUNCTION split_zones() -> Zone[]:
    zones = []
    FOR zy IN 0 .. ZONE_ROWS-1:
        FOR zx IN 0 .. ZONE_COLS-1:
            zones.append(Zone{
                idx = zy * ZONE_COLS + zx,
                zx  = zx,  zy = zy,
                x0  = zx * ZONE_W,               y0 = zy * ZONE_H,
                x1  = zx * ZONE_W + ZONE_W - 1,  y1 = zy * ZONE_H + ZONE_H - 1
            })
    RETURN zones
```

區域索引配置（後續連通圖用的就是這 9 個節點）：

```
      x:0-9    x:10-19   x:20-29
y:0-9   [0]      [1]       [2]
y:10-19 [3]      [4]       [5]
y:20-29 [6]      [7]       [8]
```

---

## 2. Step 3：在區域內生成房間

每個區域**內縮 `MARGIN = 1` 格**後，在剩下的 8x8 範圍內隨機決定房間的尺寸與位置。

```
CONST ROOM_MIN = 3          # 房間最小邊長
CONST MIN_ROOMS = 6         # 至少 6 間房，避免地圖過空
CONST MAX_EMPTY_ZONES = 3

FUNCTION place_rooms(rng, zones) -> (rooms, junctions):
    # 決定哪些區域不放房間
    empty_count = rng.randint(0, MAX_EMPTY_ZONES)
    empty_count = min(empty_count, 9 - MIN_ROOMS)
    empty_set   = rng.sample(all_zone_indices, empty_count)

    rooms = {}          # zone_idx -> Room
    junctions = {}      # zone_idx -> Point

    FOR z IN zones:
        ux0 = z.x0 + MARGIN;   ux1 = z.x1 - MARGIN      # 可用範圍 8 格寬
        uy0 = z.y0 + MARGIN;   uy1 = z.y1 - MARGIN

        IF z.idx IN empty_set:
            # ★ 空區域仍是連通圖上的節點，只是退化成一個交會點
            junctions[z.idx] = Point(rng.randint(ux0+1, ux1-1),
                                     rng.randint(uy0+1, uy1-1))
            CONTINUE

        max_w = ux1 - ux0 + 1        # = 8
        max_h = uy1 - uy0 + 1        # = 8
        w = rng.randint(ROOM_MIN, max_w - 1)     # 3..7，留 1 格給通道轉圜
        h = rng.randint(ROOM_MIN, max_h - 1)
        x = rng.randint(ux0, ux1 - w + 1)
        y = rng.randint(uy0, uy1 - h + 1)

        rooms[z.idx] = Room{ zone = z.idx, x = x, y = y, w = w, h = h, doors = [] }

    RETURN rooms, junctions
```

### `MARGIN = 1` 帶來的三個關鍵性質

這一格內縮不是美觀考量，它讓後面三件事**在數學上必然成立**，不需要任何額外檢查：

1. **相鄰區域的房間之間必定有間隙**。
   區域 `zx` 的房間最右可到 `zx*10 + 8`；區域 `zx+1` 的房間最左只到 `(zx+1)*10 + 1`。兩者至少差 3 格 → 房間永遠不會黏在一起，通道永遠有地方走。
2. **通道轉折線必定存在合法位置**。
   水平連接時，出口 `pa.x ≤ zx*10 + 9`，入口 `pb.x ≥ (zx+1)*10`，故 `pa.x < pb.x` 恆成立 → `rng.randint(pa.x, pb.x)` 永遠有解，不必處理退化情形。
3. **地圖外框必定是牆**。
   最左的房間 x 最小為 1，最右最大為 28 → `x=0` 與 `x=29` 永遠是牆，不需要額外補邊界。

> **空區域為什麼要放交會點**：若空區域直接從連通圖移除，3x3 的鄰接圖有可能被切斷（例如區域 [1] 與 [3] 皆空時，區域 [0] 就孤立了）。讓空區域保留為節點，**9 個節點永遠存在** → 生成樹永遠涵蓋全圖。這是「所有房間皆可到達」最省事的保證方式。

---

## 3. Step 4：連通圖（保證所有房間可達）

在 3x3 區域的 **4 鄰接圖**（共 12 條候選邊）上操作。

```
CONST LOOP_CHANCE = 0.18

FUNCTION build_connection_graph(rng, zones) -> Edge[]:
    # 收集所有 4 鄰接的區域對
    candidates = []
    FOR a, b IN all_zone_pairs WHERE a.idx < b.idx:
        IF |a.zx - b.zx| + |a.zy - b.zy| == 1:
            candidates.append(Edge(a.idx, b.idx))
    # 3x3 網格共 12 條：水平 6 條 + 垂直 6 條

    # ---- (1) 隨機生成樹：連通性的數學保證 ----
    rng.shuffle(candidates)
    uf = UnionFind(9)
    tree = [];  rest = []
    FOR e IN candidates:
        IF uf.union(e.a, e.b):   tree.append(e)      # 成功合併 → 這條邊入樹
        ELSE:                    rest.append(e)      # 已在同一集合 → 是環路邊
    ASSERT tree.size == 8                             # 9 節點的生成樹恆有 8 條邊

    # ---- (2) 環路注入：避免「死路 = 必死」 ----
    extra = []
    FOR e IN rest:
        IF rng.random() < LOOP_CHANCE:   extra.append(e)

    RETURN tree + extra
```

**為什麼用生成樹而不是「連完再檢查」**：生成樹**由構造保證連通**，不是靠事後驗證通過。Step 6 的 flood fill 只是防呆（防挖通道時的實作錯誤），而不是演算法正確性的依賴。實測 2000 次生成，**重試次數為 0**。

**環路的必要性**：純生成樹是一棵樹 → 任兩房間之間只有唯一路徑 → 被怪物堵在死路就必死。注入 18% 的額外邊後，地圖出現迴圈，「繞圈甩開追兵」這個 CHASER 型怪的核心對策才成立（見 `data_spec` §2.1）。

---

## 4. Step 5：挖 Z 字形通道

通道的形狀就是「特魯內克感」的來源：**從房間垂直走出去 → 走到轉折線 → 平移 → 再垂直走進另一間房**。

```
FUNCTION node_port(rng, rooms, junctions, zone_idx, side) -> Point:
    """回傳該節點朝指定方向的出口座標。房間 → 牆外 1 格；交會點 → 自身。"""
    IF zone_idx IN junctions:
        RETURN junctions[zone_idx]              # 交會點沒有方向性，統一處理

    r = rooms[zone_idx]
    SWITCH side:
        CASE RIGHT: RETURN Point(r.right + 1,                    rng.randint(r.y, r.bottom))
        CASE LEFT:  RETURN Point(r.x - 1,                        rng.randint(r.y, r.bottom))
        CASE DOWN:  RETURN Point(rng.randint(r.x, r.right),      r.bottom + 1)
        CASE UP:    RETURN Point(rng.randint(r.x, r.right),      r.y - 1)


FUNCTION carve_corridors(rng, tiles, zones, rooms, junctions, edges):
    # 先把所有房間挖成地板
    FOR r IN rooms:  fill_rect(tiles, r.rect, ROOM_FLOOR)

    FOR e IN edges:
        za = zones[e.a];  zb = zones[e.b]

        IF za.zy == zb.zy:                              # ---- 水平連接 ----
            (L, R) = (za, zb) IF za.zx < zb.zx ELSE (zb, za)
            pa = node_port(rng, rooms, junctions, L.idx, RIGHT)
            pb = node_port(rng, rooms, junctions, R.idx, LEFT)
            mid_x = rng.randint(pa.x, pb.x)             # 轉折線（MARGIN 保證 pa.x < pb.x）

            carve_h(tiles, pa.x, mid_x, pa.y)           # ①  由 L 房水平走到轉折線
            carve_v(tiles, pa.y, pb.y, mid_x)           # ②  沿轉折線垂直平移
            carve_h(tiles, mid_x, pb.x, pb.y)           # ③  水平走進 R 房

        ELSE:                                            # ---- 垂直連接 ----
            (T, B) = (za, zb) IF za.zy < zb.zy ELSE (zb, za)
            pa = node_port(rng, rooms, junctions, T.idx, DOWN)
            pb = node_port(rng, rooms, junctions, B.idx, UP)
            mid_y = rng.randint(pa.y, pb.y)

            carve_v(tiles, pa.y, mid_y, pa.x)
            carve_h(tiles, pa.x, pb.x, mid_y)
            carve_v(tiles, mid_y, pb.y, pb.x)

        register_door(rooms, L_or_T.idx, pa)             # ★ 記錄門口
        register_door(rooms, R_or_B.idx, pb)


FUNCTION carve_h(tiles, x_a, x_b, y):
    FOR x IN min(x_a,x_b) .. max(x_a,x_b):
        IF tiles[y][x] == WALL:  tiles[y][x] = CORRIDOR   # ★ 只覆蓋牆，不覆蓋房間地板

FUNCTION carve_v(tiles, y_a, y_b, x):
    FOR y IN min(y_a,y_b) .. max(y_a,y_b):
        IF tiles[y][x] == WALL:  tiles[y][x] = CORRIDOR
```

### 三個實作細節

1. **`carve_*` 只覆蓋牆**：通道與通道交叉時自然形成十字路口（預期行為）；通道經過房間邊緣時不會把房間地板改成通道 tile —— 這對視野系統很重要，`room_at` 的判定不能被通道汙染。

2. **`register_door` 記錄門口**：GDD §1.5 規定「門口禁止任何斜向進出」。門口就是通道與房間相接的那一格，必須在生成階段記錄，執行期才能 O(1) 判定。

3. **通道不會誤穿房間**：水平連接的垂直段落在 `mid_x`，而 `mid_x > L.room.right` 且 `mid_x < R.room.left`，垂直範圍又限制在同一區域列內 —— 由構造保證不會切過任何房間，不需要碰撞檢查。

---

## 5. Step 6：連通性驗證

```
FUNCTION verify_connectivity(tiles) -> bool:
    walkable = all tiles WHERE tiles[y][x] != WALL
    IF walkable.empty:  RETURN false
    reached = flood_fill_4dir(tiles, walkable[0])
    RETURN reached.size == walkable.size
```

> ⚠ **必須用 4 向 flood fill，不可用 8 向。**
> GDD §1.5 禁止斜向切牆角（`(x,y) → (x+1,y+1)` 需 `(x+1,y)` 與 `(x,y+1)` 皆非牆）。若用 8 向驗證，會放行「只有斜向能通過」的地圖 —— 生成器認為合格，玩家實際走不過去，且這種 bug 只在特定 seed 出現，極難重現。

主流程含重試與保底：

```
FUNCTION generate_floor(run_seed, floor_index) -> FloorMap:
    FOR attempt IN 0 .. MAX_ATTEMPTS-1:
        rng = DeterministicRng(hash64(run_seed, floor_index, attempt))
        map = try_generate(rng, floor_index)
        IF map != NULL:  RETURN map
    RETURN fallback_floor()      # 保底：單一大房間。寧可無聊，絕不讓玩家卡死
```

`floor_seed = hash64(run_seed, floor_index, attempt)` 讓同一場 Run 的同一層永遠生成同一張圖 → 支援重播、每日挑戰、Bug 重現（架構文件 §6）。

---

## 6. Step 7：物件放置

```
FUNCTION place_objects(rng, map, F):     # F = 樓層數
    # ---- 1. 出生點（上行樓梯同格）----
    spawn_room = rng.choice(map.rooms)
    map.player_pos = random_tile_in(spawn_room)
    map.stairs_up  = map.player_pos

    # ---- 2. 下行樓梯：區域圖上距離出生區域最遠 ----
    dist    = bfs_on_zone_graph(map.edges, from = spawn_room.zone)
    ranked  = map.rooms sorted by dist DESC
    cands   = [r FOR r IN ranked IF r.zone != spawn_room.zone][0..2]
    map.stairs_down = random_tile_in(rng.choice(cands))

    occupied = { player_pos, stairs_down }

    # ---- 3. 密度公式（GDD §4.2）----
    n_items    = rng.randint(3, 6) + F / 8
    n_gold     = rng.randint(1, 3)
    n_traps    = rng.randint(1, 2) + F / 5
    n_monsters = clamp(2 + F / 3, 2, 12)

    FOR i IN 1..n_items:     place(free_tile(), roll_from_item_table(F))
    FOR i IN 1..n_gold:      place(free_tile(), roll_gold(F))
    FOR i IN 1..n_traps:     place(free_tile(), roll_trap(F))
    FOR i IN 1..n_monsters:
        # ★ 絕不在玩家 3 格內生成 —— 開局就被貼臉是純粹的挫折，不是難度
        place(free_tile(min_chebyshev_dist_from_player = 3),
              roll_from_encounter_table(F))

    # ---- 4. 特殊房間（GDD §4.3）----
    IF F >= 3 AND rng.random() < 0.08:
        # 商店必須恰有 1 個門口 —— 這是「不付錢就跑」能被店主堵住的前提
        single_door_rooms = [r FOR r IN map.rooms IF r.doors.size == 1]
        IF single_door_rooms.not_empty:
            map.shop_zone = rng.choice(single_door_rooms).zone
```

**「下行樓梯放在最遠處」的理由**：若樓梯可能就在出生點旁邊，玩家會養成「一落地先找樓梯、找到就走」的退化玩法，整個探索與資源蒐集循環就崩了。取區域圖 BFS 距離最遠的**前 3 名**中隨機（而非固定第 1 名），是為了避免每層都呈現同一種對角線移動模式。

**出現表衰減**（`data_spec` §2.3）：

```
FUNCTION falloff(F, lo, hi, edge_ratio = 0.4):
    IF F < lo OR F > hi:  RETURN 0
    IF hi == lo:          RETURN 1.0
    center = (lo + hi) / 2
    t = |F - center| / ((hi - lo) / 2)          # 0 = 主場中央, 1 = 邊界
    RETURN 1.0 - (1.0 - edge_ratio) * t

weight_final = spawn_weight * falloff(F, floor_range.lo, floor_range.hi)
```

---

## 7. 參考實作與實測結果

`docs/roguelike_data/mapgen_reference.py` 是上述虛擬碼的可執行版本，直接讀取 `items.json` / `monsters.json` 產生物件。

```bash
python3 docs/roguelike_data/mapgen_reference.py --seed 20260802 --floor 5
python3 docs/roguelike_data/mapgen_reference.py --stress 2000
```

### 壓力測試（2000 個 seed）

```
樣本數        : 2000
生成失敗      : 0  (0.000%)
重試次數合計  : 0
房間數        : min=6 max=9 avg=7.48
通道佔可走格  : avg=27.7%
連通性        : 全數通過（4 向 flood fill，含樓梯可達性）
```

重試 0 次印證了 §3 的說法：**連通性由生成樹保證，不是靠重試撞出來的。**

### 實際輸出（seed=20260802, floor=5）

圖例：`#` 牆　`.` 房間地板　`+` 通道　`@` 出生點　`>` 下行樓梯　`!` 道具　`$` 金錢　`^` 陷阱　`M` 怪物

```
##############################
##.......#################...#
##.......#################...#
##.!.....####...##########...#
##.......####...##########@..#
##......M#+++...##########...#
##.......+!##...#########+...#
##.......####...$+++++++++.!.#
########+####...##############
##+++++++####+################
##+##########+################
##+##########+++++############
##+#####+++++.....############
##+#####+####.....+++.......##
#.......+####.....##+......!##
#.......+####.....###.....!.##
#....>..+####.....######+#####
#.......#####.....######+#####
###^#########.....######+#####
###+####################+#####
###+####################+#####
###+###########.M.######+#####
###+###########..M^+####+#####
###+###########...#+####$#####
###+###########...#++++++#####
###+###########.!.############
###++++#######################
##############################
```

房間 7 / 交會點 2 / 通道邊 9（生成樹 8 + 環路 1）。可以看到中央區域 [4] 的房間、右下的長通道環路，以及左下角區域 [6] 被拉長的 Z 字形通道 —— 正是系列作的視覺特徵。

### 深層樣本（seed=777, floor=20）

```
##############################
#############....#############
#############....#############
#############....+M###########
############+....#+####....###
#######++++++###+#+####....###
#######+########+#+####....###
#######M#######++#+####..@.###
###+++++#######+##M++!+....###
###+###########+########+#####
###+###########^########+++M##
###+#########.....#########^##
###!+M+++####.....#########+##
###+####+####.....#########+##
###+####+####.....#########+##
###+####+####.....#########+##
###+++++++$++.M.!.#########+##
########+########+########++##
########+###++++!+########+###
########+###+#############+###
########+###+#############+###
######...##......#########+###
######...##....M.######...^.!#
######...##......######......#
######..>##############......#
######^..##############.....M#
######..^##############......#
#######################..$...#
#######################.....^#
##############################
```

房間 6 / 交會點 3。深層的怪物與陷阱密度明顯提高（`n_monsters = 2 + 20/3 = 8`、`n_traps = randint(1,2) + 4`），符合 GDD §4.2 的密度公式。

---

## 8. 參數調校建議

| 參數 | 現值 | 調高的效果 | 調低的效果 |
|---|---|---|---|
| `MARGIN` | 1 | 房間更小、通道更長 → 走廊戰更吃重 | 房間可能相鄰、通道極短（不建議 < 1，會破壞 §2 的三個保證） |
| `ROOM_MIN` | 3 | 房間更一致、更少小房 | 出現 3x3 的小房間，適合埋伏 |
| `MIN_ROOMS` | 6 | 地圖更密、探索時間更長 | 空曠通道迷宮感更強 |
| `LOOP_CHANCE` | 0.18 | 環路多 → 逃跑容易 → 難度下降 | 樹狀結構 → 容易被堵死 → 難度上升 |
| `MAX_EMPTY_ZONES` | 3 | 更多純通道區塊，地圖更「迷宮」 | 每區都有房，結構更規律 |

> **`LOOP_CHANCE` 是最有效的難度旋鈕**：它不改任何數值，只改變地圖拓樸，卻直接決定「被 CHASER 型怪追上時有沒有活路」。建議依樓層調整：`LOOP_CHANCE = clamp(0.25 - F * 0.005, 0.08, 0.25)` —— 越深層，死路越多。

---

## 9. 移植到引擎時的注意事項

1. **`hash64` 必須跨平台一致**。Python 的 `hash()` 有 salt，正式版請用固定演算法（FNV-1a 或 xxhash）。參考實作為求簡潔用了內建 `hash`，移植時**務必替換**，否則同一 seed 在不同機器會生出不同地圖。
2. **`rng.randint` 的區間慣例不同**。Python 的 `randint(a, b)` 含兩端；C# 的 `Random.Next(a, b)` 不含上界；GDScript 的 `randi_range(a, b)` 含兩端。移植時逐一核對，這是最常見的 off-by-one 來源。
3. **不要在生成器裡實例化引擎節點**。`MapGenerator` 回傳的應該是純資料 `FloorMap`；由 `MapRenderer` 讀它去畫 TileMapLayer。這樣才能在 CI 裡跑 §7 的壓力測試（架構文件 §0）。
4. **`room_at` 一定要一起產生**。視野系統靠它做 O(1) 的「我在不在房間裡」判定（架構文件 §5）。生成階段順手填好，比執行期每回合對所有房間做矩形測試便宜得多。
