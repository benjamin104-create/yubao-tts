## Core 的 headless 測試。
##
##   godot --headless --path godot --script res://tests/test_core.gd
##
## 這支測試證明了架構的核心主張：Core 完全不依賴引擎節點與呈現層，
## 因此可以在 CI 裡跑大量模擬來驗證平衡（架構文件 §6）。
extends SceneTree

var _pass := 0
var _fail := 0


func _init() -> void:
	print("=== Core 測試 ===\n")
	var db := ItemDatabase.new()
	db.load_from("res://data/items.json", "res://data/monsters.json")

	test_database(db)
	test_mapgen(db)
	test_mapgen_stress(db)
	test_identification(db)
	test_combat_formula()
	test_corner_rule()
	test_vision(db)
	test_turn_loop(db)
	test_pot_system(db)
	test_ground_interaction(db)
	test_torneko_mechanics(db)
	test_determinism(db)

	print("\n=== 結果：%d 通過，%d 失敗 ===" % [_pass, _fail])
	quit(1 if _fail > 0 else 0)


func ok(cond: bool, label: String) -> void:
	if cond:
		_pass += 1
		print("  [PASS] %s" % label)
	else:
		_fail += 1
		print("  [FAIL] %s" % label)


func section(name: String) -> void:
	print("\n-- %s" % name)


# ----------------------------------------------------------------

func test_database(db: ItemDatabase) -> void:
	section("資料表")
	ok(db.items.size() >= 70, "道具定義載入 %d 筆" % db.items.size())
	ok(db.monsters.size() == 12, "怪物定義載入 %d 筆" % db.monsters.size())
	ok(db.ai_profiles.size() == 3, "AI profile 載入 %d 種" % db.ai_profiles.size())
	for category: String in IdentificationTable.MASKED:
		var defs: Array = db.items_by_category.get(category, [])
		var pool: Array = db.appearance_pools.get(category, [])
		ok(pool.size() >= defs.size() + 2,
			"%s 外觀池 %d >= 種類 %d + 2 個假外觀" % [category, pool.size(), defs.size()])


func test_mapgen(db: ItemDatabase) -> void:
	section("地圖生成")
	var map := MapGenerator.generate(20260802, 5, db)
	ok(map != null, "生成成功")
	ok(map.rooms.size() >= MapGenerator.MIN_ROOMS,
		"房間數 %d >= %d" % [map.rooms.size(), MapGenerator.MIN_ROOMS])
	ok(map.rooms.size() + map.junctions.size() == 9, "9 個區域全部有節點")
	ok(map.edges.size() >= 8, "連通邊 %d >= 生成樹的 8 條" % map.edges.size())
	ok(map.is_walkable(map.player_spawn), "出生點可站立")
	ok(map.is_walkable(map.stairs_down), "樓梯可站立")
	ok(map.player_spawn != map.stairs_down, "出生點與樓梯不同格")
	ok(not map.floor_items.is_empty(), "有道具 %d 件" % map.floor_items.size())
	ok(not map.monster_spawns.is_empty(), "有怪物 %d 隻" % map.monster_spawns.size())

	# 每層保證至少 1 份食物
	var has_food := false
	for it: ItemInstance in map.floor_items.values():
		if it.category == "food":
			has_food = true
	ok(has_food, "每層保證至少 1 份食物")

	# 外框必為牆（MARGIN=1 的保證之一）
	var border_ok := true
	for x in FloorMap.W:
		if map.is_walkable(Vector2i(x, 0)) or map.is_walkable(Vector2i(x, FloorMap.H - 1)):
			border_ok = false
	ok(border_ok, "地圖外框全為牆")

	print(_render(map))


func test_mapgen_stress(db: ItemDatabase) -> void:
	section("地圖生成壓力測試（300 seed）")
	var fails := 0
	var rooms_total := 0
	for s in range(300):
		var map := MapGenerator.generate(s, 5, db)
		if map == null:
			fails += 1
			continue
		rooms_total += map.rooms.size()
		# 4 向 flood fill：必須用 4 向，8 向會放行實際走不通的地圖
		var reached := _flood4(map, map.player_spawn)
		if reached.size() != map.walkable_tiles().size():
			fails += 1
		elif not reached.has(map.stairs_down):
			fails += 1
	ok(fails == 0, "300 張地圖連通性與樓梯可達性全過（失敗 %d）" % fails)
	print("       平均房間數 %.2f" % (rooms_total / 300.0))


