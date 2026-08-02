## 背包介面：四種動詞（吃／讀／揮／投）+ 裝備 + 壺操作。
##
## 鐵則：這個類別不修改任何 Core 資料。所有操作一律轉成 ActionIntent 送出，
## 由 TurnManager 執行 —— 因此每一個操作都會消耗回合、讓怪物同步行動、
## 產生事件、進存檔、被重播記錄（架構文件 §4 / §7）。
##
## 自行建立子節點而不依賴 .tscn：原型階段少一個要維護的檔案，
## 節點樹的結構也直接寫在程式裡看得到。
class_name InventoryUI
extends Control

signal intent_requested(intent: ActionIntent)
## 需要方向的動作（揮杖、投擲）先交回 Main 進入瞄準模式
signal aim_requested(item: ItemInstance, verb: int)

enum Action {
	EAT = 100, READ, WAVE, THROW, EQUIP, UNEQUIP,
	PUT_IN, TAKE_OUT, INSPECT, DROP,
}

var host: GameHost

var _list: InventoryList
var _menu: PopupMenu
var _pot_dialog: AcceptDialog
var _pot_list: ItemList
var _hint: Label

var _selected: ItemInstance = null
var _pending_pot: ItemInstance = null      # 正在等待「要放入什麼」的壺
var _open_pot: ItemInstance = null         # 內容物視窗正在顯示的壺


func _ready() -> void:
	set_anchors_preset(Control.PRESET_RIGHT_WIDE)
	custom_minimum_size = Vector2(300, 0)
	visible = false

	var panel := PanelContainer.new()
	panel.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(panel)

	var box := VBoxContainer.new()
	panel.add_child(box)

	var title := Label.new()
	title.text = "背包"
	box.add_child(title)

	_hint = Label.new()
	_hint.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_hint.add_theme_font_size_override("font_size", 12)
	_hint.add_theme_color_override("font_color", Color(0.8, 0.8, 0.6))
	box.add_child(_hint)

	_list = InventoryList.new()
	_list.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_list.item_clicked.connect(_on_item_clicked)
	_list.drop_requested.connect(_on_drop_requested)
	box.add_child(_list)

	_menu = PopupMenu.new()
	_menu.id_pressed.connect(_on_menu_pressed)
	add_child(_menu)

	_pot_dialog = AcceptDialog.new()
	_pot_dialog.title = "壺的內容物"
	_pot_list = ItemList.new()
	_pot_list.custom_minimum_size = Vector2(280, 160)
	_pot_list.item_clicked.connect(_on_pot_item_clicked)
	_pot_dialog.add_child(_pot_list)
	add_child(_pot_dialog)


func setup(p_host: GameHost) -> void:
	host = p_host
	host.inventory_changed.connect(refresh)
	refresh()


func toggle() -> void:
	visible = not visible
	if visible:
		refresh()
	else:
		_cancel_pending()


func refresh() -> void:
	# setup() 會在 start_run() 之前被呼叫，此時還沒有玩家
	if host == null or host.player == null:
		return
	_list.clear()
	_list.inventory_ref = host.player.inventory.slots
	for it: ItemInstance in host.player.inventory.slots:
		var text := host.display_name(it)
		if it == host.player.weapon:
			text += "  〈裝備中〉"
		elif it == host.player.shield:
			text += "  〈裝備中〉"
		_list.add_item(text)
	_update_hint()


func _update_hint() -> void:
	if _pending_pot != null:
		_hint.text = "選擇要放進「%s」的道具（Esc 取消）" % host.display_name(_pending_pot)
	else:
		_hint.text = "%d / %d 格　　左鍵：選單　拖曳到壺上：放入" % [
			host.player.inventory.size(), Inventory.CAPACITY]


# ---------------------------------------------------------------- 互動

func _on_item_clicked(index: int, _at: Vector2, _button: int) -> void:
	var item := host.player.inventory.at(index)
	if item == null:
		return

	# 正在等待「放入什麼」→ 這次點擊就是選材料
	if _pending_pot != null:
		var pot := _pending_pot
		_cancel_pending()
		intent_requested.emit(ActionIntent.put_into_pot(item, pot))
		return

	_selected = item
	_build_menu(item)
	_menu.position = Vector2i(get_global_mouse_position()) + Vector2i(4, 4)
	_menu.reset_size()
	_menu.popup()


