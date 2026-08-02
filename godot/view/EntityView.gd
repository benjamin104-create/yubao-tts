## 實體與地面物件的呈現。
##
## 每個實體對應一個可被 Tween 移動的 actor 節點 —— 位移插值因此可以做在
## 節點上，而 Core 的座標永遠是整數格。邏輯與表現的分離在這裡最具體：
## Core 說「從 (3,4) 到 (4,4)」，View 決定那要花 120ms 還是 40ms。
class_name EntityView
extends Node2D

## 用 ASCII 字形而非中文字 —— Godot 內建字型沒有 CJK 字符，
## 地圖上的符號必須在任何環境下都畫得出來。
const MONSTER_GLYPH := {
	"mon_cave_rat": "r", "mon_blue_slime": "s", "mon_green_goblin": "g",
	"mon_drunk_shroom": "m", "mon_pebble_imp": "i", "mon_rot_grub": "w",
	"mon_skeleton": "S", "mon_gale_wolf": "W", "mon_hex_mage": "M",
	"mon_wander_golem": "G", "mon_crystal_turret": "T", "mon_abyss_knight": "K",
}

const ITEM_GLYPH := {
	"food": "%", "herb": "!", "scroll": "?", "wand": "/",
	"weapon": ")", "shield": "]", "pot": "u",
}

var host: GameHost

var _actors: Dictionary = {}      # entity_id -> Node2D
var _objects: Node2D


func setup(p_host: GameHost) -> void:
	host = p_host
	_objects = Node2D.new()
	# 必須低於 actor：玩家站在道具上時要看得到自己，而不是被道具圖示蓋住
	_objects.z_index = -1
	add_child(_objects)
	z_index = 10


static func tile_center(p: Vector2i) -> Vector2:
	return Vector2(p) * TileArt.TILE + Vector2(TileArt.TILE, TileArt.TILE) * 0.5


## 換樓層時整個重建。
func rebuild() -> void:
	for a: Node2D in _actors.values():
		a.queue_free()
	_actors.clear()
	for e: Entity in host.entities.all():
		_add_actor(e)
	sync()


func _add_actor(e: Entity) -> void:
	var glyph := "@"
	var color := Color(0.95, 0.95, 1.0)
	if e is MonsterEntity:
		var m := e as MonsterEntity
		glyph = MONSTER_GLYPH.get(m.def_id, "?")
		color = TileArt.monster_color(m.profile_id)

	var actor := Node2D.new()
	actor.position = tile_center(e.pos)

	var sprite := Sprite2D.new()
	var art := TileArt.entity_texture("" if e.is_player \
		else (e as MonsterEntity).def_id)
	if art != null:
		sprite.texture = art
		# 多影格圖：先只取第 1 格，待動畫系統接上再跑其餘影格
		if art.get_width() > TileArt.TILE:
			sprite.region_enabled = true
			sprite.region_rect = Rect2(0, 0, TileArt.TILE, art.get_height())
		actor.add_child(sprite)
	else:
		# 還沒有美術：色塊 + 字母，一樣看得懂在打什麼
		sprite.texture = TileArt.make_token(color)
		actor.add_child(sprite)
		actor.add_child(_make_glyph(glyph, Color(0.08, 0.06, 0.05), 13))

	add_child(actor)
	_actors[e.id] = actor


## 依視野決定誰看得見。已探索但不可見的格子只記得地形，不記得實體。
func sync() -> void:
	for e: Entity in host.entities.all():
		if not _actors.has(e.id):
			_add_actor(e)
	for id: int in _actors.keys():
		var e := host.entities.by_id(id)
		var actor: Node2D = _actors[id]
		if e == null:
			actor.queue_free()
			_actors.erase(id)
			continue
		actor.visible = e.is_player or host.vision.is_visible(e.pos)
	_redraw_objects()


func _redraw_objects() -> void:
	for c in _objects.get_children():
		c.queue_free()

	var map := host.map
	for p: Vector2i in map.floor_items.keys():
		if not host.vision.is_visible(p):
			continue
		var it: ItemInstance = map.floor_items[p]
		var art := TileArt.item_texture(host.art_key(it))
		if art != null:
			var s2 := Sprite2D.new()
			s2.texture = art
			s2.position = tile_center(p)
			_objects.add_child(s2)
		else:
			_add_marker(p, ITEM_GLYPH.get(it.category, "*"),
				TileArt.item_color(it.category))
	for p: Vector2i in map.floor_gold.keys():
		if host.vision.is_visible(p):
			_add_marker(p, "$", Color(0.95, 0.82, 0.35))
	for p: Vector2i in map.traps.keys():
		# 陷阱只在踩到或被探知後才畫；原型階段一律顯示於可見範圍內
		if host.vision.is_visible(p):
			_add_marker(p, "^", Color(0.90, 0.45, 0.25))


func _add_marker(p: Vector2i, glyph: String, color: Color) -> void:
	var label := _make_glyph(glyph, color, 14)
	label.position += tile_center(p)
	_objects.add_child(label)


static func _make_glyph(glyph: String, color: Color, size: int) -> Label:
	var label := Label.new()
	label.text = glyph
	label.size = Vector2(TileArt.TILE, TileArt.TILE)
	label.position = Vector2(-TileArt.TILE, -TileArt.TILE) * 0.5
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	label.add_theme_color_override("font_color", color)
	label.add_theme_font_size_override("font_size", size)
	return label


# ---------------------------------------------------------------- 動畫

func move_actor(entity_id: int, to: Vector2i, duration: float) -> void:
	var actor: Node2D = _actors.get(entity_id)
	if actor == null:
		return
	var target := tile_center(to)
	if duration <= 0.0:
		actor.position = target
		return
	var tween := create_tween()
	tween.tween_property(actor, "position", target, duration)


func flash(entity_id: int, color: Color) -> void:
	var actor: Node2D = _actors.get(entity_id)
	if actor == null or actor.get_child_count() == 0:
		return
	var sprite := actor.get_child(0) as Sprite2D
	if sprite == null:
		return
	var tween := create_tween()
	tween.tween_property(sprite, "modulate", color, 0.05)
	tween.tween_property(sprite, "modulate", Color.WHITE, 0.10)


## 取得 actor 目前的世界座標（含插值中的位置）。飄字要跟著實際畫面位置
## 冒出來，而不是 Core 的格子座標 —— 動畫還在播時兩者會差一格。
func actor_position(entity_id: int) -> Vector2:
	var actor: Node2D = _actors.get(entity_id)
	if actor == null:
		var e := host.entities.by_id(entity_id)
		return tile_center(e.pos) if e != null else Vector2.ZERO
	return actor.position


func remove_actor(entity_id: int) -> void:
	var actor: Node2D = _actors.get(entity_id)
	if actor != null:
		actor.queue_free()
		_actors.erase(entity_id)
