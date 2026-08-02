## 30x30 / 3x3 區域切割的房間與通道生成器。
##
## 演算法說明與虛擬碼：docs/roguelike_mapgen.md
## 參考實作（Python，已壓測 2000 seed）：docs/roguelike_data/mapgen_reference.py
##
## 這份 GDScript 是上述參考實作的逐行移植。改演算法時請兩邊同步，
## 因為 Python 版是拿來跑大量壓力測試與平衡模擬的。
class_name MapGenerator
extends RefCounted

const ZONE_COLS := 3
const ZONE_ROWS := 3
const ZONE_W := FloorMap.W / ZONE_COLS      # 10
const ZONE_H := FloorMap.H / ZONE_ROWS      # 10

## 區域內縮量。這 1 格保證了三件事（見 mapgen 文件 §2）：
##   1. 相鄰區域的房間必有間隙  2. 通道轉折線必有合法位置  3. 地圖外框必為牆
const MARGIN := 1
const ROOM_MIN := 3
const MIN_ROOMS := 6
const MAX_EMPTY_ZONES := 3
const MAX_ATTEMPTS := 5

enum { RIGHT, LEFT, DOWN, UP }


## 依樓層調整環路機率：越深層死路越多，被追上時越難逃。
## 這是全生成器最有效的難度旋鈕 —— 不動任何數值，只改地圖拓樸。
static func loop_chance_for(floor_index: int) -> float:
	return clampf(0.25 - floor_index * 0.005, 0.08, 0.25)


static func generate(run_seed: int, floor_index: int, db) -> FloorMap:
	for attempt in MAX_ATTEMPTS:
		var rng := DeterministicRng.new(
			DeterministicRng.hash64([run_seed, floor_index, attempt]))
		var map := _try_generate(rng, floor_index, db)
		if map != null:
			map.floor_index = floor_index
			map.seed_value = run_seed
			return map
	return _fallback_floor(floor_index)


static func _try_generate(rng: DeterministicRng, floor_index: int, db) -> FloorMap:
	var map := FloorMap.new()
	var zones := _split_zones()

	var placed := _place_rooms(rng, zones)
	var rooms: Dictionary = placed["rooms"]
	var junctions: Dictionary = placed["junctions"]

	for r: Room in rooms.values():
		for p in r.all_tiles():
			map.set_tile(p, Tiles.ROOM_FLOOR)
			map.room_at[map.idx(p)] = r.zone

	var edges := _build_connection_graph(rng, zones, floor_index)
	_carve_corridors(rng, map, zones, rooms, junctions, edges)

	if not _verify_connectivity(map):
		return null

	map.rooms = rooms
	map.junctions = junctions
	map.edges = edges
	_place_objects(rng, map, floor_index, db)

	# 最終保險：樓梯必須從出生點可達
	if not _flood_fill_4dir(map, map.player_spawn).has(map.stairs_down):
		return null
	return map


# ---------------------------------------------------------------- Step 1-2

static func _split_zones() -> Array:
	var zones := []
	for zy in ZONE_ROWS:
		for zx in ZONE_COLS:
			zones.append({
				"idx": zy * ZONE_COLS + zx, "zx": zx, "zy": zy,
				"x0": zx * ZONE_W, "y0": zy * ZONE_H,
				"x1": zx * ZONE_W + ZONE_W - 1, "y1": zy * ZONE_H + ZONE_H - 1,
			})
	return zones


# ---------------------------------------------------------------- Step 3

static func _place_rooms(rng: DeterministicRng, zones: Array) -> Dictionary:
	var empty_count := mini(rng.randi_range(0, MAX_EMPTY_ZONES), zones.size() - MIN_ROOMS)
	var all_idx := []
	for z in zones:
		all_idx.append(z["idx"])
	var empty_set := {}
	for i in rng.sample(all_idx, empty_count):
		empty_set[i] = true

	var rooms := {}
	var junctions := {}

	for z in zones:
		var ux0: int = z["x0"] + MARGIN
		var ux1: int = z["x1"] - MARGIN
		var uy0: int = z["y0"] + MARGIN
		var uy1: int = z["y1"] - MARGIN

		if empty_set.has(z["idx"]):
			# 空區域退化為通道交會點，但仍留在連通圖上 —— 這是「所有房間皆可
			# 到達」最省事的保證：9 個節點永遠存在，生成樹必然涵蓋全圖。
			junctions[z["idx"]] = Vector2i(
				rng.randi_range(ux0 + 1, ux1 - 1),
				rng.randi_range(uy0 + 1, uy1 - 1))
			continue

		var max_w := ux1 - ux0 + 1
		var max_h := uy1 - uy0 + 1
		var w := rng.randi_range(ROOM_MIN, max_w - 1)   # 留 1 格給通道轉圜
		var h := rng.randi_range(ROOM_MIN, max_h - 1)
		var x := rng.randi_range(ux0, ux1 - w + 1)
		var y := rng.randi_range(uy0, uy1 - h + 1)
		rooms[z["idx"]] = Room.new(z["idx"], Rect2i(x, y, w, h))

	return { "rooms": rooms, "junctions": junctions }


