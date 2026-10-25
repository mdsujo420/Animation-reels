// Cloudflare Worker: Telegram message -> triggers the GitHub Actions workflow.
// Env vars (Worker settings): TG_TOKEN, GH_TOKEN, GH_REPO ("user/repo"), ALLOWED_CHAT_ID, WEBHOOK_SECRET
export default {
  async fetch(request, env) {
    if (request.method !== "POST") return new Response("ok");
    if (request.headers.get("X-Telegram-Bot-Api-Secret-Token") !== env.WEBHOOK_SECRET)
      return new Response("forbidden", { status: 403 });

    const update = await request.json();
    const msg = update.message;
    if (!msg || !msg.text) return new Response("ok");

    const chatId = String(msg.chat.id);
    const reply = (text) =>
      fetch(`https://api.telegram.org/bot${env.TG_TOKEN}/sendMessage`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ chat_id: chatId, text }),
      });

    if (chatId !== String(env.ALLOWED_CHAT_ID)) {
      await reply("এই বট শুধু মালিকের জন্য।");
      return new Response("ok");
    }

    const text = msg.text.trim();
    if (text.startsWith("/reel")) {
      const topic = text.replace(/^\/reel(@\w+)?/, "").trim();
      const res = await fetch(
        `https://api.github.com/repos/${env.GH_REPO}/actions/workflows/reel.yml/dispatches`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${env.GH_TOKEN}`,
            Accept: "application/vnd.github+json",
            "User-Agent": "reel-bot",
          },
          body: JSON.stringify({ ref: "main", inputs: { topic, chat_id: chatId } }),
        }
      );
      await reply(res.status === 204 ? "ঠিক আছে, কাজ শুরু হচ্ছে..." : `GitHub error: ${res.status}`);
    } else {
      await reply("রিলস বানাতে লেখো:\n/reel  (ট্রেন্ড থেকে)\n/reel টপিক  (নিজের টপিক)");
    }
    return new Response("ok");
  },
};
