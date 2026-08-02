# 近戰連擊系統 —— Code Review 與重構

> **這份東西沒有接進遊戲。** 本專案是回合制網格 roguelike，沒有即時制的招式
> 前後搖，也沒有連擊。這個資料夾是一份獨立的 review 產出，放在專案內只是為了
> 讓 Godot 一併做編譯檢查。`godot/README.md` 已說明為什麼刀光／殘影／Hit Stop
> 不適用於本作。

## 檔案

| 檔案 | 說明 |
|---|---|
| `PlayerCombat.gd` | 重構版連擊狀態機（`class_name ActionPlayerCombat`） |
| `ComboSlashController.gd` | 重構版刀光控制器（`class_name ActionComboSlashController`） |
| `gut/test_player_combat_gut.gd` | GUT 測試用例（需安裝 GUT 才能跑） |
| `../../tests/test_action_combat.gd` | 同樣斷言的免 GUT 版本，可直接執行 |

`gut/` 底下放了 `.gdignore`，因為未安裝 GUT 時 `extends GutTest` 會造成解析
錯誤，那個錯誤會一直出現在每次 import 的輸出裡，掩蓋掉真正的問題。

```bash
# 免 GUT 版本（34 項斷言，目前全過）
godot --headless --path godot --script res://tests/test_action_combat.gd

# GUT 版本（需先安裝 addons/gut）
godot --headless --path godot -s addons/gut/gut_cmdln.gd \
      -gdir=res://experiments/action_combat/gut -gexit
```

---

## 1. 連擊與 Timer 的競態

### 1.1 致命：舊招式的協程會中斷新招式

原版 `_run_attack_timeline()`：

```gdscript
await get_tree().create_timer(0.08).timeout
can_combo_cancel = true
if has_buffered_attack:
    _consume_buffer_and_attack()
    return
await get_tree().create_timer(0.12).timeout
_finish_attack()
```

**問題出在「視窗開啟時沒有預輸入，但玩家稍後才按」這條路徑。**
`_buffer_attack_input()` 裡有一段：

```gdscript
if can_combo_cancel:
    _consume_buffer_and_attack()
```

這條路徑會在**舊協程仍卡在第二個 await** 的情況下發動新招式：

```
t=0.00  第 1 刀開始，協程 A 啟動
t=0.08  協程 A 醒來 → can_combo_cancel = true，無預輸入 → 進入第二個 await(0.12)
t=0.10  玩家按下攻擊 → can_combo_cancel 為 true → 立刻發動第 2 刀
        第 2 刀的協程 B 啟動；協程 A 仍在等它的 0.12 秒
t=0.18  協程 B 醒來 → 第 2 刀的取消視窗開啟
t=0.20  ★ 協程 A 醒來 → _finish_attack()
        → is_attacking = false、can_combo_cancel = false
        → 第 2 刀還在後搖中，狀態機卻認為玩家已經空閒
```

後果：第 2 刀的後搖被憑空取消（玩家獲得不該有的自由行動），而第 2 刀自己的
協程稍後還會再呼叫一次 `_finish_attack()`。狂點攻擊時每一刀都會踩到這條路徑。

**根因不是 Timer，是協程沒有識別碼。** 你在 `hit_stop` 那邊已經用過正確的
解法（`_hit_stop_id` 競態鎖），這裡同樣需要 —— 但更好的做法是根本不要協程。

### 1.2 `_clear_combo_reset_timer()` 完全沒有作用

```gdscript
func _clear_combo_reset_timer() -> void:
	if combo_reset_timer:
		combo_reset_timer.disconnect("timeout", Callable())
```

`Callable()` 是空的 Callable。這行不但斷不掉任何連線，還會在執行期報
「Attempt to disconnect a nonexistent connection」。

更根本的問題是：`_start_combo_reset_timer()` 連的是一個**行內 lambda**，
沒有存下任何參照 —— 那個連線在設計上就無法 disconnect。所以連擊重置一定會
在原定時間開火，即使玩家早就接上了下一刀。

### 1.3 `Callable(this, ...)` —— GDScript 沒有 `this`

`ComboSlashController._start_combo_timeout_timer()`：

```gdscript
combo_timer.disconnect("timeout", Callable(this, "_on_combo_timeout"))
```

GDScript 用 `self`，沒有 `this`。這行會直接造成解析錯誤，整個腳本載入失敗。

### 1.4 兩份 `combo_step`

`PlayerCombat.combo_step` 宣告了、被重置了，但**從來沒有被遞增過** ——
真正遞增的是 `ComboSlashController.combo_step`。兩個類別各跑一個重置計時器，
起算時間點還不同。同一個概念有兩個擁有者，遲早對不起來。

### 1.5 低幀率下可取消視窗可能被整幀跳過

`create_timer` 的到期檢查發生在幀邊界。一幀 100ms 時，`0.08` 與 `0.12` 兩個
計時器可能在同一幀到期，可取消視窗實際長度趨近於零；而輸入也是一幀取樣一次，
玩家的預輸入就這樣無聲無息地掉了。

---

## 2. 角度跨越 ±180 度

**你找錯地方了 —— Shader 那邊沒問題，出問題的是武器 Sprite 的 Tween。**

### Shader 是安全的

```glsl
float rel_angle = angle - rot_rad;
rel_angle = mod(rel_angle + PI, 2.0 * PI) - PI;
```

