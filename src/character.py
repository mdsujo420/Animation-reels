"""Stick-figure character drawn from parts, so every frame looks identical.
Design space is 380x420 (same as the preview). Rendered 2x supersampled then downsized."""
import math
from functools import lru_cache
from PIL import Image, ImageDraw

W, H = 380, 420
OUT_SCALE = 2.8          # final layer = 1064 x 1176
SS = 2
K = OUT_SCALE * SS

INK = (17, 17, 17)
WHITE = (255, 255, 255)
HAIR = (74, 31, 23)
SHIRT = (169, 155, 208)
BLANKET = (217, 201, 163)
MOUTH_IN = (90, 21, 21)

# brow angles (deg), brow lift, eye scale, pupil offset, closed-mouth shape
EXPR = {
    "angry":     dict(l=15,  r=-15, by=0,   eye=1.0,  px=6, py=0,  mouth="angry"),
    "surprised": dict(l=0,   r=0,   by=-14, eye=1.15, px=0, py=0,  mouth="o"),
    "happy":     dict(l=-8,  r=8,   by=-6,  eye=1.0,  px=0, py=2,  mouth="smile"),
    "scared":    dict(l=-16, r=16,  by=-8,  eye=1.05, px=0, py=-4, mouth="wave"),
}


def _bez(p0, p1, p2, n=28):
    out = []
    for i in range(n + 1):
        t = i / n
        x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t ** 2 * p2[0]
        y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t ** 2 * p2[1]
        out.append((x, y))
    return out


def _s(points):
    return [(x * K, y * K) for x, y in points]


def _line(d, points, width, fill=INK):
    pts = _s(points)
    w = max(1, int(width * K))
    d.line(pts, fill=fill, width=w, joint="curve")
    r = w / 2
    for x, y in (pts[0], pts[-1]):
        d.ellipse([x - r, y - r, x + r, y + r], fill=fill)


def _ell(d, cx, cy, rx, ry, fill=None, outline=None, width=0):
    d.ellipse([(cx - rx) * K, (cy - ry) * K, (cx + rx) * K, (cy + ry) * K],
              fill=fill, outline=outline, width=int(width * K))


def _poly(d, points, fill, width=4):
    d.polygon(_s(points), fill=fill)
    _line(d, points + [points[0]], width)


def _rot(cx, cy, x, y, deg):
    a = math.radians(deg)
    return cx + x * math.cos(a) - y * math.sin(a), cy + x * math.sin(a) + y * math.cos(a)


@lru_cache(maxsize=512)
def character(expr="angry", mouth=0, blink=False):
    """mouth: 0 = closed (expression mouth), 1..5 = open while talking."""
    e = EXPR[expr]
    img = Image.new("RGBA", (int(W * K), int(H * K)), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    _ell(d, 190, 62, 34, 34, HAIR, INK, 4)                                   # bun
    _poly(d, [(118, 305), (262, 305), (280, 420), (100, 420)], SHIRT)         # shirt
    _line(d, _bez((122, 312), (92, 360), (100, 395)), 6)                      # arms
    _line(d, _bez((258, 312), (288, 360), (280, 395)), 6)
    d.rounded_rectangle([168 * K, 285 * K, 212 * K, 325 * K], radius=10 * K,
                        fill=WHITE, outline=INK, width=int(4 * K))            # neck
    blanket = _bez((0, 392), (120, 370), (200, 388)) + _bez((200, 388), (300, 410), (380, 385)) + [(380, 420), (0, 420)]
    d.polygon(_s(blanket), fill=BLANKET)
    _ell(d, 100, 398, 16, 12, INK)                                            # hands
    _ell(d, 280, 398, 16, 12, INK)

    _ell(d, 190, 190, 106, 106, WHITE, INK, 4)                                # head
    hair = (_bez((82, 195), (76, 70), (190, 78)) + _bez((190, 78), (304, 70), (298, 195))
            + _bez((298, 195), (292, 138), (190, 126)) + _bez((190, 126), (88, 138), (82, 195)))
    _poly(d, hair, HAIR)

    for cx in (148, 232):                                                     # eyes
        r = 27 * e["eye"]
        if blink:
            _line(d, [(cx - r, 190), (cx + r, 190)], 4)
        else:
            _ell(d, cx, 190, r, r, WHITE, INK, 3.5)
            _ell(d, cx + e["px"] * e["eye"], 190 + e["py"] * e["eye"], 9 * e["eye"], 9 * e["eye"], INK)

    for cx, ang in ((148, e["l"]), (232, e["r"])):                            # brows
        cy = 150 + e["by"]
        _line(d, [_rot(cx, cy, -26, 0, ang), _rot(cx, cy, 26, 0, ang)], 7)

    if mouth > 0:                                                             # talking
        h = 4 + mouth * 5
        shape = _bez((172, 252), (190, 252 + h), (208, 252)) + [(172, 252)]
        d.polygon(_s(shape), fill=MOUTH_IN)
        _line(d, shape, 4.5)
    else:
        m = e["mouth"]
        if m == "angry":
            _line(d, _bez((165, 264), (190, 246), (215, 264)), 4.5)
        elif m == "smile":
            _line(d, _bez((156, 244), (190, 292), (224, 244)), 4.5)
        elif m == "wave":
            _line(d, _bez((165, 266), (177, 254), (190, 266)) + _bez((190, 266), (203, 278), (215, 266)), 4.5)
        else:
            _ell(d, 190, 256, 10, 15, None, INK, 4.5)

    return img.resize((int(W * OUT_SCALE), int(H * OUT_SCALE)), Image.LANCZOS)