# ---------------------------------------------------------------- Step 4

static func _build_connection_graph(
		rng: DeterministicRng, zones: Array, floor_index: int) -> Array:
	var candidates := []
	for a in zones:
		for b in zones:
			if a["idx"] < b["idx"] \
					and absi(a["zx"] - b["zx"]) + absi(a["zy"] - b["zy"]) == 1:
				candidates.append([a["idx"], b["idx"]])

	rng.shuffle(candidates)

	# (1) 隨機生成樹 —— 連通性由構造保證，不靠事後重試
	var parent := []
	parent.resize(zones.size())
	for i in zones.size():
		parent[i] = i

	var tree := []
	var rest := []
	for e in candidates:
		if _uf_union(parent, e[0], e[1]):
			tree.append(e)
		else:
			rest.append(e)
	assert(tree.size() == zones.size() - 1, "9 節點的生成樹必有 8 條邊")

	# (2) 環路注入 —— 避免「死路 = 必死」，讓繞圈甩開追兵可行
	var p := loop_chance_for(floor_index)
	var out := tree.duplicate()
	for e in rest:
		if rng.chance(p):
			out.append(e)
	return out


static func _uf_find(parent: Array, a: int) -> int:
	var x := a
	while parent[x] != x:
		parent[x] = parent[parent[x]]
		x = parent[x]
	return x


static func _uf_union(parent: Array, a: int, b: int) -> bool:
	var ra := _uf_find(parent, a)
	var rb := _uf_find(parent, b)
	if ra == rb:
		return false
	parent[ra] = rb
	return true


# ---------------------------------------------------------------- Step 5

## 回傳節點朝指定方向的出口座標。房間 → 牆外 1 格；交會點 → 自身。
static func _node_port(rng: DeterministicRng, rooms: Dictionary,
		junctions: Dictionary, zone_idx: int, side: int) -> Vector2i:
	if junctions.has(zone_idx):
		return junctions[zone_idx]
	var r: Room = rooms[zone_idx]
	match side:
		RIGHT:
			return Vector2i(r.right() + 1, rng.randi_range(r.top(), r.bottom()))
		LEFT:
			return Vector2i(r.left() - 1, rng.randi_range(r.top(), r.bottom()))
		DOWN:
			return Vector2i(rng.randi_range(r.left(), r.right()), r.bottom() + 1)
		_:
			return Vector2i(rng.randi_range(r.left(), r.right()), r.top() - 1)


static func _carve_corridors(rng: DeterministicRng, map: FloorMap, zones: Array,
		rooms: Dictionary, junctions: Dictionary, edges: Array) -> void:
	for e in edges:
		var za: Dictionary = zones[e[0]]
		var zb: Dictionary = zones[e[1]]

		if za["zy"] == zb["zy"]:
			# 水平連接：出房間 → 走到轉折線 → 垂直平移 → 進另一間房
			var l: Dictionary = za if za["zx"] < zb["zx"] else zb
			var r: Dictionary = zb if za["zx"] < zb["zx"] else za
			var pa := _node_port(rng, rooms, junctions, l["idx"], RIGHT)
			var pb := _node_port(rng, rooms, junctions, r["idx"], LEFT)
			# MARGIN 保證 pa.x < pb.x，randi_range 永遠有解
			var mid_x := rng.randi_range(pa.x, pb.x)
			_carve_h(map, pa.x, mid_x, pa.y)
			_carve_v(map, pa.y, pb.y, mid_x)
			_carve_h(map, mid_x, pb.x, pb.y)
			_register_door(rooms, l["idx"], pa)
			_register_door(rooms, r["idx"], pb)
		else:
			var t: Dictionary = za if za["zy"] < zb["zy"] else zb
			var b: Dictionary = zb if za["zy"] < zb["zy"] else za
			var pa := _node_port(rng, rooms, junctions, t["idx"], DOWN)
			var pb := _node_port(rng, rooms, junctions, b["idx"], UP)
			var mid_y := rng.randi_range(pa.y, pb.y)
			_carve_v(map, pa.y, mid_y, pa.x)
			_carve_h(map, pa.x, pb.x, mid_y)
			_carve_v(map, mid_y, pb.y, pb.x)
			_register_door(rooms, t["idx"], pa)
			_register_door(rooms, b["idx"], pb)


