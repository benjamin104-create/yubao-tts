## 視野與探索記憶。
##
## 規則（架構文件 §5）：
##   在房間內 → 揭露整間房 + 外圍一圈牆 + 所有門口
##   在通道／門口 → 只看得到周圍 1 格
##
## 「已探索但當前不可見」時只記得地形，不記得怪物與道具 —— 這點很關鍵：
## 若玩家能看到記憶中的怪物位置，走廊戰術就失去資訊不對稱，「不知道轉角
## 後面有什麼」的緊張感會整個消失。
class_name VisionSystem
extends RefCounted

var visible_tiles: Dictionary = {}    # Vector2i -> true
var explored: Dictionary = {}         # Vector2i -> true


func reset() -> void:
	visible_tiles.clear()
	explored.clear()


func is_visible(p: Vector2i) -> bool:
	return visible_tiles.has(p)


func is_explored(p: Vector2i) -> bool:
	return explored.has(p)


## 重算可見集合。回傳 { visible, newly_visible, newly_hidden, newly_explored }，
## 讓 FogRenderer 只需重畫變動的格子。
func recompute(map: FloorMap, from: Vector2i) -> Dictionary:
	var next := {}
	var rid := map.room_id_at(from)

	if rid >= 0:
		var room: Room = map.rooms[rid]
		# 含外圍一圈牆：讓玩家看得出房間形狀，而不是一團浮空的地板
		for y in range(room.top() - 1, room.bottom() + 2):
			for x in range(room.left() - 1, room.right() + 2):
				var p := Vector2i(x, y)
				if map.in_bounds(p):
					next[p] = true
		# 門口必須可見，否則玩家在房裡找不到出口
		for d: Vector2i in room.doors:
			next[d] = true
	else:
		next[from] = true
		for d in Tiles.DIRS_8:
			var p: Vector2i = from + d
			if map.in_bounds(p):
				next[p] = true

	var newly_visible: Array[Vector2i] = []
	var newly_explored: Array[Vector2i] = []
	for p: Vector2i in next.keys():
		if not visible_tiles.has(p):
			newly_visible.append(p)
		if not explored.has(p):
			explored[p] = true
			newly_explored.append(p)

	var newly_hidden: Array[Vector2i] = []
	for p: Vector2i in visible_tiles.keys():
		if not next.has(p):
			newly_hidden.append(p)

	visible_tiles = next
	return {
		"visible": next,
		"newly_visible": newly_visible,
		"newly_hidden": newly_hidden,
		"newly_explored": newly_explored,
	}
