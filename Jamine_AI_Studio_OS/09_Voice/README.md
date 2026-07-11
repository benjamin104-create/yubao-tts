# 09 — 配音 (Voice)

> 角色的聲音。**串接本 repo 的語寶 TTS 系統**（`../../tts_gateway.py`）。
> 這是 Studio OS 與 yubao-tts 專案的交會點——語寶就是這座工廠的配音部。

## 聲線來源

每個角色的音色設定寫在 `03_Characters/{slug}` 的「聲音」段。此處只做**執行與歸檔**。

| 角色 | slug | 音色摘要 |
|------|------|----------|
| 潔米爸 | `jamie-dad` | 中低沉、溫厚、慢、留白 |
| 阿哲 | `ah-zhe` | 中音、偏緊、快 |
| 小薇 | `xiao-wei` | 中高、清亮、克制 |

## 流程

```
劇本對白（05_Scripts）
      │  依角色聲線
  語寶 TTS（tts_gateway.py）
      │
     WAV / MP3（單句或整段）
      │
   09_Voice/{PROJECT}/S{季}/E{集}/
      │
   交 10_Edit 對嘴 / 對節奏
```

## 命名

`{PROJECT}_S{季}_E{集}_voice_{角色slug}_{鏡頭編號}_v{版本}.wav`
例：`JMD_S01_E01_voice_ah-zhe_012_v01.wav`

## 守則

- 同一角色跨集使用**同一組聲線參數**，確保聲音一致性（等同外型一致性）。
- 潔米爸的口白刻意留白、放慢——不要為了塞資訊而加速。
- 語寶設定與參數建議另存一份 `voice_profiles.md`（Phase 2 建立）。
