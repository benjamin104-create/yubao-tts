## 實機試玩並截圖。
##
##   xvfb-run -a godot --path godot --script res://tests/play_capture.gd
##
## 載入真正的 Main.tscn（含 TileMapLayer、霧效、飄字、UI），用程式驅動輸入
## 走一段路，把畫面存成 PNG。headless 測試證明的是邏輯正確，這支證明的是
## 「畫面真的畫得出來」—— 兩者是不同的事。
extends SceneTree

const SHOT_DIR := "user://shots"
const CAPTURE_SEED := 20260802

var main: Node2D
var _log: Array[String] = []


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	DirAccess.make_dir_recursive_absolute(SHOT_DIR)
	main = load("res://main/Main.tscn").instantiate()
	root.add_child(main)
	await process_frame

	# 固定 seed，讓截圖可重現 —— 否則每次跑出來的圖不一樣，
	# 就沒辦法拿來比對「這次改動有沒有弄壞畫面」
	main.host.start_run(CAPTURE_SEED)
	main._on_floor_changed(1)
	await process_frame

	_note("啟動：%dF，玩家 %s，場上 %d 隻怪，地面 %d 件道具" % [
		main.host.floor_index, main.host.player.pos,
		main.host.entities.monster_count(), main.host.map.floor_items.size()])
	await _settle(8)
	await _shot("01_start")

	# 走 60 步，優先撿道具、否則往樓梯前進
	var moves := 0
	for i in 60:
		if main.host.is_game_over:
			break
		var acted := await _step_once()
		if acted:
			moves += 1
		if i == 24:
			await _shot("02_explore")
	_note("走了 %d 步，回合數 %d，HP %d/%d，飽足 %.1f%%" % [
		moves, main.host.turns.turn_count, main.host.player.hp,
		main.host.player.max_hp, main.host.player.satiety / 1000.0])
	await _shot("03_after_walk")

	# 開背包
	main.inventory_ui.toggle()
	await _settle(6)
	_dump_rect("InventoryUI", main.inventory_ui)
	_dump_rect("MessageLog", main.message_log)
	_dump_rect("StatusBar", main.status_bar)
	_note("訊息列行數 %d" % main.message_log._lines.size())
	await _shot("04_inventory")
	main.inventory_ui.toggle()
	await _settle(4)

	# 直奔樓梯下樓
	for i in 300:
		if main.host.is_game_over:
			break
		if main.host.player.pos == main.host.map.stairs_down:
			await _submit(ActionIntent.descend())
			break
		var dir := _next_step(main.host.player.pos, main.host.map.stairs_down)
		if dir == Vector2i.ZERO:
			_note("尋路中斷：玩家 %s → 樓梯 %s（第 %d 次嘗試）"
				% [main.host.player.pos, main.host.map.stairs_down, i])
			break
		var before_pos: Vector2i = main.host.player.pos
		await _submit(ActionIntent.move(dir))
		if main.host.player.pos == before_pos:
			_note("移動被擋：%s 方向 %s（可能是怪物擋路）"
				% [before_pos, dir])
	_note("目前樓層：%dF（回合 %d）" % [main.host.floor_index, main.host.turns.turn_count])
	await _settle(8)
	await _shot("05_floor%d" % main.host.floor_index)

	print("\n".join(_log))
	print("截圖輸出目錄：%s" % ProjectSettings.globalize_path(SHOT_DIR))
	quit(0)


func _dump_rect(label: String, c: Control) -> void:
	_note("%s visible=%s rect=%s min=%s 子節點=%d"
		% [label, c.visible, c.get_rect(), c.get_combined_minimum_size(),
			c.get_child_count()])


func _note(text: String) -> void:
	_log.append("  " + text)


func _step_once() -> bool:
	var host: GameHost = main.host
	var p := host.player

	if host.map.floor_items.has(p.pos) and p.inventory.has_space():
		await _submit(ActionIntent.pickup())
		return true

	for d in Tiles.DIRS_8:
		var e := host.entities.at(p.pos + d)
		if e != null and not e.is_player \
				and WorldSnapshot.corner_rule_ok(host.map, p.pos, p.pos + d):
			await _submit(ActionIntent.move(d))
			return true

	var goal := host.map.stairs_down
	var nearest := _nearest_item()
	if nearest != Vector2i(-1, -1) and p.inventory.has_space():
		goal = nearest
	var dir := _next_step(p.pos, goal)
	if dir == Vector2i.ZERO:
		return false
	await _submit(ActionIntent.move(dir))
	return true


func _submit(intent: ActionIntent) -> void:
	var events: Array = main.host.submit_intent(intent)
	if events.is_empty():
		return
	await main.event_player.play(events)
	if main.host.has_pending_floor():
		main.host.commit_pending_floor()
	main._center_camera()
	main.status_bar.refresh()


func _nearest_item() -> Vector2i:
	var best := Vector2i(-1, -1)
	var best_d := 999
	for pos: Vector2i in main.host.map.floor_items.keys():
		var d := Tiles.chebyshev(pos, main.host.player.pos)
		if d < best_d:
			best_d = d
			best = pos
	return best


func _next_step(from: Vector2i, goal: Vector2i) -> Vector2i:
	if from == goal:
		return Vector2i.ZERO
	var map: FloorMap = main.host.map
	var came := { from: Vector2i.ZERO }
	var queue: Array[Vector2i] = [from]
	var head := 0
	while head < queue.size():
		var cur := queue[head]
		head += 1
		for d in Tiles.DIRS_8:
			var n: Vector2i = cur + d
			if came.has(n) or not map.is_walkable(n):
				continue
			if not WorldSnapshot.corner_rule_ok(map, cur, n):
				continue
			came[n] = cur
			if n == goal:
				var node := n
				while came[node] != from:
					node = came[node]
				return node - from
			queue.append(n)
	return Vector2i.ZERO


func _settle(frames: int) -> void:
	for i in frames:
		await process_frame


func _shot(name: String) -> void:
	await RenderingServer.frame_post_draw
	var img := root.get_viewport().get_texture().get_image()
	var path := "%s/%s.png" % [SHOT_DIR, name]
	img.save_png(path)
	_note("截圖 %s（%dx%d）" % [name, img.get_width(), img.get_height()])
