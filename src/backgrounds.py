"""Blurred room/street backdrops drawn with code, plus a crisp table/blanket band in front."""
from functools import lru_cache
from PIL import Image, ImageDraw, ImageFilter

VW, VH = 1080, 1920

FRONT = {
    "bedroom": (217, 201, 163), "office": (130, 95, 70), "street": (84, 84, 98),
    "kitchen": (176, 136, 100), "school": (190, 160, 120), "living": (150, 98, 92),
}

SETTINGS = {
    "bedroom": ((91, 127, 184), [("r", (0, 0, 330, 1500), (143, 168, 207)), ("r", (760, 0, 1080, 1500), (63, 100, 160)),
                                  ("e", (620, 900, 1200, 1500), (205, 212, 225))]),
    "office":  ((120, 140, 150), [("r", (120, 200, 700, 900), (170, 205, 230)), ("r", (800, 500, 1000, 1300), (90, 110, 120)),
                                   ("r", (0, 1200, 1080, 1920), (100, 120, 130))]),
    "street":  ((140, 190, 235), [("r", (0, 700, 300, 1500), (150, 150, 160)), ("r", (350, 500, 650, 1500), (120, 125, 140)),
                                   ("r", (700, 800, 1080, 1500), (165, 160, 150)), ("r", (0, 1300, 1080, 1920), (70, 70, 80))]),
    "kitchen": ((235, 215, 180), [("r", (0, 300, 500, 800), (200, 160, 110)), ("r", (600, 300, 1080, 800), (200, 160, 110)),
                                   ("r", (100, 900, 400, 1300), (240, 240, 240))]),
    "school":  ((170, 210, 190), [("r", (150, 250, 930, 900), (45, 90, 70)), ("r", (0, 1300, 1080, 1920), (190, 170, 130))]),
    "living":  ((205, 175, 155), [("r", (150, 330, 650, 800), (35, 35, 45)), ("r", (175, 355, 625, 775), (70, 110, 160)),
                                   ("r", (760, 200, 1000, 900), (180, 205, 225)), ("r", (0, 1250, 1080, 1920), (160, 120, 110))]),
}


@lru_cache(maxsize=16)
def _blurred(name):
    base, shapes = SETTINGS.get(name, SETTINGS["bedroom"])
    img = Image.new("RGB", (VW, VH), base)
    d = ImageDraw.Draw(img)
    for kind, box, col in shapes:
        (d.rectangle if kind == "r" else d.ellipse)(box, fill=col)
    return img.filter(ImageFilter.GaussianBlur(22))


@lru_cache(maxsize=24)
def scene_bg(name, table_top):
    """Blurred backdrop with a crisp table band starting at table_top (pixels)."""
    img = _blurred(name).copy()
    col = FRONT.get(name, FRONT["bedroom"])
    d = ImageDraw.Draw(img)
    d.rectangle([0, table_top, VW, VH], fill=col)
    d.rectangle([0, table_top, VW, table_top + 20], fill=tuple(min(255, c + 22) for c in col))
    return img
