## 把 ActionIntent 變成實際的狀態變更與事件。
##
## 這裡是所有「規則」的落點：撞牆會不會消耗回合、詛咒裝備能不能卸下、
## 放進吸物壺會發生什麼。UI 一律不得自己做這些判斷（架構文件 §4）。
class_name ActionResolver
extends RefCounted


# ================================================================ 玩家

static func resolve_player(intent: ActionIntent, ctx: Dictionary) -> Array:
	var ev: Array = []
	var player: PlayerEntity = ctx["player"]

	# 混亂：移動與攻擊方向隨機化。UI 上仍照玩家按的方向送 Intent，
	# 由這裡改寫 —— 玩家因此會看到「我明明按右邊」的錯亂感。
	if player.has_status("CONFUSED") and intent.kind == ActionIntent.Kind.MOVE:
		intent = ActionIntent.move((ctx["rng"] as DeterministicRng).choice(Tiles.DIRS_8))

	match intent.kind:
		ActionIntent.Kind.MOVE:
			ev.append_array(_player_move(intent.dir, ctx))
		ActionIntent.Kind.PICKUP:
			ev.append_array(_pickup(ctx))
		ActionIntent.Kind.DROP:
			ev.append_array(_drop(intent.item, ctx))
		ActionIntent.Kind.DESCEND:
			ev.append_array(_descend(ctx))
		ActionIntent.Kind.EQUIP:
			ev.append_array(_equip(intent.item, ctx))
		ActionIntent.Kind.USE_ITEM:
			ev.append_array(use_item(intent.item, intent.verb, intent.dir, ctx))
		ActionIntent.Kind.THROW_ITEM:
			ev.append_array(_throw(intent.item, intent.dir, ctx))
		ActionIntent.Kind.PUT_INTO_POT:
			ev.append_array(put_into_pot(intent.item, intent.container, ctx))
		ActionIntent.Kind.TAKE_FROM_POT:
			ev.append_array(take_from_pot(intent.item, intent.container, ctx))
		_:
			ev.append(GameEvent.msg("原地待機。"))

	return ev


static func _player_move(dir: Vector2i, ctx: Dictionary) -> Array:
	var ev: Array = []
	var player: PlayerEntity = ctx["player"]
	var map: FloorMap = ctx["map"]
	var entities: EntityIndex = ctx["entities"]
	var to := player.pos + dir

	var occupant := entities.at(to)
	if occupant != null and not occupant.is_player:
		# 撞擊即攻擊
		return _melee(player, occupant, ctx)

	if not map.is_walkable(to):
		# 撞牆不消耗回合（回合的消耗由 TurnManager 依事件判斷）
		ev.append(GameEvent.new(GameEvent.Kind.MESSAGE,
			{ "text": "前面是牆壁。", "no_turn": true }, false))
		return ev

	if not WorldSnapshot.corner_rule_ok(map, player.pos, to):
		ev.append(GameEvent.new(GameEvent.Kind.MESSAGE,
			{ "text": "沒辦法從這個角度過去。", "no_turn": true }, false))
		return ev

	var from := player.pos
	entities.move_entity(player, to)
	ev.append(GameEvent.moved(player, from, to))
	ev.append_array(_step_on(player, ctx))
	return ev


## 踩踏結算：陷阱、金錢自動撿取、樓梯提示。道具不自動撿 ——
## 自動撿會讓背包在滿的時候產生大量惱人訊息，也剝奪玩家的取捨。
static func _step_on(e: Entity, ctx: Dictionary) -> Array:
	var ev: Array = []
	var map: FloorMap = ctx["map"]
	var player: PlayerEntity = ctx["player"]

	if map.floor_gold.has(e.pos) and e.is_player:
		var amount: int = map.floor_gold[e.pos]
		map.floor_gold.erase(e.pos)
		player.gold += amount
		ev.append(GameEvent.msg("撿到了 %d G。" % amount))

	if map.traps.has(e.pos):
		map.traps.erase(e.pos)
		var dmg := e.take_damage(maxi(1, e.max_hp / 8))
		ev.append(GameEvent.new(GameEvent.Kind.TRAP_TRIGGERED,
			{ "entity_id": e.id, "pos": e.pos, "damage": dmg }, false))
		ev.append(GameEvent.msg("%s 踩到了陷阱！受到 %d 點傷害。"
			% [e.display_name, dmg]))

	if e.is_player and map.floor_items.has(e.pos):
		var it: ItemInstance = map.floor_items[e.pos]
		ev.append(GameEvent.msg("腳下有「%s」。（G 撿取）"
			% (ctx["ident"] as IdentificationTable).display_name(it, ctx["db"])))

	if e.is_player and e.pos == map.stairs_down:
		ev.append(GameEvent.msg("這裡有向下的樓梯。（> 下樓）"))

	return ev


