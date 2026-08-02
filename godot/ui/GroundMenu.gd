## 腳下選單 —— 站在道具上時的四個選項：撿起 / 使用 / 替換 / 踏過。
##
## 這是原作最被低估的機制：**不撿起就能直接使用**。背包滿的時候、
## 或是低血急著喝草藥的時候，「省下撿起那 1 回合」往往就是生死之別。
## 少了它，滿背包等於完全不能碰地上的東西，整個資源管理的張力會塌掉。
##
## 開啟選單本身是 0 回合（唯讀操作），選定的動作才消耗 1 回合。
class_name GroundMenu
extends Control

signal intent_requested(intent: ActionIntent)
## 揮杖需要方向，交回 Main 進入瞄準模式
signal wave_aim_requested(item: ItemInstance)

enum Action { PICK_UP = 200, USE, SWAP, STEP_OVER }

var host: GameHost

var _menu: PopupMenu
var _swap_dialog: AcceptDialog
var _swap_list: ItemList

var _ground_item: ItemInstance = null


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE

	_menu = PopupMenu.new()
	_menu.id_pressed.connect(_on_menu_pressed)
	add_child(_menu)

	_swap_dialog = AcceptDialog.new()
	_swap_dialog.title = "選擇要換出去的道具"
	_swap_list = ItemList.new()
	_swap_list.custom_minimum_size = Vector2(300, 200)
	_swap_list.item_clicked.connect(_on_swap_item_clicked)
	_swap_dialog.add_child(_swap_list)
	add_child(_swap_dialog)


func setup(p_host: GameHost) -> void:
	host = p_host


func is_open() -> bool:
	return _menu.visible or _swap_dialog.visible


## 由 Main 在玩家按下 G 時呼叫。腳下沒東西就什麼都不做。
func open_at_player() -> bool:
	if host == null or host.player == null:
		return false
	var map := host.map
	if not map.floor_items.has(host.player.pos):
		return false

	_ground_item = map.floor_items[host.player.pos]
	_build_menu()
	_menu.position = Vector2i(get_viewport().get_visible_rect().size * 0.5) + Vector2i(20, -40)
	_menu.reset_size()
	_menu.popup()
	return true


func _build_menu() -> void:
	_menu.clear()

	_menu.add_item("撿起", Action.PICK_UP)
	if not host.player.inventory.has_space():
		# 背包滿時撿起變灰 —— 但「使用」與「替換」仍然可用，這正是這個
		# 選單存在的理由
		_menu.set_item_disabled(_menu.get_item_index(Action.PICK_UP), true)

	var verb_label := _use_label(_ground_item.category)
	if verb_label != "":
		_menu.add_item("%s（不撿起）" % verb_label, Action.USE)

	_menu.add_item("替換", Action.SWAP)
	if host.player.inventory.size() == 0:
		_menu.set_item_disabled(_menu.get_item_index(Action.SWAP), true)

	_menu.add_separator()
	_menu.add_item("踏過", Action.STEP_OVER)


static func _use_label(category: String) -> String:
	match category:
		"food": return "吃"
		"herb": return "喝"
		"scroll": return "讀"
		"wand": return "揮動"
	return ""


static func _verb_of(category: String) -> int:
	match category:
		"food", "herb": return ActionIntent.Verb.EAT
		"scroll": return ActionIntent.Verb.READ
		"wand": return ActionIntent.Verb.WAVE
	return ActionIntent.Verb.NONE


func _on_menu_pressed(id: int) -> void:
	match id:
		Action.PICK_UP:
			intent_requested.emit(ActionIntent.pickup())
		Action.USE:
			var verb := _verb_of(_ground_item.category)
			if verb == ActionIntent.Verb.WAVE:
				# 杖需要方向，交回 Main 進入瞄準模式
				wave_aim_requested.emit(_ground_item)
			else:
				intent_requested.emit(ActionIntent.use_ground(_ground_item, verb))
		Action.SWAP:
			_show_swap_dialog()
		Action.STEP_OVER:
			pass      # 關閉選單，道具留在地面，不消耗回合


func _show_swap_dialog() -> void:
	_swap_list.clear()
	for it: ItemInstance in host.player.inventory.slots:
		var text := host.display_name(it)
		if it == host.player.weapon or it == host.player.shield:
			text += "  〈裝備中〉"
		_swap_list.add_item(text)
	_swap_dialog.title = "用什麼換「%s」？" % host.display_name(_ground_item)
	_swap_dialog.popup_centered(Vector2i(340, 260))


func _on_swap_item_clicked(index: int, _at: Vector2, _button: int) -> void:
	var item := host.player.inventory.at(index)
	if item == null:
		return
	_swap_dialog.hide()
	intent_requested.emit(ActionIntent.swap_ground(item))