GLSL 的 `mod(x, y) = x - y * floor(x/y)`，對正的 `y` 恆為非負，所以結果落在
`[-PI, PI)`。無論 `rotation_degrees` 傳 `179` 還是 `-179`，弧形的位置都一樣。

噪聲取樣也是連續的：`noise_uv.x = angle / (2PI) + ...`，在接縫處 `angle` 從
`-PI` 跳到 `+PI`，對應 `-0.5` 與 `+0.5`；在 `repeat_enable` 下 `-0.5` 與
`+0.5` 落在同一個 texel，所以接縫不會有跳動。

### 真正的 bug 在這裡

```gdscript
weapon_sprite.rotation_degrees = start_angle
tween.tween_property(weapon_sprite, "rotation_degrees", end_angle, duration)
```

`rotation_degrees` 是普通的 float，Tween 做的是**線性補間**。從 `170°` 補到
`-170°` 實際只差 20 度，線性補間卻會反方向轉 340 度 —— 玩家會看到武器在正左方
突然甩一大圈。

修法是取最短角度差再算目標值：

```gdscript
var shortest_delta := wrapf(end_angle - start_angle, -180.0, 180.0)
tween.tween_property(weapon_sprite, "rotation_degrees",
    start_angle + shortest_delta, duration)
```

`lerp_angle` 用在算揮砍中點是對的（它本來就走最短路徑），但要注意兩角恰好
相差 180 度時方向是未定義的。

---

## 3. 記憶體洩漏與信號解綁

**這一項多半是虛驚 —— 但有一個真的 bug，只是不在你猜的地方。**

| 疑慮 | 實情 |
|---|---|
| `SceneTreeTimer` 洩漏 | 不會。它是 `RefCounted`，`timeout` 發出後就會被釋放。 |
| 節點被釋放後 Timer 呼叫到野指標 | 不會。Godot 的 `Object` 解構時會自動移除所有連到它的信號連線。 |
| lambda 捕獲 `self` 造成循環參照 | 不會。`Node` 不是 refcounted，Callable 也只存 ObjectID 而非強參照。 |
| **`await` 之後節點已被釋放** | **會出事。** GDScript 的協程不會因為 `self` 被釋放而取消。招式播到一半玩家死亡並 `queue_free()`，計時器到期時協程恢復執行、觸碰已釋放的 `self` → 執行期錯誤。若保留 `await` 寫法，`await` 後必須加 `if not is_inside_tree(): return`。 |

### 真正的資源 bug：Tween 沒有互斥

```gdscript
tween.finished.connect(func(): slash_effect.visible = false)
```

第 1 刀的 tween 在第 2 刀播到一半時 `finished` → 把**新的**刀光 `visible`
設成 false。連打時刀光會隨機消失。這跟本專案 `FloatingText` 的搶占情境是
同一類問題：**開始新動畫前必須先 `kill()` 舊的**。

---

## 4. 重構

核心決定：**把 `await` + `SceneTreeTimer` 換成 delta 驅動的顯式狀態機。**

```
IDLE ──press──► STARTUP ──► ACTIVE ──► RECOVERY ──► IDLE
                              │           │
                              │           └─ 可取消視窗；有預輸入就直接回 STARTUP
                              └─ 傷害判定生效
```

一次換掉三個問題：

1. **沒有協程 → 沒有重入。** 不需要 `_attack_id` 這類競態鎖。
2. **沒有 Timer → 沒有解綁問題。** 預輸入與連擊逾時都只是遞減的 float。
3. **可以單元測試。** `advance(delta)` 是公開方法，測試可以餵任意步長，
   包括「一幀 0.10 秒」這種原本無法模擬的 lag spike。

其他修正：

- `combo_step` 只有一個擁有者，方向透過 `attack_started(index, is_backhand)`
  訊號傳給呈現層，`ComboSlashController` 不再持有任何連擊狀態
- 階段推進用 `while` 而非 `if`，單一大 delta 不會跳過可取消視窗
- `MAX_PHASE_STEPS_PER_FRAME` 保險絲，避免階段時間被設成 0 時無限迴圈
- `PHASE_EPSILON` 浮點容差 —— 寫測試時發現的：`advance(0.02)` 後再
  `advance(0.03)`（合計正好等於 0.05 的前搖）會因為
  `0.05 - 0.02 == 0.030000000000000002` 而少轉一個階段。狀態機的行為不該
  取決於浮點雜訊。
- Tween 互斥（`kill()` 舊的）
- 武器旋轉取最短角度路徑

---

## 目前的測試結果

```
=== 連擊狀態機測試 ===
  1.  空閒時按攻擊 → 第 1 刀                    5 項
  2.  預輸入在可取消視窗開啟時兌現（反手刀）      7 項
  2b. 後搖中按鍵立即取消進下一刀                 3 項
  3.  超過 buffer_time 後預輸入失效              4 項
  4.  超過 combo_timeout 後連擊歸零              5 項
  4b. 連擊接上時重置計時器重新開始               1 項
  迴歸：舊招式的殘留計時不中斷新招式             3 項
  迴歸：單一大 delta（lag spike）仍兌現預輸入    2 項
  迴歸：極端 delta 不卡死                        1 項
  角度跨越 ±180 度邊界取最短路徑                 3 項

=== 結果：34 通過，0 失敗 ===
```

後三組是針對原版三個 bug 的迴歸測試 —— 把 `PlayerCombat.gd` 換回 `await`
版本，它們會立刻變紅。
