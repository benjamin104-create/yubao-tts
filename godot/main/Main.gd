## 組裝整個遊戲並處理輸入。
##
## 節點樹在程式裡建起來（而不是 .tscn），原型階段少一個要維護的檔案，
## 結構也一眼看得到。正式專案可以拆回場景。
##
## 操作：
##   方向鍵 / WASD  移動        Q E Z C  斜向移動
##   空白鍵         原地待機     G  撿取     >  下樓
##   I              背包        Esc 取消瞄準
extends Node2D

const CJK_FONTS: Array[String] = [
	"Noto Sans CJK TC", "Noto Sans CJK SC", "Noto Sans TC",
	"Microsoft JhengHei", "PingFang TC", "Heiti TC",
	"WenQuanYi Zen Hei", "Source Han Sans TC", "sans-serif",
]

const DIAGONAL_KEYS := {
	KEY_Q: Vector2i(-1, -1), KEY_E: Vector2i(1, -1),
	KEY_Z: Vector2i(-1, 1), KEY_C: Vector2i(1, 1),
}

var host: GameHost
var map_renderer: MapRenderer
var fog: FogRenderer
var entity_view: EntityView
var event_player: EventPlayer
var camera: Camera2D

var status_bar: StatusBar
var message_log: MessageLog
var inventory_ui: InventoryUI

## 瞄準模式：選了杖或投擲之後，等玩家按方向鍵決定射向
var _aim_item: ItemInstance = null
var _aim_verb := ActionIntent.Verb.NONE

var _ui_theme: Theme


func _ready() -> void:
	_build_theme()
	_build_world()
	_build_ui()

	host.start_run(0)
	_on_floor_changed(1)
	message_log.push("進入了地下城。方向鍵移動，I 開背包，G 撿取，> 下樓。")


# ---------------------------------------------------------------- 建構

## 用 SystemFont 取用系統的 CJK 字型 —— Godot 內建字型沒有中文字符，
## 不做這件事所有中文 UI 都會變成方塊。
func _build_theme() -> void:
	var font := SystemFont.new()
	font.font_names = PackedStringArray(CJK_FONTS)
	font.allow_system_fallback = true
	_ui_theme = Theme.new()
	_ui_theme.default_font = font
	_ui_theme.default_font_size = 15


func _build_world() -> void:
	host = GameHost.new()
	host.name = "GameHost"
	add_child(host)

	var world := Node2D.new()
	world.name = "World"
	add_child(world)

	map_renderer = MapRenderer.new()
	world.add_child(map_renderer)

	fog = FogRenderer.new()
	world.add_child(fog)

	entity_view = EntityView.new()
	world.add_child(entity_view)
	entity_view.setup(host)

	event_player = EventPlayer.new()
	add_child(event_player)
	event_player.setup(host, entity_view, fog)

	camera = Camera2D.new()
	camera.zoom = Vector2(1.6, 1.6)
	add_child(camera)

	host.floor_changed.connect(_on_floor_changed)
	host.player_died.connect(_on_player_died)


func _build_ui() -> void:
	var layer := CanvasLayer.new()
	layer.name = "UI"
	add_child(layer)

	var root := Control.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.theme = _ui_theme       # 主題掛在 UI 根 Control 上（Node2D 沒有 theme）
	layer.add_child(root)

	status_bar = StatusBar.new()
	status_bar.set_anchors_preset(Control.PRESET_TOP_WIDE)
	root.add_child(status_bar)
	status_bar.setup(host)

	message_log = MessageLog.new()
	message_log.set_anchors_preset(Control.PRESET_BOTTOM_WIDE)
	root.add_child(message_log)

	inventory_ui = InventoryUI.new()
	root.add_child(inventory_ui)
	inventory_ui.setup(host)

	event_player.message.connect(message_log.push)
	inventory_ui.intent_requested.connect(_submit)
	inventory_ui.aim_requested.connect(_begin_aim)


