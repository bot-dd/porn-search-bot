import asyncio, aiohttp, threading, json
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from flask import Flask
from bs4 import BeautifulSoup
from datetime import datetime

# ----------------------- Config -----------------------
API_ID = 26649585
API_HASH = "588a3ea6fd01ae88bd2e10fed7d55b2c"
BOT_TOKEN = "7669234075:AAHU3BZ0sjUPnn9aFw_jBg9CFNnyfYlDH9Y"
ADMIN_ID = 7822720438
CHANNEL_ID = "7030759377"

app = Client("mega_nsfw", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
flask_app = Flask(__name__)
user_keywords = {}
user_favs = {}

@flask_app.route("/")
def home(): return "🔥 Mega NSFW Bot is running!"

def run_flask(): flask_app.run(host="0.0.0.0", port=8080)

# ----------------------- Scraper -----------------------
async def fetch_videos(query, site="pornhub", limit=5):
    url, selector, base = "", "", ""
    result = []

    if site == "pornhub":
        url = f"https://www.pornhub.com/video/search?search={query}"
        selector = ".videoPreviewBg"
        base = "https://www.pornhub.com"
    elif site == "xnxx":
        url = f"https://www.xnxx.com/search/{query}"
        selector = "div.mozaique .thumb"
        base = "https://www.xnxx.com"
    elif site == "xhamster":
        url = f"https://xhamster.com/search/{query}"
        selector = ".thumb-list__item"
        base = "https://xhamster.com"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as res:
                html = await res.text()
        soup = BeautifulSoup(html, "lxml")
        videos = soup.select(selector)
        for item in videos[:limit]:
            try:
                if site == "pornhub":
                    title = item["data-title"]
                    link = base + item["href"]
                    thumb = item["data-thumb_url"]
                    duration = item.select_one(".duration").text.strip()
                elif site == "xnxx":
                    a = item.find("a")
                    title = a["title"]
                    link = base + a["href"]
                    thumb = a.img.get("data-src", a.img["src"])
                    duration = "N/A"
                elif site == "xhamster":
                    a = item.find("a")
                    title = a.img["alt"]
                    link = a["href"]
                    thumb = a.img["src"]
                    duration = "N/A"
                result.append({
                    "title": title,
                    "thumb": thumb,
                    "url": link,
                    "duration": duration,
                    "site": site.upper()
                })
            except Exception as e:
                print(f"Parsing error: {e}")
                continue
    except Exception as e:
        print(f"Scraping error: {e}")
    return result

# ----------------------- Button UI -----------------------
def video_buttons(url, fav=False):
    buttons = [
        [InlineKeyboardButton("▶️ Watch", url=url)],
        [InlineKeyboardButton("🎯 Suggest More", callback_data="suggest")],
        [InlineKeyboardButton("📥 Download", url=url)]
    ]
    if fav:
        buttons.append([InlineKeyboardButton("❤️ Add to Favorites", callback_data=f"fav_{url}")])
    return InlineKeyboardMarkup(buttons)

# ----------------------- Bot Commands -----------------------
@app.on_message(filters.command("start"))
async def start(client, msg: Message):
    user_keywords[msg.from_user.id] = "trending"
    await msg.reply(
        "🔥 **Welcome to Mega NSFW Bot!**\n\n"
        "Type any keyword to search videos from Pornhub, XNXX, XHamster.\n"
        "Use /help to see available commands.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔥 Trending", callback_data="trending"),
             InlineKeyboardButton("📈 Weekly Top", callback_data="weekly")],
            [InlineKeyboardButton("❤️ Favorites", callback_data="favlist"),
             InlineKeyboardButton("🛠 Admin", callback_data="admin")]
        ])
    )

@app.on_message(filters.command("help"))
async def help_msg(client, msg):
    await msg.reply(
        "**📘 Commands List**\n\n"
        "`/start` - Start the bot\n"
        "`/help` - Show help\n"
        "`/stats` - Show bot stats\n"
        "`/admin` - Admin panel (admin only)\n\n"
        "📌 **Just send any keyword like:**\n"
        "`mia khalifa`, `lesbian`, `bd girl`, `hentai`"
    )

