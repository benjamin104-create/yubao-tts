## 錄製一段完整試玩，每回合存一張畫面。
##
##   xvfb-run -a --server-args="-screen 0 960x720x24" \
##     godot --path godot --script res://tests/play_demo.gd
##
## 產出 user://frames/NNNN.png，之後用 tools/make_gif.py 組成動畫與接觸表。
## 固定 seed，所以同一版程式碼永遠錄出同一段 —— 改動之後重錄可以直接比對。
extends SceneTree

const FRAME_DIR := "user://frames"
const DEMO_SEED := 424242
const MAX_TURNS := 150

var main: Node2D
var _frame := 0
var _moments: Array[String] = []


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	_reset_dir(FRAME_DIR)
	main = load("res://main/Main.tscn").instantiate()
	root.add_child(main)
	await process_frame
	main.host.start_run(DEMO_SEED)
	main._on_floor_changed(1)
	await _settle(6)
	await _frame_shot("開場：出生房間，霧效只揭露這一間")

	var turns := 0
	while turns < MAX_TURNS and not main.host.is_game_over:
		var label := await _play_one_turn()
		turns += 1
		await _frame_shot(label)

		# 中途開一次背包與腳下選單，讓 UI 也入鏡
		if turns == 40:
			main.inventory_ui.toggle()
			await _settle(6)
			await _frame_shot("背包：未鑑定道具只顯示外觀名")
			await _frame_shot("")
			main.inventory_ui.toggle()
			await _settle(4)

	_note("結束：%dF，Lv %d，HP %d/%d，飽足 %.1f%%，%d 回合，%d 張畫面" % [
		main.host.floor_index, main.host.player.level, main.host.player.hp,
		main.host.player.max_hp, main.host.player.satiety / 1000.0,
		main.host.turns.turn_count, _frame])
	await _frame_shot("結束")

	print("\n".join(_moments))
	print("FRAME_DIR=%s" % ProjectSettings.globalize_path(FRAME_DIR))
	quit(0)


## 回傳這一回合值得標註的事件說明（空字串代表普通移動）。
func _play_one_turn() -> String:
	var host: GameHost = main.host
	var p := host.player

	# 低血且身上有已鑑定的回復草 → 喝掉
	if p.hp * 5 < p.max_hp * 2:
		for it: ItemInstance in p.inventory.slots:
			if it.def_id == "hrb_heal" and host.ident.is_identified(it.def_id):
				await _submit(ActionIntent.use(it, ActionIntent.Verb.EAT))
				return "低血喝下回復草"

	# 餓了就吃
	if p.satiety < 30000:
		var food := p.inventory.first_by_category("food")
		if food != null:
			await _submit(ActionIntent.use(food, ActionIntent.Verb.EAT))
			return "進食，飽足度回升"

	# 相鄰有怪就打
	for d in Tiles.DIRS_8:
		var e := host.entities.at(p.pos + d)
		if e != null and not e.is_player \
				and WorldSnapshot.corner_rule_ok(host.map, p.pos, p.pos + d):
			var before_count := host.entities.monster_count()
			await _submit(ActionIntent.move(d))
			if host.entities.monster_count() < before_count:
				return "擊倒 %s" % e.display_name
			return "與 %s 交戰" % e.display_name

	# 視野內有遠處的怪 → 丟東西試試（同時驗證投擲與鑑定）
	var visible_far := _visible_aligned_monster()
	if visible_far != null and p.inventory.size() > 12:
		var ammo := _throwable()
		if ammo != null:
			await _submit(ActionIntent.throw_item(ammo,
				Tiles.step_dir(p.pos, visible_far.pos)))
			return "朝 %s 投擲道具" % visible_far.display_name

	# 腳下有東西：有空間就撿，沒空間就直接用
	if host.map.floor_items.has(p.pos):
		if p.inventory.has_space():
			await _submit(ActionIntent.pickup())
			return "撿起腳下的道具"
		var ground: ItemInstance = host.map.floor_items[p.pos]
		if ground.category in ["food", "herb"]:
			await _submit(ActionIntent.use_ground(ground, ActionIntent.Verb.EAT))
			return "背包滿了 → 不撿起直接使用"

	# 站在樓梯上就下樓
	if p.pos == host.map.stairs_down:
		await _submit(ActionIntent.descend())
		return "下到地下 %d 層" % host.floor_index

	var goal := host.map.stairs_down
	var nearest := _nearest_item()
	if nearest != Vector2i(-1, -1) and p.inventory.has_space():
		goal = nearest
	var dir := _next_step(p.pos, goal)
	if dir == Vector2i.ZERO:
		await _submit(ActionIntent.wait())
		return ""
	await _submit(ActionIntent.move(dir))
	return ""


func _visible_aligned_monster() -> MonsterEntity:
	for m: MonsterEntity in main.host.visible_monsters():
		var d := Tiles.chebyshev(m.pos, main.host.player.pos)
		if d >= 2 and d <= 6 and Tiles.is_aligned(main.host.player.pos, m.pos):
			return m
	return null


func _throwable() -> ItemInstance:
	for it: ItemInstance in main.host.player.inventory.slots:
		if it == main.host.player.weapon or it == main.host.player.shield:
			continue
		if it.category in ["herb", "scroll"]:
			return it
	return null


func _submit(intent: ActionIntent) -> void:
	var events: Array = main.host.submit_intent(intent)
	if events.is_empty():
		return
	await main.event_player.play(events)
	if main.host.has_pending_floor():
		main.host.commit_pending_floor()
	main._center_camera()
	main.status_bar.refresh()
	await _settle(8)      # 等位移插值與飄字播完，畫面才是穩定狀態


# ---------------------------------------------------------------- 工具

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


func _reset_dir(path: String) -> void:
	var dir := DirAccess.open(path)
	if dir != null:
		for f in dir.get_files():
			dir.remove(f)
	else:
		DirAccess.make_dir_recursive_absolute(path)


func _note(text: String) -> void:
	_moments.append("  " + text)


func _frame_shot(label: String) -> void:
	await RenderingServer.frame_post_draw
	var img := root.get_viewport().get_texture().get_image()
	img.save_png("%s/%04d.png" % [FRAME_DIR, _frame])
	if label != "":
		_note("frame %04d  %s" % [_frame, label])
	_frame += 1
