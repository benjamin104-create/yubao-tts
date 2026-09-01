#!/usr/bin/env python3
"""
潔米爸短影音 — 柔和鋼琴墊底音樂生成器（零版權，自己合成，IG/TikTok 不會被消音）。
用法： python3 genmusic.py <秒數> <輸出.wav>
例：   python3 genmusic.py 32 music.wav
進行：C–G–Am–F 循環，溫柔琶音 + 低音墊 + 殘響 + 低通。純標準庫，免裝套件。
"""
import math, wave, struct, sys
sr = 44100
total = float(sys.argv[1]) if len(sys.argv) > 1 else 32.0
out = sys.argv[2] if len(sys.argv) > 2 else "music.wav"
N = int(sr*total); buf = [0.0]*N

def add_note(f, t0, dur, amp, decay, harm=(1.0, 0.3, 0.12)):
    s0 = int(t0*sr); n = int(dur*sr)
    for i in range(n):
        idx = s0+i
        if idx >= N: break
        t = i/sr
        env = (min(t/0.008, 1.0))*math.exp(-t*decay)
        v = 0.0
        for k, a in enumerate(harm, 1):
            v += a*math.sin(2*math.pi*f*k*t)
        buf[idx] += amp*env*v

chords = [
 ([261.63, 329.63, 392.00], 130.81),  # C
 ([246.94, 293.66, 392.00],  98.00),  # G
 ([220.00, 261.63, 329.63], 110.00),  # Am
 ([220.00, 261.63, 349.23],  87.31),  # F
]
cd = 2.0; t = 0.0; ci = 0
while t < total:
    notes, bass = chords[ci % 4]
    add_note(bass, t, cd, 0.18, 1.1, harm=(1.0, 0.25))
    for j, nf in enumerate([notes[0], notes[1], notes[2], notes[1]]):
        add_note(nf, t+j*0.5, 1.4, 0.16, 2.4)
    t += cd; ci += 1
# 殘響
for dly, g in [(0.05, 0.25), (0.09, 0.18), (0.15, 0.12), (0.22, 0.07)]:
    d = int(dly*sr)
    for i in range(N-1, d-1, -1):
        buf[i] += g*buf[i-d]
# 低通柔化
a = 0.18; prev = 0.0
for i in range(N):
    prev = prev + a*(buf[i]-prev); buf[i] = prev
pk = max(1e-6, max(abs(x) for x in buf)); s = 0.6/pk
with wave.open(out, 'w') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
    w.writeframes(b''.join(struct.pack('<h', int(max(-1, min(1, x*s))*32767)) for x in buf))
print(f"{out} done {total}s")
