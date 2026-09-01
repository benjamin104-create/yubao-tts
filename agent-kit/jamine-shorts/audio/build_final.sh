#!/usr/bin/env bash
# 潔米爸短影音 — 一鍵合成「美化人聲(1.2x) + 柔和鋼琴墊底」最終影片
# 用法： ./build_final.sh <無聲影片.mp4> <原始口播.m4a> <輸出.mp4>
# 需求： PATH 內要有 ffmpeg / ffprobe；同資料夾的 genmusic.py
# 標準配方 v3：切開口前雜音 + 強去低頻轟隆 + 降噪 + 美化 + 1.2倍速；影片自動配速貼合語音。
set -e
SILENT="$1"; RAWVOICE="$2"; OUT="$3"
HERE="$(cd "$(dirname "$0")" && pwd)"

# 1) 人聲處理：切掉開口前/結尾的環境雜音 → 去低頻轟隆 → 降噪+gate → EQ美化 → 壓縮 → 1.2倍 → 響度 → 淡入
ffmpeg -y -i "$RAWVOICE" -af \
"silenceremove=start_periods=1:start_silence=0.15:start_threshold=-34dB:detection=peak,areverse,silenceremove=start_periods=1:start_silence=0.15:start_threshold=-34dB:detection=peak,areverse,\
highpass=f=120:poles=2,highpass=f=120:poles=2,equalizer=f=90:t=q:w=1:g=-12,\
afftdn=nr=20:nf=-30:nt=w,agate=threshold=0.02:ratio=2.5:attack=8:release=180,\
equalizer=f=220:t=q:w=1.2:g=-2,equalizer=f=3800:t=q:w=1.4:g=4,equalizer=f=5200:t=q:w=1.8:g=2,\
equalizer=f=6500:t=q:w=2:g=-3,equalizer=f=11000:t=h:w=1:g=3,\
acompressor=threshold=-20dB:ratio=3:attack=5:release=130:makeup=3,atempo=1.2,\
loudnorm=I=-14:TP=-1.5:LRA=10,afade=t=in:st=0:d=0.18" \
-c:a aac -b:a 192k /tmp/_voice.m4a

VL=$(ffprobe -v error -show_entries format=duration -of default=nw=1 /tmp/_voice.m4a)
OL=$(ffprobe -v error -show_entries format=duration -of default=nw=1 "$SILENT")
TARGET=$(python3 -c "print(round(0.5+$VL+0.8,2))")
FACTOR=$(python3 -c "print(round($OL/$TARGET,4))")

# 2) 影片自動配速貼合語音（字幕跟著變快，免重渲染 HTML）
ffmpeg -y -i "$SILENT" -vf "setpts=PTS/$FACTOR" -r 30 -an -c:v libx264 -crf 20 -preset veryfast -pix_fmt yuv420p /tmp/_sf.mp4

# 3) 等長墊底音樂
python3 "$HERE/genmusic.py" "$(python3 -c "print(int($TARGET)+2)")" /tmp/_music.wav

# 4) 混音：人聲延遲0.5s + 音樂(0.55) + sidechain閃避 + 限幅
FO=$(python3 -c "print(round($TARGET-2.2,2))")
ffmpeg -y -i /tmp/_sf.mp4 -i /tmp/_voice.m4a -i /tmp/_music.wav \
 -filter_complex "[1:a]adelay=500|500,apad,asplit=2[v1][vsc];\
[2:a]volume=0.55,lowpass=f=3600,afade=t=in:st=0:d=1.8,afade=t=out:st=${FO}:d=2.5[mraw];\
[mraw][vsc]sidechaincompress=threshold=0.03:ratio=6:attack=15:release=350[mduck];\
[v1][mduck]amix=inputs=2:normalize=0,alimiter=limit=0.97[a]" \
 -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 192k -t "$TARGET" "$OUT"
echo "✅ 完成：$OUT  (語音 ${VL}s → 影片 ${TARGET}s, 1.2x)"
