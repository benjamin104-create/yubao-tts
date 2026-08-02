## 玩家。
##
## 飽足度以「毫點」整數儲存（100.000% = 100000），避免浮點誤差累積 ——
## 一場 Run 有上千回合，浮點誤差會真的跑掉（GDD §2.2）。
class_name PlayerEntity
extends Entity

const BASE_MAX_HP := 15
const MAX_SATIETY_INIT := 100000
const MAX_SATIETY_CAP := 200000
const SATIETY_PER_TURN := 100          # 0.100% / 回合 → 滿胃約 1000 回合
const REGEN_THRESHOLD := 150 * 100     # 每回合回復 ≈ MaxHP / 150

var level := 1
var exp_points := 0

var satiety := MAX_SATIETY_INIT
var max_satiety := MAX_SATIETY_INIT
var hunger_rate := 1.0
var regen_acc := 0
var crit_rate := 0.05

var gold := 0
var inventory := Inventory.new()
var weapon: ItemInstance = null
var shield: ItemInstance = null

## 由 EffectResolver 施加的臨時修正（力量草、毒草…）。
var str_bonus := 0


func _init() -> void:
	is_player = true
	display_name = "玩家"
	max_hp = BASE_MAX_HP
	hp = max_hp


## 力量隨等級線性成長 —— 刻意選可心算的公式，玩家能自己推出下一級的傷害。
func strength() -> int:
	return 8 + int(floor((level - 1) * 4.0 / 3.0)) + str_bonus


func get_atk() -> int:
	var a := strength()
	if weapon != null:
		a += _weapon_atk()
	return maxi(1, a)


func get_defense() -> int:
	if shield == null:
		return 0
	return maxi(0, _shield_def())


func get_hit_mod() -> int:
	if weapon == null:
		return 0
	return int(_def_of(weapon).get("hit_mod", 0))


func _weapon_atk() -> int:
	var d := _def_of(weapon)
	var a := int(d.get("atk", 0)) + int(d.get("atk_per_upgrade", 0)) * weapon.upgrade
	var ks := trait_of(weapon, "KILL_STACK")
	if not ks.is_empty():
		a += mini(int(weapon.kill_stacks * float(ks.get("atk_per_kill", 0.0))),
			int(ks.get("cap", 0)))
	return a


func _shield_def() -> int:
	var d := _def_of(shield)
	return int(d.get("def", 0)) + int(d.get("def_per_upgrade", 0)) * shield.upgrade


## 由 GameHost 注入 —— PlayerEntity 不該自己去 load 資料庫。
var db: ItemDatabase = null

func _def_of(inst: ItemInstance) -> Dictionary:
	if db == null or inst == null:
		return {}
	return db.item_def(inst.def_id)


## 取出裝備上的某個特性定義，找不到回傳空字典。
func trait_of(inst: ItemInstance, kind: String) -> Dictionary:
	if inst == null:
		return {}
	for t: Dictionary in _def_of(inst).get("traits", []):
		if t.get("type", "") == kind:
			return t
	return {}


func weapon_trait(kind: String) -> Dictionary:
	return trait_of(weapon, kind)


func shield_trait(kind: String) -> Dictionary:
	return trait_of(shield, kind)


# ---------------------------------------------------------------- 飽足度

func is_starving() -> bool:
	return satiety <= 0


## 裝備與狀態的消耗倍率相乘疊加（GDD §2.3）。
func effective_hunger_rate() -> float:
	var r := hunger_rate
	for it: ItemInstance in [weapon, shield]:
		if it == null:
			continue
		for t: Dictionary in _def_of(it).get("traits", []):
			if t.get("type", "") == "HUNGER_RATE":
				r *= float(t.get("multiplier", 1.0))
	if has_status("HASTE"):
		r *= 2.0                       # 動得快，餓得快 —— 加速有代價
	if satiety > max_satiety:
		r *= 2.0                       # 過飽時加速消耗，抑制囤積
	return r


## 進食。溢出以 10:1 轉為胃袋容量 —— 讓「吃不完」不是純浪費，但仍是失誤。
func eat(gain: int) -> int:
	var over := maxi(0, satiety + gain - max_satiety)
	satiety = mini(satiety + gain, max_satiety)
	if over > 0:
		var expand := (over / 10000) * 1000
		max_satiety = mini(max_satiety + expand, MAX_SATIETY_CAP)
		return expand
	return 0


# ---------------------------------------------------------------- 升級

static func need_exp(lv: int) -> int:
	return 6 * lv * lv


func gain_exp(amount: int) -> int:
	exp_points += amount
	var gained := 0
	while level < 99 and exp_points >= need_exp(level):
		exp_points -= need_exp(level)
		level += 1
		gained += 1
	return gained


## 等級歸一。等級是局內資源，不是永久成長 —— 若可繼承，玩家會用低層刷等級
## 破壞難度曲線（GDD §4.5）。胃袋容量刻意保留，那才是長期成長。
func reset_on_death() -> void:
	level = 1
	exp_points = 0
	max_hp = BASE_MAX_HP
	hp = max_hp
	str_bonus = 0
	satiety = max_satiety
	statuses.clear()
	gold = 0