static func _melee(attacker: Entity, target: Entity, ctx: Dictionary) -> Array:
	var ev: Array = []
	var rng: DeterministicRng = ctx["rng"]

	var mult := 1.0
	# 遠程怪貼身時攻擊力打折 —— 明確獎勵「貼上去」這個正解
	if attacker is MonsterEntity:
		var am := attacker as MonsterEntity
		if am.is_ranged():
			mult *= am.melee_penalty
	# 剋星特效（斬鬼刀 vs oni 族）
	if attacker is PlayerEntity and target is MonsterEntity:
		mult *= _slayer_multiplier(attacker as PlayerEntity, target as MonsterEntity, ctx)

	ev.append(GameEvent.new(GameEvent.Kind.ENTITY_ATTACKED,
		{ "attacker_id": attacker.id, "target_id": target.id }))

	var result := CombatResolver.resolve_attack(rng, attacker, target, mult)
	if not result["hit"]:
		ev.append(GameEvent.new(GameEvent.Kind.ATTACK_MISSED,
			{ "attacker_id": attacker.id, "target_id": target.id }, false))
		ev.append(GameEvent.msg("%s 的攻擊落空了。" % attacker.display_name))
		return ev

	var dealt: int = target.take_damage(result["damage"])
	ev.append(GameEvent.new(GameEvent.Kind.DAMAGE_DEALT, {
		"target_id": target.id, "amount": dealt, "crit": result["crit"],
	}, not result["crit"]))
	ev.append(GameEvent.msg("%s 對 %s 造成 %d 點傷害%s"
		% [attacker.display_name, target.display_name, dealt,
			"（會心一擊！）" if result["crit"] else "。"]))

	# 反擊（深淵騎士）—— 讓「純近戰硬拚」不再是最優解
	if target is MonsterEntity and target.is_alive() and attacker.is_player:
		var tm := target as MonsterEntity
		var c := tm.trait_of("COUNTER")
		if not c.is_empty() and rng.chance(float(c.get("chance", 0.0))):
			var back := CombatResolver.roll_damage(rng, tm.get_atk(),
				attacker.get_defense(), false, float(c.get("ratio", 0.5)))
			var taken := attacker.take_damage(back)
			ev.append(GameEvent.new(GameEvent.Kind.DAMAGE_DEALT,
				{ "target_id": attacker.id, "amount": taken, "crit": false }, false))
			ev.append(GameEvent.msg("%s 發動了反擊！" % tm.display_name))

	return ev


static func _slayer_multiplier(p: PlayerEntity, m: MonsterEntity,
		ctx: Dictionary) -> float:
	if p.weapon == null:
		return 1.0
	var def := (ctx["db"] as ItemDatabase).item_def(p.weapon.def_id)
	for t: Dictionary in def.get("traits", []):
		if t.get("type", "") == "SLAYER" \
				and t.get("family", "") == (ctx["db"] as ItemDatabase) \
					.monster_def(m.def_id).get("family", ""):
			return float(t.get("multiplier", 1.0))
	return 1.0


# ---------------------------------------------------------------- 背包操作

