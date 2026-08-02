## 全螢幕世界 Drop 區：把道具拖出背包視窗外放開 = 投擲或丟棄。
##
## 原理：Godot 的拖放判定由最前面的 UI 節點往後找。只要這個節點在節點樹中
## 排在背包**前面**（= 渲染在背包後方），任何沒降落在背包或壺上的放開事件
## 就會自然落到這裡。不需要任何邊界計算。
##
## 和你原本那份範例的差別：這裡不直接改資料。它只發出一個「玩家想丟」的
## 訊號，交給 Main 轉成 ActionIntent —— 因此丟棄與投擲一樣會消耗回合、
## 讓怪物同步行動、進事件串與存檔。
class_name WorldDropZone
extends Control

## drop_position 是這個 Control 的**區域座標**，不是螢幕座標。
## Main 會自己換算成世界座標再算方向 —— 直接拿它跟 get_global_transform_
## with_canvas().origin 比較是錯的，只有在 Drop 區剛好貼齊原點時才會對。
signal item_dropped_to_world(item: ItemInstance, drop_position: Vector2)


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	# 必須是 PASS 而不是 IGNORE：IGNORE 會讓節點完全退出滑鼠命中測試，
	# 連拖放判定都收不到；PASS 則是「不攔截點擊，但仍參與拖放」。
	mouse_filter = Control.MOUSE_FILTER_PASS


func _can_drop_data(_at_position: Vector2, data: Variant) -> bool:
	return typeof(data) == TYPE_DICTIONARY \
		and data.has("item") and data["item"] is ItemInstance


func _drop_data(at_position: Vector2, data: Variant) -> void:
	item_dropped_to_world.emit(data["item"], at_position)


## 把任意向量吸附到 8 方向。
##
## 不可用 round(dir.x) / round(dir.y) —— 那樣算出來的斜向扇區只有 30 度，
## 正交扇區卻有 60 度，玩家會覺得「斜著丟很難丟中」。用角度吸附才能讓
## 八個方向各佔 45 度。
static func snap_to_8_way(v: Vector2) -> Vector2i:
	if v.length_squared() < 0.001:
		return Vector2i.ZERO
	var a := snappedf(v.angle(), PI / 4.0)
	return Vector2i(roundi(cos(a)), roundi(sin(a)))
