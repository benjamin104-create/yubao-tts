## 把 FloorMap 畫到 TileMapLayer。
##
## 純呈現：只讀 FloorMap，不寫任何 Core 狀態。
## Godot 4.3+ 用 TileMapLayer；4.0~4.2 請改 extends TileMap 並在 set_cell
## 的第一個參數傳圖層索引 0。
class_name MapRenderer
extends TileMapLayer


func _ready() -> void:
	tile_set = TileArt.make_tileset(TileArt.TERRAIN_COLORS)


## 整層重畫。一層樓只有 900 格，每次換樓重畫一次完全不是瓶頸，
## 換取的是「畫面必定與資料一致」——不必維護增量更新的正確性。
func draw_map(map: FloorMap) -> void:
	clear()
	for y in FloorMap.H:
		for x in FloorMap.W:
			var p := Vector2i(x, y)
			set_cell(p, 0, Vector2i(map.get_tile(p), 0))
