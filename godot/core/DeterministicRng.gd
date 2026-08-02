## 全遊戲唯一的亂數來源。
##
## 為什麼不直接用 randi()：全域 RNG 沒有種子控制，一旦用了就無法重播、
## 無法用 seed 重現 Bug、每日挑戰也不可能。架構文件 §6 的「重播 = seed +
## Intent 序列」完全依賴這裡。
##
## 注意 Array.shuffle() / Array.pick_random() 走的是全域 RNG，本類別因此
## 自己實作 shuffle 與 choice —— 絕對不要在 core/ 裡呼叫那兩個內建方法。
class_name DeterministicRng
extends RefCounted

var _rng := RandomNumberGenerator.new()


func _init(seed_value: int = 0) -> void:
	_rng.seed = seed_value


## FNV-1a 64bit。跨平台、跨版本穩定 —— 不可改用內建 hash()，
## 那個的實作細節沒有保證，換 Godot 版本就可能生出不同地圖。
static func hash64(values: Array) -> int:
	var h := 0x811C9DC5
	for v in values:
		var n := int(v)
		for shift in range(0, 64, 8):
			h ^= (n >> shift) & 0xFF
			h = (h * 0x100000001B3) & 0x7FFFFFFFFFFFFFFF
	return h


func randi_range(from: int, to: int) -> int:
	return _rng.randi_range(from, to)


func randf() -> float:
	return _rng.randf()


func randf_range(from: float, to: float) -> float:
	return _rng.randf_range(from, to)


func chance(p: float) -> bool:
	return _rng.randf() < p


func choice(arr: Array) -> Variant:
	if arr.is_empty():
		return null
	return arr[_rng.randi_range(0, arr.size() - 1)]


## 原地 Fisher-Yates。
func shuffle(arr: Array) -> void:
	for i in range(arr.size() - 1, 0, -1):
		var j := _rng.randi_range(0, i)
		var tmp: Variant = arr[i]
		arr[i] = arr[j]
		arr[j] = tmp


## 不重複抽 n 個。
func sample(arr: Array, n: int) -> Array:
	var copy := arr.duplicate()
	shuffle(copy)
	return copy.slice(0, mini(n, copy.size()))


## 加權隨機。entries 格式：[[物件, 權重], ...]
func weighted_pick(entries: Array) -> Variant:
	var total := 0.0
	for e in entries:
		total += float(e[1])
	if total <= 0.0:
		return null
	var r := _rng.randf_range(0.0, total)
	for e in entries:
		r -= float(e[1])
		if r <= 0.0:
			return e[0]
	return entries[entries.size() - 1][0]
