"""Crop, resize and compress Mistvale images to WebP for the web.

Usage:  python tools/optimize_images.py [source_dir]

Put the AI-generated originals in tools/source/ named p101.png ... p108.png and
hero-banner.png (any format Pillow reads: png, jpg, webp). Anything missing there
are skipped.

Output goes to images/:
  p101.webp ... p108.webp  800x800 (1:1 centre crop), < 150 KB
  hero-banner.webp         1200x900 (4:3 centre crop), < 250 KB
"""
import sys
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "tools" / "source"
OUT = ROOT / "images"

JOBS = [(f"p{n}", (800, 800), 150_000) for n in range(101, 109)]
JOBS.append(("hero-banner", (1200, 900), 250_000))


def find_source(stem):
    for folder in (SRC,):
        for ext in (".png", ".jpg", ".jpeg", ".webp"):
            path = folder / (stem + ext)
            if path.exists():
                return path
    return None


def cover(img, size):
    """Scale to fill `size`, then centre-crop (like CSS object-fit: cover)."""
    tw, th = size
    scale = max(tw / img.width, th / img.height)
    img = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
    left, top = (img.width - tw) // 2, (img.height - th) // 2
    return img.crop((left, top, left + tw, top + th))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for stem, size, limit in JOBS:
        src = find_source(stem)
        if not src:
            print(f"MISSING  {stem}")
            continue
        img = cover(Image.open(src).convert("RGB"), size)
        dest = OUT / f"{stem}.webp"
        for quality in range(82, 39, -4):
            img.save(dest, "WEBP", quality=quality, method=6)
            if dest.stat().st_size <= limit:
                break
        kb = dest.stat().st_size / 1000
        flag = "OK " if dest.stat().st_size <= limit else "BIG"
        print(f"{flag} {dest.name:18} {size[0]}x{size[1]}  q{quality}  {kb:6.1f} KB  <- {src.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
