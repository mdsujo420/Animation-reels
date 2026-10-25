import glob
import os
import subprocess
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFont

WHITE = (255, 255, 255)
HILITE = (255, 214, 0)


def _find_font_path():
    cands = [os.getenv("FONT_PATH", ""),
             "/usr/share/fonts/truetype/noto/NotoSansBengali-Bold.ttf",
             "/usr/share/fonts/truetype/noto/NotoSansBengali-Regular.ttf"]
    cands += sorted(glob.glob("/usr/share/fonts/**/NotoSansBengali*.ttf", recursive=True))
    try:
        out = subprocess.run(["fc-list", ":lang=bn", "-f", "%{file}\n"], capture_output=True, text=True, timeout=10).stdout
        cands += [l.strip() for l in out.splitlines() if l.strip().lower().endswith((".ttf", ".otf"))]
    except Exception:
        pass
    for p in cands:
        if p and os.path.exists(p):
            return p
    return None


@lru_cache(maxsize=1)
def load_font(size=68):
    p = _find_font_path()
    if not p:
        print("WARNING: no Bengali font found; captions may show boxes")
        return ImageFont.load_default()
    try:
        f = ImageFont.truetype(p, size, layout_engine=ImageFont.Layout.RAQM)
        print("caption font:", p, "(raqm shaping)")
        return f
    except Exception:
        print("WARNING: raqm not available, Bengali joined letters may look wrong")
        return ImageFont.truetype(p, size)


def _wrap(words, font, max_w):
    lines, cur = [], []
    for w in words:
        trial = " ".join(cur + [w])
        if font.getlength(trial) <= max_w or not cur:
            cur.append(w)
        else:
            lines.append(cur)
            cur = [w]
    if cur:
        lines.append(cur)
    return lines


@lru_cache(maxsize=512)
def caption_layer(words, active, canvas_w=1080, max_w=940, line_h=100):
    """RGBA strip with the sentence; the word being spoken is highlighted."""
    font = load_font()
    lines = _wrap(list(words), font, max_w)
    img = Image.new("RGBA", (canvas_w, line_h * max(1, len(lines)) + 20), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    sp = font.getlength(" ")
    idx = 0
    for li, line in enumerate(lines):
        total = sum(font.getlength(w) for w in line) + sp * (len(line) - 1)
        x = (canvas_w - total) / 2
        for w in line:
            d.text((x, li * line_h + 6), w, font=font, fill=HILITE if idx == active else WHITE,
                   stroke_width=7, stroke_fill=(0, 0, 0))
            x += font.getlength(w) + sp
            idx += 1
    return img