static func _pickup(ctx: Dictionary) -> Array:
	var ev: Array = []
	var player: PlayerEntity = ctx["player"]
	var map: FloorMap = ctx["map"]
	if not map.floor_items.has(player.pos):
		ev.append(GameEvent.new(GameEvent.Kind.MESSAGE,
			{ "text": "腳下沒有東西。", "no_turn": true }, false))
		return ev
	if not player.inventory.has_space():
		ev.append(GameEvent.new(GameEvent.Kind.MESSAGE,
			{ "text": "背包已經滿了。", "no_turn": true }, false))
		return ev
	var it: ItemInstance = map.floor_items[player.pos]
	map.floor_items.erase(player.pos)
	player.inventory.add(it)
	ev.append(GameEvent.new(GameEvent.Kind.ITEM_PICKED_UP,
		{ "def_id": it.def_id, "pos": player.pos }))
	ev.append(GameEvent.msg("撿起了「%s」。"
		% (ctx["ident"] as IdentificationTable).display_name(it, ctx["db"])))
	ev.append(GameEvent.new(GameEvent.Kind.INVENTORY_CHANGED))
	return ev


static func _drop(item: ItemInstance, ctx: Dictionary) -> Array:
	var ev: Array = []
	var player: PlayerEntity = ctx["player"]
	var map: FloorMap = ctx["map"]
	if item == null:
		return ev
	if map.floor_items.has(player.pos):
		ev.append(GameEvent.new(GameEvent.Kind.MESSAGE,
			{ "text": "腳下已經有東西了。", "no_turn": true }, false))
		return ev
	if item.cursed and (item == player.weapon or item == player.shield):
		ev.append(GameEvent.msg("被詛咒了，拿不下來！"))
		item.known_modifier = true
		return ev
	player.inventory.remove(item)
	if item == player.weapon:
		player.weapon = null
	if item == player.shield:
		player.shield = null
	map.floor_items[player.pos] = item
	ev.append(GameEvent.new(GameEvent.Kind.ITEM_DROPPED,
		{ "def_id": item.def_id, "pos": player.pos }))
	ev.append(GameEvent.new(GameEvent.Kind.INVENTORY_CHANGED))
	return ev


static func _equip(item: ItemInstance, ctx: Dictionary) -> Array:
	var ev: Array = []
	var player: PlayerEntity = ctx["player"]
	if item == null or not item.is_equipment():
		return ev

	var slot_is_weapon := item.category == "weapon"
	var current: ItemInstance = player.weapon if slot_is_weapon else player.shield

	if current == item:
		# 卸下。詛咒裝備卸下失敗仍消耗 1 回合（GDD §1.2）
		if item.cursed:
			item.known_modifier = true
			ev.append(GameEvent.msg("「%s」被詛咒了，拿不下來！"
				% (ctx["ident"] as IdentificationTable).display_name(item, ctx["db"])))
			return ev
		if slot_is_weapon:
			player.weapon = null
		else:
			player.shield = null
		ev.append(GameEvent.msg("卸下了裝備。"))
		ev.append(GameEvent.new(GameEvent.Kind.INVENTORY_CHANGED))
		return ev

	if current != null and current.cursed:
		current.known_modifier = true
		ev.append(GameEvent.msg("身上的裝備被詛咒了，換不下來！"))
		return ev

	if slot_is_weapon:
		player.weapon = item
	else:
		player.shield = item
	# 裝上身即揭露強化值與詛咒 —— 這是「換不換？可能卸不下來」的張力來源
	item.known_modifier = true
	var name := (ctx["ident"] as IdentificationTable).display_name(item, ctx["db"])
	ev.append(GameEvent.msg("裝備了「%s」。" % name))
	if item.cursed:
		ev.append(GameEvent.msg("……手上傳來一陣寒意。這是被詛咒的裝備！"))
	ev.append(GameEvent.new(GameEvent.Kind.INVENTORY_CHANGED))
	return ev


static func _descend(ctx: Dictionary) -> Array:
	var player: PlayerEntity = ctx["player"]
	var map: FloorMap = ctx["map"]
	if player.pos != map.stairs_down:
		return [GameEvent.new(GameEvent.Kind.MESSAGE,
			{ "text": "這裡沒有樓梯。", "no_turn": true }, false)]
	return [GameEvent.new(GameEvent.Kind.FLOOR_CHANGED,
		{ "next_floor": map.floor_index + 1 }, false)]


# ---------------------------------------------------------------- 四種動詞

