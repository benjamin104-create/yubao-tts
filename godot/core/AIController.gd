## 三種行為模式的決策樹（data_spec §2.2）。
##
## 鐵則：decide() 是純函式 —— 只讀 WorldSnapshot，除了怪物自己的 AI 記憶
## 欄位（memory / aggro / cooldown / last_dir）之外不寫任何世界狀態。
## 決策與執行分離是「同步行動」的前提，破壞它整個回合制手感就垮了。
class_name AIController
extends RefCounted


static func decide(m: MonsterEntity, snap: WorldSnapshot,
		rng: DeterministicRng) -> ActionIntent:
	if m.is_incapacitated():
		return ActionIntent.wait()

	if m.has_status("CONFUSED"):
		var d: Vector2i = rng.choice(Tiles.DIRS_8)
		return ActionIntent.move(d)

	match m.profile_id:
		"WANDERER":
			return _decide_wanderer(m, snap, rng)
		"RANGED":
			return _decide_ranged(m, snap, rng)
		_:
			return _decide_chaser(m, snap, rng)


# ---------------------------------------------------------------- CHASER

## 直線追逐型。完全可預測 —— 玩家能精確算出幾回合後被追上，因此「拉到走廊
## 1v1」「繞柱子」等走位戰術對牠成立。難度來自數值，不是行為。
static func _decide_chaser(m: MonsterEntity, snap: WorldSnapshot,
		rng: DeterministicRng) -> ActionIntent:
	if _can_melee(m, snap):
		return ActionIntent.attack(snap.player_pos)

	if snap.can_see_player(m.pos, m.sight):
		m.memory_pos = snap.player_pos
		m.memory_left = 8
		return _step_toward(m, snap, snap.player_pos)

	if m.memory_left > 0:
		m.memory_left -= 1
		return _step_toward(m, snap, m.memory_pos)

	return _patrol(m, snap, rng)


# ---------------------------------------------------------------- WANDERER

## 隨機遊蕩型。不主動追擊 → 玩家可以選擇不打；但受擊後轉為追擊，讓
## 「打了一半就跑」要付代價。牠的存在讓「避戰」成為一種正當策略。
static func _decide_wanderer(m: MonsterEntity, snap: WorldSnapshot,
		rng: DeterministicRng) -> ActionIntent:
	if m.aggro_left > 0:
		m.aggro_left -= 1
		return _decide_chaser(m, snap, rng)      # 委派 CHASER 決策樹

	if _can_melee(m, snap):
		return ActionIntent.attack(snap.player_pos)

	# 有慣性地遊走，避免原地抖動的視覺噪音
	if m.last_dir != Vector2i.ZERO and rng.chance(0.6) \
			and snap.can_step(m.pos, m.pos + m.last_dir):
		return ActionIntent.move(m.last_dir)

	return _patrol(m, snap, rng)


# ---------------------------------------------------------------- RANGED

## 遠程攻擊型。走廊戰術的剋星 —— CHASER 讓走廊變安全，RANGED 讓走廊變成
## 射擊場。沒有牠，全遊戲的戰鬥會塌縮成同一招。
static func _decide_ranged(m: MonsterEntity, snap: WorldSnapshot,
		rng: DeterministicRng) -> ActionIntent:
	# 被封魔後退化為普通追擊怪 —— 封魔之杖因此是明確的針對解
	if m.has_status("ABILITY_SEALED"):
		return _decide_chaser(m, snap, rng)

	var dist := Tiles.chebyshev(m.pos, snap.player_pos)

	if float(m.hp) / float(m.max_hp) < 0.25 and not m.immobile:
		return _step_away(m, snap)

	# 貼身時只能近戰，且攻擊力打折 → 「貼上去」就是正解
	if dist <= 1 and _can_melee(m, snap):
		return ActionIntent.attack(snap.player_pos)

	if dist < 3 and not m.immobile:
		return _step_away(m, snap)

	if m.cooldown_left > 0:
		m.cooldown_left -= 1
		return ActionIntent.wait() if m.immobile else _reposition(m, snap, rng)

	# 只在同列／同行／正對角線且路徑淨空時可射擊。玩家能靠站到非對齊格
	# 主動規避 —— 這是可推理的規避手段，不是骰運。
	if dist <= m.ranged_range() and Tiles.is_aligned(m.pos, snap.player_pos) \
			and snap.line_clear(m.pos, snap.player_pos, true):
		m.cooldown_left = 2
		return ActionIntent.ranged_attack(snap.player_pos)

	if m.immobile:
		return ActionIntent.wait()

	if snap.can_see_player(m.pos, m.sight):
		return _step_to_align(m, snap)

	if m.memory_left > 0:
		m.memory_left -= 1
		return _step_toward(m, snap, m.memory_pos)

	return ActionIntent.wait()


