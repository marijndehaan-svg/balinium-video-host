#!/usr/bin/env bash
# Prints the HTTP status for every file in videos/.
# Anything that is not 200 must not be handed to the TikTok API.
BASE="https://marijndehaan-svg.github.io/balinium-video-host"
shopt -s nullglob
found=0
for f in videos/*.mp4; do
  [ -f "$f" ] || continue
  found=1
  url="$BASE/$f"
  code=$(curl -s -o /dev/null -w '%{http_code}' -I "$url")
  if [ "$code" = "200" ]; then
    printf '  OK    %s\n' "$f"
  else
    printf '  FAIL  %s  (%s)  %s\n' "$f" "$code" "$url"
  fi
done
[ "$found" = 0 ] && echo "No .mp4 files in videos/ yet."
