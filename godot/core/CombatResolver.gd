## 命中、會心、傷害。
##
## 公式推導與驗算見 docs/roguelike_data_spec.md §3。核心選擇是用
## 「指數遞減防禦」而非減法：每 1 點 DEF 恆定吸收 6.25%，玩家的每一次
## +1 強化都會穿透敵人的防禦生效 —— 這就是成長感的數學來源。
class_name CombatResolver
extends RefCounted

const DEF_FACTOR := 15.0 / 16.0
const BASE_HIT := 92
const HIT_MIN := 50
const HIT_MAX := 99
const RAND_LO := 0.9375        # ±1/16
const RAND_HI := 1.0625


static func hit_rate(hit_mod: int, evade: int) -> int:
	return clampi(BASE_HIT + hit_mod - evade, HIT_MIN, HIT_MAX)


static func defense_factor(d: int) -> float:
	return pow(DEF_FACTOR, float(maxi(0, d)))


## 保底 1 點：杜絕「完全打不動」的斷崖，但也因此需要監控
## 「對高防怪打出 1 傷的戰鬥佔比 < 3%」這個指標（data_spec §3.5）。
static func roll_damage(rng: DeterministicRng, atk: int, target_def: int,
		is_crit: bool, multiplier: float = 1.0) -> int:
	var raw := float(atk)
	if not is_crit:
		raw *= defense_factor(target_def)      # 會心跳過防禦項
	raw *= rng.randf_range(RAND_LO, RAND_HI) * multiplier
	return maxi(1, int(floor(raw)))


## 一次完整的攻擊結算。回傳 { hit, crit, damage }。
## 不直接改動 entity —— 由 ActionResolver 決定何時套用，方便之後加反擊、
## 護盾、傷害轉移這類插入點。
static func resolve_attack(rng: DeterministicRng, attacker: Entity,
		target: Entity, multiplier: float = 1.0,
		ignore_defense := false) -> Dictionary:
	var rate := hit_rate(attacker.get_hit_mod(), target.get_evade())
	if rng.randi_range(1, 100) > rate:
		return { "hit": false, "crit": false, "damage": 0 }

	var crit_rate := 0.05
	if attacker is PlayerEntity:
		crit_rate = (attacker as PlayerEntity).crit_rate
	var crit := rng.chance(crit_rate)

	var dmg := roll_damage(rng, attacker.get_atk(), target.get_defense(),
			crit or ignore_defense, multiplier)
	return { "hit": true, "crit": crit, "damage": dmg }
