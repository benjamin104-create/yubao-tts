## 刀光呈現（重構版）。
##
## 職責只剩「把一次揮砍畫出來」—— combo_step 不再存在這裡。原版在
## PlayerCombat 與這裡各存一份、各跑一個重置計時器，兩份狀態遲早會脫節。
## 現在方向由 attack_started 訊號傳進來，這個類別沒有任何自己的連擊狀態。
class_name ActionComboSlashController
extends Node2D

@export var slash_effect: ColorRect       # 掛 Slash Arc Shader 的 ColorRect
@export var weapon_pivot: Node2D          # 揮砍樞軸（通常是玩家或手部節點）
@export var weapon_sprite: Sprite2D       # 武器實體，可留空

@export var forehand_arc := 120.0
@export var backhand_arc := 140.0
@export var forehand_color := Color("0099ff")
@export var backhand_color := Color("ff0055")
@export var slash_duration := 0.10

var _mat: ShaderMaterial
var _progress_tween: Tween
var _weapon_tween: Tween


func _ready() -> void:
	if slash_effect == null:
		return
	_mat = slash_effect.material as ShaderMaterial
	# 縮放樞軸必須在正中央，scale.y = -1 翻轉時才不會產生位移
	slash_effect.pivot_offset = slash_effect.size * 0.5
	slash_effect.visible = false


## 接 ActionPlayerCombat.attack_started 訊號。
func play(target_global_pos: Vector2, is_backhand: bool) -> void:
	if _mat == null or weapon_pivot == null:
		return

	_align_to_pivot()

	var dir := target_global_pos - weapon_pivot.global_position
	var base_angle := rad_to_deg(dir.angle()) if dir.length_squared() > 0.0001 else 0.0
	var arc := backhand_arc if is_backhand else forehand_arc

	_mat.set_shader_parameter("rotation_degrees", base_angle)
	_mat.set_shader_parameter("arc_angle_degrees", arc)
	_mat.set_shader_parameter("color_edge",
		backhand_color if is_backhand else forehand_color)

	# 反手：垂直翻轉節點即可得到逆時針軌跡，progress 仍是 0 → 1，
	# 不必為了反向再寫一套動畫
	slash_effect.scale.y = -1.0 if is_backhand else 1.0

	_animate_progress()
	_animate_weapon(base_angle, arc, is_backhand)


# ---------------------------------------------------------------- 內部

## ColorRect 的 global_position 在左上角，直接設成樞軸座標會讓刀光的
## 旋轉中心偏掉半個尺寸。Shader 的 UV 原點是 (0.5, 0.5)，必須讓它落在
## 武器樞軸上。
func _align_to_pivot() -> void:
	slash_effect.global_position = weapon_pivot.global_position \
		- slash_effect.size * 0.5


func _animate_progress() -> void:
	# 沒有這一行，前一刀的 tween.finished 會在第二刀播到一半時
	# 把 visible 設回 false —— 連打時刀光會隨機消失
	if _progress_tween != null and _progress_tween.is_running():
		_progress_tween.kill()

	slash_effect.visible = true
	_mat.set_shader_parameter("progress", 0.0)

	_progress_tween = create_tween().set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	_progress_tween.tween_property(
		_mat, "shader_parameter/progress", 1.0, slash_duration)
	_progress_tween.finished.connect(_hide_effect, CONNECT_ONE_SHOT)


func _hide_effect() -> void:
	if slash_effect != null:
		slash_effect.visible = false


## 武器實體跟著揮。
##
## 關鍵：不能直接 tween rotation_degrees 到絕對角度。從 170° 揮到 -170°
## 只差 20°，但線性補間會繞遠路轉 340° —— 這才是「角度跨越 ±180 度」
## 真正會出問題的地方（Shader 那邊已經用 mod 正規化過，反而沒事）。
func _animate_weapon(base_angle: float, arc: float, is_backhand: bool) -> void:
	if weapon_sprite == null:
		return
	if _weapon_tween != null and _weapon_tween.is_running():
		_weapon_tween.kill()

	var half := arc * 0.5
	var start_angle := base_angle + half if is_backhand else base_angle - half
	var end_angle := base_angle - half if is_backhand else base_angle + half

	# 取最短路徑的角度差，再用「起點 + 差值」當補間目標
	var shortest_delta := wrapf(end_angle - start_angle, -180.0, 180.0)

	weapon_sprite.rotation_degrees = start_angle
	_weapon_tween = create_tween().set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	_weapon_tween.tween_property(weapon_sprite, "rotation_degrees",
		start_angle + shortest_delta, slash_duration)


## 給測試與外部工具用：驗證最短路徑計算，不需要真的建一個 Sprite2D。
static func shortest_arc_target(start_deg: float, end_deg: float) -> float:
	return start_deg + wrapf(end_deg - start_deg, -180.0, 180.0)
