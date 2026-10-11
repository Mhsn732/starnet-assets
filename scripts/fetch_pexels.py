#!/usr/bin/env python3
"""
يقرأ requests.txt ويحمّل كل صورة من Pexels API إلى مجلد photos/.

صيغة requests.txt (سطر لكل صورة، # للتعليق):
    12823541  desert-men-sunset
    12823577  sudan-group-white
الرقم = رقم الصورة في رابط Pexels (آخر رقم في الرابط)، والاسم اختياري.

لكل صورة يحفظ:
  photos/<name>-<id>.jpg   النسخة الأصلية بأعلى دقة
  photos/sources.json      المصوّر والرابط الأصلي والأبعاد (سجل الترخيص)
الصور الموجودة مسبقاً لا تُحمّل مرة ثانية.
"""
import json, os, re, sys, urllib.request, urllib.error, pathlib

API = "https://api.pexels.com/v1/photos/{}"
UA = "starnet-assets-fetcher/1.0"


def get(url, headers=None):
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def main(req_file, out_dir):
    key = os.environ.get("PEXELS_API_KEY", "").strip()
    if not key:
        sys.exit("PEXELS_API_KEY secret is missing (Settings → Secrets and variables → Actions).")
    out = pathlib.Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    src_file = out / "sources.json"
    sources = json.loads(src_file.read_text()) if src_file.exists() else {}

    failed = 0
    for line in pathlib.Path(req_file).read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        parts = line.split()
        m = re.search(r"(\d{4,})", parts[0])
        if not m:
            print(f"skip (no id): {line}")
            continue
        pid = m.group(1)
        name = re.sub(r"[^a-z0-9-]+", "-", (parts[1] if len(parts) > 1 else "photo").lower()).strip("-")
        dest = out / f"{name}-{pid}.jpg"
        if dest.exists():
            print(f"exists: {dest.name}")
            continue
        try:
            meta = json.loads(get(API.format(pid), {"Authorization": key}))
            img = get(meta["src"]["original"])
            dest.write_bytes(img)
            sources[dest.name] = {
                "pexels_id": pid,
                "url": meta.get("url"),
                "photographer": meta.get("photographer"),
                "photographer_url": meta.get("photographer_url"),
                "width": meta.get("width"),
                "height": meta.get("height"),
                "alt": meta.get("alt"),
                "license": "Pexels License (free to use) — https://www.pexels.com/license/",
            }
            print(f"saved: {dest.name} ({len(img)//1024} KB, {meta.get('width')}x{meta.get('height')})")
        except urllib.error.HTTPError as e:
            failed += 1
            print(f"FAILED {pid}: HTTP {e.code}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"FAILED {pid}: {e}")

    src_file.write_text(json.dumps(sources, ensure_ascii=False, indent=2), encoding="utf-8")
    if failed:
        sys.exit(f"{failed} photo(s) failed")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
