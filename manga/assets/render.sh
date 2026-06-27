#!/bin/bash
# usage: render.sh input.html output.png W H
CHROME=/opt/pw-browsers/chromium-1194/chrome-linux/chrome
IN="$1"; OUT="$2"; W="$3"; H="$4"
"$CHROME" --headless=new --no-sandbox --disable-gpu --hide-scrollbars \
  --force-device-scale-factor=2 --window-size=${W},${H} \
  --virtual-time-budget=12000 --default-background-color=00000000 \
  --screenshot="$OUT" "file://$IN" 2>/dev/null
echo "exit=$? -> $OUT"; ls -l "$OUT" 2>/dev/null
