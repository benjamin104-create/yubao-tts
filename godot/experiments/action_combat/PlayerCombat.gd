## 近戰連擊狀態機（重構版）。
##
## 原版用 `await get_tree().create_timer()` 串接招式階段，這是所有問題的根源：
##
##   1. 協程可以重入 —— 舊招式的 await 到期後仍會呼叫 _finish_attack()，
##      在新招式進行中把 is_attacking 清成 false（詳見 README 的競態時序圖）
##   2. SceneTreeTimer 不可取消，只能 disconnect；而 inline lambda 根本
##      無法 disconnect，所以「重置連擊」的計時器一定會在錯的時間點開火
##   3. 無法單元測試 —— 測試必須真的等 0.08 秒，而且沒辦法模擬 lag spike
##
## 改成 delta 驅動的顯式狀態機後，這三件事同時消失：沒有協程就沒有重入，
## 沒有 Timer 就沒有解綁問題，而 advance(delta) 可以被測試手動餵任意步長。
class_name ActionPlayerCombat
extends Node

signal attack_started(combo_step: int, is_backhand: bool)
signal hit_active(combo_step: int)
signal cancel_window_opened(combo_step: int)
signal attack_finished(combo_step: int)
signal combo_reset()

enum State { IDLE, STARTUP, ACTIVE, RECOVERY }

@export_group("招式時間軸")
@export var startup_time := 0.05      # 前搖
@export var active_time := 0.03       # 判定生效
@export var recovery_time := 0.12     # 後搖（= 可取消視窗）

@export_group("連擊")
@export var buffer_time := 0.25       # 預輸入有效時間
@export var combo_timeout := 0.80     # 多久沒攻擊就重置連擊段數
@export var combo_length := 2         # 幾刀一循環（正手 / 反手）

## 單一事實來源。原版在 PlayerCombat 與 ComboSlashController 各存了一份
## combo_step，還各自跑一個重置計時器 —— 兩份狀態遲早會對不起來。
var combo_step := 0
var state: State = State.IDLE

var _state_time := 0.0
var _buffer_left := 0.0
var _idle_time := 0.0

## 保險絲：極端 lag spike（例如視窗被拖動後一次補 2 秒 delta）時，
## 避免 while 迴圈在「階段時間為 0」的設定下無限打轉。
const MAX_PHASE_STEPS_PER_FRAME := 16

## 階段邊界的浮點容差。
##
## 沒有它的話，advance(0.02) 之後再 advance(0.03)（合計正好等於 0.05 的前搖）
## 會因為 0.05 - 0.02 == 0.030000000000000002 而少轉一個階段 —— 狀態機的
## 行為變成取決於浮點雜訊，測試也會時過時不過。
const PHASE_EPSILON := 1e-6


func _process(delta: float) -> void:
	advance(delta)


func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed(&"attack"):
		press_attack()


# ---------------------------------------------------------------- 公開 API

func is_attacking() -> bool:
	return state != State.IDLE


func has_buffered_attack() -> bool:
	return _buffer_left > 0.0


func can_combo_cancel() -> bool:
	return state == State.RECOVERY


## 玩家按下攻擊。空閒時立刻出招；攻擊中則寫入預輸入。
## 若當下剛好已在可取消視窗內，立即兌現，不必等到下一幀。
func press_attack() -> void:
	if state == State.IDLE:
		_begin_attack()
		return
	_buffer_left = buffer_time
	if can_combo_cancel():
		_begin_attack()


## 推進 delta 秒。_process 會呼叫它，測試也可以直接手動餵值 ——
## 這正是把 await 換掉最大的好處。
func advance(delta: float) -> void:
	if _buffer_left > 0.0:
		_buffer_left = maxf(0.0, _buffer_left - delta)

	if state == State.IDLE:
		if combo_step > 0:
			_idle_time += delta
			if _idle_time >= combo_timeout:
				reset_combo()
		return

	# 逐階段消化 delta，而不是「一幀只推進一個階段」。
	# 低幀率下單一幀可能跨過整個 ACTIVE，用 if 會讓可取消視窗被完全跳過，
	# 玩家的預輸入就會無聲無息地掉了。
	var remaining := delta
	var steps := 0
	while remaining > 0.0 and state != State.IDLE:
		steps += 1
		if steps > MAX_PHASE_STEPS_PER_FRAME:
			break
		var need := _phase_duration() - _state_time
		if remaining < need - PHASE_EPSILON:
			_state_time += remaining
			return
		remaining -= need
		_state_time = 0.0
		_enter_next_phase()


func reset_combo() -> void:
	if combo_step == 0:
		return
	combo_step = 0
	_idle_time = 0.0
	combo_reset.emit()


# ---------------------------------------------------------------- 內部

func _phase_duration() -> float:
	match state:
		State.STARTUP: return startup_time
		State.ACTIVE: return active_time
		State.RECOVERY: return recovery_time
	return 0.0


func _enter_next_phase() -> void:
	match state:
		State.STARTUP:
			state = State.ACTIVE
			hit_active.emit(combo_step)
		State.ACTIVE:
			state = State.RECOVERY
			cancel_window_opened.emit(combo_step)
			# 視窗一開就檢查預輸入 —— 這是 Input Buffer 的兌現點
			if has_buffered_attack():
				_begin_attack()
		State.RECOVERY:
			var finished := combo_step
			state = State.IDLE
			_idle_time = 0.0
			attack_finished.emit(finished)


func _begin_attack() -> void:
	# combo_step 是「這條連擊鏈已經打了幾刀」，單調遞增、只在 reset 時歸零。
	# 不做環狀回捲：一旦回捲到 0，「連擊進行中」與「沒有連擊」就無法區分，
	# idle timeout 的判斷會整個失效。方向改用 modulo 取，需要三刀循環時
	# 把 combo_length 設成 3 即可。
	var index := combo_step % maxi(1, combo_length)
	var is_backhand := (index % 2) == 1

	state = State.STARTUP
	_state_time = 0.0
	_buffer_left = 0.0
	_idle_time = 0.0

	attack_started.emit(index, is_backhand)
	combo_step += 1
