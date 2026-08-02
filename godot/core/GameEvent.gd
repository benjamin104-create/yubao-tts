## Model 與 View 之間的唯一通道。
##
## Core 在一個 frame 內跑完整個回合、產生有序的事件串；View 讀事件播動畫。
## 新增機制時先加事件、再加 View 反應 —— 不可讓 View 直接去讀 Core 狀態，
## 否則連打壓縮動畫時必然出現「動畫還在播、狀態已經又變了」的競態
## （架構文件 §0）。
class_name GameEvent
extends RefCounted

enum Kind {
	ENTITY_MOVED,
	ENTITY_ATTACKED,
	ATTACK_MISSED,
	DAMAGE_DEALT,
	ENTITY_DIED,
	HP_CHANGED,
	SATIETY_CHANGED,
	STATUS_ADDED,
	STATUS_REMOVED,
	ITEM_PICKED_UP,
	ITEM_DROPPED,
	ITEM_USED,
	ITEM_IDENTIFIED,
	ITEM_THROWN,
	INVENTORY_CHANGED,
	VISIBILITY_CHANGED,
	TRAP_TRIGGERED,
	FLOOR_CHANGED,
	MONSTER_SPAWNED,
	LEVEL_UP,
	MESSAGE,
	TURN_ADVANCED,
	PLAYER_DIED,
}

var kind: Kind
var data: Dictionary

## 可否在連續移動時壓縮動畫時間。會心一擊、跨飽足度閾值、鑑定、死亡等
## 事件一律不可壓縮 —— 玩家必須看清楚（GDD §1.7）。
var compressible := true


func _init(p_kind: Kind, p_data: Dictionary = {}, p_compressible := true) -> void:
	kind = p_kind
	data = p_data
	compressible = p_compressible


static func msg(text: String) -> GameEvent:
	return GameEvent.new(Kind.MESSAGE, { "text": text })


static func moved(e: Entity, from: Vector2i, to: Vector2i, sub_turn := 0) -> GameEvent:
	return GameEvent.new(Kind.ENTITY_MOVED, {
		"entity_id": e.id, "from": from, "to": to, "sub_turn": sub_turn,
	})