@app.on_message(filters.command("stats"))
async def stats_msg(client, msg):
    u_count = len(user_keywords)
    f_count = sum(len(v) for v in user_favs.values())
    await msg.reply(f"📊 **Bot Stats**\n\n👤 Total Users: {u_count}\n❤️ Total Favorites: {f_count}")

@app.on_message(filters.command("admin") & filters.user(ADMIN_ID))
async def admin_panel(client, msg):
    await msg.reply("🛠 **Admin Panel**",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📤 Post Trending Now", callback_data="post_now")],
                        [InlineKeyboardButton("📊 View Stats", callback_data="stats")]
                    ]))

# ----------------------- Search Handler -----------------------
@app.on_message(filters.text & ~filters.command(["start", "help", "stats", "admin"]))
async def search_handler(client, msg):
    query = msg.text.strip()
    uid = msg.from_user.id
    user_keywords[uid] = query
    for site in ["pornhub", "xnxx", "xhamster"]:
        await msg.reply(f"🔍 Searching `{query}` on **{site.upper()}**...")
        videos = await fetch_videos(query, site)
        if not videos:
            await msg.reply(f"❌ No results found on {site.upper()}")
            continue
        for vid in videos:
            caption = f"🎬 **{vid['title']}**\n⏱ {vid['duration']} | 🌐 {vid['site']}"
            await msg.reply_photo(photo=vid["thumb"], caption=caption,
                                  reply_markup=video_buttons(vid["url"], fav=True))

# ----------------------- Callback Handler -----------------------
@app.on_callback_query()
async def cb(client, cbq):
    data = cbq.data
    uid = cbq.from_user.id

    if data == "trending":
        vids = await fetch_videos("trending", "pornhub")
    elif data == "weekly":
        vids = await fetch_videos("top+weekly", "pornhub")
    elif data == "suggest":
        key = user_keywords.get(uid, "popular")
        vids = await fetch_videos(key, "pornhub")
    elif data.startswith("fav_"):
        url = data.replace("fav_", "")
        if uid not in user_favs:
            user_favs[uid] = []
        if url not in user_favs[uid]:
            user_favs[uid].append(url)
        return await cbq.answer("✅ Added to favorites")
    elif data == "favlist":
        favs = user_favs.get(uid, [])
        if not favs:
            return await cbq.message.reply("❌ No favorites saved.")
        btns = [[InlineKeyboardButton(f"❤️ Favorite {i+1}", url=favs[i])] for i in range(min(len(favs), 10))]
        return await cbq.message.reply("📁 **Your Saved Favorites:**", reply_markup=InlineKeyboardMarkup(btns))
    elif data == "post_now":
        await post_trending_now()
        return await cbq.answer("✅ Posted trending video to channel!")
    elif data == "stats":
        return await stats_msg(client, cbq.message)
    else:
        return await cbq.answer("⚠️ Unknown Action")

    # If video list present, send first 3
    for vid in vids[:3]:
        caption = f"🎬 **{vid['title']}**\n⏱ {vid['duration']} | 🌐 {vid['site']}"
        await cbq.message.reply_photo(photo=vid["thumb"], caption=caption,
                                      reply_markup=video_buttons(vid["url"], fav=True))
    await cbq.answer()

# ----------------------- Auto Post System -----------------------
async def post_trending_now():
    vids = await fetch_videos("trending", "pornhub")
    for vid in vids[:1]:
        caption = f"🔥 **Viral Now**\n🎬 {vid['title']}\n⏱ {vid['duration']} | 🌐 {vid['site']}"
        await app.send_photo(CHANNEL_ID, vid["thumb"], caption=caption,
                             reply_markup=video_buttons(vid["url"]))

async def auto_poster():
    while True:
        await post_trending_now()
        await asyncio.sleep(2000)  # Every 1 hour

# ----------------------- Start Everything -----------------------
if __name__ == "__main__":
    threading.Thread(target=run_flask).start()
    loop = asyncio.get_event_loop()
    loop.create_task(auto_poster())
    app.run()
