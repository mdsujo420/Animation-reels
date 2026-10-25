"""Flat blurred room/street backdrops drawn with code (no image API needed)."""
from functools import lru_cache
from PIL import Image, ImageDraw, ImageFilter

VW, VH = 1080, 1920

SETTINGS = {
    "bedroom": ((91, 127, 184), [("r", (0, 0, 330, 1500), (143, 168, 207)), ("r", (760, 0, 1080, 1500), (63, 100, 160)),
                                  ("e", (620, 1000, 1200, 1500), (205, 212, 225))]),
    "office":  ((120, 140, 150), [("r", (120, 200, 700, 900), (170, 205, 230)), ("r", (0, 1300, 1080, 1920), (130, 95, 70)),
                                   ("r", (800, 500, 1000, 1300), (90, 110, 120))]),
    "street":  ((140, 190, 235), [("r", (0, 700, 300, 1500), (150, 150, 160)), ("r", (350, 500, 650, 1500), (120, 125, 140)),
                                   ("r", (700, 800, 1080, 1500), (165, 160, 150)), ("r", (0, 1500, 1080, 1920), (70, 70, 80))]),
    "kitchen": ((235, 215, 180), [("r", (0, 300, 500, 800), (200, 160, 110)), ("r", (600, 300, 1080, 800), (200, 160, 110)),
                                   ("r", (0, 1350, 1080, 1920), (160, 120, 85))]),
    "school":  ((170, 210, 190), [("r", (150, 250, 930, 900), (45, 90, 70)), ("r", (0, 1400, 1080, 1920), (190, 160, 120))]),
}


@lru_cache(maxsize=16)
def background(name):
    base, shapes = SETTINGS.get(name, SETTINGS["bedroom"])
    img = Image.new("RGB", (VW, VH), base)
    d = ImageDraw.Draw(img)
    for kind, box, col in shapes:
        (d.rectangle if kind == "r" else d.ellipse)(box, fill=col)
    return img.filter(ImageFilter.GaussianBlur(22))
