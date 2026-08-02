## 未鑑定外觀映射與已鑑定集合。
##
## 每局（Run）開場洗牌一次，局內固定，跨局重洗 —— 跨局不繼承外觀映射
## 是整套鑑定機制存活的前提（GDD §4.5）。
class_name IdentificationTable
extends RefCounted

## 只有這四類會被外觀名遮蔽。武器/盾牌的種類永遠可見（玩家看得出那是劍
## 還是盾），被藏起來的是強化值與詛咒 —— 理由見 data_spec §1.1。
const MASKED := ["herb", "scroll", "wand", "pot"]

var appearance: Dictionary = {}    # def_id -> 外觀名
var identified: Dictionary = {}    # def_id -> true
var notes: Dictionary = {}         # def_id -> 玩家標註


func _init(db: ItemDatabase = null, rng: DeterministicRng = null) -> void:
	if db != null and rng != null:
		shuffle_appearances(db, rng)


func shuffle_appearances(db: ItemDatabase, rng: DeterministicRng) -> void:
	appearance.clear()
	identified.clear()
	for category: String in MASKED:
		var defs: Array = db.items_by_category.get(category, [])
		var pool: Array = (db.appearance_pools.get(category, []) as Array).duplicate()
		# 外觀池必須 >= 真實種類數，且多備假外觀防排除法（data_spec §1.2）
		assert(pool.size() >= defs.size(),
			"外觀池不足：%s 需要 %d 個，只有 %d 個" % [category, defs.size(), pool.size()])
		rng.shuffle(pool)
		for i in defs.size():
			appearance[defs[i]["id"]] = pool[i]


func is_identified(def_id: String) -> bool:
	return identified.has(def_id)


## 鑑定是全域的：一旦知道「藍色的草 = 回復草」，背包裡與地上的同種
## 全部立即改顯示。回傳是否為新鑑定（用來決定要不要發事件）。
func identify(def_id: String) -> bool:
	if identified.has(def_id):
		return false
	identified[def_id] = true
	return true


func set_note(def_id: String, text: String) -> void:
	notes[def_id] = text


func display_name(inst: ItemInstance, db: ItemDatabase) -> String:
	if inst == null:
		return "（空）"
	var base: String

	if inst.category in MASKED and not is_identified(inst.def_id):
		base = appearance.get(inst.def_id, "不明的道具")
		if notes.has(inst.def_id):
			base += "（%s）" % notes[inst.def_id]
	else:
		base = db.true_name(inst.def_id)

	if inst.is_pot():
		base += " [%d/%d]" % [inst.contents.size(), inst.pot_capacity]
	elif inst.category == "wand" and is_identified(inst.def_id):
		base += " [%d]" % inst.uses

	if inst.is_equipment() and inst.known_modifier:
		if inst.upgrade != 0:
			base += " %+d" % inst.upgrade
		if inst.cursed:
			base += "【詛咒】"

	return base
