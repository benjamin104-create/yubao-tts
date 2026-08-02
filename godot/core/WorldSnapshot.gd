## P3 結束時的世界唯讀快照。
##
## 這個類別是「同步行動」的技術保證：所有怪物依據同一份快照決策，而不是
## 依據前一隻怪移動後的結果。玩家看到的因此是全體對同一個局面的反應 ——
## 行為可預測，走位戰術才成立（GDD §1.3 / §1.5）。
##
## 約定：AIController 只能讀這裡，不得寫入任何世界狀態。
class_name WorldSnapshot
extends RefCounted

var player_pos := Vector2i.ZERO
var player: Entity = null

var _map: FloorMap
var _occupied: Dictionary = {}     # Vector2i -> Entity


func _init(map: FloorMap, index: EntityIndex, p: Entity) -> void:
	_map = map
	player = p
	player_pos = p.pos
	for e: Entity in index.all():
		if e.is_alive():
			_occupied[e.pos] = e


func is_walkable(p: Vector2i) -> bool:
	return _map.is_walkable(p)


func entity_at(p: Vector2i) -> Entity:
	return _occupied.get(p)


func occupied(p: Vector2i) -> bool:
	return _occupied.has(p)


func room_id_at(p: Vector2i) -> int:
	return _map.room_id_at(p)


func is_door(p: Vector2i) -> bool:
	return _map.is_door(p)


## 斜向牆角規則（GDD §1.5）。對玩家與怪物完全對稱 —— 這是走廊戰術成立的
## 基礎，任何一方例外都會讓整套戰術崩掉。
##   1. 不可切牆角：斜移時兩個正交鄰格都必須非牆
##   2. 門口禁止任何斜向進出
static func corner_rule_ok(map: FloorMap, from: Vector2i, to: Vector2i) -> bool:
	var d := to - from
	if not Tiles.is_diagonal(d):
		return true
	if map.is_wall(Vector2i(to.x, from.y)) or map.is_wall(Vector2i(from.x, to.y)):
		return false
	if map.is_door(from) or map.is_door(to):
		return false
	return true


func can_step(from: Vector2i, to: Vector2i) -> bool:
	if not is_walkable(to) or occupied(to):
		return false
	return corner_rule_ok(_map, from, to)


## 直線視線是否無阻擋。用於 RANGED 的射擊條件與 CHASER 的索敵。
## blocked_by_entities = true 時，路徑上有其他實體也算擋住。
func line_clear(a: Vector2i, b: Vector2i, blocked_by_entities := false) -> bool:
	if not Tiles.is_aligned(a, b):
		return false
	var step := Tiles.step_dir(a, b)
	var cur := a + step
	while cur != b:
		if _map.is_wall(cur):
			return false
		if blocked_by_entities and _occupied.has(cur):
			return false
		cur += step
	return true


## 怪物能否看見玩家。
## 同房間 → 必定發現（Mystery Dungeon 的傳統，也讓「進房間」成為明確的
## 決策點）；走廊 → 需在 sight 格內且視線無阻擋。
func can_see_player(from: Vector2i, sight: int) -> bool:
	var rid := room_id_at(from)
	if rid >= 0 and rid == room_id_at(player_pos):
		return true
	if Tiles.chebyshev(from, player_pos) > sight:
		return false
	return line_clear(from, player_pos)


func map() -> FloorMap:
	return _map
