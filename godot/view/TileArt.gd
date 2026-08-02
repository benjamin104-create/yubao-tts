## 貼圖來源。有美術資產就用，沒有就用程式產生的色塊。
##
## 這個 fallback 機制是刻意的：美術可以一張一張補，補一張畫面就多一張真圖，
## 中間任何時刻專案都跑得起來。不必等整包美術到齊才能整合，也不會因為缺一張
## 圖就 crash。
##
## 資產放在 res://assets/ 之下（見 docs/roguelike_art_guide.md）：
##   assets/terrain.png            地形圖集，每格 TILE x TILE
##   assets/monsters/<def_id>.png  怪物，寬度 = TILE * 影格數
##   assets/player.png             玩家，同上
##   assets/items/<key>.png        道具圖示，key 為外觀名或 def_id
class_name TileArt
extends RefCounted

## 一格的像素尺寸。改這個值必須同步更新所有美術資產的尺寸。
const TILE := 24

const ASSET_DIR := "res://assets/"
const TERRAIN_PATH := ASSET_DIR + "terrain.png"

## 地形色。索引必須對齊 Tiles 的 enum 順序，也對齊 terrain.png 的圖集欄位。
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

## 已載入資產的快取。每格畫面都要重建貼圖的話 llvmpipe 會直接跪。
static var _cache: Dictionary = {}


# ---------------------------------------------------------------- 地形

## 有 assets/terrain.png 就用它切圖集，否則用程式產生的色塊。
static func make_tileset(colors: Array[Color], inset := true) -> TileSet:
	var ts := TileSet.new()
	ts.tile_size = Vector2i(TILE, TILE)
	var src := TileSetAtlasSource.new()

	var use_art := colors == TERRAIN_COLORS and ResourceLoader.exists(TERRAIN_PATH)
	if use_art:
		src.texture = load(TERRAIN_PATH)
	else:
		src.texture = ImageTexture.create_from_image(make_atlas_image(colors, inset))

	src.texture_region_size = Vector2i(TILE, TILE)
	var count: int = int(src.texture.get_width() / TILE) if use_art else colors.size()
	for i in count:
		src.create_tile(Vector2i(i, 0))
	ts.add_source(src, 0)
	return ts


static func has_terrain_art() -> bool:
	return ResourceLoader.exists(TERRAIN_PATH)


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


# ---------------------------------------------------------------- 實體

## 玩家 / 怪物的貼圖。找不到資產時回傳 null，呼叫端改用色塊 + 字母。
static func entity_texture(def_id: String) -> Texture2D:
	var path := ASSET_DIR + ("player.png" if def_id == "" \
		else "monsters/%s.png" % def_id)
	return _load_cached(path)


## 道具圖示。key 對未鑑定道具是「外觀名」，對武器/盾牌/食物是 def_id ——
## 因為未鑑定的道具在畫面上就該長成它的外觀，而不是它的真身。
static func item_texture(key: String) -> Texture2D:
	return _load_cached(ASSET_DIR + "items/%s.png" % key)


static func _load_cached(path: String) -> Texture2D:
	if _cache.has(path):
		return _cache[path]
	var tex: Texture2D = load(path) if ResourceLoader.exists(path) else null
	_cache[path] = tex
	return tex


# ---------------------------------------------------------------- 程式生成

## 實體 / 道具用的小方塊（帶深色外框，在任何地形上都看得清楚）。
static func make_token(fill: Color, size := TILE - 6) -> ImageTexture:
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