static func use_item(item: ItemInstance, verb: int, dir: Vector2i,
		ctx: Dictionary) -> Array:
	var ev: Array = []
	if item == null:
		return ev
	var player: PlayerEntity = ctx["player"]
	var db: ItemDatabase = ctx["db"]
	var ident: IdentificationTable = ctx["ident"]
	var def := db.item_def(item.def_id)
	var shown := ident.display_name(item, db)

	match verb:
		ActionIntent.Verb.EAT:
			if item.category == "food":
				var gain := int(def.get("satiety_value", 0))
				var expand := player.eat(gain)
				ev.append(GameEvent.msg("吃掉了「%s」。" % shown))
				if expand > 0:
					ev.append(GameEvent.msg("胃袋似乎變大了一點。"))
				ev.append(GameEvent.new(GameEvent.Kind.SATIETY_CHANGED,
					{ "satiety": player.satiety, "max": player.max_satiety }, false))
				ev.append_array(EffectResolver.apply(def.get("effects", []), ctx))
			elif item.category == "herb":
				ev.append(GameEvent.msg("喝下了「%s」。" % shown))
				ev.append_array(EffectResolver.apply(def.get("effects", []), ctx))
			else:
				return [GameEvent.new(GameEvent.Kind.MESSAGE,
					{ "text": "這個東西不能吃。", "no_turn": true }, false)]
			player.inventory.remove(item)

		ActionIntent.Verb.READ:
			if item.category != "scroll":
				return [GameEvent.new(GameEvent.Kind.MESSAGE,
					{ "text": "這個東西沒有字。", "no_turn": true }, false)]
			ev.append(GameEvent.msg("讀了「%s」。" % shown))
			ctx["chosen_item"] = _auto_target_item(item.def_id, ctx)
			ev.append_array(EffectResolver.apply(def.get("effects", []), ctx))
			player.inventory.remove(item)

		ActionIntent.Verb.WAVE:
			if item.category != "wand":
				return [GameEvent.new(GameEvent.Kind.MESSAGE,
					{ "text": "這個東西不能揮。", "no_turn": true }, false)]
			if item.uses <= 0:
				ev.append(GameEvent.msg("「%s」已經沒有效力了。" % shown))
				return ev
			item.uses -= 1
			ev.append(GameEvent.msg("揮動了「%s」。" % shown))
			var target := _first_entity_in_line(player.pos, dir,
				int(def.get("range", 10)), ctx)
			if target == null:
				# 打到牆：仍消耗次數與回合，且不鑑定 —— 這正是
				# 「留一隻弱怪當試杖靶」成為必要戰術的原因
				ev.append(GameEvent.new(GameEvent.Kind.MESSAGE,
					{ "text": "魔力射向遠方，什麼也沒發生。", "no_identify": true }, false))
				return ev
			ctx["target"] = target
			ev.append_array(EffectResolver.apply(def.get("effects", []), ctx))

		ActionIntent.Verb.THROW:
			return _throw(item, dir, ctx)

	# 效果明顯者立即全域鑑定（data_spec §1.6 的 IMMEDIATE）
	if _should_identify(def, ev):
		if ident.identify(item.def_id):
			ev.append(GameEvent.new(GameEvent.Kind.ITEM_IDENTIFIED,
				{ "def_id": item.def_id, "name": db.true_name(item.def_id) }, false))
	ev.append(GameEvent.new(GameEvent.Kind.INVENTORY_CHANGED))
	return ev


## CONDITIONAL / DELAYED 的道具在情境不成立時不鑑定。
## EffectResolver 會在事件裡標 no_identify，這裡據此判斷。
static func _should_identify(def: Dictionary, events: Array) -> bool:
	var mode := String(def.get("identify_on_use", "IMMEDIATE"))
	if mode == "DELAYED":
		return false
	for e: GameEvent in events:
		if e.data.get("no_identify", false):
			return false
	return true