func test_identification(db: ItemDatabase) -> void:
	section("鑑定系統")
	var rng := DeterministicRng.new(123)
	var ident := IdentificationTable.new(db, rng)

	var herb := db.make_by_id("hrb_sleep", rng)
	var name_before := ident.display_name(herb, db)
	ok(name_before != "睡眠草", "未鑑定時顯示外觀名：%s" % name_before)
	ok(name_before.ends_with("的草"), "外觀名格式正確")

	ident.identify("hrb_sleep")
	ok(ident.display_name(herb, db) == "睡眠草", "鑑定後顯示真名")

	# 鑑定是全域的：另一份同種道具立即改顯示
	var herb2 := db.make_by_id("hrb_sleep", rng)
	ok(ident.display_name(herb2, db) == "睡眠草", "鑑定為全域，同種道具一起揭露")

	# 武器種類永遠可見，隱藏的是強化值
	var sword := db.make_by_id("wpn_steel_sword", rng)
	sword.upgrade = 3
	sword.known_modifier = false
	ok(ident.display_name(sword, db) == "鋼之劍", "武器種類可見、強化值隱藏")
	sword.known_modifier = true
	ok(ident.display_name(sword, db) == "鋼之劍 +3", "鑑定強化值後顯示 +3")

	# 外觀映射每局重洗
	var ident2 := IdentificationTable.new(db, DeterministicRng.new(999))
	var differs := 0
	for def_id: String in ident.appearance.keys():
		if ident.appearance[def_id] != ident2.appearance.get(def_id, ""):
			differs += 1
	ok(differs > 0, "換 seed 後外觀映射改變（%d 種不同）" % differs)


func test_combat_formula() -> void:
	section("傷害公式")
	ok(absf(CombatResolver.defense_factor(0) - 1.0) < 0.001, "DEF 0 → 因子 1.000")
	ok(absf(CombatResolver.defense_factor(10) - 0.5245) < 0.001, "DEF 10 → 因子 0.525")
	ok(absf(CombatResolver.defense_factor(18) - 0.3128) < 0.001, "DEF 18 → 因子 0.313")

	# data_spec §3.3 的成長感驗算：擊殺骷髏兵（HP30 / DEF10）所需回合
	var expected := { 8: 3, 12: 2, 18: 2, 24: 1 }
	var atk_by_lv := { 8: 26, 12: 34, 18: 50, 24: 64 }
	for lv: int in [8, 12, 18, 24]:
		var dmg := int(floor(atk_by_lv[lv] * CombatResolver.defense_factor(10)))
		var turns := int(ceil(30.0 / dmg))
		ok(turns == expected[lv],
			"Lv%d ATK%d → 每擊 %d，%d 回合擊殺（規格 %d）"
				% [lv, atk_by_lv[lv], dmg, turns, expected[lv]])

	# 力量成長公式
	var p := PlayerEntity.new()
	for pair in [[1, 8], [10, 20], [20, 33], [30, 46]]:
		p.level = pair[0]
		ok(p.strength() == pair[1], "Lv%d 力量 = %d" % [pair[0], pair[1]])

	# 保底 1 點：永遠不會完全打不動
	var rng := DeterministicRng.new(1)
	ok(CombatResolver.roll_damage(rng, 1, 99, false) == 1, "極端防禦下仍保底 1 傷")

	# 經驗曲線
	ok(PlayerEntity.need_exp(10) == 600, "Lv10→11 需 600 經驗")
	ok(PlayerEntity.need_exp(20) == 2400, "Lv20→21 需 2400 經驗")


