# 標準音訊配方（潔米爸短影音）

定案版 **v3**：**切開口前雜音 + 強去低頻 + 降噪 + 美化人聲 + 1.2 倍速 + 柔和鋼琴墊底(0.55) + 自動閃避**。
零版權、自己合成，IG/TikTok 不會被消音。影片以 `setpts` 自動配速貼合語速（免重渲染）。

## v3 額外處理（相對 v2）
- `silenceremove`：切掉開口前 / 結尾的環境雜音。
- `highpass=120 (×2) + equalizer=90 g=-12`：強力去低頻「轟」聲。
- `afftdn nt=w + agate`：noise tracking 降噪 + 雜訊閘。
- `atempo=1.2`：語速 1.2 倍（保音高），更有精神。
- 影片 `setpts=PTS/factor` 自動配速。

## 檔案
- `genmusic.py` — 生成墊底音樂（C–G–Am–F 溫柔琶音）。`python3 genmusic.py <秒數> music.wav`
- `build_final.sh` — 一鍵把「無聲影片 + 原始口播」合成最終版。
  `./build_final.sh 無聲影片.mp4 原始口播.m4a 輸出.mp4`

## 人聲美化鏈（ffmpeg -af）
```
highpass=f=90               # 去低頻轟隆
afftdn=nr=14:nf=-26         # 降噪
equalizer=f=150 g=+1.5      # 暖度
equalizer=f=220 g=-2.5      # 去濁
equalizer=f=3800 g=+4       # 臨場感/清晰
equalizer=f=5200 g=+2       # 咬字清晰
equalizer=f=6500 g=-3       # 控齒音(de-ess)
equalizer=f=11000 g=+3      # 空氣感
acompressor th=-20 ratio=3 makeup=3   # 動態更穩
loudnorm I=-14:TP=-1.5:LRA=10         # 響度
```

## 混音
- 人聲延遲 0.5s 起（對齊第一段字幕）。
- 音樂 `volume=0.55` + `lowpass=3600` + 淡入1.8s/淡出尾段。
- **sidechain 自動閃避**：`sidechaincompress=threshold=0.03:ratio=6:attack=15:release=350`（人聲一出現音樂自動微降，停頓回來）→ 音樂大聲也不蓋人聲。
- `amix=normalize=0`（保住人聲音量）+ `alimiter=0.97`（防爆）。

## 注意
- 影片長度需先配合口播長度算好（在 render 階段設 data-duration）。`build_final.sh` 會依無聲影片長度生成等長音樂。
- 要調整：音樂大小改 `build_final.sh` 的 `volume=0.40`；美化強弱改各 `equalizer` 增益。
