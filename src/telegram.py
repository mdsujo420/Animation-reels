import os
import requests

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
API = f"https://api.telegram.org/bot{TOKEN}"


def send_text(chat_id, text):
    try:
        requests.post(f"{API}/sendMessage", data={"chat_id": chat_id, "text": text}, timeout=30)
    except Exception as e:
        print("telegram text failed:", e)


def send_video(chat_id, path, caption=""):
    with open(path, "rb") as f:
        r = requests.post(f"{API}/sendVideo",
                          data={"chat_id": chat_id, "caption": caption[:1000], "supports_streaming": "true",
                                "width": 1080, "height": 1920},
                          files={"video": f}, timeout=300)
    r.raise_for_status()