func test_corner_rule() -> void:
	section("斜向牆角規則")
	var map := FloorMap.new()
	for p in [Vector2i(1, 1), Vector2i(2, 2), Vector2i(2, 1)]:
		map.set_tile(p, Tiles.ROOM_FLOOR)
	# (1,1) → (2,2)：需要 (2,1) 與 (1,2) 皆非牆。(1,2) 是牆 → 禁止
	ok(not WorldSnapshot.corner_rule_ok(map, Vector2i(1, 1), Vector2i(2, 2)),
		"缺一個正交鄰格 → 禁止斜向切角")
	map.set_tile(Vector2i(1, 2), Tiles.ROOM_FLOOR)
	ok(WorldSnapshot.corner_rule_ok(map, Vector2i(1, 1), Vector2i(2, 2)),
		"兩個正交鄰格皆通 → 允許斜向")
	# 正交移動不受限
	ok(WorldSnapshot.corner_rule_ok(map, Vector2i(1, 1), Vector2i(2, 1)),
		"正交移動不受牆角規則限制")
	# 門口禁止斜向
	var room := Room.new(0, Rect2i(1, 1, 2, 2))
	room.doors.append(Vector2i(1, 1))
	map.rooms = { 0: room }
	ok(not WorldSnapshot.corner_rule_ok(map, Vector2i(1, 1), Vector2i(2, 2)),
		"門口禁止任何斜向進出")


func test_vision(db: ItemDatabase) -> void:
	section("視野系統")
	var map := MapGenerator.generate(4242, 3, db)
	var vision := VisionSystem.new()

	# 站在房間裡 → 整間房可見
	var room: Room = map.rooms.values()[0]
	var inside := Vector2i(room.left() + 1, room.top() + 1)
	vision.recompute(map, inside)
	var all_room_visible := true
	for p in room.all_tiles():
		if not vision.is_visible(p):
			all_room_visible = false
	ok(all_room_visible, "站在房間內 → 整間房揭露（%d 格）" % room.all_tiles().size())
	ok(vision.is_visible(Vector2i(room.left() - 1, room.top() - 1)),
		"房間外圍一圈牆也可見（看得出房間形狀）")

	# 站在通道 → 只看得到周圍 1 格
	var corridor := Vector2i(-1, -1)
	for p in map.walkable_tiles():
		if map.is_corridor(p):
			corridor = p
			break
	if corridor != Vector2i(-1, -1):
		vision.recompute(map, corridor)
		ok(vision.visible_tiles.size() <= 9,
			"站在通道 → 只見周圍 1 格（%d 格）" % vision.visible_tiles.size())

	# 探索記憶只增不減
	var explored_before := vision.explored.size()
	vision.recompute(map, inside)
	ok(vision.explored.size() >= explored_before, "已探索記憶不會減少")


func test_turn_loop(db: ItemDatabase) -> void:
	section("回合主迴圈")
	var host := GameHost.new()
	host.start_run(555, db)

	ok(host.player.is_alive(), "玩家存在且存活")
	ok(host.entities.monster_count() > 0, "場上有 %d 隻怪物" % host.entities.monster_count())
	ok(host.player.weapon != null and host.player.shield != null, "起始裝備已裝上")

	var satiety_before := host.player.satiety
	var turn_before := host.turns.turn_count

	# 撞牆不應推進世界
	var wall_dir := Vector2i.ZERO
	for d in Tiles.DIRS_4:
		if not host.map.is_walkable(host.player.pos + d):
			wall_dir = d
			break
	if wall_dir != Vector2i.ZERO:
		host.submit_intent(ActionIntent.move(wall_dir))
		ok(host.turns.turn_count == turn_before, "撞牆不消耗回合")
		ok(host.player.satiety == satiety_before, "撞牆不消耗飽足度")

	# 走 30 步，怪物必須跟著動
	var moves := 0
	var monster_moved := false
	for i in 30:
		var before_positions := {}
		for m: MonsterEntity in host.entities.monsters():
			before_positions[m.id] = m.pos
		var d: Vector2i = Tiles.DIRS_8[i % 8]
		var events := host.submit_intent(ActionIntent.move(d))
		for e: GameEvent in events:
			if e.kind == GameEvent.Kind.ENTITY_MOVED and e.data["entity_id"] != host.player.id:
				monster_moved = true
		if not events.is_empty():
			moves += 1
	ok(moves > 0, "玩家移動了 %d 次" % moves)
	ok(monster_moved, "怪物在玩家行動後同步行動")
	ok(host.turns.turn_count > turn_before, "回合數推進到 %d" % host.turns.turn_count)
	ok(host.player.satiety < satiety_before,
		"飽足度隨回合下降（%.2f%% → %.2f%%）"
			% [satiety_before / 1000.0, host.player.satiety / 1000.0])

	# 飽足度速率：滿胃約 1000 回合
	var per_turn := float(satiety_before - host.player.satiety) / float(host.turns.turn_count)
	ok(absf(per_turn - 100.0) < 1.0, "每回合消耗 %.1f 毫點（規格 100）" % per_turn)

	host.free()
	test_kill_and_exp(db)


