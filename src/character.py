"""Stick-figure cast drawn from parts (identical in every frame).
Design space 380x420. Each call renders one character at a given pixel width."""
import math
from functools import lru_cache
from PIL import Image, ImageDraw

W, H = 380, 420
SS = 2

INK = (17, 17, 17)
WHITE = (255, 255, 255)
MOUTH_IN = (90, 21, 21)
TONGUE = (214, 110, 120)

LOOKS = {
    "A": dict(hair=(74, 31, 23), shirt=(169, 155, 208), style="bun", glasses=False),     # young woman
    "B": dict(hair=(34, 28, 30), shirt=(112, 184, 136), style="spiky", glasses=False),   # young man
    "C": dict(hair=(176, 176, 182), shirt=(236, 160, 100), style="bun", glasses=True),   # elderly woman
}

# l/r brow angle, ly/ry brow lift, eye scale, pupil offset, lid (0..1 half-closed), closed eyes, mouth shape
EXPR = {
    "neutral":   dict(l=0,   r=0,   ly=0,   ry=0,   eye=1.0,  px=0, py=0,  lid=0,    closed=False, mouth="flat"),
    "angry":     dict(l=15,  r=-15, ly=2,   ry=2,   eye=1.0,  px=6, py=0,  lid=0,    closed=False, mouth="frown"),
    "surprised": dict(l=0,   r=0,   ly=-14, ry=-14, eye=1.15, px=0, py=0,  lid=0,    closed=False, mouth="o"),
    "happy":     dict(l=-8,  r=8,   ly=-6,  ry=-6,  eye=1.0,  px=0, py=2,  lid=0,    closed=False, mouth="smile"),
    "scared":    dict(l=-16, r=16,  ly=-8,  ry=-8,  eye=1.05, px=0, py=-4, lid=0,    closed=False, mouth="wave"),
    "sad":       dict(l=-14, r=14,  ly=0,   ry=0,   eye=1.0,  px=0, py=4,  lid=0,    closed=False, mouth="sad"),
    "smug":      dict(l=4,   r=-8,  ly=0,   ry=-10, eye=1.0,  px=0, py=0,  lid=0.38, closed=False, mouth="smirk"),
    "laugh":     dict(l=-6,  r=6,   ly=-8,  ry=-8,  eye=1.0,  px=0, py=0,  lid=0,    closed=True,  mouth="laugh"),
}

# arm targets: (control point, hand end). Single-arm poses are defined for the right arm and mirrored for the left.
IDLE = {"L": ((92, 360), (100, 395)), "R": ((288, 360), (280, 395))}
SHOULDER = {"L": (122, 312), "R": (258, 312)}
POSES = {
    "point":    {"R": ((322, 292), (352, 214))},
    "wave":     {"R": ((332, 282), (340, 172))},
    "facepalm": {"R": ((304, 262), (196, 176))},
    "shrug":    {"L": ((52, 332), (36, 284)), "R": ((328, 332), (344, 284))},
    "excited":  {"L": ((78, 292), (94, 224)), "R": ((302, 292), (286, 224))},
    "shock":    {"L": ((130, 302), (150, 266)), "R": ((250, 302), (230, 266))},
}
SINGLE = {"point", "wave", "facepalm"}


