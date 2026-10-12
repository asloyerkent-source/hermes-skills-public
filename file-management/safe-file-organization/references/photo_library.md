# Photo Library: EXIF-year move script

Used in the 3046 session (2026-08-26) to move 6351 Camera photos into
`/data/vault/照片库/<year>/` with a `.meta.json` per year. Semi-auto: agent sorts by
year, user later creates event subfolders + writes per-event `.meta.json`.

## Prereqs
```bash
sudo apt-get install -y libimage-exiftool-perl   # exiftool for DateTimeOriginal
```

## Move-by-directory-year (Camera uses YYYYMM subdirs already)
The 3046 Camera tree was `Camera/202403/`, `Camera/202410/`, ... — directory name IS the
month, so year = first 4 chars. No EXIF parse needed for that case:

```python
import os, shutil, json
SRC="/data/fast/Kent/Camera"; DST="/data/vault/照片库"; EXT=(".jpg",".jpeg",".png",".heic")
for d in sorted(os.listdir(SRC)):
    s=os.path.join(SRC,d)
    if not os.path.isdir(s) or not (d[0:6].isdigit() and len(d)==6): continue
    yr=d[0:4]; t=os.path.join(DST,yr); os.makedirs(t,exist_ok=True)
    meta=os.path.join(t,".meta.json")
    if not os.path.exists(meta):
        json.dump({"year":yr,"cloud":False,"note":"Camera导入,默认不出本地;事件子目录待细分",
                   "source":"Camera/"+d}, open(meta,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
    for fn in os.listdir(s):
        if fn.lower().endswith(EXT):
            sp=os.path.join(s,fn); dp=os.path.join(t,fn)
            if os.path.exists(dp):                       # collision guard
                b,e=os.path.splitext(fn); dp=os.path.join(t,f"{b}__{d}{e}")
            shutil.move(sp,dp)
```

⚠️ **Bug caught & fixed this session**: `json.dump(data, file)` had args reversed
(`AttributeError: 'str' object has no attribute 'write'`). Always open the file and pass
the handle: `json.dump(data, open(meta,"w",encoding="utf-8"))` or `with open(...) as f: json.dump(data,f)`.

## If source dirs are NOT yyyy-mm (e.g. flat dump)
Parse EXIF instead of trusting the path:
```bash
exiftool -DateTimeOriginal -S -s photo.jpg    # -> Date/Time Original: 2024:03:08 17:29:39
# year = line.split(":",1)[1][:4]
```

## `.meta.json` schema
```json
{"year":"2024","cloud":false,"note":"...","source":"Camera/202403"}
```
Per-event subfolder (user-created): `{"cloud":true,"note":"家庭照可上云"}` or
`{"cloud":false,"note":"博恩业务,不含私料"}`.

## Verification
After move: each year dir count sums to source total; source dirs empty; `.meta.json`
present in every year dir with `cloud:false`.
