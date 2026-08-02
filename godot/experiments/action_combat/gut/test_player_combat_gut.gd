## GUT（Godot Unit Testing）測試用例。
##
## 需先安裝 GUT：AssetLib 搜尋 "Gut"，或 https://github.com/bitwes/Gut
## 放到 res://addons/gut/ 並在 Project Settings → Plugins 啟用。
##
## 這些測試之所以能寫得出來，完全是因為重構把 await + SceneTreeTimer 換成了
## advance(delta)。原版要測「預輸入在 0.08 秒後兌現」只能真的 await 0.08 秒，
## 而且沒有任何方法模擬 lag spike —— 那正是原版最容易壞的情境。
extends GutTest

const Combat := preload("res://experiments/action_combat/PlayerCombat.gd")
const Slash := preload("res://experiments/action_combat/ComboSlashController.gd")

var combat


func before_each() -> void:
	combat = Combat.new()
	combat.set_process(false)          # 由測試手動驅動時間
	add_child_autofree(combat)
	# 固定時間軸，讓斷言可以算得準
	combat.startup_time = 0.05
	combat.active_time = 0.03
	combat.recovery_time = 0.12
	combat.buffer_time = 0.25
	combat.combo_timeout = 0.80


# ---------------------------------------------------------------- 1

func test_press_from_idle_starts_first_slash() -> void:
	watch_signals(combat)
	assert_false(combat.is_attacking(), "初始應為空閒")

	combat.press_attack()

	assert_true(combat.is_attacking(), "按下攻擊後應進入攻擊狀態")
	assert_eq(combat.state, Combat.State.STARTUP, "應處於前搖階段")
	assert_eq(combat.combo_step, 1, "連擊計數推進到 1")
	assert_signal_emitted_with_parameters(
		combat, "attack_started", [0, false], "第 1 刀是正手（index 0）")


# ---------------------------------------------------------------- 2

func test_buffered_input_fires_backhand_when_window_opens() -> void:
	watch_signals(combat)
	combat.press_attack()                      # 第 1 刀

	combat.advance(0.02)                       # 仍在前搖
	combat.press_attack()                      # 攻擊中 → 寫入預輸入
	assert_true(combat.has_buffered_attack(), "攻擊中按鍵應寫入預輸入")
	assert_eq(combat.combo_step, 1, "預輸入階段不該提前推進連擊")

	combat.advance(0.03)                       # 前搖結束 → ACTIVE
	assert_eq(combat.state, Combat.State.ACTIVE)

	combat.advance(0.03)                       # ACTIVE 結束 → 可取消視窗開啟
	assert_eq(combat.combo_step, 2, "視窗開啟時應兌現預輸入，發動第 2 刀")
	assert_eq(combat.state, Combat.State.STARTUP, "第 2 刀從前搖重新開始")
	assert_false(combat.has_buffered_attack(), "預輸入已被消耗")
	assert_signal_emitted_with_parameters(
		combat, "attack_started", [1, true], "第 2 刀是反手（index 1）")


func test_press_during_recovery_cancels_immediately() -> void:
	combat.press_attack()
	combat.advance(0.08)                       # 直接進入 RECOVERY
	assert_true(combat.can_combo_cancel(), "後搖期間應可取消")

	combat.press_attack()
	assert_eq(combat.combo_step, 2, "可取消視窗內按鍵應立即發動下一刀")
	assert_eq(combat.state, Combat.State.STARTUP)


# ---------------------------------------------------------------- 3

func test_buffered_input_expires() -> void:
	combat.buffer_time = 0.02                  # 讓預輸入在視窗開啟前就過期

	combat.press_attack()
	combat.press_attack()                      # 前搖中寫入預輸入
	assert_true(combat.has_buffered_attack())

	combat.advance(0.03)                       # 超過 buffer_time
	assert_false(combat.has_buffered_attack(), "超過預輸入時間應失效")

	combat.advance(0.05)                       # 推進到可取消視窗
	assert_eq(combat.state, Combat.State.RECOVERY)
	assert_eq(combat.combo_step, 1, "預輸入已過期，不該發動第 2 刀")


# ---------------------------------------------------------------- 4

func test_combo_resets_after_timeout() -> void:
	watch_signals(combat)
	combat.press_attack()
	combat.advance(0.20)                       # 一整套招式打完
	assert_eq(combat.state, Combat.State.IDLE, "招式結束回到空閒")
	assert_eq(combat.combo_step, 1, "連擊段數保留")

	combat.advance(0.79)
	assert_eq(combat.combo_step, 1, "尚未超過 combo_timeout，不該重置")

	combat.advance(0.02)
	assert_eq(combat.combo_step, 0, "超過 combo_timeout 後連擊歸零")
	assert_signal_emitted(combat, "combo_reset")


func test_combo_timer_restarts_on_new_attack() -> void:
	combat.press_attack()
	combat.advance(0.20)
	combat.advance(0.70)                       # 快到 timeout 了
	combat.press_attack()                      # 但玩家接上了
	combat.advance(0.20)
	combat.advance(0.70)
	assert_eq(combat.combo_step, 2, "連擊接上時計時器應重新開始")


# ---------------------------------------------------------------- 迴歸：原版的競態

func test_stale_attack_does_not_cancel_new_one() -> void:
	# 原版的致命 bug：第 1 刀的協程在第 2 刀進行中到期，
	# 呼叫 _finish_attack() 把 is_attacking 清成 false。
	combat.press_attack()
	combat.advance(0.08)                       # 進入第 1 刀的後搖
	combat.press_attack()                      # 取消進第 2 刀
	assert_eq(combat.state, Combat.State.STARTUP)

	# 推進「第 1 刀原本剩下的後搖時間」——舊版會在這裡把狀態清掉
	combat.advance(0.12)
	assert_true(combat.is_attacking(), "舊招式的殘留計時不該中斷新招式")
	assert_eq(combat.combo_step, 2, "連擊段數不該被回捲")


func test_single_large_delta_still_honours_buffer() -> void:
	# 模擬 lag spike：一幀 0.10 秒直接跨過 STARTUP 與 ACTIVE。
	# 若階段推進寫成 if 而非 while，可取消視窗會被整幀跳過，
	# 玩家的預輸入就無聲無息地掉了。
	combat.press_attack()
	combat.press_attack()                      # 預輸入
	combat.advance(0.10)

	assert_eq(combat.combo_step, 2, "單一大 delta 仍須兌現預輸入")
	assert_eq(combat.state, Combat.State.STARTUP, "已進入第 2 刀的前搖")


func test_extreme_delta_does_not_hang() -> void:
	combat.press_attack()
	combat.advance(10.0)                       # 誇張的 delta
	assert_eq(combat.state, Combat.State.IDLE, "極端 delta 應正常收招而非卡死")


# ---------------------------------------------------------------- 角度

func test_shortest_arc_across_180_boundary() -> void:
	# 170° → -170° 實際只差 20°，線性補間卻會繞遠路轉 340°
	assert_almost_eq(Slash.shortest_arc_target(170.0, -170.0), 190.0, 0.001,
		"跨越 +180 邊界應走 20 度的短路徑")
	assert_almost_eq(Slash.shortest_arc_target(-170.0, 170.0), -190.0, 0.001,
		"跨越 -180 邊界同理")
	assert_almost_eq(Slash.shortest_arc_target(10.0, 70.0), 70.0, 0.001,
		"不跨邊界時維持原值")
