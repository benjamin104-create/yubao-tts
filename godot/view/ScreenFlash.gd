## 全螢幕衝擊閃光。
##
## 只在少數真正需要玩家抬頭的時刻觸發：受到會心一擊、升級、死亡。
## 回合制遊戲的每一步都是玩家主動按下的，濫用全螢幕效果會讓移動變成
## 一場閃光秀 —— 稀有才有效。
class_name ScreenFlash
extends ColorRect


func _ready() -> void:
	set_anchors_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	color = Color(0, 0, 0, 0)


func flash(tint: Color, duration := 0.22) -> void:
	color = tint
	var tween := create_tween()
	tween.tween_property(self, "color:a", 0.0, duration) \
		.set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)