## 擊殺 → 屍體移除 → 給經驗 → 升級。
## 這條路徑曾經整條壞掉（EntityIndex.monsters() 濾掉了屍體，
## 死亡結算因此永遠掃不到），是自動遊玩模擬發現的。
func test_kill_and_exp(db: ItemDatabase) -> void:
	var host := GameHost.new()
	host.start_run(31337, db)

	# 在玩家旁邊放一隻必定被一擊打死的怪
	var spot := Vector2i(-1, -1)
	for d in Tiles.DIRS_4:
		var p: Vector2i = host.player.pos + d
		if host.map.is_walkable(p) and not host.entities.occupied(p):
			spot = p
			break
	ok(spot != Vector2i(-1, -1), "找得到相鄰空格")

	var rat := MonsterEntity.from_def(db.monster_def("mon_cave_rat"),
		spot, host.entities.next_id())
	rat.hp = 1
	rat.exp_value = 100          # 一次就足以升到 Lv5 附近
	host.entities.add(rat)

	var count_before := host.entities.monster_count()
	var level_before := host.player.level
	host.submit_intent(ActionIntent.move(spot - host.player.pos))

	ok(host.entities.monster_count() == count_before - 1, "怪物死亡後從場上移除")
	ok(host.entities.by_id(rat.id) == null, "屍體不再存在於索引中")
	ok(host.player.level > level_before,
		"擊殺獲得經驗並升級（Lv%d → Lv%d）" % [level_before, host.player.level])
	ok(host.player.max_hp > PlayerEntity.BASE_MAX_HP, "升級提高了 HP 上限")

	host.free()


func test_pot_system(db: ItemDatabase) -> void:
	section("壺系統")
	var host := GameHost.new()
	host.start_run(777, db)
	var ctx := host.turns.ctx

	var storage := db.make_by_id("pot_storage", host.rng)
	storage.pot_capacity = 2
	var herb := db.make_by_id("hrb_heal", host.rng)
	host.player.inventory.add(storage)
	host.player.inventory.add(herb)

	ActionResolver.put_into_pot(herb, storage, ctx)
	ok(storage.contents.size() == 1, "道具放入保存壺")
	ok(not host.player.inventory.slots.has(herb), "放入後從背包移除")
	ok(host.ident.is_identified("pot_storage"), "放入即鑑定壺的種類")

	ActionResolver.take_from_pot(herb, storage, ctx)
	ok(storage.contents.is_empty() and host.player.inventory.slots.has(herb),
		"保存壺可以取出")

	# 壺不能放進壺
	var pot2 := db.make_by_id("pot_storage", host.rng)
	host.player.inventory.add(pot2)
	ActionResolver.put_into_pot(pot2, storage, ctx)
	ok(storage.contents.is_empty(), "壺不能放進另一個壺")

	# 吸物壺：放進去就消失
	var devour := db.make_by_id("pot_devour", host.rng)
	var victim := db.make_by_id("hrb_heal", host.rng)
	host.player.inventory.add(devour)
	host.player.inventory.add(victim)
	ActionResolver.put_into_pot(victim, devour, ctx)
	ok(devour.contents.is_empty() and not host.player.inventory.slots.has(victim),
		"吸物壺吞掉道具")

	# 合成壺：強化值疊加且夾在上限內
	var fusion := db.make_by_id("pot_fusion", host.rng)
	fusion.pot_capacity = 4
	var base := db.make_by_id("wpn_steel_sword", host.rng)
	base.upgrade = 3
	var mat := db.make_by_id("wpn_steel_sword", host.rng)
	mat.upgrade = 2
	host.player.inventory.add(fusion)
	host.player.inventory.add(base)
	host.player.inventory.add(mat)
	ActionResolver.put_into_pot(base, fusion, ctx)
	ActionResolver.put_into_pot(mat, fusion, ctx)
	ok(fusion.contents.size() == 1, "合成後只剩基底")
	ok(base.upgrade == 5, "強化值疊加 +3 +2 = +%d" % base.upgrade)

	# 上限夾住：鋼之劍 upgrade_range 上限 +5，再合成不會超過
	var mat2 := db.make_by_id("wpn_steel_sword", host.rng)
	mat2.upgrade = 5
	host.player.inventory.add(mat2)
	ActionResolver.put_into_pot(mat2, fusion, ctx)
	ok(base.upgrade == 5, "強化值夾在上限 +5（實際 +%d）" % base.upgrade)

	host.free()


