"""Story renderer: characters, acting, camera cuts, sfx, captions -> ffmpeg."""
import math
import os
import random
import subprocess
import wave

import numpy as np
from PIL import Image

from . import sfx, tts
from .backgrounds import FRONT, VH, VW, scene_bg
from .captions import caption_layer
from .character import H as CH, W as CW, render

FPS = 24
SR = tts.SR
SPF = SR // FPS
TAIL = 0.20
LEAD = 0.06
BEAT = 1.0
CAPTION_TOP = 1480
STRONG = {"angry", "surprised", "scared", "laugh"}

LAYOUT = {
    1: dict(width=960, top=330, centers=[540]),
    2: dict(width=560, top=780, centers=[290, 790]),
    3: dict(width=400, top=900, centers=[200, 540, 880]),
}
DEFAULT_REACT = {"angry": "scared", "surprised": "surprised", "happy": "happy", "scared": "surprised",
                 "sad": "sad", "smug": "neutral", "laugh": "laugh", "neutral": "neutral"}
SHAKY_SFX = {"thud", "scratch", "boing"}


def _ease(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def _mouth(voice, frames):
    """Mouth open level (0-5) and shape variant for every animation step (12 per second)."""
    step = SR // 12
    n = math.ceil(frames / 2) + 2
    rms = np.zeros(n)
    for i in range(n):
        seg = voice[i * step:(i + 1) * step].astype(np.float64)
        rms[i] = math.sqrt(np.mean(seg ** 2)) if len(seg) else 0.0
    pos = rms[rms > 0]
    ref = np.percentile(pos, 90) if len(pos) else 1.0
    lv = np.clip(np.round(rms / ref * 5), 0, 5)
    lv[(rms > 0.12 * ref) & (lv < 1)] = 1
    sm = lv.copy()
    for i in range(1, n - 1):
        sm[i] = round((lv[i - 1] + 2 * lv[i] + lv[i + 1]) / 4)
    var = np.zeros(n, dtype=int)
    cnt = 0
    for i in range(1, n):
        if sm[i] >= 2 and sm[i - 1] <= 1:
            cnt += 1
        var[i] = cnt % 2
    return sm.astype(int), var


def _prepare(script, workdir):
    scenes = []
    for i, sc in enumerate(script["scenes"]):
        text = sc["text"]
        if text:
            pcm = tts.synth(text, sc["speaker"], sc["emotion"], os.path.join(workdir, f"s{i}.mp3"))
            lead = int(LEAD * SR)
            dur = len(pcm) / SR
            frames = math.ceil((LEAD + dur + TAIL) * FPS)
            voice = np.zeros(frames * SPF, dtype=np.int16)
            voice[lead:lead + len(pcm)] = pcm
        else:
            frames = math.ceil(BEAT * FPS)
            voice = np.zeros(frames * SPF, dtype=np.int16)
            dur = 0.0
        lv, var = _mouth(voice, frames)
        words = tuple(text.split())
        weights = [len(w) + 1.5 for w in words]
        tot = sum(weights) or 1
        cum, acc = [], 0.0
        for w in weights:
            cum.append((acc / tot * dur + LEAD, (acc + w) / tot * dur + LEAD))
            acc += w
        scenes.append(dict(sc=sc, voice=voice, frames=frames, lv=lv, var=var, words=words, wtime=cum, dur=dur))
    return scenes


def _camera(si, s, n_scenes, chars, lay):
    sc = s["sc"]
    n = len(chars)
    h = CH * lay["width"] / CW
    head_y = lay["top"] + 0.42 * h
    cx_sp = lay["centers"][chars.index(sc["speaker"])]
    if n == 1:
        return (1.3, 540, head_y + 120) if si % 2 == 0 else (1.0, 540, 960)
    strong = sc["emotion"] in STRONG or si == n_scenes - 1 or not sc["text"]
    if strong:
        return (1.55 if n == 2 else 1.75, cx_sp, head_y + 40)
    return (1.12 if n == 2 else 1.0, 540, 1000)


def build(script, workdir, out_path):
    os.makedirs(workdir, exist_ok=True)
    chars = script["characters"]
    lay = LAYOUT[len(chars)]
    width = lay["width"]
    char_h = int(round(CH * width / CW))
    table_top = int(lay["top"] + 388 * width / CW)
    scenes = _prepare(script, workdir)
    n_scenes = len(scenes)

    # ---- audio timeline (voice + sfx)
    total_frames = sum(s["frames"] for s in scenes)
    mix = np.zeros(total_frames * SPF + SR, dtype=np.float32)
    off = 0
    for s in scenes:
        mix[off:off + len(s["voice"])] += s["voice"].astype(np.float32)
        fx = sfx.make(s["sc"]["sfx"])
        if len(fx):
            late = s["sc"]["sfx"] in ("ding", "sad") and s["sc"]["text"]
            at = off + (int((LEAD + s["dur"] * 0.9) * SR) if late else int(0.02 * SR))
            end = min(len(mix), at + len(fx))
            mix[at:end] += fx[:end - at].astype(np.float32) * 0.8
        off += s["frames"] * SPF
    mix = np.clip(mix[:total_frames * SPF], -32000, 32000).astype(np.int16)
    wav_path = os.path.join(workdir, "mix.wav")
    with wave.open(wav_path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(mix.tobytes())

    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{VW}x{VH}", "-r", str(FPS),
           "-i", "-", "-i", wav_path, "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", out_path]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    rng = random.Random(11)
    blink_off = {c: o for c, o in zip("ABC", (7, 21, 33))}
    prev_cam = None

    for si, s in enumerate(scenes):
        sc = s["sc"]
        n = s["frames"]
        bg = scene_bg(sc["setting"], table_top)
        front = FRONT.get(sc["setting"], FRONT["bedroom"])
        sp_slot = chars.index(sc["speaker"])
        cam_zoom, cam_x, cam_y = _camera(si, s, n_scenes, chars, lay)
        start_cam = prev_cam or (cam_zoom, cam_x, cam_y)
        react = sc["react"] or DEFAULT_REACT.get(sc["emotion"], "neutral")
        last = si == n_scenes - 1
        shaky = sc["emotion"] in ("angry", "scared")
        gesture = sc["pose"]

        for f in range(n):
            t = f / FPS
            g = f // 2
            frame = bg.copy()
            order = [i for i in range(len(chars)) if i != sp_slot] + [sp_slot]
            for slot in order:
                cid = chars[slot]
                is_sp = slot == sp_slot
                if len(chars) == 1:
                    gaze = 0
                elif is_sp:
                    gaze = 1 if sp_slot < len(chars) - 1 else -1
                else:
                    gaze = 1 if sp_slot > slot else -1
                expr = sc["emotion"] if is_sp else react
                blink = (g + blink_off.get(cid, 0)) % 40 == 0
                lvl, var = (int(s["lv"][g]), int(s["var"][g])) if (is_sp and sc["text"]) else (0, 0)
                pose, pb, wob = "idle", 0, 0
                if is_sp and gesture != "idle":
                    ramp = min(_ease((t - 0.12) / 0.22), _ease((n / FPS - t - 0.05) / 0.2))
                    pb = int(round(4 * ramp))
                    pose = gesture
                    wob = (-1, 0, 1, 0)[int(t * 9) % 4]
                side = "R" if gaze >= 0 else "L"
                layer = render(cid, expr, lvl, var, blink, gaze, pose, side, pb, wob, front, width)
                amp = 5 if is_sp else 3
                dy = int(math.sin(2 * math.pi * 1.1 * (g / 12.0) + slot) * amp - lvl * 0.9)
                x = lay["centers"][slot] - width // 2
                y = lay["top"] + dy
                if is_sp and sc["text"] and t < 0.14:
                    k = 1 + 0.05 * (1 - t / 0.14)
                    nw, nh = int(width * k), int(char_h * k)
                    layer = layer.resize((nw, nh), Image.BILINEAR)
                    x -= (nw - width) // 2
                    y -= nh - char_h
                frame.paste(layer, (x, y), layer)

            # camera: ease from previous shot, slow push-in, shakes
            z = cam_zoom * (1 + 0.05 * f / n)
            cx, cy = cam_x, cam_y
            if prev_cam and t < 0.22:
                e = _ease(t / 0.22)
                z = start_cam[0] + (z - start_cam[0]) * e
                cx = start_cam[1] + (cx - start_cam[1]) * e
                cy = start_cam[2] + (cy - start_cam[2]) * e
            shake = 3 if shaky else 0
            if (last or sc["sfx"] in SHAKY_SFX) and t < 0.35:
                shake = max(shake, 11 * (1 - t / 0.35))
                z *= 1 + 0.07 * (1 - t / 0.35)
            if shake:
                cx += rng.uniform(-shake, shake)
                cy += rng.uniform(-shake, shake)
            if z > 1.001:
                cw, ch = VW / z, VH / z
                x0 = min(max(cx - cw / 2, 0), VW - cw)
                y0 = min(max(cy - ch / 2, 0), VH - ch)
                img = frame.resize((VW, VH), Image.BICUBIC, box=(x0, y0, x0 + cw, y0 + ch))
            else:
                img = frame

            if s["words"]:
                active = -1
                for wi, (a, b) in enumerate(s["wtime"]):
                    if a <= t < b:
                        active = wi
                if active == -1 and t >= s["wtime"][-1][1]:
                    active = len(s["words"]) - 1
                cap = caption_layer(s["words"], active)
                img.paste(cap, (0, CAPTION_TOP), cap)
            proc.stdin.write(img.tobytes())
        prev_cam = (cam_zoom * 1.05, cam_x, cam_y)

    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError("ffmpeg failed")
    return out_path
