## 三態霧效（架構文件 §5）。
##
##   未探索          → 全黑，什麼都看不到
##   已探索・不可見   → 半透明黑，只看得到地形
##   可見            → 無遮罩
##
## 「已探索但不可見時不顯示怪物與道具」是刻意的：如果玩家能看到記憶中的
## 怪物位置，走廊戰術就失去資訊不對稱，「不知道轉角後面有什麼」的緊張感
## 會整個消失。實體的顯示與否由 EntityView 依 visible 集合決定。
class_name FogRenderer
extends TileMapLayer

const UNEXPLORED := 0
const REMEMBERED := 1


func _ready() -> void:
	tile_set = TileArt.make_tileset(TileArt.FOG_COLORS, false)
	z_index = 5


## 全量重畫。每回合 900 格的 set_cell 對 Godot 來說是可忽略的成本，
## 換來的是不必維護增量更新的正確性。
func redraw(vision: VisionSystem) -> void:
	clear()
	for y in FloorMap.H:
		for x in FloorMap.W:
			var p := Vector2i(x, y)
			if vision.is_visible(p):
				continue                       # 可見 → 不畫遮罩
			if vision.is_explored(p):
				set_cell(p, 0, Vector2i(REMEMBERED, 0))
			else:
				set_cell(p, 0, Vector2i(UNEXPLORED, 0))
