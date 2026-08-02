## 回合階段機（GDD §1.3）。
##
##   P0 狀態遞減與持續傷害
##   P1 玩家輸入 → P2 玩家行動解算 → P3 玩家踩踏結算
##   P4 怪物決策（全體依同一份快照）→ P5 怪物執行（序列化）→ P6 怪物踩踏
##   P7 環境：飽足度、自然回復、增援生成
##   P8 死亡結算
##   P9 turn_count += 1
##
## 整個回合在一次呼叫內跑完，回傳有序的 GameEvent 串。View 之後才播動畫。
class_name TurnManager
extends RefCounted

const SPAWN_CAP_EXTRA := 6
const OVERSTAY_TURNS := 1000

var turn_count := 0
var ctx: Dictionary = {}

var _player_pending := 0


func _init(p_ctx: Dictionary) -> void:
	ctx = p_ctx


func _player() -> PlayerEntity:
	return ctx["player"]


func _entities() -> EntityIndex:
	return ctx["entities"]


func _map() -> FloorMap:
	return ctx["map"]


## 執行一個玩家行動所推進的完整世界時間。
func execute_turn(intent: ActionIntent) -> Array:
	var events: Array = []
	var player := _player()

	if not player.is_alive():
		return events

	var world_turn_start := _player_pending <= 0
	if world_turn_start:
		_advance_gauges()

	# ---- P0 ----
	if world_turn_start:
		events.append_array(_phase_status_tick())

	# ---- P1 ~ P3 ----
	var player_events := ActionResolver.resolve_player(intent, ctx)
	if _contains_no_turn(player_events):
		# 撞牆、背包滿之類的無效操作不推進世界
		return player_events
	events.append_array(player_events)
	_player_pending = maxi(0, _player_pending - 1)

	# 玩家倍速時，把下一次輸入權立刻交回去，中間不插入怪物行動
	if _player_pending > 0:
		events.append_array(_refresh_vision())
		return events

	# ---- P4 ~ P6 ----
	events.append_array(_phase_monsters())

	# ---- P7 ----
	events.append_array(_phase_environment())

	# ---- P8 ----
	events.append_array(_phase_deaths())

	# ---- P9 ----
	turn_count += 1
	events.append_array(_refresh_vision())
	events.append(GameEvent.new(GameEvent.Kind.TURN_ADVANCED,
		{ "turn": turn_count }))
	return events


static func _contains_no_turn(events: Array) -> bool:
	for e: GameEvent in events:
		if e.data.get("no_turn", false):
			return true
	return false


# ---------------------------------------------------------------- P0

## 行動點累積器（GDD §1.4）。倍速實體不是「連動兩步」，而是拆成前後半
## 子回合，玩家才能算清逃跑距離。
func _advance_gauges() -> void:
	for e: Entity in _entities().all():
		e.speed_modifier = _speed_modifier_of(e)
		e.gauge += e.speed * e.speed_modifier
		var n := int(e.gauge)
		e.gauge -= n
		if e.is_player:
			_player_pending = maxi(n, 1)
		else:
			e.set_meta("pending", n)


static func _speed_modifier_of(e: Entity) -> float:
	if e.has_status("HASTE"):
		return 2.0
	if e.has_status("SLOW"):
		return 0.5
	return 1.0


func _phase_status_tick() -> Array:
	var events: Array = []
	for e: Entity in _entities().all():
		if not e.is_alive():
			continue
		if e.has_status("POISON"):
			var dmg := e.take_damage(2)
			events.append(GameEvent.new(GameEvent.Kind.DAMAGE_DEALT,
				{ "target_id": e.id, "amount": dmg, "crit": false }, false))
		for s: String in e.tick_statuses():
			events.append(GameEvent.new(GameEvent.Kind.STATUS_REMOVED,
				{ "entity_id": e.id, "status": s }))
			if e.is_player:
				events.append_array(_on_player_status_expired(s))
	return events


func _on_player_status_expired(s: String) -> Array:
	var player := _player()
	match s:
		"GLUTTON":
			player.hunger_rate = 1.0
			return [GameEvent.msg("食慾恢復正常了。")]
		"LUCKY":
			player.crit_rate = 0.05
			return [GameEvent.msg("身體的輕盈感消失了。")]
	return []


