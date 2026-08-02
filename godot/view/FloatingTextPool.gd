## 飄字物件池。
##
## 池滿時搶占「最舊的」活躍節點（Oldest Stealing）而不是放棄顯示 ——
## 最新的傷害數字永遠比 0.4 秒前那個重要。
##
## 這個池活在 View 層、由 EventPlayer 驅動。它不是 Autoload，也不會被
## Core 呼叫 —— Core 裡沒有任何節點，也不該知道「飄字」這種東西存在。
class_name FloatingTextPool
extends Node2D

const POOL_SIZE := 48

var _available: Array[FloatingText] = []
var _active: Array[FloatingText] = []
var _spread := 0


func _ready() -> void:
	z_index = 100
	for i in POOL_SIZE:
		var node := FloatingText.new()
		node.recycled.connect(_on_recycled)
		add_child(node)
		_available.append(node)


func spawn(text: String, type: FloatingText.Type, world_pos: Vector2) -> void:
	var node: FloatingText = null

	if not _available.is_empty():
		node = _available.pop_back()
	elif not _active.is_empty():
		node = _active.pop_front()          # 搶占存活最久的
	else:
		return

	_active.append(node)
	# 同一格連續受傷時左右錯開，避免數字完全重疊看不清
	_spread = (_spread + 1) % 4
	node.activate(text, type, world_pos, (_spread - 1.5) * 7.0)


func _on_recycled(node: FloatingText) -> void:
	_active.erase(node)
	if not _available.has(node):
		_available.append(node)


func clear_all() -> void:
	for node in _active.duplicate():
		node.recycle()
