"""Two-step comedy writer: (1) story concept in English, (2) Bangla dialogue script as JSON.
Uses Groq (free, no card) first, Gemini as backup."""
import json
import os

import requests

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
EMOTIONS = ["neutral", "angry", "surprised", "happy", "scared", "sad", "smug", "laugh"]
SETTINGS = ["bedroom", "office", "street", "kitchen", "school", "living"]
POSES = ["idle", "point", "wave", "facepalm", "shrug", "excited", "shock"]
SFX = ["none", "pop", "thud", "whoosh", "ding", "boing", "sad", "scratch"]

CONCEPT_PROMPT = """You are a comedy writer for 25-second vertical cartoon skits (stick figures) for a Bangladeshi audience.
Inspiration (use loosely, or only the mood): {source}

Invent ONE short, genuinely funny story:
- A relatable everyday situation with a clear CONFLICT between characters (family, friends, roommates, shopkeeper, phone/internet/food/exam/traffic life).
- Build it: setup -> things get worse (rule of three) -> a surprising twist punchline.
- Cast (pick 1 to 3): A = young woman, B = young man, C = elderly woman (mother/grandma/aunt). Prefer 2 characters. Use 1 only for a monologue with a strong comic argument.
- Family-friendly. No politics, religion, death, accidents, sexual content, or insulting real people.

Return JSON only:
{{"premise": "...", "characters": ["A","B"], "setup": "...", "escalation": "...", "punchline": "..."}}"""

SCRIPT_PROMPT = """তুমি একজন ভাইরাল ফানি অ্যানিমেটেড রিলসের স্ক্রিপ্ট রাইটার। নিচের গল্পটাকে ২৫ সেকেন্ডের কথোপকথনের স্ক্রিপ্টে লেখো।

গল্প:
{concept}

ক্যারেক্টার: A = তরুণী, B = তরুণ, C = বয়স্ক নারী। শুধু গল্পে যারা আছে তাদের ব্যবহার করো।

নিয়ম:
- ৮ থেকে ১১টা সিন। প্রতি সিনে একজন কথা বলে (speaker), সর্বোচ্চ ১২ শব্দ। কথা হবে ঘরোয়া, প্রাণবন্ত কথ্য বাংলা (বাংলা হরফে)। ইংরেজি হরফ ও ইমোজি নয়।
- প্রথম সিনেই হুক, মাঝে সমস্যা বাড়বে, শেষ সিনে পাঞ্চলাইন। শেষে ইচ্ছা হলে একটা নীরব রিঅ্যাকশন সিন রাখতে পারো (text খালি "", speaker যার প্রতিক্রিয়া দেখাবে)।
- একজনের পর আরেকজন উত্তর দেবে, একই মানুষ টানা ২টার বেশি নয় (একা ক্যারেক্টারের গল্প হলে ঠিক আছে)।
- emotion = যে কথা বলছে তার ভাব। react = অন্যদের ভাব (শুনে তাদের প্রতিক্রিয়া)।
- pose = যে কথা বলছে তার অঙ্গভঙ্গি; সব সিনে না দিয়ে বেছে বেছে দাও (বাকিতে "idle")।
- sfx = শব্দ-প্রভাব; শুধু সত্যিকারের মজার মুহূর্তে (বেশিরভাগ "none")। পাঞ্চলাইনে "sad", "thud", "scratch" বা "ding" ভালো।
- emotion শুধু: {emotions}
- react শুধু: {emotions}
- setting শুধু: {settings}
- pose শুধু: {poses}
- sfx শুধু: {sfx}

শুধু এই JSON ফরম্যাটে উত্তর দাও:
{{"title": "ছোট টাইটেল", "caption": "পোস্টের ক্যাপশন + ২-৩টা হ্যাশট্যাগ", "characters": ["A","B"],
  "scenes": [
    {{"speaker": "A", "text": "...", "emotion": "angry", "react": "scared", "setting": "living", "pose": "point", "sfx": "none"}}
  ]}}"""


def _parse(text):
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text[4:] if text.lower().startswith("json") else text
    return json.loads(text)


_SKIP = ("whisper", "guard", "tts", "playai", "allam", "embed", "orpheus", "safeguard")
_PREFER = ("llama-3.3-70b", "gpt-oss-120b", "qwen", "llama-4", "gpt-oss-20b", "kimi", "llama-3.1-8b", "llama")
_models_cache = []