## 只覆蓋牆。通道交叉時自然形成十字路口；經過房間邊緣時不會把房間地板
## 改成通道 tile —— 視野系統的 room_at 判定不能被通道汙染。
static func _carve_h(map: FloorMap, x_a: int, x_b: int, y: int) -> void:
	for x in range(mini(x_a, x_b), maxi(x_a, x_b) + 1):
		var p := Vector2i(x, y)
		if map.get_tile(p) == Tiles.WALL:
			map.set_tile(p, Tiles.CORRIDOR)


static func _carve_v(map: FloorMap, y_a: int, y_b: int, x: int) -> void:
	for y in range(mini(y_a, y_b), maxi(y_a, y_b) + 1):
		var p := Vector2i(x, y)
		if map.get_tile(p) == Tiles.WALL:
			map.set_tile(p, Tiles.CORRIDOR)


static func _register_door(rooms: Dictionary, zone_idx: int, p: Vector2i) -> void:
	if rooms.has(zone_idx):
		var r: Room = rooms[zone_idx]
		if not r.doors.has(p):
			r.doors.append(p)


# ---------------------------------------------------------------- Step 6

## 必須用 4 向。GDD §1.5 禁止斜向切牆角 —— 用 8 向驗證會放行「只有斜向能
## 通過」的地圖，生成器覺得合格但玩家實際走不過去，而且只在特定 seed 出現。
static func _flood_fill_4dir(map: FloorMap, start: Vector2i) -> Dictionary:
	var seen := { start: true }
	var queue: Array[Vector2i] = [start]
	var head := 0
	while head < queue.size():
		var cur := queue[head]
		head += 1
		for d in Tiles.DIRS_4:
			var n := cur + d
			if map.is_walkable(n) and not seen.has(n):
				seen[n] = true
				queue.append(n)
	return seen


static func _verify_connectivity(map: FloorMap) -> bool:
	var walkable := map.walkable_tiles()
	if walkable.is_empty():
		return false
	return _flood_fill_4dir(map, walkable[0]).size() == walkable.size()


# ---------------------------------------------------------------- Step 7

static func _place_objects(rng: DeterministicRng, map: FloorMap,
		f: int, db) -> void:
	var room_list := map.rooms.values()
	var spawn_room: Room = rng.choice(room_list)
	map.player_spawn = _rand_tile_in(rng, spawn_room, {})
	map.stairs_up = map.player_spawn

	# 下行樓梯放在區域圖距離最遠的前 3 個房間中隨機。
	# 若可能就在出生點旁邊，玩家會養成「落地先找樓梯就走」的退化玩法。
	var dist := _bfs_zone_distance(map.edges, spawn_room.zone)
	var ranked := room_list.duplicate()
	ranked.sort_custom(func(a: Room, b: Room) -> bool:
		return dist.get(a.zone, 0) > dist.get(b.zone, 0))
	var cands := []
	for r: Room in ranked:
		if r.zone != spawn_room.zone:
			cands.append(r)
	cands = cands.slice(0, 3)
	if cands.is_empty():
		cands = [ranked[0]]
	var stairs_room: Room = rng.choice(cands)
	map.stairs_down = _rand_tile_in(rng, stairs_room, { map.player_spawn: true })
	map.set_tile(map.stairs_down, Tiles.STAIRS_DOWN)

	var occupied := { map.player_spawn: true, map.stairs_down: true }

	# 密度公式（GDD §4.2）
	var n_items := rng.randi_range(3, 6) + f / 8
	var n_gold := rng.randi_range(1, 3)
	var n_traps := rng.randi_range(1, 2) + f / 5
	var n_monsters := clampi(2 + f / 3, 2, 12)

	# 每層保證至少 1 份食物。玩家不會被生成器直接餓死 —— 飢餓應該來自
	# 「探索太久」這個玩家的選擇，而不是「這層剛好沒生食物」的運氣。
	var food_pos := _free_tile(rng, map, occupied, 0)
	var food_def: Dictionary = db.roll_category(rng, "food", f)
	if food_pos != Vector2i(-1, -1) and not food_def.is_empty():
		map.floor_items[food_pos] = db.make_instance(food_def, rng)

	for i in n_items:
		var p := _free_tile(rng, map, occupied, 0)
		var def: Dictionary = db.roll_item(rng, f)
		if p != Vector2i(-1, -1) and not def.is_empty():
			map.floor_items[p] = db.make_instance(def, rng)
	for i in n_gold:
		var p := _free_tile(rng, map, occupied, 0)
		if p != Vector2i(-1, -1):
			map.floor_gold[p] = rng.randi_range(10, 40) * (1 + f / 3)
	for i in n_traps:
		var p := _free_tile(rng, map, occupied, 0)
		if p != Vector2i(-1, -1):
			map.traps[p] = "trap_generic"
	var spawned := 0
	while spawned < n_monsters:
		# 絕不在玩家 3 格內生成 —— 開局被貼臉是純粹的挫折，不是難度
		var p := _free_tile(rng, map, occupied, 3, map.player_spawn)
		var def: Dictionary = db.roll_monster(rng, f)
		if p == Vector2i(-1, -1) or def.is_empty():
			break
		map.monster_spawns.append({ "pos": p, "id": def["id"] })
		spawned += 1

		# PACK：成群出現。疾風狼單隻不可怕，三隻倍速狼才是問題
		var pack := {}
		for t: Dictionary in def.get("traits", []):
			if t.get("type", "") == "PACK":
				pack = t
		if pack.is_empty():
			continue
		var extra := rng.randi_range(int(pack.get("min", 2)), int(pack.get("max", 3))) - 1
		for k in extra:
			if spawned >= n_monsters:
				break
			# 同伴生在本體旁邊，才叫成群
			var near := _free_tile_near(rng, map, occupied, p)
			if near == Vector2i(-1, -1):
				break
			map.monster_spawns.append({ "pos": near, "id": def["id"] })
			spawned += 1

	# 商店必須恰有 1 個門口 —— 這是「不付錢就跑會被店主堵住」的前提
	if f >= 3 and rng.chance(0.08):
		var single := []
		for r: Room in room_list:
			if r.doors.size() == 1:
				single.append(r)
		if not single.is_empty():
			map.shop_zone = (rng.choice(single) as Room).zone


