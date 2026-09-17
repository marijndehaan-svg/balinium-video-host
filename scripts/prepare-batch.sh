#!/usr/bin/env bash
# prepare-batch.sh - download from Drive, compress, verify, in one pass.
#
# Usage:   bash scripts/prepare-batch.sh batch.tsv
#
# batch.tsv is tab- or space-separated, one video per line. Blank lines and
# lines starting with # are ignored.
#
#   <planner id>   <drive file id>   <product-slug>
#   20             1-EDi8MXupID...   bangle-gold-bedsheet
#
# The planner id is the "ID" column in the Content Planner (TT-20 -> 20).
# The Drive file id is the long string in the share link, between /d/ and /view.
#
# Output lands in videos/ as v020-bangle-gold-bedsheet.mp4 and is ready to
# commit. Sources are cached in .work/ which is gitignored, so re-running is
# cheap and never re-downloads.
#
# Nothing is committed or pushed. Review the summary, then commit yourself.

set -uo pipefail

MANIFEST="${1:-batch.tsv}"
WORK=".work"
OUT="videos"
MAX_BYTES=$((100 * 1024 * 1024))   # GitHub hard limit per file
WARN_BYTES=$((25 * 1024 * 1024))   # above this, compression probably underperformed

CRF=23
FPS=30

for bin in ffmpeg ffprobe curl; do
  command -v "$bin" >/dev/null 2>&1 || { echo "ERROR: $bin not found. See WINDOWS.md."; exit 1; }
done
[ -f "$MANIFEST" ] || { echo "ERROR: manifest '$MANIFEST' not found."; exit 1; }

mkdir -p "$WORK" "$OUT"

pass=0; fail=0
summary=""

human() {
  awk -v b="$1" 'BEGIN{ if (b<1024) printf "%dB", b;
    else if (b<1048576) printf "%.0fKB", b/1024;
    else printf "%.1fMB", b/1048576 }'
}

# Drive serves small files directly but puts large ones behind a confirm token.
drive_download() {
  local fid="$1" dest="$2" cookie="$WORK/.cookie.$$"
  curl -sL -c "$cookie" -o "$dest" \
    "https://drive.google.com/uc?export=download&id=$fid"
  # If we got HTML back, it was the interstitial, not the file. Retry with token.
  if head -c 512 "$dest" | grep -qi '<html'; then
    local token
    token=$(curl -sL -c "$cookie" -b "$cookie" \
      "https://drive.google.com/uc?export=download&id=$fid" \
      | grep -o 'confirm=[^&"]*' | head -1 | cut -d= -f2)
    if [ -n "$token" ]; then
      curl -sL -b "$cookie" -o "$dest" \
        "https://drive.usercontent.google.com/download?id=$fid&export=download&confirm=$token"
    fi
  fi
  rm -f "$cookie"
  # Still HTML means no public access, or the id is wrong.
  if head -c 512 "$dest" | grep -qi '<html'; then
    rm -f "$dest"
    return 1
  fi
  return 0
}

# One ffprobe value at a time. Asking for several at once returns them across
# multiple lines, which is easy to mis-parse into a single variable.
probe_one() {
  local f="$1" section="$2" field="$3"
  if [ "$section" = stream ]; then
    ffprobe -v error -select_streams v:0 -show_entries "stream=$field" \
      -of csv=p=0 "$f" 2>/dev/null | head -1 | tr -d '\r,'
  else
    ffprobe -v error -show_entries "format=$field" \
      -of csv=p=0 "$f" 2>/dev/null | head -1 | tr -d '\r,'
  fi
}

# faststart check: the moov atom must sit before mdat, or TikTok's fetcher has
# to pull the whole file before it can start reading.
moov_is_first() {
  local f="$1" moov mdat
  moov=$(grep -abo 'moov' "$f" 2>/dev/null | head -1 | cut -d: -f1)
  mdat=$(grep -abo 'mdat' "$f" 2>/dev/null | head -1 | cut -d: -f1)
  [ -n "$moov" ] && [ -n "$mdat" ] && [ "$moov" -lt "$mdat" ]
}