# ---------------------------------------------------------------- P4 ~ P6

func _phase_monsters() -> Array:
	var events: Array = []
	var monsters := _entities().monsters()
	var max_actions := 0
	for m: MonsterEntity in monsters:
		max_actions = maxi(max_actions, m.get_meta("pending", 1))

	for sub in max_actions:
		# 每個子回合重建快照。同一子回合內所有怪物依同一份快照決策 ——
		# 這就是「同步行動」：玩家看到的是全體對同一個局面的反應。
		var snap := WorldSnapshot.new(_map(), _entities(), _player())
		var actors: Array = []
		for m: MonsterEntity in _entities().monsters():
			if m.get_meta("pending", 1) > sub:
				actors.append(m)
		if actors.is_empty():
			continue

		_sort_actors(actors, snap.player_pos)

		# P4：決策（純函式，不寫世界狀態）
		var intents := {}
		for m: MonsterEntity in actors:
			intents[m.id] = AIController.decide(m, snap, ctx["rng"])

		# P5：執行（序列化）
		for m: MonsterEntity in actors:
			if not m.is_alive():
				continue
			var it: ActionIntent = intents[m.id]
			it.target_pos.x = sub          # 傳給 View 標記子回合
			events.append_array(ActionResolver.resolve_monster(m, it, ctx))
			if not _player().is_alive():
				return events
	return events


## 決定論排序：特殊怪優先 → 離玩家近的先動 → 生成序號 tie-break。
## 全程不用亂數，重播才會一致（GDD §1.5）。
func _sort_actors(actors: Array, player_pos: Vector2i) -> void:
	var db: ItemDatabase = ctx["db"]
	actors.sort_custom(func(a: MonsterEntity, b: MonsterEntity) -> bool:
		var pa := int(db.profile(a.profile_id).get("priority_class", 5))
		var pb := int(db.profile(b.profile_id).get("priority_class", 5))
		if pa != pb:
			return pa < pb
		var da := Tiles.chebyshev(a.pos, player_pos)
		var dbb := Tiles.chebyshev(b.pos, player_pos)
		if da != dbb:
			return da < dbb
		return a.spawn_id < b.spawn_id)


# ---------------------------------------------------------------- P7

func _phase_environment() -> Array:
	var events: Array = []
	var player := _player()

	# ---- 飽足度 ----
	var before := player.satiety
	var cost := int(PlayerEntity.SATIETY_PER_TURN * player.effective_hunger_rate())
	player.satiety = maxi(0, player.satiety - cost)

	var crossed := _threshold_crossed(before, player.satiety, player.max_satiety)
	if crossed != "":
		events.append(GameEvent.msg(crossed))
	events.append(GameEvent.new(GameEvent.Kind.SATIETY_CHANGED,
		{ "satiety": player.satiety, "max": player.max_satiety },
		crossed == ""))

	if player.satiety <= 0:
		# 空腹：每回合固定 -1，不受防禦影響，且停用自然回復
		var dmg := player.take_damage(1)
		events.append(GameEvent.new(GameEvent.Kind.DAMAGE_DEALT,
			{ "target_id": player.id, "amount": dmg, "starving": true }, false))
	elif not player.has_status("STOMACHACHE"):
		# 自然回復用累積器，避免小數（每回合約 MaxHP / 150）
		player.regen_acc += player.max_hp
		while player.regen_acc >= PlayerEntity.REGEN_THRESHOLD and player.hp < player.max_hp:
			player.regen_acc -= PlayerEntity.REGEN_THRESHOLD
			player.hp += 1

	# ---- 增援生成：不許久留的執行機構（GDD §4.2）----
	var f := _map().floor_index
	var interval := maxi(60, 130 - f * 2)
	var cap := clampi(2 + f / 3, 2, 12) + SPAWN_CAP_EXTRA
	if turn_count > 0 and turn_count % interval == 0 \
			and _entities().monster_count() < cap:
		events.append_array(_spawn_reinforcement(f))

	if turn_count >= OVERSTAY_TURNS:
		events.append(GameEvent.msg("一陣狂風襲來……"))
		events.append(GameEvent.new(GameEvent.Kind.FLOOR_CHANGED,
			{ "next_floor": f + 1, "forced": true }, false))

	return events


