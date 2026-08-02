## 房間。rect 為含端點的實際地板範圍（不含牆）。
class_name Room
extends RefCounted

var zone: int = 0
var rect := Rect2i()

## 通道與房間相接的座標。GDD §1.5「門口禁止斜向進出」靠這份清單做 O(1) 判定，
## 必須在地圖生成階段就填好。
var doors: Array[Vector2i] = []


func _init(p_zone: int = 0, p_rect: Rect2i = Rect2i()) -> void:
	zone = p_zone
	rect = p_rect


func left() -> int:
	return rect.position.x


func top() -> int:
	return rect.position.y


func right() -> int:
	return rect.position.x + rect.size.x - 1


func bottom() -> int:
	return rect.position.y + rect.size.y - 1


func contains(p: Vector2i) -> bool:
	return rect.has_point(p)


func all_tiles() -> Array[Vector2i]:
	var out: Array[Vector2i] = []
	for y in range(top(), bottom() + 1):
		for x in range(left(), right() + 1):
			out.append(Vector2i(x, y))
	return out


func center() -> Vector2i:
	return rect.position + rect.size / 2