## 腳下物品：不撿起直接使用、原位替換。
## 「背包滿了還是能用地上的東西」是原作最關鍵的戰術出口。
func test_ground_interaction(db: ItemDatabase) -> void:
	section("腳下物品")
	var host := GameHost.new()
	host.start_run(20260802, db)
	var ctx := host.turns.ctx
	var p := host.player

	# ---- 背包塞滿，再把回復草放到腳下 ----
	while p.inventory.has_space():
		p.inventory.add(db.make_by_id("food_fruit", host.rng))
	ok(not p.inventory.has_space(), "背包已塞滿 %d 格" % p.inventory.size())

	var herb := db.make_by_id("hrb_heal", host.rng)
	host.map.floor_items[p.pos] = herb
	p.hp = 1
	host.ident.identify("hrb_heal")

	# 撿起應該失敗（沒空間），但直接使用要能成功
	var pick_events := ActionResolver.resolve_player(ActionIntent.pickup(), ctx)
	ok(TurnManager._contains_no_turn(pick_events), "背包滿時撿起失敗且不消耗回合")

	ActionResolver.resolve_player(
		ActionIntent.use_ground(herb, ActionIntent.Verb.EAT), ctx)
	ok(p.hp > 1, "背包滿時仍能直接喝掉腳下的草藥（HP → %d）" % p.hp)
	ok(not host.map.floor_items.has(p.pos), "使用後地面物品消失")
	ok(p.inventory.size() == Inventory.CAPACITY, "直接使用不佔用背包格")

	# ---- 揮杖：留在地面，只扣次數 ----
	var wand := db.make_by_id("wnd_knockback", host.rng)
	var uses_before: int = wand.uses
	host.map.floor_items[p.pos] = wand
	ActionResolver.resolve_player(
		ActionIntent.use_ground(wand, ActionIntent.Verb.WAVE, Vector2i(1, 0)), ctx)
	ok(wand.uses == uses_before - 1, "揮杖扣 1 次使用次數")
	ok(host.map.floor_items.get(p.pos) == wand, "杖揮完仍留在地面上")

	# ---- 原位替換 ----
	var ground_sword := db.make_by_id("wpn_steel_sword", host.rng)
	host.map.floor_items[p.pos] = ground_sword
	var slot := 5
	var swapped_out := p.inventory.at(slot)
	var size_before := p.inventory.size()

	ActionResolver.resolve_player(ActionIntent.swap_ground(swapped_out), ctx)
	ok(p.inventory.at(slot) == ground_sword, "地面物品進入原本那個背包格（保持順序）")
	ok(host.map.floor_items.get(p.pos) == swapped_out, "換出去的物品留在地面")
	ok(p.inventory.size() == size_before, "一對一交換，背包容量不變")

	# ---- 詛咒裝備不能替換 ----
	var cursed := db.make_by_id("wpn_club", host.rng)
	cursed.cursed = true
	p.inventory.slots[0] = cursed
	p.weapon = cursed
	host.map.floor_items[p.pos] = db.make_by_id("wpn_bronze_sword", host.rng)

	ActionResolver.resolve_player(ActionIntent.swap_ground(cursed), ctx)
	ok(p.weapon == cursed and p.inventory.at(0) == cursed,
		"詛咒裝備無法替換，仍留在身上")

	# ---- 未裝備的物品替換時不會誤卸裝備 ----
	p.weapon = null
	host.free()


