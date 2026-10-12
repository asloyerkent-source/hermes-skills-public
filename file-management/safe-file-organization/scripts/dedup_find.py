#!/usr/bin/env python3
"""Find duplicate files between two directories.
Usage: python3 dedup_find.py /path/to/dir1 /path/to/dir2
Output: dedup_report.json (duplicates + stats)
"""
import os, hashlib, json, sys
from collections import defaultdict
from datetime import datetime

def sha256_file(path, chunk=1024*1024):
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            while True:
                b = f.read(chunk)
                if not b: break
                h.update(b)
        return h.hexdigest()
    except Exception as e:
        return f"ERR:{e}"

def collect_files(root):
    size_map = defaultdict(list)
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in ('.thumbnails', '.Gallery2', '$RECYCLE.BIN', 'System Volume Information')]
        for fn in files:
            fp = os.path.join(dirpath, fn)
            try:
                sz = os.path.getsize(fp)
                rel = os.path.relpath(fp, root)
                size_map[sz].append((rel, fp))
            except:
                pass
    return size_map

def find_dups(dir1, dir2):
    print(f"Scanning {dir1}...")
    map1 = collect_files(dir1)
    print(f"Scanning {dir2}...")
    map2 = collect_files(dir2)
    
    common_sizes = set(map1.keys()) & set(map2.keys())
    print(f"Common sizes: {len(common_sizes)}")
    
    duplicates = []
    for sz in sorted(common_sizes, reverse=True):
        all_files = map1[sz] + map2[sz]
        if len(all_files) < 2:
            continue
        hash_map = defaultdict(list)
        for rel, fp in all_files:
            h = sha256_file(fp)
            loc = "dir1" if fp.startswith(dir1) else "dir2"
            hash_map[h].append({"path": rel, "full": fp, "size": sz, "location": loc})
        for h, files in hash_map.items():
            if len(files) >= 2:
                duplicates.append({"hash": h, "size": sz, "size_mb": round(sz / 1048576, 2), "files": files})
    
    report = {
        "scan_time": datetime.now().isoformat(),
        "dir1": dir1,
        "dir2": dir2,
        "duplicate_groups": len(duplicates),
        "wasted_mb": round(sum(d["size_mb"] for d in duplicates), 2),
        "duplicates": duplicates
    }
    
    with open("dedup_report.json", "w") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"Done: {len(duplicates)} groups, {report['wasted_mb']} MB wasted")
    print("Report: dedup_report.json")
    return report

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 dedup_find.py <dir1> <dir2>")
        sys.exit(1)
    find_dups(sys.argv[1], sys.argv[2])
