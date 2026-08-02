## 實體的雙索引：依 id 查、依座標查。
##
## 座標索引讓「這格有沒有東西」變成 O(1)。回合制每回合要對所有怪物做
## 多次佔位判定，線性掃描在滿場 12 隻怪時會變成明顯的浪費。
class_name EntityIndex
extends RefCounted

var _by_id: Dictionary = {}      # int -> Entity
var _by_pos: Dictionary = {}     # Vector2i -> Entity
var _next_id := 1


func next_id() -> int:
	var i := _next_id
	_next_id += 1
	return i


func add(e: Entity) -> void:
	_by_id[e.id] = e
	_by_pos[e.pos] = e


func remove(e: Entity) -> void:
	_by_id.erase(e.id)
	if _by_pos.get(e.pos) == e:
		_by_pos.erase(e.pos)


## 移動時務必走這個方法，直接改 entity.pos 會讓座標索引失效。
func move_entity(e: Entity, to: Vector2i) -> void:
	if _by_pos.get(e.pos) == e:
		_by_pos.erase(e.pos)
	e.pos = to
	_by_pos[to] = e


func at(p: Vector2i) -> Entity:
	return _by_pos.get(p)


func occupied(p: Vector2i) -> bool:
	return _by_pos.has(p)


func by_id(i: int) -> Entity:
	return _by_id.get(i)


func all() -> Array:
	return _by_id.values()


## 只回傳存活的怪物 —— AI 與快照都只該看得到活著的實體。
## 死亡結算請用 all_monsters()，否則屍體會被這個過濾器藏起來、
## 永遠不會被移除也不會給經驗值。
func monsters() -> Array:
	var out := []
	for e: Entity in _by_id.values():
		if not e.is_player and e.is_alive():
			out.append(e)
	return out


## 含屍體的完整怪物清單，供 P8 死亡結算使用。
func all_monsters() -> Array:
	var out := []
	for e: Entity in _by_id.values():
		if not e.is_player:
			out.append(e)
	return out


func monster_count() -> int:
	return monsters().size()


func clear() -> void:
	_by_id.clear()
	_by_pos.clear()
