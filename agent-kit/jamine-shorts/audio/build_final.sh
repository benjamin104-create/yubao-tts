#!/usr/bin/env bash
# 潔米爸短影音 — 一鍵合成「美化人聲 + 柔和鋼琴墊底」最終影片
# 用法： ./build_final.sh <無聲影片.mp4> <原始口播.m4a> <輸出.mp4>
# 需求： PATH 內要有 ffmpeg / ffprobe（本機 apt 裝，或 npm 的 ffmpeg-static/ffprobe-static）
#       同資料夾的 genmusic.py
set -e
SILENT="$1"; RAWVOICE="$2"; OUT="$3"
HERE="$(cd "$(dirname "$0")" && pwd)"

# 1) 修掉口播頭尾靜音
ffmpeg -y -i "$RAWVOICE" -af \
"silenceremove=start_periods=1:start_silence=0.3:start_threshold=-40dB:detection=peak,areverse,silenceremove=start_periods=1:start_silence=0.3:start_threshold=-40dB:detection=peak,areverse" \
-c:a aac /tmp/_voice_trim.m4a

# 2) 人聲美化（標準配方 v2：去轟隆+降噪+EQ臨場/空氣+控齒音+壓縮+響度）
ffmpeg -y -i /tmp/_voice_trim.m4a -af \
"highpass=f=90,afftdn=nr=14:nf=-26,equalizer=f=150:t=q:w=1:g=1.5,equalizer=f=220:t=q:w=1.2:g=-2.5,equalizer=f=3800:t=q:w=1.4:g=4,equalizer=f=5200:t=q:w=1.8:g=2,equalizer=f=6500:t=q:w=2:g=-3,equalizer=f=11000:t=h:w=1:g=3,acompressor=threshold=-20dB:ratio=3:attack=5:release=130:makeup=3,loudnorm=I=-14:TP=-1.5:LRA=10" \
-c:a aac -b:a 192k /tmp/_voice_enh.m4a

# 3) 依影片長度生成墊底音樂
VLEN=$(ffprobe -v error -show_entries format=duration -of default=nw=1 "$SILENT")
python3 "$HERE/genmusic.py" "$VLEN" /tmp/_music.wav

# 4) 混音：人聲延遲0.5s + 音樂(大聲版 volume=0.40)壓底，淡入淡出，限幅防爆
FADEOUT=$(python3 -c "print(max(0,$VLEN-2.2))")
ffmpeg -y -i "$SILENT" -i /tmp/_voice_enh.m4a -i /tmp/_music.wav \
 -filter_complex "[1:a]adelay=500|500,apad[v];[2:a]volume=0.40,lowpass=f=3600,afade=t=in:st=0:d=1.8,afade=t=out:st=${FADEOUT}:d=2.2[m];[v][m]amix=inputs=2:normalize=0,alimiter=limit=0.97[a]" \
 -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 192k -t "$VLEN" "$OUT"
echo "✅ 完成：$OUT"
