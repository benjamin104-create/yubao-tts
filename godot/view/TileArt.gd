## 以程式產生所有貼圖與 TileSet。
##
## 原型階段刻意不依賴任何美術資產：clone 下來就能跑，不會因為缺圖而卡住。
## 之後換成真的 TileSet 時，只要替換這裡的兩個 make_* 函式即可 ——
## MapRenderer 與 FogRenderer 不需要改。
class_name TileArt
extends RefCounted

const TILE := 20

## 地形色。索引必須對齊 Tiles 的 enum 順序。
const TERRAIN_COLORS: Array[Color] = [
	Color(0.13, 0.13, 0.17),      # WALL
	Color(0.52, 0.47, 0.39),      # ROOM_FLOOR
	Color(0.34, 0.31, 0.29),      # CORRIDOR
	Color(0.88, 0.76, 0.30),      # STAIRS_DOWN
	Color(0.40, 0.58, 0.80),      # STAIRS_UP
]

const FOG_COLORS: Array[Color] = [
	Color(0, 0, 0, 1.0),          # 0 = 未探索：全黑
	Color(0, 0, 0, 0.55),         # 1 = 已探索但當前不可見
]


## 把一排顏色畫成橫向圖集：第 i 格 = 第 i 種顏色。
static func make_atlas_image(colors: Array[Color], inset: bool) -> Image:
	var img := Image.create(TILE * colors.size(), TILE, false, Image.FORMAT_RGBA8)
	img.fill(Color(0, 0, 0, 0))
	for i in colors.size():
		var base: Color = colors[i]
		for y in TILE:
			for x in TILE:
				var c := base
				if inset and (x == 0 or y == 0):
					# 一格暗邊，讓網格在視覺上可數 —— 回合制遊戲裡
					# 「這裡到那裡幾格」必須一眼看得出來
					c = base.darkened(0.25)
				img.set_pixel(i * TILE + x, y, c)
	return img


static func make_tileset(colors: Array[Color], inset := true) -> TileSet:
	var ts := TileSet.new()
	ts.tile_size = Vector2i(TILE, TILE)
	var src := TileSetAtlasSource.new()
	src.texture = ImageTexture.create_from_image(make_atlas_image(colors, inset))
	src.texture_region_size = Vector2i(TILE, TILE)
	for i in colors.size():
		src.create_tile(Vector2i(i, 0))
	ts.add_source(src, 0)
	return ts


## 實體 / 道具用的小方塊（帶深色外框，在任何地形上都看得清楚）。
static func make_token(fill: Color, size := TILE - 4) -> ImageTexture:
	var img := Image.create(size, size, false, Image.FORMAT_RGBA8)
	for y in size:
		for x in size:
			var edge := x == 0 or y == 0 or x == size - 1 or y == size - 1
			img.set_pixel(x, y, Color(0, 0, 0, 0.85) if edge else fill)
	return ImageTexture.create_from_image(img)


## 依 AI profile 上色 —— 玩家一眼就能分辨威脅類型，這是回合制可推理性
## 的一部分：你必須先知道那是追擊型還是遠程型，才談得上判斷。
static func monster_color(profile_id: String) -> Color:
	match profile_id:
		"WANDERER":
			return Color(0.45, 0.78, 0.45)
		"RANGED":
			return Color(0.72, 0.45, 0.85)
		_:
			return Color(0.88, 0.35, 0.32)


static func item_color(category: String) -> Color:
	match category:
		"food":
			return Color(0.90, 0.70, 0.40)
		"weapon", "shield":
			return Color(0.70, 0.75, 0.85)
		"pot":
			return Color(0.55, 0.80, 0.85)
		_:
			return Color(0.95, 0.90, 0.45)