static func _threshold_crossed(before: int, after: int, max_v: int) -> String:
	var pct_before := float(before) / float(max_v)
	var pct_after := float(after) / float(max_v)
	if pct_before > 0.30 and pct_after <= 0.30:
		return "肚子有點餓了。"
	if pct_before > 0.10 and pct_after <= 0.10:
		return "肚子餓得咕咕叫！"
	if before > 0 and after <= 0:
		return "肚子餓扁了！再不吃東西就……"
	return ""


## 絕不在玩家視野內憑空出現 —— 憑空冒出的怪是挫折，不是難度。
func _spawn_reinforcement(f: int) -> Array:
	var vision: VisionSystem = ctx["vision"]
	var rng: DeterministicRng = ctx["rng"]
	var db: ItemDatabase = ctx["db"]
	var map := _map()
	var entities := _entities()

	var spots: Array = []
	for p in map.walkable_tiles():
		if not vision.is_visible(p) and not entities.occupied(p):
			spots.append(p)
	if spots.is_empty():
		return []

	var def := db.roll_monster(rng, f)
	if def.is_empty():
		return []
	var m := MonsterEntity.from_def(def, rng.choice(spots), entities.next_id())
	entities.add(m)
	return [GameEvent.new(GameEvent.Kind.MONSTER_SPAWNED,
		{ "entity_id": m.id, "pos": m.pos, "def_id": m.def_id })]


# ---------------------------------------------------------------- P8

func _phase_deaths() -> Array:
	var events: Array = []
	var player := _player()
	var entities := _entities()

	for m: MonsterEntity in entities.all_monsters():
		if m.is_alive():
			continue
		entities.remove(m)
		events.append(GameEvent.new(GameEvent.Kind.ENTITY_DIED,
			{ "entity_id": m.id, "pos": m.pos }, false))
		events.append(GameEvent.msg("打倒了 %s。" % m.display_name))

		# 掉落（含牠生前撿走的道具）
		events.append_array(ActionResolver.resolve_drops(m, ctx))

		# 成長之劍：每次擊殺累積攻擊力
		if player.weapon != null and not player.weapon_trait("KILL_STACK").is_empty():
			player.weapon.kill_stacks += 1

		var levels := player.gain_exp(m.exp_value)
		if levels > 0:
			player.max_hp += (ctx["rng"] as DeterministicRng).randi_range(4, 8) * levels
			player.hp = player.max_hp
			events.append(GameEvent.new(GameEvent.Kind.LEVEL_UP,
				{ "level": player.level }, false))
			events.append(GameEvent.msg("等級提升到 %d！" % player.level))

	if not player.is_alive():
		events.append_array(_resolve_player_death())
	return events


## 死亡結算 Step 1：保命道具檢查（GDD §4.5）。
## 復活草留在背包中就有效 —— 這是整套鑑定機制張力的核心。
func _resolve_player_death() -> Array:
	var player := _player()
	var revive := player.inventory.find_by_def("hrb_revive")
	if revive != null:
		player.inventory.remove(revive)
		player.hp = player.max_hp
		return [
			GameEvent.msg("復活草發出光芒，你重新站了起來！"),
			GameEvent.new(GameEvent.Kind.ITEM_IDENTIFIED,
				{ "def_id": "hrb_revive", "name": "復活草" }, false),
			GameEvent.new(GameEvent.Kind.INVENTORY_CHANGED),
		]
	return [GameEvent.new(GameEvent.Kind.PLAYER_DIED, {
		"floor": _map().floor_index,
		"turn": turn_count,
		"level": player.level,
		"cause": "STARVATION" if player.is_starving() else "KILLED",
	}, false)]


# ---------------------------------------------------------------- 視野

func _refresh_vision() -> Array:
	var vision: VisionSystem = ctx["vision"]
	var result := vision.recompute(_map(), _player().pos)
	return [GameEvent.new(GameEvent.Kind.VISIBILITY_CHANGED, result)]
