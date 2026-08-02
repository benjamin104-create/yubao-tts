## 連擊狀態機的可執行驗證（不需要安裝 GUT）。
##
##   godot --headless --path godot --script res://tests/test_action_combat.gd
##
## 這支腳本與 experiments/action_combat/gut/test_player_combat_gut.gd 斷言
## 完全對應 —— GUT 版是交付給你的正式測試，這一版是為了在沒有 GUT 的環境下
## 也能證明「這些斷言真的會過」。
extends SceneTree

const Combat := preload("res://experiments/action_combat/PlayerCombat.gd")
const Slash := preload("res://experiments/action_combat/ComboSlashController.gd")

var _pass := 0
var _fail := 0
var _combat


func _init() -> void:
	print("=== 連擊狀態機測試 ===")

	test_press_from_idle()
	test_buffer_fires_on_window()
	test_press_during_recovery()
	test_buffer_expires()
	test_combo_timeout()
	test_combo_timer_restarts()
	test_stale_attack_race()
	test_large_delta_honours_buffer()
	test_extreme_delta()
	test_shortest_arc()

	print("\n=== 結果：%d 通過，%d 失敗 ===" % [_pass, _fail])
	quit(1 if _fail > 0 else 0)


func _new_combat():
	var c = Combat.new()
	c.set_process(false)
	c.startup_time = 0.05
	c.active_time = 0.03
	c.recovery_time = 0.12
	c.buffer_time = 0.25
	c.combo_timeout = 0.80
	return c


func ok(cond: bool, label: String) -> void:
	if cond:
		_pass += 1
		print("  [PASS] %s" % label)
	else:
		_fail += 1
		print("  [FAIL] %s" % label)


func section(name: String) -> void:
	print("\n-- %s" % name)


# ----------------------------------------------------------------

func test_press_from_idle() -> void:
	section("1. 空閒時按攻擊 → 第 1 刀")
	var c = _new_combat()
	var started := []
	c.attack_started.connect(func(step: int, back: bool): started.append([step, back]))

	ok(not c.is_attacking(), "初始為空閒")
	c.press_attack()
	ok(c.is_attacking(), "按下後進入攻擊狀態")
	ok(c.state == Combat.State.STARTUP, "處於前搖階段")
	ok(c.combo_step == 1, "連擊計數推進到 1")
	ok(started.size() == 1 and started[0] == [0, false], "第 1 刀是正手（index 0）")
	c.free()


func test_buffer_fires_on_window() -> void:
	section("2. 預輸入在可取消視窗開啟時兌現（反手刀）")
	var c = _new_combat()
	var started := []
	c.attack_started.connect(func(step: int, back: bool): started.append([step, back]))

	c.press_attack()
	c.advance(0.02)
	c.press_attack()
	ok(c.has_buffered_attack(), "攻擊中按鍵寫入預輸入")
	ok(c.combo_step == 1, "預輸入階段不提前推進連擊")

	c.advance(0.03)
	ok(c.state == Combat.State.ACTIVE, "前搖結束進入判定期")

	c.advance(0.03)
	ok(c.combo_step == 2, "視窗開啟時兌現預輸入，發動第 2 刀")
	ok(c.state == Combat.State.STARTUP, "第 2 刀從前搖重新開始")
	ok(not c.has_buffered_attack(), "預輸入已被消耗")
	ok(started.size() == 2 and started[1] == [1, true], "第 2 刀是反手（index 1）")
	c.free()


func test_press_during_recovery() -> void:
	section("2b. 後搖中按鍵立即取消進下一刀")
	var c = _new_combat()
	c.press_attack()
	c.advance(0.08)
	ok(c.can_combo_cancel(), "後搖期間可取消")
	c.press_attack()
	ok(c.combo_step == 2, "立即發動下一刀")
	ok(c.state == Combat.State.STARTUP, "回到前搖")
	c.free()


func test_buffer_expires() -> void:
	section("3. 超過 buffer_time 後預輸入失效")
	var c = _new_combat()
	c.buffer_time = 0.02

	c.press_attack()
	c.press_attack()
	ok(c.has_buffered_attack(), "寫入預輸入")

	c.advance(0.03)
	ok(not c.has_buffered_attack(), "超過預輸入時間後失效")

	c.advance(0.05)
	ok(c.state == Combat.State.RECOVERY, "推進到後搖")
	ok(c.combo_step == 1, "預輸入已過期，不發動第 2 刀")
	c.free()


func test_combo_timeout() -> void:
	section("4. 超過 combo_timeout 後連擊歸零")
	var c = _new_combat()
	var reset_count := [0]
	c.combo_reset.connect(func(): reset_count[0] += 1)

	c.press_attack()
	c.advance(0.20)
	ok(c.state == Combat.State.IDLE, "招式結束回到空閒")
	ok(c.combo_step == 1, "連擊段數保留")

	c.advance(0.79)
	ok(c.combo_step == 1, "尚未超時，不重置")

	c.advance(0.02)
	ok(c.combo_step == 0, "超過 combo_timeout 後歸零")
	ok(reset_count[0] == 1, "發出一次 combo_reset")
	c.free()


func test_combo_timer_restarts() -> void:
	section("4b. 連擊接上時重置計時器重新開始")
	var c = _new_combat()
	c.press_attack()
	c.advance(0.20)
	c.advance(0.70)
	c.press_attack()
	c.advance(0.20)
	c.advance(0.70)
	ok(c.combo_step == 2, "計時器重新開始，連擊未被誤判為中斷")
	c.free()


func test_stale_attack_race() -> void:
	section("迴歸：舊招式的殘留計時不中斷新招式")
	var c = _new_combat()
	c.press_attack()
	c.advance(0.08)
	c.press_attack()
	ok(c.state == Combat.State.STARTUP, "取消進第 2 刀")

	# 推進「第 1 刀原本剩下的後搖」—— 原版會在這裡把 is_attacking 清成 false
	c.advance(0.12)
	ok(c.is_attacking(), "舊招式的殘留計時不該中斷新招式")
	ok(c.combo_step == 2, "連擊段數不被回捲")
	c.free()


func test_large_delta_honours_buffer() -> void:
	section("迴歸：單一大 delta（lag spike）仍兌現預輸入")
	var c = _new_combat()
	c.press_attack()
	c.press_attack()
	c.advance(0.10)          # 一幀跨過 STARTUP(.05) + ACTIVE(.03)
	ok(c.combo_step == 2, "跨過整個判定期仍兌現預輸入")
	ok(c.state == Combat.State.STARTUP, "已進入第 2 刀前搖")
	c.free()


func test_extreme_delta() -> void:
	section("迴歸：極端 delta 不卡死")
	var c = _new_combat()
	c.press_attack()
	c.advance(10.0)
	ok(c.state == Combat.State.IDLE, "正常收招而非無限迴圈")
	c.free()


func test_shortest_arc() -> void:
	section("角度跨越 ±180 度邊界取最短路徑")
	ok(absf(Slash.shortest_arc_target(170.0, -170.0) - 190.0) < 0.001,
		"170° → -170° 走 20 度（目標 190°）而非繞 340 度")
	ok(absf(Slash.shortest_arc_target(-170.0, 170.0) + 190.0) < 0.001,
		"-170° → 170° 同理（目標 -190°）")
	ok(absf(Slash.shortest_arc_target(10.0, 70.0) - 70.0) < 0.001,
		"不跨邊界時維持原值")
