#!/usr/bin/env bash
# find_dupes.sh — report exact-duplicate files (by MD5) across one or more dirs.
# NEVER deletes. Prints duplicate hash groups and per-dir overlap counts.
# Usage: find_dupes.sh dir1 dir2 [dir3 ...]
set -u
[ "$#" -ge 1 ] || { echo "usage: find_dupes.sh dir1 [dir2 ...]" >&2; exit 1; }
TMP=$(mktemp)
for d in "$@"; do
  find "$d" -type f -exec md5sum {} \; 2>/dev/null >> "$TMP"
done
echo "=== total files scanned: $(wc -l < "$TMP") ==="
echo "=== fully-duplicate hash groups (hash shown, count) ==="
awk '{print $1}' "$TMP" | sort | uniq -c | awk '$1>1{print $1"  "$2}'
echo "=== example duplicate file paths ==="
dups=$(awk '{print $1}' "$TMP" | sort | uniq -c | awk '$1>1{print $2}')
while read -r h; do
  echo "HASH $h:"
  grep "^$h " "$TMP" | awk '{print "   "$2}'
done <<< "$dups" | head -40
rm -f "$TMP"
echo "NOTE: report only. Do not delete without explicit user confirmation."
