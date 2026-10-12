#!/usr/bin/env bash
# organize_by_date.sh — categorize a flat camera/export dir into YYYY-MM subdirs
# by filename date. DRY-RUN by default (set DO_IT=1 to actually move).
# Usage: DO_IT=1 organize_by_date.sh /data/fast/Kent/Camera
set -u
SRC="${1:?usage: organize_by_date.sh <dir>}"
DO_IT="${DO_IT:-0}"
moved=0; skipped=0
for f in "$SRC"/IMG_* "$SRC"/VID_* "$SRC"/video_* "$SRC"/pt*; do
  [ -f "$f" ] || continue
  base=$(basename "$f")
  ymd=$(echo "$base" | grep -oE '[0-9]{4}[_ ]?[0-9]{2}[_ ]?[0-9]{2}' | head -1 | tr -d '_ ')
  if [ ${#ymd} -eq 8 ]; then
    ym="${ymd:0:6}"
    dest="$SRC/$ym"
    if [ "$DO_IT" = "1" ]; then
      mkdir -p "$dest"
      mv "$f" "$dest/" && moved=$((moved+1)) || skipped=$((skipped+1))
    else
      echo "DRY: would move $base -> $ym/"
      moved=$((moved+1))
    fi
  else
    echo "SKIP (no date): $base"
    skipped=$((skipped+1))
  fi
done
echo "would-move/ moved=$moved skipped=$skipped"
echo "remaining files at root: $(find "$SRC" -maxdepth 1 -type f | wc -l)"
