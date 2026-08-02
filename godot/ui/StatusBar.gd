## 狀態列：HP / 攻防 / 飽足度 / 樓層 / 等級 / 回合數。
##
## 攻防數值變化時播放彈跳與浮動差值 —— 換裝備、喝力量草、被弱化之杖打中
## 都會即時可見。回合制遊戲沒有連續的動作回饋，數值本身就是主要的打擊感
## 來源，值得花力氣做。
##
## 飽足度的顏色警示是硬性需求：餓死絕不能是「意外」（GDD §2.5）。
class_name StatusBar
extends PanelContainer

var host: GameHost

var _main: Label
var _atk: Label
var _atk_delta: Label
var _def: Label
var _def_delta: Label
var _satiety: Label
var _status: Label

var _last_atk := -1
var _last_def := -1
var _atk_tween: Tween
var _def_tween: Tween


func _ready() -> void:
	var box := HBoxContainer.new()
	box.add_theme_constant_override("separation", 16)
	add_child(box)

	_main = Label.new()
	box.add_child(_main)

	var atk_pair := _make_stat_pair(box)
	_atk = atk_pair[0]
	_atk_delta = atk_pair[1]

	var def_pair := _make_stat_pair(box)
	_def = def_pair[0]
	_def_delta = def_pair[1]

	_satiety = Label.new()
	box.add_child(_satiety)

	_status = Label.new()
	_status.add_theme_color_override("font_color", Color(0.9, 0.7, 1.0))
	box.add_child(_status)


## 數值本體與浮動差值疊在同一個容器裡，差值浮起來時不會擠動旁邊的排版。
func _make_stat_pair(parent: Node) -> Array:
	var holder := Control.new()
	holder.custom_minimum_size = Vector2(84, 24)
	parent.add_child(holder)

	var value := Label.new()
	holder.add_child(value)

	var delta := Label.new()
	delta.position = Vector2(56, 0)
	delta.modulate = Color(1, 1, 1, 0)
	holder.add_child(delta)

	return [value, delta]


func setup(p_host: GameHost) -> void:
	host = p_host
	refresh()


func refresh() -> void:
	if host == null or host.player == null:
		return
	var p := host.player

	_main.text = "%dF  Lv %d  HP %d/%d  %dG  %d回合" % [
		host.floor_index, p.level, p.hp, p.max_hp, p.gold, host.turns.turn_count]

	_update_stat(_atk, _atk_delta, "ATK ", p.get_atk(), _last_atk, true)
	_update_stat(_def, _def_delta, "DEF ", p.get_defense(), _last_def, false)
	_last_atk = p.get_atk()
	_last_def = p.get_defense()

	_refresh_satiety(p)

	var flags: Array[String] = []
	for s: String in p.statuses.keys():
		flags.append("%s(%d)" % [s, p.statuses[s]])
	_status.text = "  ".join(flags)


func _update_stat(value_label: Label, delta_label: Label, prefix: String,
		new_val: int, old_val: int, is_atk: bool) -> void:
	value_label.text = prefix + str(new_val)
	if old_val < 0 or new_val == old_val:
		return

	var diff := new_val - old_val
	var up := diff > 0
	var tint := Color(0.4, 1.0, 0.5) if up else Color(1.0, 0.45, 0.4)

	# 快速連續換裝時，舊 Tween 沒殺掉會讓 scale 與 alpha 疊加，
	# 文字會卡在變形或半透明狀態
	var active: Tween = _atk_tween if is_atk else _def_tween
	if active != null and active.is_running():
		active.kill()

	value_label.pivot_offset = value_label.size * 0.5
	delta_label.text = "%+d" % diff
	delta_label.modulate = tint
	delta_label.position.y = 0.0

	var tween := create_tween()
	var pulse := tween.set_parallel(true)
	pulse.tween_property(value_label, "scale", Vector2(1.25, 1.25), 0.09) \
		.set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
	pulse.tween_property(value_label, "modulate", tint, 0.09)
	pulse.tween_property(delta_label, "position:y", -18.0 if up else 18.0, 0.5) \
		.set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
	pulse.tween_property(delta_label, "modulate:a", 0.0, 0.3).set_delay(0.2)

	var back := tween.chain().set_parallel(true)
	back.tween_property(value_label, "scale", Vector2.ONE, 0.16) \
		.set_trans(Tween.TRANS_SPRING)
	back.tween_property(value_label, "modulate", Color.WHITE, 0.16)

	if is_atk:
		_atk_tween = tween
	else:
		_def_tween = tween


func _refresh_satiety(p: PlayerEntity) -> void:
	var pct := float(p.satiety) / float(p.max_satiety)
	if p.satiety <= 0:
		_satiety.text = "飢餓！"
		_satiety.add_theme_color_override("font_color", Color(1.0, 0.3, 0.3))
		return
	_satiety.text = "飽足 %.1f%%" % (p.satiety / 1000.0)
	if pct <= 0.10:
		_satiety.add_theme_color_override("font_color", Color(1.0, 0.45, 0.35))
	elif pct <= 0.30:
		_satiety.add_theme_color_override("font_color", Color(1.0, 0.85, 0.35))
	else:
		_satiety.add_theme_color_override("font_color", Color(0.85, 0.9, 0.85))
