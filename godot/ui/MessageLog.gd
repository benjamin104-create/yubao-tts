## 訊息列。
##
## 只讀 GameEvent 產生的字串 —— 訊息文字由 Core 決定，UI 不自己拼句子。
## 未鑑定名稱、傷害數字的規則只能有一個實作。
class_name MessageLog
extends PanelContainer

const MAX_LINES := 6

var _label: RichTextLabel
var _lines: Array[String] = []


func _ready() -> void:
	custom_minimum_size = Vector2(0, 108)
	_label = RichTextLabel.new()
	_label.bbcode_enabled = true
	_label.scroll_following = true
	_label.fit_content = false
	add_child(_label)


func push(text: String) -> void:
	if text.strip_edges().is_empty():
		return
	_lines.append(text)
	while _lines.size() > MAX_LINES:
		_lines.pop_front()
	_render()


func _render() -> void:
	var out := PackedStringArray()
	for i in _lines.size():
		# 越舊的訊息越暗，讓玩家的視線自動落在最新一行
		var fade := 0.45 + 0.55 * float(i + 1) / float(_lines.size())
		out.append("[color=#%s]%s[/color]" % [
			Color(fade, fade, fade * 0.95).to_html(false), _lines[i]])
	_label.text = "\n".join(out)


func clear_log() -> void:
	_lines.clear()
	_render()
