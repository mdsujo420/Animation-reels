import glob
import os
from PIL import ImageFont

_CANDIDATES = [
    os.getenv("FONT_PATH", ""),
    "/usr/share/fonts/truetype/noto/NotoSansBengali-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansBengali-Regular.ttf",
]


def load_font(size=66):
    paths = [p for p in _CANDIDATES if p] + glob.glob("/usr/share/fonts/**/NotoSansBengali*.ttf", recursive=True)
    for p in paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size, layout_engine=ImageFont.Layout.RAQM)
            except Exception:
                return ImageFont.truetype(p, size)
    print("WARNING: no Bengali font found; captions may show boxes")
    return ImageFont.load_default()


def wrap(text, font, max_w):
    lines, cur = [], ""
    for word in text.split():
        trial = (cur + " " + word).strip()
        if font.getlength(trial) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def draw_caption(draw, text, font, canvas_w=1080, top=1620, max_w=940, line_h=96):
    for i, line in enumerate(wrap(text, font, max_w)):
        w = font.getlength(line)
        draw.text(((canvas_w - w) / 2, top + i * line_h), line, font=font, fill=(255, 255, 255),
                  stroke_width=7, stroke_fill=(0, 0, 0))
