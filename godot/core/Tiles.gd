## 地形常數與方向工具。
##
## 純常數類別，不持有狀態。放在 core/ 最底層，任何模組都可以引用。
class_name Tiles
extends RefCounted

enum { WALL, ROOM_FLOOR, CORRIDOR, STAIRS_DOWN, STAIRS_UP }

const DIRS_4: Array[Vector2i] = [
	Vector2i(1, 0), Vector2i(-1, 0), Vector2i(0, 1), Vector2i(0, -1),
]

## 8 方向。順序固定 —— AI 的 fallback 方向掃描依賴這個順序，換順序會改變行為。
const DIRS_8: Array[Vector2i] = [
	Vector2i(1, 0), Vector2i(1, 1), Vector2i(0, 1), Vector2i(-1, 1),
	Vector2i(-1, 0), Vector2i(-1, -1), Vector2i(0, -1), Vector2i(1, -1),
]


static func is_diagonal(d: Vector2i) -> bool:
	return d.x != 0 and d.y != 0


## 切比雪夫距離 —— 8 方向網格上的實際步數。
static func chebyshev(a: Vector2i, b: Vector2i) -> int:
	return maxi(absi(a.x - b.x), absi(a.y - b.y))


## 朝目標前進 1 步的方向（允許斜向）。
static func step_dir(from: Vector2i, to: Vector2i) -> Vector2i:
	return Vector2i(signi(to.x - from.x), signi(to.y - from.y))


## 兩點是否落在同一直線或正對角線上 —— RANGED 型怪物的射擊條件。
static func is_aligned(a: Vector2i, b: Vector2i) -> bool:
	if a == b:
		return false
	var d := b - a
	return d.x == 0 or d.y == 0 or absi(d.x) == absi(d.y)