## 需要指定對象的卷軸（鑑定／強化）暫時自動挑選。
## 正式版應該由 UI 彈出目標選擇器 —— 這是 F 階段之後的工作。
static func _auto_target_item(scroll_def_id: String, ctx: Dictionary) -> ItemInstance:
	var player: PlayerEntity = ctx["player"]
	var ident: IdentificationTable = ctx["ident"]
	match scroll_def_id:
		"scr_enchant":
			return player.weapon if player.weapon != null else player.shield
		"scr_identify":
			for it: ItemInstance in player.inventory.slots:
				if not ident.is_identified(it.def_id) and it.category in IdentificationTable.MASKED:
					return it
			for it: ItemInstance in player.inventory.slots:
				if it.is_equipment() and not it.known_modifier:
					return it
	return null


static func _first_entity_in_line(from: Vector2i, dir: Vector2i, max_range: int,
		ctx: Dictionary) -> Entity:
	var map: FloorMap = ctx["map"]
	var entities: EntityIndex = ctx["entities"]
	if dir == Vector2i.ZERO:
		return null
	var cur := from + dir
	for i in max_range:
		if not map.is_walkable(cur):
			return null
		var e := entities.at(cur)
		if e != null:
			return e
		cur += dir
	return null


static func _throw(item: ItemInstance, dir: Vector2i, ctx: Dictionary) -> Array:
	var ev: Array = []
	var player: PlayerEntity = ctx["player"]
	var map: FloorMap = ctx["map"]
	var db: ItemDatabase = ctx["db"]
	var ident: IdentificationTable = ctx["ident"]
	if item == null or dir == Vector2i.ZERO:
		return [GameEvent.new(GameEvent.Kind.MESSAGE,
			{ "text": "沒有指定方向。", "no_turn": true }, false)]

	var def := db.item_def(item.def_id)
	player.inventory.remove(item)
	if item == player.weapon:
		player.weapon = null
	if item == player.shield:
		player.shield = null

	var target := _first_entity_in_line(player.pos, dir, 10, ctx)
	ev.append(GameEvent.new(GameEvent.Kind.ITEM_THROWN, {
		"def_id": item.def_id, "from": player.pos,
		"to": target.pos if target != null else player.pos,
	}))
	ev.append(GameEvent.msg("投擲了「%s」。" % ident.display_name(item, db)))

	if target == null:
		# 落地。找不到落點就消失（極少見）
		var landing := player.pos + dir
		while map.is_walkable(landing + dir):
			landing += dir
		if not map.floor_items.has(landing):
			map.floor_items[landing] = item
		ev.append(GameEvent.new(GameEvent.Kind.INVENTORY_CHANGED))
		return ev

	ctx["target"] = target
	var throw_effect: Array = def.get("throw_effect", [])
	if not throw_effect.is_empty():
		ev.append_array(EffectResolver.apply(throw_effect, ctx))
		if ident.identify(item.def_id):
			ev.append(GameEvent.new(GameEvent.Kind.ITEM_IDENTIFIED,
				{ "def_id": item.def_id, "name": db.true_name(item.def_id) }, false))
	else:
		var dmg := CombatResolver.roll_damage(ctx["rng"], 8, target.get_defense(), false)
		var dealt := target.take_damage(dmg)
		ev.append(GameEvent.new(GameEvent.Kind.DAMAGE_DEALT,
			{ "target_id": target.id, "amount": dealt, "crit": false }, false))

	ev.append(GameEvent.new(GameEvent.Kind.INVENTORY_CHANGED))
	return ev


# ---------------------------------------------------------------- 壺

