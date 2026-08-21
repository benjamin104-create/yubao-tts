# 動畫圖集

正式角色動畫放在以下路徑：

```text
hero/<skin>.png
hat/<id>.png
weapon/<id>.png
shield/<id>.png
mon/<id>.png
boss/<id>.png
```

- 主角／裝備／一般怪：10x3、每格 32px，整張 320x96，單張不超過 32 KB。
- 頭目：10x3、每格 48px，整張 480x144，單張不超過 64 KB。
- 欄列語意見 `../../../docs/art_animation_spec.md`。
- `tools/build_single.py` 會自動把本資料夾的 PNG 內嵌進單檔 HTML。
- 直接開 `web/index.html` 開發時，把已完成的 id 加到 `ART_ANIM_AVAILABLE`；
  單檔 HTML 會從內嵌清單自動辨認，不需登記。

缺圖時引擎會使用靜態 PNG 加程式化動作，不要刪除舊資產。
