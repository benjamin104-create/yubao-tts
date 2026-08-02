## 執行 items.json 裡的 effects op 陣列。
##
## 資料驅動：新增一種草藥＝在 JSON 加一筆，不必改程式碼；只有新增「新的
## 效果種類」時才需要在這裡加一個 case。
##
## 未實作的 op 會明確回報而不是靜默略過 —— 靜默 no-op 是最難察覺的 bug。
class_name EffectResolver
extends RefCounted

## ctx 需要的鍵：player, map, entities, rng, ident, db, vision
## 選填：source, target, item
static func apply(ops: Array, ctx: Dictionary) -> Array:
	var events: Array = []
	for op: Dictionary in ops:
		events.append_array(_apply_one(op, ctx))
	return events


static func _apply_one(op: Dictionary, ctx: Dictionary) -> Array:
	var ev: Array = []
	var player: PlayerEntity = ctx["player"]
	var rng: DeterministicRng = ctx["rng"]
	var target: Entity = ctx.get("target", player)
	var kind: String = op.get("op", "")

	match kind:
		"HEAL_HP":
			var v: Variant = op.get("value", 0)
			var amount: int = target.max_hp if typeof(v) == TYPE_STRING else int(v)
			var healed := target.heal(amount)
			ev.append(GameEvent.new(GameEvent.Kind.HP_CHANGED,
				{ "entity_id": target.id, "delta": healed, "hp": target.hp }, false))
			ev.append(GameEvent.msg("%s 恢復了 %d 點體力。" % [target.display_name, healed]))

		"DAMAGE_HP":
			var dmg := int(op.get("value", 0))
			if op.get("ignore_defense", false) == false and target != player:
				dmg = int(dmg * CombatResolver.defense_factor(target.get_defense()))
			var dealt := target.take_damage(maxi(1, dmg))
			ev.append(GameEvent.new(GameEvent.Kind.DAMAGE_DEALT,
				{ "target_id": target.id, "amount": dealt, "crit": false }, false))

		"MOD_MAX_HP":
			var d := int(op.get("value", 0))
			target.max_hp = maxi(1, target.max_hp + d)
			target.hp = mini(target.hp + maxi(0, d), target.max_hp)
			ev.append(GameEvent.msg("體力上限 %+d。" % d))

		"MOD_STR":
			var d := int(op.get("value", 0))
			player.str_bonus += d
			ev.append(GameEvent.msg("力量 %+d。" % d))

		"RESTORE_STR":
			if player.str_bonus < 0:
				player.str_bonus = 0
				ev.append(GameEvent.msg("力量恢復了。"))

		"ADD_STATUS":
			var s := String(op.get("value", ""))
			var dur := int(op.get("duration", 1))
			target.add_status(s, dur)
			ev.append(GameEvent.new(GameEvent.Kind.STATUS_ADDED,
				{ "entity_id": target.id, "status": s, "duration": dur }, false))
			ev.append(GameEvent.msg("%s 陷入了%s。" % [target.display_name, _status_label(s)]))

		"CURE_STATUS":
			var cured := false
			for s: String in op.get("value", []):
				if target.has_status(s):
					target.remove_status(s)
					cured = true
			if cured:
				ev.append(GameEvent.msg("異常狀態解除了。"))
			else:
				# 情境不成立 → 不鑑定（data_spec §1.6 的 CONDITIONAL）
				ev.append(GameEvent.new(GameEvent.Kind.MESSAGE,
					{ "text": "什麼都沒有發生……", "no_identify": true }, false))

		"SET_SPEED":
			var v := float(op.get("value", 1.0))
			var dur := int(op.get("duration", 10))
			target.add_status("HASTE" if v >= 1.5 else "SLOW", dur)
			ev.append(GameEvent.msg("%s 的動作%s了。"
				% [target.display_name, "變快" if v >= 1.5 else "變慢"]))

		"MOD_MAX_SATIETY":
			var d := int(op.get("value", 0))
			player.max_satiety = mini(player.max_satiety + d, PlayerEntity.MAX_SATIETY_CAP)
			player.satiety = mini(player.satiety + d, player.max_satiety)
			ev.append(GameEvent.msg("胃袋變大了！"))
			ev.append(GameEvent.new(GameEvent.Kind.SATIETY_CHANGED,
				{ "satiety": player.satiety, "max": player.max_satiety }, false))

		"SET_HUNGER_RATE":
			player.hunger_rate = float(op.get("value", 1.0))
			player.add_status("GLUTTON", int(op.get("duration", 50)))
			ev.append(GameEvent.msg("肚子餓得比平常快了。"))

		"SET_CRIT_RATE":
			player.crit_rate = float(op.get("value", 0.05))
			player.add_status("LUCKY", int(op.get("duration", 15)))
			ev.append(GameEvent.msg("身體變得輕盈，攻擊更容易命中要害。"))

		"IDENTIFY_ITEM":
			var it: ItemInstance = ctx.get("chosen_item")
			if it == null:
				ev.append(GameEvent.msg("沒有可鑑定的道具。"))
			else:
				ev.append_array(_identify(it, ctx))

		"REVEAL_MAP":
			var vision: VisionSystem = ctx["vision"]
			var map: FloorMap = ctx["map"]
			for p in map.walkable_tiles():
				vision.explored[p] = true
			ev.append(GameEvent.new(GameEvent.Kind.VISIBILITY_CHANGED, { "full": true }, false))
			ev.append(GameEvent.msg("這一層的地圖浮現在腦海中。"))

		"MOD_UPGRADE":
			var it: ItemInstance = ctx.get("chosen_item")
			if it == null or not it.is_equipment():
				ev.append(GameEvent.msg("什麼都沒有發生……"))
			else:
				var def := (ctx["db"] as ItemDatabase).item_def(it.def_id)
				var ur: Array = def.get("upgrade_range", [0, 0])
				# 上限必須夾住 —— 沒有夾的話配合複製壺會直接數值失控
				it.upgrade = mini(it.upgrade + int(op.get("value", 1)), int(ur[1]))
				it.known_modifier = true
				ev.append(GameEvent.msg("道具發出了光芒。"))

		"REMOVE_CURSE":
			var n := 0
			for it: ItemInstance in player.inventory.all_including_nested():
				if it.cursed:
					it.cursed = false
					n += 1
			ev.append(GameEvent.msg("身上的詛咒消失了。" if n > 0 else "什麼都沒有發生……"))

		"APPLY_CURSE":
			var pool := player.inventory.slots.filter(
				func(i: ItemInstance) -> bool: return not i.cursed)
			for i in mini(int(op.get("count", 1)), pool.size()):
				(rng.choice(pool) as ItemInstance).cursed = true
			ev.append(GameEvent.msg("一股不祥的氣息纏上了身。"))

		"ADD_STATUS_AREA":
			var s := String(op.get("value", ""))
			var dur := int(op.get("duration", 1))
			var hit := 0
			for m: MonsterEntity in _visible_monsters(ctx):
				m.add_status(s, dur)
				hit += 1
			if hit == 0:
				ev.append(GameEvent.new(GameEvent.Kind.MESSAGE,
					{ "text": "什麼都沒有發生……", "no_identify": true }, false))
			else:
				ev.append(GameEvent.msg("視野內的 %d 隻敵人陷入了%s。" % [hit, _status_label(s)]))

		"DAMAGE_AREA":
			var radius := int(op.get("radius", 1))
			var value := int(op.get("value", 0))
			var dtype := String(op.get("damage_type", "physical"))
			var entities: EntityIndex = ctx["entities"]
			for m: MonsterEntity in entities.monsters():
				if Tiles.chebyshev(m.pos, player.pos) <= radius:
					var mult := m.weakness_multiplier(dtype)
					var dealt := m.take_damage(maxi(1, int(value * mult)))
					ev.append(GameEvent.new(GameEvent.Kind.DAMAGE_DEALT,
						{ "target_id": m.id, "amount": dealt, "crit": false }, false))

		"DESTROY_ITEM":
			var pool := player.inventory.slots.filter(
				func(i: ItemInstance) -> bool: return i.category == "scroll")
			if not pool.is_empty():
				var victim: ItemInstance = rng.choice(pool)
				player.inventory.remove(victim)
				ev.append(GameEvent.msg("背包裡的一張卷軸被燒毀了！"))

		"SPAWN_MONSTER":
			ev.append_array(_spawn_monsters(op, ctx))

		"TELEPORT_TARGET":
			if target != null and target != player:
				var map: FloorMap = ctx["map"]
				var entities: EntityIndex = ctx["entities"]
				var spots := map.walkable_tiles().filter(
					func(p: Vector2i) -> bool: return not entities.occupied(p))
				if not spots.is_empty():
					entities.move_entity(target, rng.choice(spots))
					ev.append(GameEvent.msg("%s 被傳送到了別處。" % target.display_name))

		"SWAP_POSITION":
			if target != null and target != player:
				var entities: EntityIndex = ctx["entities"]
				var a := player.pos
				var b := target.pos
				entities.move_entity(target, a)
				entities.move_entity(player, b)
				ev.append(GameEvent.moved(player, a, b))
				ev.append(GameEvent.moved(target, b, a))
				ev.append(GameEvent.msg("與 %s 交換了位置！" % target.display_name))

		"PUSH_TARGET":
			ev.append_array(_push(op, ctx))

		"MOD_ATK":
			if target != null:
				target.atk = maxi(1, target.atk + int(op.get("value", 0)))
				ev.append(GameEvent.msg("%s 的攻擊力下降了。" % target.display_name))

		"MOD_DEF":
			if target != null:
				target.defense = maxi(0, target.defense + int(op.get("value", 0)))

		"NO_EFFECT_ON_READ":
			ev.append(GameEvent.msg("讀完了，但什麼事都沒發生。"))

		_:
			# 明確回報而非靜默略過
			ev.append(GameEvent.msg("[尚未實作的效果：%s]" % kind))

	return ev


