"""Gemini writes a short funny Bangla skit as JSON scenes."""
import json
import os
from google import genai

MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
EMOTIONS = ["angry", "surprised", "happy", "scared"]
SETTINGS = ["bedroom", "office", "street", "kitchen", "school"]

PROMPT = """তুমি একজন ভাইরাল ফানি রিলস স্ক্রিপ্ট রাইটার। একটা স্টিকম্যান-স্টাইল অ্যানিমেটেড রিলসের জন্য স্ক্রিপ্ট লেখো।
একটাই ক্যারেক্টার কথা বলবে (একজন মেয়ে), সে ভোক্তার সাথে সরাসরি কথা বলার মতো বা নিজের মনে বলার মতো করে বলবে।

{source}

নিয়ম:
- ভাষা: সহজ, কথ্য বাংলা। ঘরোয়া, রিলেটেবল হিউমার (যেমন "তোমার ... কে কখনো এটা বোলো না" ধাঁচের)।
- ৫ থেকে ৭টা সিন। প্রতি সিনে সর্বোচ্চ ১৪ শব্দ। শুরুতে হুক, শেষে জোরালো পাঞ্চলাইন।
- ট্রেন্ডিং বিষয়ে সবসময় প্রাসঙ্গিক না হলে শুধু আইডিয়াটা দৈনন্দিন জীবনের মজার পরিস্থিতিতে বদলে নাও।
- কোনো আসল ব্যক্তির নাম ধরে অপমান নয়। মৃত্যু, দুর্ঘটনা, রাজনীতি, ধর্ম, যৌনতা, ঘৃণা এড়িয়ে চলো।
- emotion শুধু এগুলোর একটা: {emotions}
- setting শুধু এগুলোর একটা: {settings}

শুধু এই JSON ফরম্যাটে উত্তর দাও:
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
        raise ValueError("Gemini returned too few scenes")
    return {"title": data.get("title", "Reel"), "caption": data.get("caption", ""), "scenes": scenes[:8]}


def make(topic=None, trending_text=""):
    if topic:
        source = f"ভিডিওর বিষয়: {topic}"
    else:
        source = ("আজকের ট্রেন্ডিং বিষয়গুলো:\n" + trending_text +
                  "\n\nএর মধ্যে থেকে সবচেয়ে মজার ও নিরাপদ একটা বেছে নিয়ে তার উপর স্ক্রিপ্ট লেখো।")
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    prompt = PROMPT.format(source=source, emotions=", ".join(EMOTIONS), settings=", ".join(SETTINGS))
    last = None
    for _ in range(3):
        try:
            resp = client.models.generate_content(
                model=MODEL, contents=prompt, config={"response_mime_type": "application/json", "temperature": 1.0})
            return _clean(json.loads(resp.text))
        except Exception as e:  # retry on bad JSON / transient error
            last = e
    raise RuntimeError(f"script generation failed: {last}")
