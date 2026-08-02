## 一層樓的完整資料。純資料容器 —— 不含任何引擎節點，可直接序列化存檔。
##
## tiles 與 room_at 用扁平陣列（index = y * W + x）而非巢狀 Array，
## 因為每回合視野計算會大量隨機存取，Packed 陣列快得多也省記憶體。
class_name FloorMap
extends RefCounted

const W := 30
const H := 30

var tiles := PackedByteArray()
## room_at[i] = 該格所屬房間的 zone 索引；通道與牆為 -1。
## 視野系統靠它做 O(1) 的「我在不在房間裡」判定（架構文件 §5）。
var room_at := PackedInt32Array()

var rooms: Dictionary = {}          # zone_idx -> Room
var junctions: Dictionary = {}      # zone_idx -> Vector2i
var edges: Array = []               # [[zone_a, zone_b], ...]

var player_spawn := Vector2i.ZERO
var stairs_down := Vector2i.ZERO
var stairs_up := Vector2i.ZERO

var floor_items: Dictionary = {}    # Vector2i -> ItemInstance
var floor_gold: Dictionary = {}     # Vector2i -> int
var traps: Dictionary = {}          # Vector2i -> String
var monster_spawns: Array = []      # [{ "pos": Vector2i, "id": String }]
var shop_zone := -1

var floor_index := 1
var seed_value := 0


func _init() -> void:
	tiles.resize(W * H)
	tiles.fill(Tiles.WALL)
	room_at.resize(W * H)
	room_at.fill(-1)


func idx(p: Vector2i) -> int:
	return p.y * W + p.x


func in_bounds(p: Vector2i) -> bool:
	return p.x >= 0 and p.x < W and p.y >= 0 and p.y < H


func get_tile(p: Vector2i) -> int:
	if not in_bounds(p):
		return Tiles.WALL
	return tiles[idx(p)]


func set_tile(p: Vector2i, t: int) -> void:
	if in_bounds(p):
		tiles[idx(p)] = t


func is_wall(p: Vector2i) -> bool:
	return get_tile(p) == Tiles.WALL


## 地形層面可否站立。實體佔位另外由 EntityIndex 判斷 —— 兩者刻意分開，
## 因為投擲物、視線、AI 尋路對「牆」和「有怪擋著」的處理並不相同。
func is_walkable(p: Vector2i) -> bool:
	return in_bounds(p) and tiles[idx(p)] != Tiles.WALL


func room_id_at(p: Vector2i) -> int:
	if not in_bounds(p):
		return -1
	return room_at[idx(p)]


func room_at_pos(p: Vector2i) -> Room:
	var rid := room_id_at(p)
	if rid < 0 or not rooms.has(rid):
		return null
	return rooms[rid]


func is_door(p: Vector2i) -> bool:
	for r: Room in rooms.values():
		if r.doors.has(p):
			return true
	return false


## 走廊與門口都算「不在房間裡」—— 視野系統據此切換揭露模式。
func is_corridor(p: Vector2i) -> bool:
	return is_walkable(p) and room_id_at(p) < 0


func walkable_tiles() -> Array[Vector2i]:
	var out: Array[Vector2i] = []
	for y in H:
		for x in W:
			var p := Vector2i(x, y)
			if is_walkable(p):
				out.append(p)
	return out
