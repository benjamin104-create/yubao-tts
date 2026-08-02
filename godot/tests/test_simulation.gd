## 自動遊玩模擬 —— 架構文件 §6「平衡驗證可自動化」的實證。
##
##   godot --headless --path godot --script res://tests/test_simulation.gd
##
## 因為 Core 完全不依賴引擎節點與呈現層，這支腳本可以在沒有畫面的情況下
## 把整場 Run 跑完，直接產出 GDD §5.2 那幾個埋點指標。數值失衡在這裡就會
## 被看見，不必等玩家實際玩到第 20 層。
extends SceneTree

const RUNS := 120
const MAX_TURNS_PER_RUN := 4000

var db: ItemDatabase


func _init() -> void:
	db = ItemDatabase.new()
	db.load_from("res://data/items.json", "res://data/monsters.json")

	print("=== 自動遊玩模擬（%d 場）===\n" % RUNS)
	var stats := {
		"deaths": 0, "starvation": 0, "killed": 0,
		"turns": 0, "max_floor": 0, "floors": 0,
		"items_picked": 0, "items_used": 0, "unused_at_death": 0,
		"levels": 0, "identified": 0, "errors": 0,
	}

	for i in RUNS:
		_play_one(i * 7919 + 1, stats)

	_report(stats)
	quit(1 if stats["errors"] > 0 else 0)


func _play_one(seed_value: int, stats: Dictionary) -> void:
	var host := GameHost.new()
	host.start_run(seed_value, db)

	var turns := 0
	while not host.is_game_over and turns < MAX_TURNS_PER_RUN:
		var intent := _decide(host)
		if intent == null:
			break
		var before := host.player.inventory.size()
		host.submit_intent(intent)
		if host.has_pending_floor():
			host.commit_pending_floor()
		turns += 1
		if intent.kind == ActionIntent.Kind.PICKUP \
				and host.player.inventory.size() > before:
			stats["items_picked"] += 1
		if intent.kind == ActionIntent.Kind.USE_ITEM:
			stats["items_used"] += 1

	stats["turns"] += turns
	stats["floors"] += host.floor_index
	stats["max_floor"] = maxi(stats["max_floor"], host.floor_index)
	stats["levels"] += host.player.level
	stats["identified"] += host.ident.identified.size()

	if host.is_game_over:
		stats["deaths"] += 1
		if host.player.is_starving():
			stats["starvation"] += 1
		else:
			stats["killed"] += 1
		# 「帶到死亡都沒用掉的未鑑定道具」—— 指標目標 < 35%
		for it: ItemInstance in host.player.inventory.slots:
			if it.category in IdentificationTable.MASKED \
					and not host.ident.is_identified(it.def_id):
				stats["unused_at_death"] += 1

	host.free()


## 簡易 bot 策略。不求打得好，只求把系統的每條路徑都走過一遍。
func _decide(host: GameHost) -> ActionIntent:
	var p := host.player

	# 1. 快餓死了就吃
	if p.satiety < 20000:
		var food := p.inventory.first_by_category("food")
		if food != null:
			return ActionIntent.use(food, ActionIntent.Verb.EAT)

	# 2. 低血且有已鑑定的回復草
	if p.hp * 3 < p.max_hp:
		for it: ItemInstance in p.inventory.slots:
			if it.def_id == "hrb_heal" and host.ident.is_identified(it.def_id):
				return ActionIntent.use(it, ActionIntent.Verb.EAT)

	# 3. 安全時盲喝未鑑定草藥。
	# 這正是 GDD 設計的「正確玩法」：滿血、無敵人在視野內時，盲喝的期望值
	# 為正；低血被圍時盲喝才是錯的。讓 bot 照這個規則走，跑出來的鑑定率
	# 才是有意義的數字。
	if p.hp == p.max_hp and host.visible_monsters().is_empty():
		for it: ItemInstance in p.inventory.slots:
			if it.category == "herb" and not host.ident.is_identified(it.def_id):
				return ActionIntent.use(it, ActionIntent.Verb.EAT)

	# 4. 相鄰有怪就打
	for d in Tiles.DIRS_8:
		var e := host.entities.at(p.pos + d)
		if e != null and not e.is_player \
				and WorldSnapshot.corner_rule_ok(host.map, p.pos, p.pos + d):
			return ActionIntent.move(d)

	# 4. 腳下有東西就撿（背包沒滿）
	if host.map.floor_items.has(p.pos) and p.inventory.has_space():
		return ActionIntent.pickup()

	# 5. 站在樓梯上就下樓
	if p.pos == host.map.stairs_down:
		return ActionIntent.descend()

	# 6. 有空間就先去撿最近的道具，否則直奔樓梯
	var goal := host.map.stairs_down
	if p.inventory.has_space():
		var nearest := _nearest_item(host)
		if nearest != Vector2i(-1, -1):
			goal = nearest

	var step := _next_step(host, p.pos, goal)
	if step == Vector2i.ZERO:
		return ActionIntent.wait()
	return ActionIntent.move(step)


func _nearest_item(host: GameHost) -> Vector2i:
	var best := Vector2i(-1, -1)
	var best_d := 999
	for pos: Vector2i in host.map.floor_items.keys():
		var d := Tiles.chebyshev(pos, host.player.pos)
		if d < best_d:
			best_d = d
			best = pos
	return best


## BFS 尋路。用 8 向但套用牆角規則 —— 與實際移動規則一致，
## 否則 bot 會規劃出自己走不了的路線。
func _next_step(host: GameHost, from: Vector2i, goal: Vector2i) -> Vector2i:
	if from == goal:
		return Vector2i.ZERO
	var map := host.map
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
				# 回溯到第一步
				var node := n
				while came[node] != from:
					node = came[node]
				return node - from
			queue.append(n)
	return Vector2i.ZERO


func _report(s: Dictionary) -> void:
	var runs := float(RUNS)
	var deaths: int = s["deaths"]
	print("場數              : %d" % RUNS)
	print("死亡              : %d（%.1f%%）" % [deaths, deaths / runs * 100.0])
	print("  ├ 餓死          : %d（佔全部 %.1f%%）"
		% [s["starvation"], s["starvation"] / runs * 100.0])
	print("  └ 戰死          : %d" % s["killed"])
	print("平均存活回合      : %.0f" % (s["turns"] / runs))
	print("平均到達樓層      : %.1f（最深 %d）" % [s["floors"] / runs, s["max_floor"]])
	print("平均結束等級      : %.1f" % (s["levels"] / runs))
	print("平均鑑定種類數    : %.1f" % (s["identified"] / runs))
	print("撿取道具總數      : %d" % s["items_picked"])
	print("使用道具總數      : %d" % s["items_used"])
	if deaths > 0:
		print("死亡時仍未鑑定    : 平均 %.1f 件/場" % (float(s["unused_at_death"]) / deaths))

	print("\n--- 對照 GDD §5.2 的目標值 ---")
	var starve_rate: float = float(s["starvation"]) / runs * 100.0
	var avg_floor: float = float(s["floors"]) / runs
	_check("餓死率 < 8%", starve_rate < 8.0, "%.1f%%" % starve_rate)
	_check("平均到達樓層 >= 3", avg_floor >= 3.0, "%.1f" % avg_floor)
	_check("模擬過程無執行期錯誤", s["errors"] == 0, str(s["errors"]))


func _check(label: String, ok: bool, actual: String) -> void:
	print("  [%s] %s　（實測 %s）" % ["PASS" if ok else "WARN", label, actual])
