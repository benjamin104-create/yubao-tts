## 一件實際存在的道具。
##
## 刻意不為壺開一個子類別：壺與一般道具在背包裡是同一種東西，分成兩個
## class 會讓每個持有處都要做型別轉換，而收益只有幾個欄位的分離。改用
## is_pot() 判定，巢狀內容物放在 contents。
class_name ItemInstance
extends RefCounted

var def_id := ""
var category := ""          # weapon / shield / herb / scroll / wand / pot

## 鑑定狀態是兩條獨立的軸（見 data_spec §1.1）：
##   known_type     —— 這是什麼種類（武器/盾牌永遠為 true）
##   known_modifier —— 強化值與詛咒
var known_type := false
var known_modifier := false

var upgrade := 0
var cursed := false
var uses := 0               # 杖的剩餘次數
## 成長之劍的擊殺累積。存在實體上而非定義上 —— 每一把劍各自成長，
## 死亡不繼承（GDD §4.5）。
var kill_stacks := 0
var note := ""              # 玩家手動標註（TENTATIVE）

# ---- 壺專用 ----
var pot_behavior := ""      # storage / fusion / identify / devour / ...
var pot_capacity := 0
var contents: Array = []    # Array[ItemInstance]；不加型別註記以避免自我遞迴


func is_pot() -> bool:
	return category == "pot"


func is_equipment() -> bool:
	return category == "weapon" or category == "shield"


func is_full() -> bool:
	return contents.size() >= pot_capacity


## 只有保存壺類可以從選單直接取出。合成/變化/吸物壺放進去就拿不回來。
func can_extract_directly() -> bool:
	return pot_behavior == "storage"


func accepts_insert() -> bool:
	return is_pot() and pot_behavior != "" and not is_full()


func duplicate_instance() -> ItemInstance:
	var c := ItemInstance.new()
	c.def_id = def_id
	c.category = category
	c.known_type = known_type
	c.known_modifier = known_modifier
	c.upgrade = upgrade
	c.cursed = cursed
	c.uses = uses
	c.kill_stacks = kill_stacks
	c.note = note
	c.pot_behavior = pot_behavior
	c.pot_capacity = pot_capacity
	for it: ItemInstance in contents:
		c.contents.append(it.duplicate_instance())
	return c
