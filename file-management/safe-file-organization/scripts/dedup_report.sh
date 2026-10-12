#!/bin/bash
# dedup_report.sh — read-only md5 duplicate reporter for large archives.
# Usage: bash dedup_report.sh <dir>
# Handles Chinese/special filenames via find -print0 | xargs -0, parallel md5.
# NEVER deletes. Prints duplicate hash groups + sample paths.
set -u
BASE="${1:-.}"
echo "=== Dedup scan: $BASE ==="
echo "Total files: $(find "$BASE" -type f 2>/dev/null | wc -l)"
# Compute md5 in parallel (4 workers), save to temp
TMP=$(mktemp)
find "$BASE" -type f -print0 2>/dev/null | xargs -0 -P 4 -I{} md5sum "{}" 2>/dev/null > "$TMP"
echo "Hashes computed: $(wc -l < "$TMP")"
# Groups with >1 identical hash
awk '{print $1}' "$TMP" | sort | uniq -c | awk '$1>1' > /tmp/_dup_groups.txt
echo "Duplicate hash groups: $(wc -l < /tmp/_dup_groups.txt)"
echo "Redundant copies removable: $(awk '{s+=$1-1} END{print s}' /tmp/_dup_groups.txt)"
echo ""
echo "=== Sample duplicate groups (hash -> paths) ==="
head -20 /tmp/_dup_groups.txt | while read cnt h; do
  echo "[$h] x$cnt"
  grep "^$h" "$TMP" | awk '{print "  "$2}' | head -4
done
rm -f "$TMP"
