## 場上實體的共同基底。純資料 —— 沒有任何節點、沒有任何呈現邏輯。
class_name Entity
extends RefCounted

var id := 0
var display_name := ""
var pos := Vector2i.ZERO

var hp := 1
var max_hp := 1
var atk := 1
var defense := 0

## 1.0 = 等速、2.0 = 倍速、0.5 = 半速。實際行動次數由 gauge 累積決定。
var speed := 1.0
var speed_modifier := 1.0
var gauge := 0.0

var statuses: Dictionary = {}      # 狀態名 -> 剩餘回合
var is_player := false

## 衝突排序的最後 tie-break。用生成序號而非亂數，才能保證重播一致
## （GDD §1.5）。
var spawn_id := 0


func is_alive() -> bool:
	return hp > 0


func has_status(s: String) -> bool:
	return statuses.has(s)


func add_status(s: String, duration: int) -> void:
	statuses[s] = maxi(statuses.get(s, 0), duration)


func remove_status(s: String) -> void:
	statuses.erase(s)


## 每回合開始遞減。回傳本回合到期移除的狀態名。
func tick_statuses() -> Array:
	var expired := []
	for s: String in statuses.keys():
		statuses[s] -= 1
		if statuses[s] <= 0:
			expired.append(s)
	for s: String in expired:
		statuses.erase(s)
	return expired


## 無法自主行動的狀態。混亂不算 —— 混亂仍會動，只是方向隨機。
func is_incapacitated() -> bool:
	return has_status("SLEEP") or has_status("PARALYZE")


func get_atk() -> int:
	return atk


func get_defense() -> int:
	return defense


## 命中修正。玩家由武器提供，怪物預設 0。
func get_hit_mod() -> int:
	return 0


func get_evade() -> int:
	return 0


func take_damage(amount: int) -> int:
	var before := hp
	hp = maxi(0, hp - amount)
	return before - hp


func heal(amount: int) -> int:
	var before := hp
	hp = mini(max_hp, hp + amount)
	return hp - before
