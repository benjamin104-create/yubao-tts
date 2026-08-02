## 狀態列：HP / 飽足度 / 樓層 / 等級 / 回合數。
##
## 飽足度的顏色警示是硬性需求 —— 餓死絕不能是「意外」（GDD §2.5）。
class_name StatusBar
extends PanelContainer

var host: GameHost

var _main: Label
var _satiety: Label
var _status: Label


func _ready() -> void:
	var box := HBoxContainer.new()
	box.add_theme_constant_override("separation", 18)
	add_child(box)

	_main = Label.new()
	box.add_child(_main)

	_satiety = Label.new()
	box.add_child(_satiety)

	_status = Label.new()
	_status.add_theme_color_override("font_color", Color(0.9, 0.7, 1.0))
	box.add_child(_status)


func setup(p_host: GameHost) -> void:
	host = p_host
	refresh()


func refresh() -> void:
	if host == null or host.player == null:
		return
	var p := host.player
	_main.text = "%dF   Lv %d   HP %d/%d   %d G   %d 回合" % [
		host.floor_index, p.level, p.hp, p.max_hp, p.gold, host.turns.turn_count]

	var pct := float(p.satiety) / float(p.max_satiety)
	_satiety.text = "飽足 %.1f%%" % (p.satiety / 1000.0)
	if p.satiety <= 0:
		_satiety.add_theme_color_override("font_color", Color(1.0, 0.3, 0.3))
		_satiety.text = "飢餓！"
	elif pct <= 0.10:
		_satiety.add_theme_color_override("font_color", Color(1.0, 0.45, 0.35))
	elif pct <= 0.30:
		_satiety.add_theme_color_override("font_color", Color(1.0, 0.85, 0.35))
	else:
		_satiety.add_theme_color_override("font_color", Color(0.85, 0.9, 0.85))

	var flags: Array[String] = []
	for s: String in p.statuses.keys():
		flags.append("%s(%d)" % [s, p.statuses[s]])
	_status.text = "  ".join(flags)
