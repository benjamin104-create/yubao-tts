## 背包。容量上限是真的上限 —— 撿不下就是撿不下，這是資源管理的一部分。
##
## 所有變更都必須經由 Core 呼叫，UI 不可直接改（架構文件 §4）。
class_name Inventory
extends RefCounted

const CAPACITY := 20

var slots: Array = []      # Array[ItemInstance]


func size() -> int:
	return slots.size()


func has_space() -> bool:
	return slots.size() < CAPACITY


func add(item: ItemInstance) -> bool:
	if item == null or not has_space():
		return false
	slots.append(item)
	return true


func remove(item: ItemInstance) -> bool:
	var i := slots.find(item)
	if i < 0:
		return false
	slots.remove_at(i)
	return true


func at(index: int) -> ItemInstance:
	if index < 0 or index >= slots.size():
		return null
	return slots[index]


func index_of(item: ItemInstance) -> int:
	return slots.find(item)


func find_by_def(def_id: String) -> ItemInstance:
	for it: ItemInstance in slots:
		if it.def_id == def_id:
			return it
	return null


func has_def(def_id: String) -> bool:
	return find_by_def(def_id) != null


## 含壺內容物的展開清單。死亡結算與保管壺判定需要看到巢狀層。
func all_including_nested() -> Array:
	var out := []
	for it: ItemInstance in slots:
		out.append(it)
		for inner: ItemInstance in it.contents:
			out.append(inner)
	return out


## 找出裝著指定道具的壺（若該道具在壺內）。
func container_of(item: ItemInstance) -> ItemInstance:
	for it: ItemInstance in slots:
		if it.contents.has(item):
			return it
	return null


func first_by_category(category: String) -> ItemInstance:
	for it: ItemInstance in slots:
		if it.category == category:
			return it
	return null
