"""Today's trending topics from the free Google Trends RSS feed (no API key)."""
import os
import xml.etree.ElementTree as ET
import requests

GEO = os.getenv("TRENDS_GEO", "BD")
URL = "https://trends.google.com/trending/rss?geo={geo}"


def fetch(limit=12):
    r = requests.get(URL.format(geo=GEO), headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
    r.raise_for_status()
    items = []
    for it in ET.fromstring(r.content).iter("item"):
        row = {"title": "", "traffic": "", "news": ""}
        for ch in it:
            tag = ch.tag.split("}")[-1]
            if tag == "title":
                row["title"] = (ch.text or "").strip()
            elif tag == "approx_traffic":
                row["traffic"] = (ch.text or "").strip()
            elif tag == "news_item" and not row["news"]:
                for sub in ch:
                    if sub.tag.split("}")[-1] == "news_item_title":
                        row["news"] = (sub.text or "").strip()
        if row["title"]:
            items.append(row)
    return items[:limit]


def as_text(items):
    return "\n".join(f"- {i['title']} ({i['traffic']}) {('| ' + i['news']) if i['news'] else ''}" for i in items)