## 所有檢查都在資料層做。UI 的禁用按鈕只是提示，不是防線 ——
## 拖放路徑與程式呼叫路徑都能繞過 UI。
static func put_into_pot(item: ItemInstance, pot: ItemInstance,
		ctx: Dictionary) -> Array:
	var ev: Array = []
	var player: PlayerEntity = ctx["player"]
	var db: ItemDatabase = ctx["db"]
	var ident: IdentificationTable = ctx["ident"]

	if item == null or pot == null or not pot.is_pot():
		return [GameEvent.new(GameEvent.Kind.MESSAGE,
			{ "text": "沒辦法這樣做。", "no_turn": true }, false)]
	if item == pot:
		return [GameEvent.new(GameEvent.Kind.MESSAGE,
			{ "text": "不能把壺放進自己裡面。", "no_turn": true }, false)]
	# 任何壺都不能放進壺 —— 否則巢狀容器會讓背包上限失去意義
	if item.is_pot():
		return [GameEvent.new(GameEvent.Kind.MESSAGE,
			{ "text": "壺沒辦法放進另一個壺裡。", "no_turn": true }, false)]
	if pot.is_full():
		return [GameEvent.new(GameEvent.Kind.MESSAGE,
			{ "text": "壺已經滿了。", "no_turn": true }, false)]

	player.inventory.remove(item)
	var item_name := ident.display_name(item, db)

	match pot.pot_behavior:
		"storage", "vault":
			pot.contents.append(item)
			ev.append(GameEvent.msg("把「%s」放進了壺裡。" % item_name))
		"identify":
			ctx["chosen_item"] = item
			ev.append_array(EffectResolver.apply([{ "op": "IDENTIFY_ITEM" }], ctx))
			pot.contents.append(item)
		"dispel":
			item.cursed = false
			pot.contents.append(item)
			ev.append(GameEvent.msg("「%s」的詛咒被淨化了。" % item_name))
		"change":
			var rng: DeterministicRng = ctx["rng"]
			var pool: Array = db.items_by_category.get(item.category, [])
			var new_def: Dictionary = rng.choice(pool) if not pool.is_empty() else {}
			if new_def.is_empty():
				pot.contents.append(item)
			else:
				var new_item := db.make_instance(new_def, rng)
				pot.contents.append(new_item)
				ev.append(GameEvent.msg("「%s」變成了「%s」！"
					% [item_name, ident.display_name(new_item, db)]))
		"copy":
			pot.contents.append(item)
			var copy := item.duplicate_instance()
			if player.inventory.add(copy):
				ev.append(GameEvent.msg("「%s」被複製了一份！" % item_name))
			else:
				ev.append(GameEvent.msg("複製出來了，但背包放不下。"))
		"devour":
			ev.append(GameEvent.msg("「%s」被壺吸了進去，消失無蹤。" % item_name))
		"cursed":
			pot.contents.append(item)
			ev.append(GameEvent.msg("放進去了……但好像拿不出來了。"))
		"fusion":
			pot.contents.append(item)
			ev.append_array(_process_synthesis(pot, ctx))
		_:
			pot.contents.append(item)

	# 放入即鑑定壺的種類
	if ident.identify(pot.def_id):
		ev.append(GameEvent.new(GameEvent.Kind.ITEM_IDENTIFIED,
			{ "def_id": pot.def_id, "name": db.true_name(pot.def_id) }, false))
	ev.append(GameEvent.new(GameEvent.Kind.INVENTORY_CHANGED))
	return ev


static func take_from_pot(item: ItemInstance, pot: ItemInstance,
		ctx: Dictionary) -> Array:
	var player: PlayerEntity = ctx["player"]
	if pot == null or item == null or not pot.contents.has(item):
		return [GameEvent.new(GameEvent.Kind.MESSAGE,
			{ "text": "沒辦法這樣做。", "no_turn": true }, false)]
	if not pot.can_extract_directly():
		return [GameEvent.new(GameEvent.Kind.MESSAGE,
			{ "text": "這個壺沒辦法把東西拿出來。", "no_turn": true }, false)]
	if not player.inventory.has_space():
		return [GameEvent.new(GameEvent.Kind.MESSAGE,
			{ "text": "背包已經滿了。", "no_turn": true }, false)]
	pot.contents.erase(item)
	player.inventory.add(item)
	return [
		GameEvent.msg("從壺中取出了「%s」。"
			% (ctx["ident"] as IdentificationTable).display_name(item, ctx["db"])),
		GameEvent.new(GameEvent.Kind.INVENTORY_CHANGED),
	]


