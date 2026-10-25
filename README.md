# Funny Reels Bot

Telegram-এ `/reel` লিখলে ট্রেন্ডিং টপিক থেকে স্টিকম্যান-স্টাইল ফানি বাংলা রিলস বানিয়ে সেই চ্যাটেই পাঠায়।

```
Telegram → Cloudflare Worker → GitHub Actions → (Trends → Gemini স্ক্রিপ্ট → Bangla TTS → অ্যানিমেশন → ffmpeg) → Telegram
```

## সেটআপ (একবারই)

### ১. GitHub
1. নতুন প্রাইভেট রিপো বানিয়ে এই ফোল্ডারের সব ফাইল push করো (ব্রাঞ্চের নাম `main`)।
2. Settings → Secrets and variables → Actions → এই ৩টা secret যোগ করো:
   - `GEMINI_API_KEY` (aistudio.google.com থেকে ফ্রি কী)
   - `TELEGRAM_BOT_TOKEN` (@BotFather থেকে)
   - `TELEGRAM_CHAT_ID` (@userinfobot থেকে তোমার আইডি। অটো মোডে এটা লাগবে)
3. Actions ট্যাব থেকে `make-reel` ওয়ার্কফ্লো একবার হাতে চালিয়ে টেস্ট করো।

### ২. Telegram কন্ট্রোল (Cloudflare Worker, ফ্রি)
1. dash.cloudflare.com → Workers → নতুন Worker → `worker/telegram-webhook.js` এর কোড পেস্ট করে Deploy।
2. Worker-এর Settings → Variables-এ যোগ করো:
   - `TG_TOKEN` = বট টোকেন
   - `GH_TOKEN` = GitHub Personal Access Token (এই রিপোর Actions: Read and write পারমিশন)
   - `GH_REPO` = `তোমার-ইউজার/রিপো-নাম`
   - `ALLOWED_CHAT_ID` = তোমার chat id
   - `WEBHOOK_SECRET` = যেকোনো লম্বা র‍্যান্ডম লেখা
3. ওয়েবহুক সেট করো (একবার, টার্মিনালে):
```
curl "https://api.telegram.org/bot<TG_TOKEN>/setWebhook" \
  -d "url=https://<তোমার-worker>.workers.dev" \
  -d "secret_token=<WEBHOOK_SECRET>"
```

## ব্যবহার
- `/reel` : আজকের ট্রেন্ড থেকে নিজে বেছে বানাবে
- `/reel বৃষ্টির দিনে অফিস` : তোমার দেওয়া টপিকে বানাবে
- অটো মোড: প্রতিদিন ৫টা রিলস নিজে থেকে বানায় (প্রায় ৫ ঘণ্টা পর পর, UTC ০০/০৫/১০/১৫/২০ টায়)। বন্ধ করতে ওয়ার্কফ্লোর `schedule:` অংশ মুছে দাও।

## কাস্টমাইজ (Variables / env)
| নাম | কাজ | ডিফল্ট |
|---|---|---|
| `TRENDS_GEO` | কোন দেশের ট্রেন্ড | `BD` |
| `TTS_VOICE` | ভয়েস (`bn-BD-PradeepNeural` = পুরুষ) | `bn-BD-NabanitaNeural` |
| `TTS_RATE`, `TTS_PITCH` | ভয়েসের গতি ও সুর | `+8%`, `+4Hz` |
| `GEMINI_MODEL` | স্ক্রিপ্ট মডেল | `gemini-2.5-flash` |

## ফাইল কোথায় কী
- `src/character.py` : ক্যারেক্টার ও এক্সপ্রেশন (চুল, জামার রং এখানে বদলাও)
- `src/backgrounds.py` : ঝাপসা ব্যাকগ্রাউন্ড (bedroom, office, street, kitchen, school)
- `src/script_gen.py` : Gemini প্রম্পট (হিউমারের স্টাইল এখানে বদলাও)
- `src/video.py` : অ্যানিমেশন (মুখ অডিওর সাথে মেলে, পলক, দোলা, shake, zoom)
- `src/tts.py` : বাংলা ভয়েস (edge-tts, ফ্রি)

## জানা সীমাবদ্ধতা
- ক্যারেক্টার আপাতত একটাই, ৪টা এক্সপ্রেশন। আরও এক্সপ্রেশন `EXPR`-এ যোগ করা যায়।
- Edge ভয়েস কখনো GitHub সার্ভার থেকে ব্লক হলে ওয়ার্কফ্লো আবার চালাও।
- ট্রেন্ড মাঝে মাঝে মজার না-ও হতে পারে, তখন `/reel টপিক` ব্যবহার করো।
