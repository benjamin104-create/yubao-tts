## GameEvent 佇列 → 動畫排程。
##
## Core 一次跑完整個回合，這裡負責把結果「演」出來。播放期間輸入被鎖住，
## 因此不會出現「動畫還在播、狀態已經又變了」的競態（架構文件 §0）。
##
## 壓縮規則（GDD §1.7）：連續移動時把可壓縮事件縮到 40ms；但只要佇列中
## 出現任一不可壓縮事件、或玩家 HP < 30%、或視野內有敵人，就強制全速。
class_name EventPlayer
extends Node

signal playback_finished()
signal message(text: String)

const FULL_SPEED := 0.12
const COMPRESSED := 0.04

var host: GameHost
var entity_view: EntityView
var fog: FogRenderer
var text_pool: FloatingTextPool
var screen_flash: ScreenFlash

var is_playing := false
var allow_compression := false


func setup(p_host: GameHost, p_view: EntityView, p_fog: FogRenderer,
		p_pool: FloatingTextPool = null, p_flash: ScreenFlash = null) -> void:
	host = p_host
	entity_view = p_view
	fog = p_fog
	text_pool = p_pool
	screen_flash = p_flash


func play(events: Array) -> void:
	if events.is_empty():
		playback_finished.emit()
		return
	is_playing = true
	var step := _step_duration(events)

	for e: GameEvent in events:
		_apply(e, step)
		if _has_visual_weight(e):
			await get_tree().create_timer(step).timeout

	entity_view.sync()
	fog.redraw(host.vision)
	is_playing = false
	playback_finished.emit()


## 決定本回合的播放速度。危險時一律全速 —— 玩家必須看清楚。
func _step_duration(events: Array) -> float:
	if not allow_compression:
		return FULL_SPEED
	if host.player.hp * 10 < host.player.max_hp * 3:      # HP < 30%
		return FULL_SPEED
	if not host.visible_monsters().is_empty():
		return FULL_SPEED
	for e: GameEvent in events:
		if not e.compressible:
			return FULL_SPEED
	return COMPRESSED


func _spawn_text(entity_id: int, text: String, type: FloatingText.Type) -> void:
	if text_pool == null:
		return
	# 看不見的實體不飄字 —— 否則玩家能從霧裡的數字推斷怪物位置
	var e := host.entities.by_id(entity_id)
	if e != null and not e.is_player and not host.vision.is_visible(e.pos):
		return
	text_pool.spawn(text, type, entity_view.actor_position(entity_id))


static func _has_visual_weight(e: GameEvent) -> bool:
	match e.kind:
		GameEvent.Kind.ENTITY_MOVED, GameEvent.Kind.ENTITY_ATTACKED, \
		GameEvent.Kind.DAMAGE_DEALT, GameEvent.Kind.ENTITY_DIED, \
		GameEvent.Kind.ITEM_THROWN, GameEvent.Kind.TRAP_TRIGGERED:
			return true
	return false


func _apply(e: GameEvent, step: float) -> void:
	match e.kind:
		GameEvent.Kind.ENTITY_MOVED:
			entity_view.move_actor(e.data["entity_id"], e.data["to"], step)

		GameEvent.Kind.DAMAGE_DEALT:
			var target_id: int = e.data["target_id"]
			var crit: bool = e.data.get("crit", false)
			entity_view.flash(target_id,
				Color(2.2, 1.6, 0.4) if crit else Color(1.6, 0.5, 0.5))
			_spawn_text(target_id, str(e.data.get("amount", 0)),
				FloatingText.Type.CRITICAL if crit else FloatingText.Type.NORMAL)
			# 只有玩家吃到會心才閃全螢幕 —— 這是「你差點死掉」的訊號，
			# 不是每次打擊的裝飾
			if crit and target_id == host.player.id and screen_flash != null:
				screen_flash.flash(Color(0.9, 0.15, 0.1, 0.32))

		GameEvent.Kind.ATTACK_MISSED:
			_spawn_text(e.data["target_id"], "MISS", FloatingText.Type.MISS)

		GameEvent.Kind.HP_CHANGED:
			var delta: int = e.data.get("delta", 0)
			if delta > 0:
				_spawn_text(e.data["entity_id"], "+%d" % delta, FloatingText.Type.HEAL)

		GameEvent.Kind.ENTITY_DIED:
			entity_view.remove_actor(e.data["entity_id"])

		GameEvent.Kind.MONSTER_SPAWNED, GameEvent.Kind.VISIBILITY_CHANGED:
			entity_view.sync()
			fog.redraw(host.vision)

		GameEvent.Kind.MESSAGE:
			message.emit(String(e.data.get("text", "")))

		GameEvent.Kind.ITEM_IDENTIFIED:
			message.emit("★ 鑑定完成：%s" % e.data.get("name", ""))

		GameEvent.Kind.LEVEL_UP:
			entity_view.flash(host.player.id, Color(0.6, 1.8, 0.9))
			_spawn_text(host.player.id, "LEVEL UP", FloatingText.Type.HEAL)
			if screen_flash != null:
				screen_flash.flash(Color(0.35, 0.95, 0.6, 0.22))

		GameEvent.Kind.PLAYER_DIED:
			if screen_flash != null:
				screen_flash.flash(Color(0.75, 0.05, 0.05, 0.65), 0.9)

		_:
			pass