## 原作機制稽核：資料表宣告的每一個特性都必須真的有作用。
## 「JSON 說會發生，程式卻沒做」比沒寫還糟 —— 資料在說謊。
func test_torneko_mechanics(db: ItemDatabase) -> void:
	section("原作機制：命中效果 / 掉落 / 竊取 / 裝備規則")
	var host := GameHost.new()
	host.start_run(88888, db)
	var ctx := host.turns.ctx
	var p := host.player

	# ---- 食腐蟲吸飽足度（on_hit_effects） ----
	var grub := MonsterEntity.from_def(db.monster_def("mon_rot_grub"),
		_adjacent_free(host), host.entities.next_id())
	host.entities.add(grub)
	var satiety_before := p.satiety
	ActionResolver.resolve_monster(grub, ActionIntent.attack(p.pos), ctx)
	ok(p.satiety < satiety_before,
		"食腐蟲命中會吸走飽足度（%.1f%% → %.1f%%）"
			% [satiety_before / 1000.0, p.satiety / 1000.0])
	host.entities.remove(grub)

	# ---- 詛咒法師詛咒裝備 ----
	p.weapon.cursed = false
	var mage := MonsterEntity.from_def(db.monster_def("mon_hex_mage"),
		_adjacent_free(host), host.entities.next_id())
	host.entities.add(mage)
	var cursed_once := false
	for i in 200:
		p.weapon.cursed = false
		p.shield.cursed = false
		ActionResolver.resolve_monster(mage, ActionIntent.attack(p.pos), ctx)
		if p.weapon.cursed or p.shield.cursed:
			cursed_once = true
			break
	ok(cursed_once, "詛咒法師命中會讓裝備變成詛咒")
	p.weapon.cursed = false
	p.shield.cursed = false
	host.entities.remove(mage)

	# ---- 掉落表 ----
	var dropped := false
	for i in 60:
		var m := MonsterEntity.from_def(db.monster_def("mon_crystal_turret"),
			_adjacent_free(host), host.entities.next_id())
		host.map.floor_items.clear()
		var events := ActionResolver.resolve_drops(m, ctx)
		if not host.map.floor_items.is_empty():
			dropped = true
			break
	ok(dropped, "怪物死亡會依 drop_table 掉落道具")

	# ---- 盜賊怪撿走地面道具，死後掉回來 ----
	host.map.floor_items.clear()
	var loot_pos := _adjacent_free(host)
	var loot := db.make_by_id("hrb_heal", host.rng)
	host.map.floor_items[loot_pos] = loot

	var goblin := MonsterEntity.from_def(db.monster_def("mon_green_goblin"),
		loot_pos, host.entities.next_id())
	host.entities.add(goblin)
	host.vision.recompute(host.map, p.pos)
	ActionResolver._step_on(goblin, ctx)
	ok(not host.map.floor_items.has(loot_pos), "哥布林把地上的道具撿走了")
	ok(goblin.carried_items.has(loot), "道具被記在牠身上")

	ActionResolver.resolve_drops(goblin, ctx)
	var recovered := false
	for it: ItemInstance in host.map.floor_items.values():
		if it == loot:
			recovered = true
	ok(recovered, "打倒牠之後道具掉回地面（追殺才拿得回來）")
	host.entities.remove(goblin)

	# ---- 雙手武器佔用盾牌欄 ----
	var great := db.make_by_id("wpn_greatsword", host.rng)
	great.cursed = false
	p.inventory.add(great)
	ActionResolver.resolve_player(ActionIntent.equip(great), ctx)
	ok(p.weapon == great and p.shield == null, "裝備雙手武器會卸下盾牌")

	var shield = db.make_by_id("shd_steel", host.rng)
	p.inventory.add(shield)
	ActionResolver.resolve_player(ActionIntent.equip(shield), ctx)
	ok(p.shield == null, "拿著雙手武器時無法裝備盾牌")

	# ---- 成長之劍累積 ----
	var growth := db.make_by_id("wpn_growth_blade", host.rng)
	growth.cursed = false
	p.inventory.add(growth)
	ActionResolver.resolve_player(ActionIntent.equip(growth), ctx)
	var atk_before := p.get_atk()
	growth.kill_stacks = 50
	ok(p.get_atk() > atk_before,
		"成長之劍隨擊殺累積攻擊力（%d → %d）" % [atk_before, p.get_atk()])
	growth.kill_stacks = 100000
	ok(p.get_atk() - atk_before <= 20, "累積量夾在 cap +20 以內")

	# ---- 鏡之盾反射魔法 ----
	ActionResolver.resolve_player(ActionIntent.equip(growth), ctx)   # 卸下雙手武器
	var mirror := db.make_by_id("shd_mirror", host.rng)
	mirror.cursed = false
	p.inventory.add(mirror)
	p.weapon = null
	p.shield = mirror
	var caster := MonsterEntity.from_def(db.monster_def("mon_hex_mage"),
		_far_free(host), host.entities.next_id())
	host.entities.add(caster)
	var caster_hp := caster.hp
	var player_hp := p.hp
	ActionResolver.resolve_monster(caster, ActionIntent.ranged_attack(p.pos), ctx)
	ok(caster.hp < caster_hp, "鏡之盾把魔法遠程原封反彈回施放者")
	ok(p.hp == player_hp, "反射時玩家不受傷")

	# ---- 徘徊石像免疫擊退 ----
	var golem := MonsterEntity.from_def(db.monster_def("mon_wander_golem"),
		_adjacent_free(host), host.entities.next_id())
	host.entities.add(golem)
	var golem_pos := golem.pos
	ctx["target"] = golem
	EffectResolver.apply([{ "op": "PUSH_TARGET", "distance": 10 }], ctx)
	ok(golem.pos == golem_pos, "徘徊石像免疫擊退，紋風不動")
	ctx.erase("target")

	# ---- PACK：疾風狼成群生成 ----
	var pack_found := false
	for seed_v in range(60):
		var m := MapGenerator.generate(seed_v, 14, db)
		var counts := {}
		for sp: Dictionary in m.monster_spawns:
			counts[sp["id"]] = counts.get(sp["id"], 0) + 1
		if counts.get("mon_gale_wolf", 0) >= 2:
			pack_found = true
			break
	ok(pack_found, "疾風狼成群生成（PACK）")

	host.free()