# ---------------------------------------------------------------- 輔助

static func _identify(it: ItemInstance, ctx: Dictionary) -> Array:
	var ev: Array = []
	var ident: IdentificationTable = ctx["ident"]
	var db: ItemDatabase = ctx["db"]
	it.known_type = true
	it.known_modifier = true
	if ident.identify(it.def_id):
		ev.append(GameEvent.new(GameEvent.Kind.ITEM_IDENTIFIED,
			{ "def_id": it.def_id, "name": db.true_name(it.def_id) }, false))
	ev.append(GameEvent.msg("看清楚了 —— 那是「%s」。" % ident.display_name(it, db)))
	return ev


static func _visible_monsters(ctx: Dictionary) -> Array:
	var vision: VisionSystem = ctx["vision"]
	var entities: EntityIndex = ctx["entities"]
	var out: Array = []
	for m: MonsterEntity in entities.monsters():
		if vision.is_visible(m.pos):
			out.append(m)
	return out


static func _spawn_monsters(op: Dictionary, ctx: Dictionary) -> Array:
	var ev: Array = []
	var rng: DeterministicRng = ctx["rng"]
	var map: FloorMap = ctx["map"]
	var entities: EntityIndex = ctx["entities"]
	var db: ItemDatabase = ctx["db"]
	var player: PlayerEntity = ctx["player"]

	for i in int(op.get("count", 1)):
		var spots: Array = []
		for d in Tiles.DIRS_8:
			var p: Vector2i = player.pos + d
			if map.is_walkable(p) and not entities.occupied(p):
				spots.append(p)
		if spots.is_empty():
			break
		var def := db.roll_monster(rng, map.floor_index)
		if def.is_empty():
			break
		var m := MonsterEntity.from_def(def, rng.choice(spots), entities.next_id())
		entities.add(m)
		ev.append(GameEvent.new(GameEvent.Kind.MONSTER_SPAWNED,
			{ "entity_id": m.id, "pos": m.pos, "def_id": m.def_id }, false))
	if not ev.is_empty():
		ev.append(GameEvent.msg("敵人從卷軸中湧了出來！"))
	return ev