func _on_floor_changed(f: int) -> void:
	map_renderer.draw_map(host.map)
	entity_view.rebuild()
	fog.redraw(host.vision)
	_center_camera()
	status_bar.refresh()
	inventory_ui.refresh()
	if f > 1:
		message_log.push("來到了地下 %d 層。" % f)


# ---------------------------------------------------------------- 輸入

func _unhandled_key_input(event: InputEvent) -> void:
	if not (event is InputEventKey) or not event.pressed or event.echo:
		return
	if event_player.is_playing or host.is_game_over:
		return

	var key := (event as InputEventKey).physical_keycode

	# 瞄準模式：下一個方向鍵決定射向
	if _aim_item != null:
		if key == KEY_ESCAPE:
			_cancel_aim("取消。")
			return
		var aim_dir := _dir_from_key(key)
		if aim_dir != Vector2i.ZERO:
			var item := _aim_item
			var verb := _aim_verb
			_aim_item = null
			_submit(ActionIntent.throw_item(item, aim_dir) if verb == ActionIntent.Verb.THROW
					else ActionIntent.use(item, verb, aim_dir))
			get_viewport().set_input_as_handled()
		return

	if key == KEY_I:
		inventory_ui.toggle()
		get_viewport().set_input_as_handled()
		return

	var dir := _dir_from_key(key)
	if dir != Vector2i.ZERO:
		# 連續移動時允許壓縮動畫；有敵人或低血時 EventPlayer 會自行否決
		event_player.allow_compression = true
		_submit(ActionIntent.move(dir))
		get_viewport().set_input_as_handled()
		return

	event_player.allow_compression = false
	match key:
		KEY_SPACE:
			_submit(ActionIntent.wait())
		KEY_G:
			_submit(ActionIntent.pickup())
		KEY_PERIOD, KEY_GREATER:
			_submit(ActionIntent.descend())
		_:
			return
	get_viewport().set_input_as_handled()


func _dir_from_key(key: int) -> Vector2i:
	if DIAGONAL_KEYS.has(key):
		return DIAGONAL_KEYS[key]
	match key:
		KEY_UP, KEY_W, KEY_KP_8:
			return Vector2i(0, -1)
		KEY_DOWN, KEY_S, KEY_KP_2:
			return Vector2i(0, 1)
		KEY_LEFT, KEY_A, KEY_KP_4:
			return Vector2i(-1, 0)
		KEY_RIGHT, KEY_D, KEY_KP_6:
			return Vector2i(1, 0)
		KEY_KP_7:
			return Vector2i(-1, -1)
		KEY_KP_9:
			return Vector2i(1, -1)
		KEY_KP_1:
			return Vector2i(-1, 1)
		KEY_KP_3:
			return Vector2i(1, 1)
	return Vector2i.ZERO


func _begin_aim(item: ItemInstance, verb: int) -> void:
	_aim_item = item
	_aim_verb = verb
	message_log.push("選擇方向（方向鍵 / QEZC，Esc 取消）。")


func _cancel_aim(reason: String) -> void:
	_aim_item = null
	message_log.push(reason)


# ---------------------------------------------------------------- 回合

## 輸入 → Intent → Core 跑完整回合 → 事件串 → View 播放。
## 播放期間輸入被鎖住，狀態與畫面因此不可能不同步。
func _submit(intent: ActionIntent) -> void:
	if event_player.is_playing or host.is_game_over:
		return
	var events := host.submit_intent(intent)
	if events.is_empty():
		return
	await event_player.play(events)
	if host.has_pending_floor():
		host.commit_pending_floor()
	_center_camera()
	status_bar.refresh()
	inventory_ui.refresh()


func _center_camera() -> void:
	if host.player != null:
		camera.position = EntityView.tile_center(host.player.pos)


func _on_player_died(record: Dictionary) -> void:
	message_log.push("你在地下 %d 層倒下了……（%d 回合，Lv %d）" % [
		record.get("floor", 0), record.get("turn", 0), record.get("level", 1)])
	message_log.push("等級歸一、道具全失 —— 但你學到的東西會留下來。")
