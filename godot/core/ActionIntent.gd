## 一個「想做什麼」的宣告。
##
## 所有改變世界狀態的操作都必須先變成 Intent 再送進 TurnManager ——
## 包含 UI 上的「把道具放進壺」。這是回合制規則無處可逃的保證：
## 只要走這條路，就一定會消耗回合、一定會讓怪物同步行動、一定會進事件串。
class_name ActionIntent
extends RefCounted

enum Kind {
	WAIT,
	MOVE,
	ATTACK,
	RANGED_ATTACK,
	USE_ITEM,
	THROW_ITEM,
	PICKUP,
	DROP,
	DESCEND,
	EQUIP,
	PUT_INTO_POT,
	TAKE_FROM_POT,
}

## 四種道具使用動詞。同一件道具用不同動詞會有不同結果 ——
## 這是「投擲未鑑定草藥試效果」這類玩法的基礎。
enum Verb { NONE, EAT, READ, WAVE, THROW }

var kind: Kind = Kind.WAIT
var dir := Vector2i.ZERO
var target_pos := Vector2i(-1, -1)
var item: ItemInstance = null
var container: ItemInstance = null
var verb: Verb = Verb.NONE


static func wait() -> ActionIntent:
	return ActionIntent.new()


static func move(d: Vector2i) -> ActionIntent:
	var i := ActionIntent.new()
	i.kind = Kind.MOVE
	i.dir = d
	return i


static func attack(target: Vector2i) -> ActionIntent:
	var i := ActionIntent.new()
	i.kind = Kind.ATTACK
	i.target_pos = target
	return i


static func ranged_attack(target: Vector2i) -> ActionIntent:
	var i := ActionIntent.new()
	i.kind = Kind.RANGED_ATTACK
	i.target_pos = target
	return i


static func use(it: ItemInstance, v: Verb, d := Vector2i.ZERO) -> ActionIntent:
	var i := ActionIntent.new()
	i.kind = Kind.USE_ITEM
	i.item = it
	i.verb = v
	i.dir = d
	return i


static func throw_item(it: ItemInstance, d: Vector2i) -> ActionIntent:
	var i := ActionIntent.new()
	i.kind = Kind.THROW_ITEM
	i.item = it
	i.verb = Verb.THROW
	i.dir = d
	return i


static func pickup() -> ActionIntent:
	var i := ActionIntent.new()
	i.kind = Kind.PICKUP
	return i


static func drop(it: ItemInstance) -> ActionIntent:
	var i := ActionIntent.new()
	i.kind = Kind.DROP
	i.item = it
	return i


static func descend() -> ActionIntent:
	var i := ActionIntent.new()
	i.kind = Kind.DESCEND
	return i


static func equip(it: ItemInstance) -> ActionIntent:
	var i := ActionIntent.new()
	i.kind = Kind.EQUIP
	i.item = it
	return i


static func put_into_pot(it: ItemInstance, pot: ItemInstance) -> ActionIntent:
	var i := ActionIntent.new()
	i.kind = Kind.PUT_INTO_POT
	i.item = it
	i.container = pot
	return i


static func take_from_pot(it: ItemInstance, pot: ItemInstance) -> ActionIntent:
	var i := ActionIntent.new()
	i.kind = Kind.TAKE_FROM_POT
	i.item = it
	i.container = pot
	return i
