## 轉接層：唯一同時認識 Core 與引擎的一層。
##
## 職責：持有 Core 狀態、接收 Intent、驅動 TurnManager、把事件串派發出去。
## 它自己不做任何遊戲規則判斷 —— 規則全在 core/ 裡。
##
## turn_ended 是「通知」而不是「機制」：怪物的行動由 TurnManager 在
## execute_turn() 內部依序列化順序執行完畢，不是靠這個訊號去驅動。
## 用訊號驅動怪物會失去決定論的執行順序，重播與同步性都會壞掉 ——
## 訊號只用來讓 UI / 音效 / 統計知道「一回合結束了」。
class_name GameHost
extends Node

signal turn_ended(turn_count: int)
signal events_ready(events: Array)
signal floor_changed(floor_index: int)
signal player_died(record: Dictionary)
signal inventory_changed()

var db: ItemDatabase
var rng: DeterministicRng
var ident: IdentificationTable
var vision: VisionSystem
var entities: EntityIndex
var player: PlayerEntity
var map: FloorMap
var turns: TurnManager

var run_seed := 0
var floor_index := 1
var is_game_over := false
var pending_floor := -1


func start_run(p_seed: int = 0, p_db: ItemDatabase = null) -> void:
	run_seed = p_seed if p_seed != 0 else int(Time.get_unix_time_from_system())
	db = p_db if p_db != null else ItemDatabase.load_default()
	rng = DeterministicRng.new(DeterministicRng.hash64([run_seed, 0xA11CE]))

	# 外觀映射每局重洗 —— 跨局不繼承是鑑定機制存活的前提（GDD §4.5）
	ident = IdentificationTable.new(db, rng)
	vision = VisionSystem.new()

	player = PlayerEntity.new()
	player.db = db
	_give_starting_kit()

	floor_index = 1
	is_game_over = false
	_build_floor(floor_index)


func _give_starting_kit() -> void:
	for def_id in ["wpn_club", "shd_leather", "food_big_bread", "hrb_heal"]:
		var it := db.make_by_id(def_id, rng)
		if it == null:
			continue
		if it.is_equipment():
			it.upgrade = 0
			it.cursed = false
			it.known_modifier = true
		player.inventory.add(it)
	player.weapon = player.inventory.find_by_def("wpn_club")
	player.shield = player.inventory.find_by_def("shd_leather")


func _build_floor(f: int) -> void:
	map = MapGenerator.generate(run_seed, f, db)
	entities = EntityIndex.new()
	vision.reset()

	player.id = entities.next_id()
	player.pos = map.player_spawn
	entities.add(player)

	for spawn: Dictionary in map.monster_spawns:
		var def := db.monster_def(spawn["id"])
		if def.is_empty():
			continue
		var m := MonsterEntity.from_def(def, spawn["pos"], entities.next_id())
		entities.add(m)

	turns = TurnManager.new({
		"player": player, "map": map, "entities": entities,
		"rng": rng, "ident": ident, "db": db, "vision": vision,
	})
	vision.recompute(map, player.pos)
	floor_changed.emit(f)


## 送出一個玩家行動。回傳完整的事件串（同時也透過訊號派發）。
func submit_intent(intent: ActionIntent) -> Array:
	if is_game_over or player == null or not player.is_alive():
		return []

	var events := turns.execute_turn(intent)
	events_ready.emit(events)

	for e: GameEvent in events:
		match e.kind:
			GameEvent.Kind.INVENTORY_CHANGED:
				inventory_changed.emit()
			GameEvent.Kind.TURN_ADVANCED:
				turn_ended.emit(turns.turn_count)
			GameEvent.Kind.FLOOR_CHANGED:
				pending_floor = int(e.data.get("next_floor", floor_index + 1))
			GameEvent.Kind.PLAYER_DIED:
				is_game_over = true
				player_died.emit(e.data)
	return events


## 樓層切換不能在 submit_intent 裡直接做：View 還要用舊地圖把這回合的動畫
## 播完。也不能用 call_deferred —— 那會綁死在引擎的 frame 迴圈上，
## headless 模擬（沒有 frame）就永遠不會換樓。改成明確的兩段式：
## 呼叫端播完動畫後自己 commit。
func has_pending_floor() -> bool:
	return pending_floor > 0


func commit_pending_floor() -> void:
	if pending_floor <= 0:
		return
	floor_index = pending_floor
	pending_floor = -1
	_build_floor(floor_index)


# ---------------------------------------------------------------- 查詢輔助

## View 與 UI 一律透過這裡取顯示名，不可自己拼字串 ——
## 未鑑定名稱的規則只能有一個實作。
func display_name(item: ItemInstance) -> String:
	return ident.display_name(item, db)


## 道具該用哪一張美術圖。View 一律走這裡，不要自己拼字串。
func art_key(item: ItemInstance) -> String:
	return ident.art_key(item)


func visible_monsters() -> Array:
	var out: Array = []
	for m: MonsterEntity in entities.monsters():
		if vision.is_visible(m.pos):
			out.append(m)
	return out


func status_line() -> String:
	return "Lv %d   HP %d/%d   飽足 %.1f%%   %dF   %d回合   %dG" % [
		player.level, player.hp, player.max_hp,
		player.satiety / 1000.0, floor_index, turns.turn_count, player.gold,
	]
