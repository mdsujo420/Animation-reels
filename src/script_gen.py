import json
import os

import requests

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
EMOTIONS = ["angry", "surprised", "happy", "scared"]
SETTINGS = ["bedroom", "office", "street", "kitchen", "school"]

PROMPT = """তুমি একজন ভাইরাল ফানি রিলস স্ক্রিপ্ট রাইটার। একটা স্টিকম্যান-স্টাইল অ্যানিমেটেড রিলসের জন্য স্ক্রিপ্ট লেখো।
একটাই ক্যারেক্টার কথা বলবে (একজন মেয়ে), সে দর্শকের সাথে সরাসরি কথা বলার মতো বা নিজের মনে বলার মতো করে বলবে।

{source}

নিয়ম:
- ভাষা: সহজ, কথ্য বাংলা। ঘরোয়া, রিলেটেবল হিউমার (যেমন "তোমার ... কে কখনো এটা বোলো না" ধাঁচের)।
- ৫ থেকে ৭টা সিন। প্রতি সিনে সর্বোচ্চ ১৪ শব্দ। শুরুতে হুক, শেষে জোরালো পাঞ্চলাইন।
- ট্রেন্ডিং বিষয় সরাসরি না মিললে শুধু আইডিয়াটা দৈনন্দিন জীবনের মজার পরিস্থিতিতে বদলে নাও।
- কোনো আসল ব্যক্তির নাম ধরে অপমান নয়। মৃত্যু, দুর্ঘটনা, রাজনীতি, ধর্ম, যৌনতা, ঘৃণা এড়িয়ে চলো।
- emotion শুধু এগুলোর একটা: {emotions}
- setting শুধু এগুলোর একটা: {settings}

শুধু এই JSON ফরম্যাটে উত্তর দাও, আর কিছু লিখবে না:
{{"title": "ছোট টাইটেল", "caption": "পোস্টের ক্যাপশন + ২-৩টা হ্যাশট্যাগ",
  "scenes": [{{"text": "...", "emotion": "angry", "setting": "bedroom"}}]}}
"""


def _clean(data):
    scenes = []
    for s in data.get("scenes", []):
        text = str(s.get("text", "")).strip()
        if not text:
            continue
        emo = s.get("emotion") if s.get("emotion") in EMOTIONS else "angry"
        setting = s.get("setting") if s.get("setting") in SETTINGS else "bedroom"
        scenes.append({"text": text, "emotion": emo, "setting": setting})
    if len(scenes) < 3:
        raise ValueError("too few scenes returned")
    return {"title": data.get("title", "Reel"), "caption": data.get("caption", ""), "scenes": scenes[:8]}


def _parse(text):
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text[4:] if text.lower().startswith("json") else text
    return json.loads(text)


def _groq(prompt):
    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {os.environ['GROQ_API_KEY']}"},
        json={"model": GROQ_MODEL, "temperature": 1.0,
              "response_format": {"type": "json_object"},
              "messages": [{"role": "user", "content": prompt}]},
        timeout=90)
    if r.status_code != 200:
        raise RuntimeError(f"Groq {r.status_code}: {r.text[:200]}")
    return _parse(r.json()["choices"][0]["message"]["content"])


def _gemini(prompt):
    from google import genai
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    resp = client.models.generate_content(
        model=GEMINI_MODEL, contents=prompt,
        config={"response_mime_type": "application/json", "temperature": 1.0})
    return _parse(resp.text)


def make(topic=None, trending_text=""):
    if topic:
        source = f"ভিডিওর বিষয়: {topic}"
    else:
        source = ("আজকের ট্রেন্ডিং বিষয়গুলো:\n" + trending_text +
                  "\n\nএর মধ্যে থেকে সবচেয়ে মজার ও নিরাপদ একটা বেছে নিয়ে তার উপর স্ক্রিপ্ট লেখো।")
    prompt = PROMPT.format(source=source, emotions=", ".join(EMOTIONS), settings=", ".join(SETTINGS))

    providers = []
    if os.getenv("GROQ_API_KEY"):
        providers.append(("groq", _groq))
    if os.getenv("GEMINI_API_KEY"):
        providers.append(("gemini", _gemini))
    if not providers:
        raise RuntimeError("no API key set: add GROQ_API_KEY (or GEMINI_API_KEY)")

    errors = []
    for name, fn in providers:
        for _ in range(2):
            try:
                return _clean(fn(prompt))
            except Exception as e:
                errors.append(f"{name}: {str(e)[:160]}")
    raise RuntimeError("script generation failed: " + " | ".join(errors[-3:]))