## 合成。基底為 contents[0]，材料為「最新放入的那一件」——
## 不可寫成 contents[1]：合成失敗時不移除材料，內容物會累積，
## 索引 1 就會一直指向同一件舊物品。
static func _process_synthesis(pot: ItemInstance, ctx: Dictionary) -> Array:
	var ev: Array = []
	if pot.contents.size() < 2:
		return ev
	var db: ItemDatabase = ctx["db"]
	var base: ItemInstance = pot.contents[0]
	var ingredient: ItemInstance = pot.contents[pot.contents.size() - 1]

	if base.category != ingredient.category or not base.is_equipment():
		ev.append(GameEvent.msg("兩件東西沒辦法合在一起。"))
		return ev

	var def := db.item_def(base.def_id)
	var ur: Array = def.get("upgrade_range", [0, 0])
	# 上限必須夾住，否則配合複製壺可以無限疊加
	base.upgrade = mini(base.upgrade + ingredient.upgrade, int(ur[1]))
	base.known_modifier = true
	if ingredient.cursed:
		base.cursed = true
	pot.contents.erase(ingredient)

	ev.append(GameEvent.msg("「%s」得到了強化！（%+d）"
		% [db.true_name(base.def_id), base.upgrade]))
	return ev


# ================================================================ 怪物

## 執行怪物的 Intent。目標格被同伴佔走時只走 fallback，不重跑 AI ——
## 重跑會讓決策依賴執行順序，破壞同步性。
static func resolve_monster(m: MonsterEntity, intent: ActionIntent,
		ctx: Dictionary) -> Array:
	var ev: Array = []
	var map: FloorMap = ctx["map"]
	var entities: EntityIndex = ctx["entities"]
	var player: PlayerEntity = ctx["player"]

	match intent.kind:
		ActionIntent.Kind.ATTACK:
			ev.append_array(_melee(m, player, ctx))

		ActionIntent.Kind.RANGED_ATTACK:
			ev.append(GameEvent.new(GameEvent.Kind.ENTITY_ATTACKED,
				{ "attacker_id": m.id, "target_id": player.id, "ranged": true }))
			var result := CombatResolver.resolve_attack(ctx["rng"], m, player)
			if result["hit"]:
				var dealt: int = player.take_damage(result["damage"])
				ev.append(GameEvent.new(GameEvent.Kind.DAMAGE_DEALT,
					{ "target_id": player.id, "amount": dealt,
						"crit": result["crit"], "ranged": true }, false))
				ev.append(GameEvent.msg("%s 的遠程攻擊命中！受到 %d 點傷害。"
					% [m.display_name, dealt]))
			else:
				ev.append(GameEvent.msg("%s 的遠程攻擊落空了。" % m.display_name))

		ActionIntent.Kind.MOVE:
			var to := m.pos + intent.dir
			if map.is_walkable(to) and not entities.occupied(to) \
					and WorldSnapshot.corner_rule_ok(map, m.pos, to):
				var from := m.pos
				entities.move_entity(m, to)
				m.last_dir = intent.dir
				ev.append(GameEvent.moved(m, from, to, intent.target_pos.x))
				ev.append_array(_step_on(m, ctx))
			else:
				var alt := _fallback_dir(m, intent.dir, ctx)
				if alt != Vector2i.ZERO:
					var from := m.pos
					entities.move_entity(m, m.pos + alt)
					m.last_dir = alt
					ev.append(GameEvent.moved(m, from, m.pos))
					ev.append_array(_step_on(m, ctx))
		_:
			pass

	# 攻擊到玩家的 WANDERER 也會被玩家的反擊觸發 aggro，統一在這裡處理
	return ev


## 目標格被佔走時的次佳方向：只考慮與原方向相鄰的兩個斜角，
## 避免怪物突然往完全相反的方向跑。
static func _fallback_dir(m: MonsterEntity, want: Vector2i,
		ctx: Dictionary) -> Vector2i:
	var map: FloorMap = ctx["map"]
	var entities: EntityIndex = ctx["entities"]
	var i := Tiles.DIRS_8.find(want)
	if i < 0:
		return Vector2i.ZERO
	for offset in [1, -1]:
		var d: Vector2i = Tiles.DIRS_8[(i + offset + 8) % 8]
		var to: Vector2i = m.pos + d
		if map.is_walkable(to) and not entities.occupied(to) \
				and WorldSnapshot.corner_rule_ok(map, m.pos, to):
			return d
	return Vector2i.ZERO
