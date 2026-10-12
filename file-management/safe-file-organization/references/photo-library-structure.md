# 照片库结构（2026-08-26 建成，用户认可的模式）

> 2026-09-27 「文件整理簇」4→1 合并：本节从 `safe-file-organization/SKILL.md` 第 61–86 行**逐字**拆出。

## Photo-library structure (built 2026-08-26, user-approved pattern)
For a personal photo hoard that must stay browsable (not a "垃圾堆"), build a year/event
tree with a per-folder cloud/local marker so sensitive batches stay offline:
```
/data/vault/照片库/
  2018/ .meta.json            # {"year":2018,"cloud":false,"note":"..."}
  2024/
    .meta.json
    博恩泡泡球验货/             # user-named event subfolder
      .meta.json               # {"cloud":false,"note":"博恩业务,不含私料"}
      IMG_xxx.jpg
    春节老家/
      .meta.json               # {"cloud":true,"note":"家庭照可上云"}
```
- **Auto-year by EXIF** (not filename guessing): `exiftool -DateTimeOriginal` → `YYYY`;
  install `libimage-exiftool-perl` on Ubuntu. Phone files usually have NO GPS, so
  location-auto-sort is unreliable — fall back to user-named event subfolders.
- **`.meta.json` carries the cloud/local rule** per folder — this is the user's requested
  "备注这个文件夹不能出本地或者可以上云" mechanism. Default `cloud:false`.
- **Semi-auto (user choice C)**: agent does EXIF year-sort + moves; user later drags into
  event subfolders and writes `.meta.json`. Don't try full content-AI-classification
  locally — 3046's P620 (2GB VRAM) can't run vision models; cloud vision API violates the
  red line for sensitive photos.
- **Red-line**: 王浩纪念照片 stays OUT of this library's open tree until the user explicitly
  says to fold it in; if folded, its folder `.meta.json` must be `cloud:false`.
- See `references/photo_library.md` for the exact EXIF-year move script.
