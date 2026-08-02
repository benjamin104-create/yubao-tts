# Mystery Dungeon 原型（Godot 4.3）

回合制網格地牢探索的可運行原型。對應文件：

| 文件 | 內容 |
|---|---|
| `docs/roguelike_dungeon_GDD.md` | 機制規格（回合制、飽足度、鑑定、死亡懲罰） |
| `docs/roguelike_data_spec.md` | 資料表欄位語意與傷害公式推導 |
| `docs/roguelike_architecture.md` | 三層架構、類別圖、GameEvent 契約 |
| `docs/roguelike_mapgen.md` | 地圖生成演算法與虛擬碼 |

## 執行

```bash
# 首次：建立 class_name 註冊表
godot --headless --path godot --import

# 玩
godot --path godot

# Core 單元測試（67 → 72 項）
godot --headless --path godot --script res://tests/test_core.gd

# 自動遊玩模擬（120 場，產出平衡指標）
godot --headless --path godot --script res://tests/test_simulation.gd
```

需要 Godot **4.3+**（`TileMapLayer` 從 4.3 開始提供）。若使用 4.0~4.2，
把 `view/MapRenderer.gd` 與 `view/FogRenderer.gd` 改成 `extends TileMap`，
並在 `set_cell` 的第一個參數傳圖層索引 `0`。

## 操作

| 鍵 | 動作 |
|---|---|
| 方向鍵 / WASD | 移動（撞到怪物即攻擊） |
| Q E Z C / 數字鍵盤 | 斜向移動 |
| 空白鍵 | 原地待機（消耗 1 回合） |
| G | 撿取腳下道具 |
| `>` 或 `.` | 下樓 |
| I | 開關背包 |
| Esc | 取消瞄準 / 取消「放入壺」 |

背包內：點擊道具開選單（吃／喝／讀／揮動／裝備／投擲／放入／取出／放下）。
把道具**拖曳到壺上**可直接放入。揮杖與投擲會進入瞄準模式，再按一次方向鍵決定射向。

## 目錄結構

```
core/     純邏輯，不 extends Node、不 import 引擎 API —— 可 headless 執行
host/     轉接層：接 Intent、驅動回合、派發事件
view/     呈現層：只讀 GameEvent，不反向寫 Core
ui/       介面：蒐集玩家選擇並轉成 Intent，不直接改資料
data/     items.json / monsters.json（唯一事實來源，與 docs/roguelike_data/ 同步）
tests/    headless 測試與模擬
main/     組裝與輸入
```

依賴方向嚴格單向：`View → Host → Core`。Core 不知道引擎存在，這是
「平衡驗證可自動化」「存檔不含節點」「重播 = seed + Intent 序列」三件事的前提。

## 已實作

- **地圖生成**：30x30 切 3x3 區域、隨機生成樹保證連通、Z 字形通道、環路注入、
  物件放置、每層保證 1 份食物。300 seed 壓測連通性全過。
- **回合系統**：P0~P9 階段機、行動點累積器（倍速前後半子回合）、
  決策/執行分離的世界快照、決定論的衝突排序、斜向牆角與門口規則。
- **AI**：CHASER / WANDERER / RANGED 三種決策樹，含索敵記憶、受擊轉追擊、
  kiting、對齊射擊、封魔後退化。
- **戰鬥**：指數遞減防禦、±1/16 亂數、會心一擊、剋星與弱點倍率、反擊。
- **飽足度**：毫點整數、倍率修正、累積器自然回復、空腹懲罰、胃袋擴張。
- **鑑定**：每局外觀映射（含假外觀）、全域鑑定、三態鑑定時機、玩家標註。
- **視野**：房間全揭露 / 通道 1 格、三態霧效、探索記憶只記地形。
- **背包**：20 格、四種動詞、裝備與詛咒、壺（保存/合成/識別/變化/破魔/複製/吸物/詛咒）。
- **呈現**：程式產生的 TileSet 與 token（零美術資產）、位移插值、動畫壓縮。

## 尚未實作（明確標示，不靜默 no-op）

`EffectResolver` 對未實作的 op 會回傳 `[尚未實作的效果：XXX]` 訊息而非靜默略過。
目前仍是 stub 的：`CARVE_TUNNEL`、`CHARM`、`REROLL_INVENTORY`、`TRANSFORM_MONSTER`、
`WARP_TO_TOWN`、`TRANSFORM_INTO`、`PULL_TARGET`。

其他缺口：
- 需要指定對象的卷軸（鑑定／強化）目前由 `ActionResolver._auto_target_item()`
  自動挑選，正式版應該彈出目標選擇器。
- 商店、怪物之家、泉水等特殊房間只有生成標記，沒有行為。
- 死亡結算只做到 Step 1（復活草）與訊息；倉庫、遺物、救援尚未實作。

## 自動遊玩模擬找到的兩個真 bug

保留在這裡，因為它們正好說明了這套架構的價值 —— 兩個都是靠 headless 模擬
發現的，用手玩很可能要好幾小時才會察覺：

1. **下樓永遠不會發生**。`GameHost` 原本用 `call_deferred` 換樓，綁死在引擎的
   frame 迴圈上；headless 模擬沒有 frame，所以 120 場全部卡在第 1 層。
   改成明確的兩段式（`has_pending_floor()` / `commit_pending_floor()`），
   由呼叫端在動畫播完後自己 commit。
2. **怪物永遠不會死**。`EntityIndex.monsters()` 會濾掉 `is_alive() == false`
   的實體，而 P8 死亡結算正好用它來找屍體 —— 於是屍體永遠掃不到，
   不會被移除也不會給經驗值。修法是另開 `all_monsters()`。
   修好之後平均到達樓層從 1.0 變成 4.7，平均等級從 1.0 變成 2.4。

## 目前的模擬指標

```
場數              : 120
死亡              : 120（100.0%）      ← bot 很笨，這不是遊戲的死亡率
  ├ 餓死          : 0（0.0%）          ← 目標 < 8%
  └ 戰死          : 120
平均存活回合      : 437
平均到達樓層      : 4.7（最深 9）
平均結束等級      : 2.4
平均鑑定種類數    : 2.2
```

bot 的策略只有「餓了吃、低血喝已知回復草、安全時盲喝未鑑定草藥、
相鄰就打、否則走向樓梯」，不會逃跑、不會用杖、不會拉走廊，因此 100% 死亡是
預期的。這些數字的用途是**回歸偵測**：改了數值之後跑一次，看哪個指標動了。
