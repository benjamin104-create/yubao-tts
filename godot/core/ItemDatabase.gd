## 讀取 items.json / monsters.json，提供查表與加權抽取。
##
## 資料是唯一事實來源（data_spec §0）—— 平衡調整改 JSON，不改程式碼。
class_name ItemDatabase
extends RefCounted

const ITEMS_PATH := "res://data/items.json"
const MONSTERS_PATH := "res://data/monsters.json"

const ITEM_CATEGORIES := ["foods", "weapons", "shields", "herbs", "scrolls", "wands", "pots"]
const POT_BEHAVIOR := {
	"pot_storage": "storage", "pot_storage_large": "storage",
	"pot_fusion": "fusion", "pot_identify": "identify",
	"pot_change": "change", "pot_dispel": "dispel",
	"pot_vault": "vault", "pot_copy": "copy",
	"pot_devour": "devour", "pot_cursed": "cursed",
}

var items: Dictionary = {}            # def_id -> Dictionary
var items_by_category: Dictionary = {}
var appearance_pools: Dictionary = {}
var price_clusters: Dictionary = {}
var monsters: Dictionary = {}         # def_id -> Dictionary
var ai_profiles: Dictionary = {}

var _item_list: Array = []
var _monster_list: Array = []


static func load_default() -> ItemDatabase:
	var db := ItemDatabase.new()
	db.load_from(ITEMS_PATH, MONSTERS_PATH)
	return db


func load_from(items_path: String, monsters_path: String) -> void:
	var idata: Dictionary = _read_json(items_path)
	var mdata: Dictionary = _read_json(monsters_path)

	appearance_pools = idata.get("appearance_pools", {})
	price_clusters = idata.get("price_clusters", {})

	for key: String in ITEM_CATEGORIES:
		var singular: String = key.substr(0, key.length() - 1)   # weapons -> weapon
		var list: Array = idata.get(key, [])
		items_by_category[singular] = []
		for def: Dictionary in list:
			def["category"] = singular
			items[def["id"]] = def
			items_by_category[singular].append(def)
			_item_list.append(def)

	ai_profiles = mdata.get("ai_profiles", {})
	for def: Dictionary in mdata.get("monsters", []):
		monsters[def["id"]] = def
		_monster_list.append(def)


func _read_json(path: String) -> Dictionary:
	if not FileAccess.file_exists(path):
		push_error("找不到資料檔：%s" % path)
		return {}
	var text := FileAccess.get_file_as_string(path)
	var parsed: Variant = JSON.parse_string(text)
	if typeof(parsed) != TYPE_DICTIONARY:
		push_error("資料檔格式錯誤：%s" % path)
		return {}
	return parsed


func item_def(def_id: String) -> Dictionary:
	return items.get(def_id, {})


func monster_def(def_id: String) -> Dictionary:
	return monsters.get(def_id, {})


func profile(profile_id: String) -> Dictionary:
	return ai_profiles.get(profile_id, {})


## 出現表衰減：主場層段中央 1.0、邊界 0.4、範圍外 0。
## 讓玩家有 2~3 層緩衝期熟悉新怪，而不是在邊界層被滿編新怪淹死。
static func falloff(f: int, lo: int, hi: int, edge_ratio: float = 0.4) -> float:
	if f < lo or f > hi:
		return 0.0
	if hi == lo:
		return 1.0
	var center := (lo + hi) / 2.0
	var t: float = absf(f - center) / ((hi - lo) / 2.0)
	return 1.0 - (1.0 - edge_ratio) * t


func _weighted_table(source: Array, f: int) -> Array:
	var out := []
	for def: Dictionary in source:
		var fr: Array = def.get("floor_range", [1, 99])
		var w: float = float(def.get("spawn_weight", 0)) * falloff(f, fr[0], fr[1])
		if w > 0.0:
			out.append([def, w])
	return out


func roll_item(rng: DeterministicRng, f: int) -> Dictionary:
	var picked: Variant = rng.weighted_pick(_weighted_table(_item_list, f))
	return picked if picked != null else {}


func roll_category(rng: DeterministicRng, category: String, f: int) -> Dictionary:
	var source: Array = items_by_category.get(category, [])
	var picked: Variant = rng.weighted_pick(_weighted_table(source, f))
	return picked if picked != null else {}


## 解析 drop_table 的 item 欄位。支援三種寫法：
##   "any"                → 全表加權抽
##   "weapon_or_shield"   → 指定類別（可用 _or_ 串接）
##   "hrb_confuse"        → 指定的 def_id
func roll_drop(rng: DeterministicRng, spec: String, f: int) -> Dictionary:
	if items.has(spec):
		return items[spec]
	if spec == "any":
		return roll_item(rng, f)
	var pool: Array = []
	for c: String in spec.split("_or_"):
		pool.append_array(items_by_category.get(c, []))
	var picked: Variant = rng.weighted_pick(_weighted_table(pool, f))
	if picked == null:
		# 該層段沒有符合條件的道具時退回全表，總比什麼都不掉好
		return roll_item(rng, f)
	return picked


func roll_monster(rng: DeterministicRng, f: int) -> Dictionary:
	var picked: Variant = rng.weighted_pick(_weighted_table(_monster_list, f))
	return picked if picked != null else {}


## 由定義建立一件實體道具，含強化值與詛咒的隨機決定。
func make_instance(def: Dictionary, rng: DeterministicRng) -> ItemInstance:
	var inst := ItemInstance.new()
	inst.def_id = def["id"]
	inst.category = def.get("category", "")

	# 武器/盾牌的種類永遠可見，未知的是強化值與詛咒（data_spec §1.1）
	inst.known_type = not (inst.category in IdentificationTable.MASKED)

	if inst.is_equipment():
		var ur: Array = def.get("upgrade_range", [0, 0])
		inst.upgrade = rng.randi_range(int(ur[0]), int(ur[1]))
		inst.cursed = rng.chance(float(def.get("curse_chance", 0.08)))
	elif inst.category == "wand":
		var r: Array = def.get("uses_range", [1, 1])
		inst.uses = rng.randi_range(int(r[0]), int(r[1]))
	elif inst.category == "pot":
		inst.pot_behavior = POT_BEHAVIOR.get(inst.def_id, "storage")
		var cr: Array = def.get("capacity_range", [3, 3])
		inst.pot_capacity = rng.randi_range(int(cr[0]), int(cr[1]))

	return inst


func make_by_id(def_id: String, rng: DeterministicRng) -> ItemInstance:
	var def := item_def(def_id)
	if def.is_empty():
		return null
	return make_instance(def, rng)


func true_name(def_id: String) -> String:
	return item_def(def_id).get("name", def_id)


func base_price(def_id: String) -> int:
	return int(item_def(def_id).get("base_price", 0))