# ---------------------------------------------------------------- 移動輔助

static func _can_melee(m: MonsterEntity, snap: WorldSnapshot) -> bool:
	if Tiles.chebyshev(m.pos, snap.player_pos) != 1:
		return false
	# 牆角規則對怪物同樣適用 —— 任何一方例外都會讓走廊戰術崩掉
	return WorldSnapshot.corner_rule_ok(snap.map(), m.pos, snap.player_pos)


static func _step_toward(m: MonsterEntity, snap: WorldSnapshot,
		target: Vector2i) -> ActionIntent:
	if m.immobile or target == Vector2i(-1, -1):
		return ActionIntent.wait()
	var best := _best_step(m.pos, target, snap, true)
	if best == Vector2i.ZERO:
		return ActionIntent.wait()
	return ActionIntent.move(best)


static func _step_away(m: MonsterEntity, snap: WorldSnapshot) -> ActionIntent:
	var best := _best_step(m.pos, snap.player_pos, snap, false)
	if best == Vector2i.ZERO:
		return ActionIntent.wait()
	return ActionIntent.move(best)


## 選一步讓與 target 的距離最小（closer=true）或最大（closer=false）。
## 平手時偏好斜向，讓移動看起來自然。
static func _best_step(from: Vector2i, target: Vector2i, snap: WorldSnapshot,
		closer: bool) -> Vector2i:
	var best := Vector2i.ZERO
	var best_score := -1
	for d in Tiles.DIRS_8:
		var to: Vector2i = from + d
		if not snap.can_step(from, to):
			continue
		var dist := Tiles.chebyshev(to, target)
		var score := (100 - dist) if closer else dist
		if Tiles.is_diagonal(d):
			score = score * 2 + 1       # 平手偏好斜向
		else:
			score = score * 2
		if score > best_score:
			best_score = score
			best = d
	return best


## 移動到能與玩家對齊的格子。這讓 RANGED 型怪物有「繞位」的感覺，
## 而不是笨笨地直線靠近。
static func _step_to_align(m: MonsterEntity, snap: WorldSnapshot) -> ActionIntent:
	var best := Vector2i.ZERO
	var best_score := -999
	for d in Tiles.DIRS_8:
		var to: Vector2i = m.pos + d
		if not snap.can_step(m.pos, to):
			continue
		var dist := Tiles.chebyshev(to, snap.player_pos)
		var score := 0
		if Tiles.is_aligned(to, snap.player_pos) \
				and snap.line_clear(to, snap.player_pos, true):
			score += 100
		if dist >= 3 and dist <= m.ranged_range():
			score += 50
		score -= absi(dist - 4)          # 傾向維持中距離
		if score > best_score:
			best_score = score
			best = d
	if best == Vector2i.ZERO:
		return ActionIntent.wait()
	return ActionIntent.move(best)


static func _reposition(m: MonsterEntity, snap: WorldSnapshot,
		rng: DeterministicRng) -> ActionIntent:
	if rng.chance(0.5):
		return ActionIntent.wait()
	return _step_to_align(m, snap)


static func _patrol(m: MonsterEntity, snap: WorldSnapshot,
		rng: DeterministicRng) -> ActionIntent:
	if m.immobile:
		return ActionIntent.wait()
	var options: Array[Vector2i] = []
	for d in Tiles.DIRS_8:
		if snap.can_step(m.pos, m.pos + d):
			options.append(d)
	if options.is_empty():
		return ActionIntent.wait()
	var d: Vector2i = rng.choice(options)
	m.last_dir = d
	return ActionIntent.move(d)
