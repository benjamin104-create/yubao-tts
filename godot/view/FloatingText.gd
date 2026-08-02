## 傷害飄字。設計成可回收 —— 不 queue_free()，播完歸還物件池。
##
## 為什麼要池化：一次 AOE 打中 12 隻怪就是 12 次 instantiate + queue_free，
## SceneTree 的掛載/卸載與 GC 是 2D 遊戲微卡頓的主因之一。預先建好、
## 重複使用，執行期的節點數量永遠是常數。
class_name FloatingText
extends Node2D

signal recycled(node: FloatingText)

enum Type { NORMAL, CRITICAL, HEAL, MISS }

const COLORS := {
	Type.NORMAL: Color(1.0, 1.0, 1.0),
	Type.CRITICAL: Color(1.0, 0.80, 0.20),
	Type.HEAL: Color(0.30, 1.0, 0.45),
	Type.MISS: Color(0.68, 0.68, 0.68),
}

var _label: Label
var _tween: Tween


func _ready() -> void:
	z_index = 100
	_label = Label.new()
	_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	_label.add_theme_font_size_override("font_size", 15)
	# 黑色描邊：任何地形背景上都讀得到
	_label.add_theme_constant_override("outline_size", 5)
	_label.add_theme_color_override("font_outline_color", Color(0, 0, 0, 0.9))
	add_child(_label)
	_deactivate()


func activate(text: String, type: Type, world_pos: Vector2,
		rng_offset: float = 0.0) -> void:
	if _tween != null and _tween.is_running():
		# 被搶占時必須先殺掉舊 Tween，否則舊的位移/淡出會與新動畫競態，
		# 造成位置跳躍或卡在半透明
		_tween.kill()

	global_position = world_pos + Vector2(rng_offset, 0)
	_label.text = text
	# 文字從 "9" 變成 "128" 時尺寸會變，重設 size 才能讓縮放中心落在數字正中央
	_label.reset_size()
	_label.pivot_offset = _label.size * 0.5
	_label.position = -_label.size * 0.5
	_label.modulate = COLORS[type]

	modulate = Color.WHITE
	visible = true
	process_mode = Node.PROCESS_MODE_INHERIT

	_tween = create_tween()
	match type:
		Type.CRITICAL:
			_animate_critical()
		Type.HEAL:
			_animate_heal()
		Type.MISS:
			_animate_miss()
		_:
			_animate_normal()
	_tween.finished.connect(recycle, CONNECT_ONE_SHOT)


func _animate_normal() -> void:
	scale = Vector2(0.8, 0.8)
	var p := _tween.set_parallel(true)
	p.tween_property(self, "position:y", position.y - 28.0, 0.55) \
		.set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
	p.tween_property(self, "scale", Vector2.ONE, 0.12)
	p.tween_property(self, "modulate:a", 0.0, 0.22).set_delay(0.33)


func _animate_critical() -> void:
	scale = Vector2(1.7, 1.7)
	_tween.tween_property(self, "scale", Vector2(1.15, 1.15), 0.10) \
		.set_trans(Tween.TRANS_SPRING).set_ease(Tween.EASE_OUT)
	var p := _tween.chain().set_parallel(true)
	p.tween_property(self, "position:y", position.y - 42.0, 0.60) \
		.set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
	p.tween_property(self, "scale", Vector2.ONE, 0.60)
	p.tween_property(self, "modulate:a", 0.0, 0.26).set_delay(0.34)


func _animate_heal() -> void:
	scale = Vector2(0.6, 0.6)
	var p := _tween.set_parallel(true)
	p.tween_property(self, "position:y", position.y - 34.0, 0.70) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	p.tween_property(self, "scale", Vector2(1.05, 1.05), 0.25)
	p.tween_property(self, "modulate:a", 0.0, 0.26).set_delay(0.44)


func _animate_miss() -> void:
	scale = Vector2(0.9, 0.9)
	var p := _tween.set_parallel(true)
	p.tween_property(self, "position:y", position.y - 20.0, 0.45)
	p.tween_property(self, "modulate:a", 0.0, 0.20).set_delay(0.25)


func recycle() -> void:
	_deactivate()
	recycled.emit(self)


func _deactivate() -> void:
	visible = false
	# 關閉 process：閒置中的節點不該再消耗任何幀時間
	process_mode = Node.PROCESS_MODE_DISABLED
