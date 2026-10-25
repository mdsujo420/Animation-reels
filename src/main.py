import os
import sys
import traceback

from . import script_gen, telegram, trends, video


def main():
    chat = os.environ["CHAT_ID"]
    topic = os.getenv("TOPIC", "").strip()
    out_dir = "out"
    os.makedirs(out_dir, exist_ok=True)
    try:
        telegram.send_text(chat, "রিলস বানানো শুরু হয়েছে, ২-৪ মিনিট লাগবে...")
        trending = ""
        if not topic:
            try:
                trending = trends.as_text(trends.fetch())
            except Exception as e:
                print("trends failed:", e)
                topic = "দৈনন্দিন জীবনের একটা মজার রিলেটেবল পরিস্থিতি"
        script = script_gen.make(topic or None, trending)
        print(script)
        path = video.build(script, os.path.join(out_dir, "work"), os.path.join(out_dir, "reel.mp4"))
        telegram.send_video(chat, path, f"{script['title']}\n\n{script['caption']}")
    except Exception as e:
        traceback.print_exc()
        telegram.send_text(chat, f"রিলস বানাতে সমস্যা হয়েছে: {str(e)[:300]}")
        sys.exit(1)


if __name__ == "__main__":
    main()
