## 怪物。行為由 ai_profile 決定（CHASER / WANDERER / RANGED），
## 數值由 monsters.json 提供。
class_name MonsterEntity
extends Entity

var def_id := ""
var profile_id := "CHASER"
var sight := 5
var evade := 0
var exp_value := 0
var traits: Array = []
var ranged: Dictionary = {}          # { range, damage_type, blocked_by }
var on_hit_effects: Array = []       # 命中玩家時附加的效果
var drop_table: Array = []           # 死亡掉落
var melee_penalty := 1.0             # 遠程怪貼身時的攻擊力倍率
var immobile := false

# ---- AI 執行期狀態 ----
var memory_pos := Vector2i(-1, -1)   # 最後看到玩家的位置
var memory_left := 0
var aggro_left := 0                  # WANDERER 受擊後轉為追擊的剩餘回合
var cooldown_left := 0               # RANGED 的射擊冷卻
var last_dir := Vector2i.ZERO        # WANDERER 的慣性方向

## 被 PICKUP_ITEMS 型怪物撿走的道具。牠死掉時會全部掉回地面 ——
## 所以哥布林撿走你的東西時，你必須追上去把牠打死才拿得回來。
var carried_items: Array = []


static func from_def(def: Dictionary, at: Vector2i, new_id: int) -> MonsterEntity:
	var m := MonsterEntity.new()
	m.id = new_id
	m.spawn_id = new_id
	m.def_id = def.get("id", "")
	m.display_name = def.get("name", "?")
	m.pos = at
	m.max_hp = int(def.get("hp", 1))
	m.hp = m.max_hp
	m.atk = int(def.get("atk", 1))
	m.defense = int(def.get("def", 0))
	m.speed = float(def.get("speed", 1.0))
	m.sight = int(def.get("sight", 5))
	m.evade = int(def.get("evade", 0))
	m.exp_value = int(def.get("exp", 0))
	m.profile_id = def.get("ai_profile", "CHASER")
	m.traits = def.get("traits", [])
	m.ranged = def.get("ranged", {})
	m.on_hit_effects = def.get("on_hit_effects", [])
	m.drop_table = def.get("drop_table", [])
	m.melee_penalty = float(def.get("melee_penalty", 1.0))
	for t: Dictionary in m.traits:
		if t.get("type", "") == "IMMOBILE":
			m.immobile = true
	return m


func get_evade() -> int:
	return evade


func is_ranged() -> bool:
	return not ranged.is_empty()


func ranged_range() -> int:
	return int(ranged.get("range", 0))


## 免疫判定。骷髏兵免疫睡眠，是為了打破「睡眠之杖萬用」的中期慣性。
func is_immune_to(status: String) -> bool:
	for t: Dictionary in traits:
		if t.get("type", "") == "IMMUNE" and status in t.get("status", []):
			return true
	return false


func has_trait(kind: String) -> bool:
	for t: Dictionary in traits:
		if t.get("type", "") == kind:
			return true
	return false


func trait_of(kind: String) -> Dictionary:
	for t: Dictionary in traits:
		if t.get("type", "") == kind:
			return t
	return {}


## 弱點倍率（例如骷髏兵吃火 x1.5）。
func weakness_multiplier(damage_type: String) -> float:
	var t := trait_of("WEAK_TO")
	if not t.is_empty() and t.get("damage_type", "") == damage_type:
		return float(t.get("multiplier", 1.0))
	return 1.0


func add_status(s: String, duration: int) -> void:
	if is_immune_to(s):
		return
	super.add_status(s, duration)