static func _rand_tile_in(rng: DeterministicRng, room: Room,
		exclude: Dictionary) -> Vector2i:
	for i in 100:
		var p := Vector2i(rng.randi_range(room.left(), room.right()),
				rng.randi_range(room.top(), room.bottom()))
		if not exclude.has(p):
			return p
	return room.rect.position


static func _free_tile(rng: DeterministicRng, map: FloorMap, occupied: Dictionary,
		min_dist: int, from: Vector2i = Vector2i.ZERO) -> Vector2i:
	for i in 200:
		var p := Vector2i(rng.randi_range(0, FloorMap.W - 1),
				rng.randi_range(0, FloorMap.H - 1))
		if not map.is_walkable(p) or occupied.has(p):
			continue
		if min_dist > 0 and Tiles.chebyshev(p, from) < min_dist:
			continue
		occupied[p] = true
		return p
	return Vector2i(-1, -1)


## 在 origin 周圍 2 格內找一個空位，給 PACK 的同伴用。
static func _free_tile_near(rng: DeterministicRng, map: FloorMap,
		occupied: Dictionary, origin: Vector2i) -> Vector2i:
	var candidates: Array[Vector2i] = []
	for dy in range(-2, 3):
		for dx in range(-2, 3):
			var p := origin + Vector2i(dx, dy)
			if map.is_walkable(p) and not occupied.has(p):
				candidates.append(p)
	if candidates.is_empty():
		return Vector2i(-1, -1)
	var chosen: Vector2i = rng.choice(candidates)
	occupied[chosen] = true
	return chosen


static func _bfs_zone_distance(edges: Array, start_zone: int) -> Dictionary:
	var adj := {}
	for e in edges:
		adj.get_or_add(e[0], []).append(e[1])
		adj.get_or_add(e[1], []).append(e[0])
	var dist := { start_zone: 0 }
	var queue := [start_zone]
	var head := 0
	while head < queue.size():
		var z: int = queue[head]
		head += 1
		for n in adj.get(z, []):
			if not dist.has(n):
				dist[n] = dist[z] + 1
				queue.append(n)
	return dist


# ---------------------------------------------------------------- 保底

## 生成連續失敗時的保底樓層：單一大房間。
## 寧可無聊，也絕不讓玩家卡在無法通關的圖上。
static func _fallback_floor(floor_index: int) -> FloorMap:
	var map := FloorMap.new()
	var room := Room.new(0, Rect2i(2, 2, FloorMap.W - 4, FloorMap.H - 4))
	for p in room.all_tiles():
		map.set_tile(p, Tiles.ROOM_FLOOR)
		map.room_at[map.idx(p)] = 0
	map.rooms = { 0: room }
	map.player_spawn = Vector2i(3, 3)
	map.stairs_up = map.player_spawn
	map.stairs_down = Vector2i(FloorMap.W - 4, FloorMap.H - 4)
	map.set_tile(map.stairs_down, Tiles.STAIRS_DOWN)
	map.floor_index = floor_index
	return map