func _adjacent_free(host: GameHost) -> Vector2i:
	for d in Tiles.DIRS_8:
		var p: Vector2i = host.player.pos + d
		if host.map.is_walkable(p) and not host.entities.occupied(p):
			return p
	return host.player.pos


## 找一格與玩家對齊、有直線視野、距離 3 格以上的位置，供遠程攻擊測試用。
func _far_free(host: GameHost) -> Vector2i:
	for dist in range(3, 8):
		for d in Tiles.DIRS_8:
			var p: Vector2i = host.player.pos + d * dist
			if host.map.is_walkable(p) and not host.entities.occupied(p):
				return p
	return _adjacent_free(host)


func test_determinism(db: ItemDatabase) -> void:
	section("決定論（重播的前提）")
	var trace_a := _run_scripted(db, 31337)
	var trace_b := _run_scripted(db, 31337)
	var trace_c := _run_scripted(db, 31338)
	ok(trace_a == trace_b, "同 seed + 同 Intent 序列 → 完全相同的結果")
	ok(trace_a != trace_c, "換 seed → 結果不同")


func _run_scripted(db: ItemDatabase, seed_value: int) -> String:
	var host := GameHost.new()
	host.start_run(seed_value, db)
	var out := PackedStringArray()
	for i in 40:
		host.submit_intent(ActionIntent.move(Tiles.DIRS_8[i % 8]))
		out.append("%d,%d" % [host.player.pos.x, host.player.pos.y])
		for m: MonsterEntity in host.entities.monsters():
			out.append("%d:%d,%d:%d" % [m.id, m.pos.x, m.pos.y, m.hp])
	var s := "|".join(out)
	host.free()
	return s


# ---------------------------------------------------------------- 工具

func _flood4(map: FloorMap, start: Vector2i) -> Dictionary:
	var seen := { start: true }
	var q: Array[Vector2i] = [start]
	var head := 0
	while head < q.size():
		var cur := q[head]
		head += 1
		for d in Tiles.DIRS_4:
			var n: Vector2i = cur + d
			if map.is_walkable(n) and not seen.has(n):
				seen[n] = true
				q.append(n)
	return seen


func _render(map: FloorMap) -> String:
	var lines := PackedStringArray()
	for y in FloorMap.H:
		var row := ""
		for x in FloorMap.W:
			var p := Vector2i(x, y)
			var ch := "#"
			match map.get_tile(p):
				Tiles.ROOM_FLOOR: ch = "."
				Tiles.CORRIDOR: ch = "+"
				Tiles.STAIRS_DOWN: ch = ">"
			if map.traps.has(p): ch = "^"
			if map.floor_gold.has(p): ch = "$"
			if map.floor_items.has(p): ch = "!"
			for s: Dictionary in map.monster_spawns:
				if s["pos"] == p: ch = "M"
			if p == map.stairs_down: ch = ">"
			if p == map.player_spawn: ch = "@"
			row += ch
		lines.append("       " + row)
	return "\n".join(lines)