## 動態禁用：不可能成功的操作直接變灰，玩家不必試了才知道。
func _build_menu(item: ItemInstance) -> void:
	_menu.clear()

	match item.category:
		"food":
			_menu.add_item("吃", Action.EAT)
		"herb":
			_menu.add_item("喝", Action.EAT)
		"scroll":
			_menu.add_item("讀", Action.READ)
		"wand":
			_menu.add_item("揮動", Action.WAVE)
			if item.uses <= 0 and host.ident.is_identified(item.def_id):
				_disable(Action.WAVE)
		"weapon", "shield":
			var equipped := item == host.player.weapon or item == host.player.shield
			_menu.add_item("卸下" if equipped else "裝備",
				Action.UNEQUIP if equipped else Action.EQUIP)
		"pot":
			_menu.add_item("放入物品", Action.PUT_IN)
			if item.is_full() or not item.accepts_insert():
				_disable(Action.PUT_IN)
			_menu.add_item("取出物品", Action.TAKE_OUT)
			# 只有保存壺類能直接取出；合成／變化／吸物壺放進去就拿不回來
			if not item.can_extract_directly() or item.contents.is_empty():
				_disable(Action.TAKE_OUT)
			_menu.add_item("檢查內容", Action.INSPECT)
			if item.contents.is_empty():
				_disable(Action.INSPECT)

	_menu.add_item("投擲", Action.THROW)
	_menu.add_separator()
	_menu.add_item("放下", Action.DROP)


func _disable(id: int) -> void:
	_menu.set_item_disabled(_menu.get_item_index(id), true)


func _on_menu_pressed(id: int) -> void:
	var item := _selected
	if item == null:
		return

	match id:
		Action.EAT:
			intent_requested.emit(ActionIntent.use(item, ActionIntent.Verb.EAT))
		Action.READ:
			intent_requested.emit(ActionIntent.use(item, ActionIntent.Verb.READ))
		Action.EQUIP, Action.UNEQUIP:
			intent_requested.emit(ActionIntent.equip(item))
		Action.DROP:
			intent_requested.emit(ActionIntent.drop(item))
		Action.WAVE:
			# 需要方向 → 交回 Main 進入瞄準模式
			aim_requested.emit(item, ActionIntent.Verb.WAVE)
		Action.THROW:
			aim_requested.emit(item, ActionIntent.Verb.THROW)
		Action.PUT_IN:
			_pending_pot = item
			_update_hint()
		Action.TAKE_OUT, Action.INSPECT:
			_show_pot_contents(item)


func _on_drop_requested(from_index: int, to_index: int) -> void:
	var item := host.player.inventory.at(from_index)
	var pot := host.player.inventory.at(to_index)
	if item != null and pot != null:
		intent_requested.emit(ActionIntent.put_into_pot(item, pot))


# ---------------------------------------------------------------- 壺內容

func _show_pot_contents(pot: ItemInstance) -> void:
	# 持有壺的「參考」而非索引 —— 索引在背包增減後會失效
	_open_pot = pot
	_pot_list.clear()
	for inner: ItemInstance in pot.contents:
		_pot_list.add_item(host.display_name(inner))
	_pot_dialog.title = "%s（%s）" % [
		host.display_name(pot),
		"點擊取出" if pot.can_extract_directly() else "無法取出",
	]
	_pot_dialog.popup_centered(Vector2i(320, 220))


func _on_pot_item_clicked(index: int, _at: Vector2, _button: int) -> void:
	if _open_pot == null or not _open_pot.can_extract_directly():
		return
	if index < 0 or index >= _open_pot.contents.size():
		return
	var inner: ItemInstance = _open_pot.contents[index]
	_pot_dialog.hide()
	intent_requested.emit(ActionIntent.take_from_pot(inner, _open_pot))


func _cancel_pending() -> void:
	_pending_pot = null
	_selected = null
	if _hint != null:
		_update_hint()


func _unhandled_input(event: InputEvent) -> void:
	if not visible:
		return
	if event.is_action_pressed("ui_cancel") and _pending_pot != null:
		_cancel_pending()
		get_viewport().set_input_as_handled()
