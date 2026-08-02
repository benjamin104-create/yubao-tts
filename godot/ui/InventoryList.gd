## 背包清單，附拖放。
##
## 拖放只負責「玩家想把 A 放進 B」這個意圖的蒐集，所有合法性檢查
## （容量、壺的行為型別、壺不能放進壺）都在 Core 做 —— UI 這層的檢查
## 純粹是為了不讓玩家做出一定會失敗的操作，不是防線。
class_name InventoryList
extends ItemList

signal drop_requested(from_index: int, to_index: int)

var inventory_ref: Array = []


func _get_drag_data(at_position: Vector2) -> Variant:
	var index := get_item_at_position(at_position, true)
	if index < 0 or index >= inventory_ref.size():
		return null

	var preview := Label.new()
	preview.text = get_item_text(index)
	preview.add_theme_color_override("font_color", Color(1, 1, 0.7))
	var wrapper := Control.new()
	wrapper.add_child(preview)
	preview.position = -preview.get_minimum_size() * 0.5
	set_drag_preview(wrapper)

	return { "from_index": index, "item": inventory_ref[index] }


func _can_drop_data(at_position: Vector2, data: Variant) -> bool:
	if typeof(data) != TYPE_DICTIONARY or not data.has("from_index"):
		return false
	var target := get_item_at_position(at_position, true)
	if target < 0 or target >= inventory_ref.size() or target == data["from_index"]:
		return false
	var dragged: ItemInstance = data["item"]
	var pot: ItemInstance = inventory_ref[target]
	if not pot.is_pot() or pot.is_full():
		return false
	# 任何壺都不能放進壺 —— 否則巢狀容器讓背包上限失去意義
	return not dragged.is_pot()


func _drop_data(at_position: Vector2, data: Variant) -> void:
	var target := get_item_at_position(at_position, true)
	if target >= 0:
		drop_requested.emit(int(data["from_index"]), target)