def _bez(p0, p1, p2, n=26):
    out = []
    for i in range(n + 1):
        t = i / n
        out.append(((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t ** 2 * p2[0],
                    (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t ** 2 * p2[1]))
    return out


def _rot(cx, cy, x, y, deg):
    a = math.radians(deg)
    return cx + x * math.cos(a) - y * math.sin(a), cy + x * math.sin(a) + y * math.cos(a)


def _lerp(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


class _P:
    def __init__(self, d, k):
        self.d, self.k = d, k

    def s(self, pts):
        return [(x * self.k, y * self.k) for x, y in pts]

    def line(self, pts, w, fill=INK):
        p = self.s(pts)
        wi = max(1, int(w * self.k))
        self.d.line(p, fill=fill, width=wi, joint="curve")
        r = wi / 2
        for x, y in (p[0], p[-1]):
            self.d.ellipse([x - r, y - r, x + r, y + r], fill=fill)

    def ell(self, cx, cy, rx, ry, fill=None, outline=None, width=0):
        k = self.k
        self.d.ellipse([(cx - rx) * k, (cy - ry) * k, (cx + rx) * k, (cy + ry) * k],
                       fill=fill, outline=outline, width=int(width * k))

    def poly(self, pts, fill, ow=4):
        self.d.polygon(self.s(pts), fill=fill)
        if ow:
            self.line(pts + [pts[0]], ow)

    def rect(self, x0, y0, x1, y1, fill):
        k = self.k
        self.d.rectangle([x0 * k, y0 * k, x1 * k, y1 * k], fill=fill)


def _arm_targets(pose, side, pb, wob):
    """Return {'L': (ctrl,end)|None, 'R': ...} for arms that are raised (blend p=pb/4)."""
    out = {"L": None, "R": None}
    spec = POSES.get(pose)
    if not spec or pb <= 0:
        return out
    p = pb / 4.0
    for arm, (ctrl, end) in spec.items():
        a = arm
        if pose in SINGLE and side == "L":
            a = "L"
            ctrl, end = (W - ctrl[0], ctrl[1]), (W - end[0], end[1])
        ic, ie = IDLE[a]
        c, e = _lerp(ic, ctrl, p), _lerp(ie, end, p)
        if pose == "wave":
            e = (e[0] + wob * 15 * p * (-1 if a == "L" else 1), e[1])
        elif pose == "point":
            e = (e[0], e[1] + wob * 5 * p)
        out[a] = (c, e)
    return out


@lru_cache(maxsize=160)
def render(look="A", expr="neutral", mouth=0, variant=0, blink=False, gaze=0,
           pose="idle", side="R", pb=0, wob=0, front=(217, 201, 163), width=560):
    k = width / W * SS
    lk = LOOKS[look]
    e = EXPR[expr]
    hair, shirt = lk["hair"], lk["shirt"]
    img = Image.new("RGBA", (int(W * k), int(H * k)), (0, 0, 0, 0))
    p = _P(ImageDraw.Draw(img), k)
    raised = _arm_targets(pose, side, pb, wob)

    # --- behind the body
    if lk["style"] == "bun":
        p.ell(190, 62, 34, 34, hair, INK, 4)
    else:
        for tri in ([(128, 104), (138, 56), (162, 94)], [(160, 94), (186, 44), (210, 92)], [(208, 94), (236, 58), (254, 104)]):
            p.poly(tri, hair, 4)
    p.poly([(118, 305), (262, 305), (280, 420), (100, 420)], shirt)
    for a in ("L", "R"):                                           # idle arms
        if raised[a] is None:
            ic, ie = IDLE[a]
            p.line(_bez(SHOULDER[a], ic, ie), 6)
    p.d.rounded_rectangle([168 * k, 285 * k, 212 * k, 325 * k], radius=10 * k, fill=WHITE, outline=INK, width=int(4 * k))
    lighter = tuple(min(255, c + 22) for c in front)
    p.rect(0, 388, W, H, front)                                    # table / blanket front
    p.rect(0, 388, W, 396, lighter)
    for a in ("L", "R"):
        if raised[a] is None:
            p.ell(IDLE[a][1][0], 398, 16, 12, INK)

    # --- head
    p.ell(190, 190, 106, 106, WHITE, INK, 4)
    cap = (_bez((82, 195), (76, 70), (190, 78)) + _bez((190, 78), (304, 70), (298, 195))
           + _bez((298, 195), (292, 138), (190, 126)) + _bez((190, 126), (88, 138), (82, 195)))
    p.poly(cap, hair)

    px = gaze * 7 if gaze else e["px"]
    for cx in (148, 232):
        r = 27 * e["eye"]
        if e["closed"]:
            p.line(_bez((cx - 24, 196), (cx, 168), (cx + 24, 196)), 4)
        elif blink:
            p.line([(cx - r, 190), (cx + r, 190)], 4)
        else:
            p.ell(cx, 190, r, r, WHITE, INK, 3.5)
            p.ell(cx + px * e["eye"], 190 + e["py"] * e["eye"], 9 * e["eye"], 9 * e["eye"], INK)
            if e["lid"]:
                ly = 190 - r + 2 * r * e["lid"]
                p.rect(cx - r - 3, 190 - r - 4, cx + r + 3, ly, WHITE)
                p.line([(cx - r, ly), (cx + r, ly)], 4)
    if lk["glasses"]:
        for cx in (148, 232):
            p.ell(cx, 190, 35, 35, None, INK, 3)
        p.line([(183, 188), (197, 188)], 3)

    for cx, ang, lift in ((148, e["l"], e["ly"]), (232, e["r"], e["ry"])):
        cy = 150 + lift
        p.line([_rot(cx, cy, -26, 0, ang), _rot(cx, cy, 26, 0, ang)], 7)

    # --- mouth
    m = e["mouth"]
    if mouth <= 0 and m == "laugh":
        mouth, variant = 4, 0
    if mouth > 0:
        d = 4 + mouth * 5
        if variant == 0:
            w2 = 17 + mouth * 2.2
            shape = _bez((190 - w2, 250), (190, 250 + 2 * d), (190 + w2, 250)) + [(190 - w2, 250)]
            p.d.polygon(p.s(shape), fill=MOUTH_IN)
            if d >= 14:
                p.ell(190, 250 + d * 0.72, w2 * 0.42, d * 0.16, TONGUE)
            p.line(shape, 4.5)
        else:
            rx, ry = 8 + mouth * 1.5, 5 + mouth * 3.2
            cy = 252 + ry * 0.55
            p.ell(190, cy, rx, ry, MOUTH_IN, INK, 4.5)
            if ry >= 14:
                p.ell(190, cy + ry * 0.45, rx * 0.5, ry * 0.2, TONGUE)
    elif m == "flat":
        p.line([(172, 262), (208, 262)], 4.5)
    elif m == "frown":
        p.line(_bez((165, 264), (190, 246), (215, 264)), 4.5)
    elif m == "smile":
        p.line(_bez((156, 244), (190, 292), (224, 244)), 4.5)
    elif m == "wave":
        p.line(_bez((165, 266), (177, 254), (190, 266)) + _bez((190, 266), (203, 278), (215, 266)), 4.5)
    elif m == "sad":
        p.line(_bez((170, 270), (190, 254), (210, 270)), 4.5)
    elif m == "smirk":
        p.line(_bez((160, 262), (190, 268), (224, 246)), 4.5)
    else:  # "o"
        p.ell(190, 256, 10, 15, None, INK, 4.5)

    # --- raised arms on top of everything
    for a in ("L", "R"):
        t = raised[a]
        if t:
            p.line(_bez(SHOULDER[a], t[0], t[1]), 6)
            p.ell(t[1][0], t[1][1], 15, 15, INK)

    return img.resize((int(width), int(round(H * width / W))), Image.LANCZOS)