static func _push(op: Dictionary, ctx: Dictionary) -> Array:
	var ev: Array = []
	var target: Entity = ctx.get("target")
	if target == null:
		return ev
	var map: FloorMap = ctx["map"]
	var entities: EntityIndex = ctx["entities"]
	var player: PlayerEntity = ctx["player"]
	var dir := Tiles.step_dir(player.pos, target.pos)
	var from := target.pos
	var moved := 0
	for i in int(op.get("distance", 1)):
		var nxt: Vector2i = target.pos + dir
		if not map.is_walkable(nxt) or entities.occupied(nxt):
			break
		entities.move_entity(target, nxt)
		moved += 1
	if moved > 0:
		ev.append(GameEvent.moved(target, from, target.pos))
	if moved < int(op.get("distance", 1)):
		var dmg := target.take_damage(12)
		ev.append(GameEvent.new(GameEvent.Kind.DAMAGE_DEALT,
			{ "target_id": target.id, "amount": dmg, "crit": false }, false))
		ev.append(GameEvent.msg("%s 撞上了牆！" % target.display_name))
	return ev


static func _status_label(s: String) -> String:
	match s:
		"SLEEP": return "睡眠"
		"CONFUSED": return "混亂"
		"BLIND": return "失明"
		"PARALYZE": return "麻痺"
		"POISON": return "中毒"
		"ABILITY_SEALED": return "封印"
		_: return s