printf '%s\n' "Reading $MANIFEST"
echo

while read -r id fid slug _rest; do
  case "$id" in ''|\#*) continue ;; esac
  [ -n "${fid:-}" ] && [ -n "${slug:-}" ] || {
    echo "SKIP  line for id '$id': needs <id> <drive-id> <slug>"; fail=$((fail+1)); continue; }

  padded=$(printf 'v%03d' "$id")
  name="${padded}-${slug}"
  src="$WORK/${name}.src"
  dst="$OUT/${name}.mp4"

  echo "--- $name"

  if [ -s "$src" ]; then
    echo "    source cached"
  else
    printf '    downloading... '
    if drive_download "$fid" "$src"; then
      echo "$(human "$(wc -c < "$src")")"
    else
      echo "FAILED"
      echo "    Drive returned a web page, not a file. Either the id is wrong or"
      echo "    the file is not shared with 'anyone with the link'."
      fail=$((fail+1)); continue
    fi
  fi

  sbytes=$(wc -c < "$src")

  printf '    compressing... '
  if ! ffmpeg -v error -i "$src" \
        -c:v libx264 -preset medium -crf "$CRF" -r "$FPS" \
        -pix_fmt yuv420p \
        -c:a aac -b:a 128k \
        -movflags +faststart \
        -y "$dst" 2>"$WORK/${name}.ffmpeg.log"; then
    echo "FAILED"
    echo "    ffmpeg errors in $WORK/${name}.ffmpeg.log"
    fail=$((fail+1)); continue
  fi
  dbytes=$(wc -c < "$dst")
  echo "$(human "$sbytes") -> $(human "$dbytes")"

  # Verify the output is something TikTok will actually accept.
  ok=1; notes=""
  dw=$(probe_one "$dst" stream width)
  dh=$(probe_one "$dst" stream height)
  ddur=$(probe_one "$dst" format duration)

  if [ "$dbytes" -ge "$MAX_BYTES" ]; then
    ok=0; notes="$notes over 100MB, git will reject it;"
  elif [ "$dbytes" -ge "$WARN_BYTES" ]; then
    notes="$notes still large, consider -crf 26;"
  fi
  if ! moov_is_first "$dst"; then
    ok=0; notes="$notes faststart missing;"
  fi
  if [ -n "${dw:-}" ] && [ -n "${dh:-}" ]; then
    if [ "$dh" -le "$dw" ]; then
      notes="$notes not vertical (${dw}x${dh});"
    fi
  else
    ok=0; notes="$notes could not probe output;"
  fi
  # TikTok rejects anything under 3s; over 60s is a different upload path.
  dsec=${ddur%%.*}
  if [ -n "${dsec:-}" ]; then
    [ "$dsec" -lt 3 ] && { ok=0; notes="$notes shorter than 3s;"; }
    [ "$dsec" -gt 60 ] && notes="$notes longer than 60s;"
  fi

  if [ "$ok" = 1 ]; then
    echo "    OK  ${dw}x${dh}  ${dsec}s"
    pass=$((pass+1))
  else
    echo "    PROBLEM:$notes"
    fail=$((fail+1))
  fi
  [ -n "$notes" ] && [ "$ok" = 1 ] && echo "    note:$notes"

  summary="$summary$(printf '%-34s %10s -> %-9s %s\n' \
    "$name" "$(human "$sbytes")" "$(human "$dbytes")" \
    "$([ "$ok" = 1 ] && echo OK || echo PROBLEM)")"$'\n'
  echo
done < "$MANIFEST"

echo "================================================================"
printf '%s' "$summary"
echo "================================================================"
echo "$pass ready, $fail with problems."
echo
if [ "$pass" -gt 0 ]; then
  echo "Next: review the files in $OUT/, then"
  echo "  git add videos/ && git commit -m 'Add batch' && git push"
  echo "Then once Pages has deployed:  bash scripts/check-urls.sh"
fi
[ "$fail" -eq 0 ]
