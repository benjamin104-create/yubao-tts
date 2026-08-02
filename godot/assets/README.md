# 美術資產放這裡

規格與提示詞見 `docs/roguelike_art_guide.md`。

程式端有 fallback：找不到檔案就用程式產生的色塊 + 字母，
所以可以一張一張補，中間任何時刻專案都跑得起來。

```
terrain.png              地形圖集，5 格橫排，每格 24x24（共 120x24）
player.png               玩家，2 影格橫排（48x24）
monsters/<def_id>.png    怪物，2 影格橫排（48x24）
items/<key>.png          道具圖示，24x24
                         外觀類用索引：herb_00 ~ herb_15 等
                         種類可見類用 def_id：wpn_club.png 等
```

驗收：`python3 tools/pixelize.py --check godot/assets`