def _groq_models(headers):
    if _models_cache:
        return list(_models_cache)
    r = requests.get("https://api.groq.com/openai/v1/models", headers=headers, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"Groq models {r.status_code}: {r.text[:120]}")
    ids = [m["id"] for m in r.json().get("data", []) if not any(k in m["id"].lower() for k in _SKIP)]

    def rank(mid):
        for i, k in enumerate(_PREFER):
            if k in mid.lower():
                return i
        return len(_PREFER)

    _models_cache.extend(sorted(ids, key=rank))
    return list(_models_cache)


def _groq(prompt, temperature=1.0):
    headers = {"Authorization": f"Bearer {os.environ['GROQ_API_KEY']}"}
    models = _groq_models(headers)
    forced = os.getenv("GROQ_MODEL", "").strip()
    if forced:
        models.insert(0, forced)
    errors = []
    for model in models[:6]:
        for use_json in (True, False):
            body = {"model": model, "temperature": temperature, "messages": [{"role": "user", "content": prompt}]}
            if use_json:
                body["response_format"] = {"type": "json_object"}
            try:
                r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=body, timeout=120)
                if r.status_code != 200:
                    errors.append(f"{model} {r.status_code}")
                    continue
                data = _parse(r.json()["choices"][0]["message"]["content"])
                print("llm model:", model)
                return data
            except Exception as e:
                errors.append(f"{model} {str(e)[:60]}")
    raise RuntimeError("Groq: " + ", ".join(errors[-4:]))


def _gemini(prompt, temperature=1.0):
    from google import genai
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    resp = client.models.generate_content(
        model=GEMINI_MODEL, contents=prompt,
        config={"response_mime_type": "application/json", "temperature": temperature})
    return _parse(resp.text)


def _providers():
    p = []
    if os.getenv("GROQ_API_KEY"):
        p.append(("groq", _groq))
    if os.getenv("GEMINI_API_KEY"):
        p.append(("gemini", _gemini))
    if not p:
        raise RuntimeError("no API key set: add GROQ_API_KEY (or GEMINI_API_KEY)")
    return p


def _ask(prompt, validate):
    errors = []
    for name, fn in _providers():
        for _ in range(2):
            try:
                return validate(fn(prompt))
            except Exception as e:
                errors.append(f"{name}: {str(e)[:150]}")
    raise RuntimeError(" | ".join(errors[-3:]))


def _pick(v, allowed, default):
    return v if v in allowed else default


def _clean(data):
    raw = data.get("scenes", [])
    cast = [c for c in data.get("characters", []) if c in ("A", "B", "C")]
    scenes = []
    for s in raw:
        sp = s.get("speaker")
        if sp not in ("A", "B", "C"):
            continue
        text = str(s.get("text", "")).strip().strip('"“”')
        scenes.append({
            "speaker": sp, "text": text,
            "emotion": _pick(s.get("emotion"), EMOTIONS, "neutral"),
            "react": _pick(s.get("react"), EMOTIONS, ""),
            "setting": _pick(s.get("setting"), SETTINGS, "living"),
            "pose": _pick(s.get("pose"), POSES, "idle"),
            "sfx": _pick(s.get("sfx"), SFX, "none"),
        })
    talk = [s for s in scenes if s["text"]]
    if len(talk) < 4:
        raise ValueError("too few spoken scenes")
    scenes = scenes[:12]
    used = []
    for c in cast + [s["speaker"] for s in scenes]:
        if c not in used:
            used.append(c)
    used = sorted(used[:3])
    scenes = [s for s in scenes if s["speaker"] in used]
    # keep one setting for the whole story (a story happens in one place)
    place = scenes[0]["setting"]
    for s in scenes:
        s["setting"] = place
    return {"title": str(data.get("title", "Reel")), "caption": str(data.get("caption", "")),
            "characters": used, "scenes": scenes}


def make(topic=None, trending_text=""):
    if topic:
        source = f"Topic given by the user: {topic}"
    else:
        source = "Today's trending topics in Bangladesh (pick a funny, safe angle or just use the mood):\n" + trending_text
    concept = None
    try:
        concept = _ask(CONCEPT_PROMPT.format(source=source), lambda d: d if d.get("punchline") else (_ for _ in ()).throw(ValueError("no punchline")))
        print("concept:", concept)
    except Exception as e:
        print("concept step failed, continuing:", e)
    cj = json.dumps(concept, ensure_ascii=False) if concept else f"ট্রেন্ড/বিষয়: {source}"
    prompt = SCRIPT_PROMPT.format(concept=cj, emotions=", ".join(EMOTIONS), settings=", ".join(SETTINGS),
                                  poses=", ".join(POSES), sfx=", ".join(SFX))
    try:
        return _ask(prompt, _clean)
    except Exception as e:
        raise RuntimeError(f"script generation failed: {e}")
