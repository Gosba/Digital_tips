import logging, json, os, hashlib, feedparser, pytz
import google.generativeai as genai
from newspaper import Article, Config
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from config import BOT_TOKEN_DT, NEWS_SOURCES, GEMINI_API_KEY
from data_tips import TOOLS, LEGISTLATION, ROLES_TIPS
from datetime import time

# --- INIT ---
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')
USER_FILE = "users_dt.json"

# Config Newspaper (Robuste)
conf = Config()
conf.browser_user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
conf.request_timeout = 15

# --- UTILITAIRES ---
def load_users():
    if not os.path.exists(USER_FILE): return []
    try:
        with open(USER_FILE, "r") as f: return json.load(f)
    except: return []

def save_user(cid):
    users = load_users()
    if cid not in users:
        users.append(cid)
        with open(USER_FILE, "w") as f: json.dump(users, f)

# --- HANDLERS ---
async def start(u, c):
    save_user(u.effective_user.id)
    txt = "🚀 <b>Digital Tips IA</b>\n\nChaque matin à 08h00, recevez un Flash IA.\nExplorez le menu :"
    kb = [["📰 Actualités IA", "🛠️ Outils Gratuits"], ["💼 Pépites par Métier", "❓ À propos"]]
    await u.message.reply_html(txt, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

async def news_handler(u, c):
    msg = u.callback_query.message if u.callback_query else u.message
    await msg.reply_chat_action("typing")
    found = False
    for s in NEWS_SOURCES:
        try:
            feed = feedparser.parse(s["url"])
            if feed.entries:
                for e in feed.entries[:2]:
                    sid = hashlib.md5(e.link.encode()).hexdigest()[:8]
                    c.bot_data[sid] = e.link
                    txt = f"<b>{s['nom']}</b>\n🔹 <a href='{e.link}'>{e.title}</a>"
                    kb = InlineKeyboardMarkup([[InlineKeyboardButton("📝 Résumer (IA)", callback_data=f"sum_{sid}")]])
                    await msg.reply_html(txt, reply_markup=kb, disable_web_page_preview=True)
                    found = True
        except: pass
    if not found: await msg.reply_text("Rien trouvé.")

async def summary_callback(u, c):
    q = u.callback_query; await q.answer(); sid = q.data.replace("sum_", ""); url = c.bot_data.get(sid)
    if not url: return await q.edit_message_text("❌ Lien expiré.")
    await q.edit_message_text("⏳ <i>Lecture de l'article avec l'IA...</i>", parse_mode="HTML")
    try:
        art = Article(url, config=conf); art.download(); art.parse()
        content = art.text.strip() or art.meta_description or "Texte protégé"
        p = f"Résume en français cet article en 3 points pour un entrepreneur : \n\n{content[:5000]}"
        res = model.generate_content(p).text
        await q.edit_message_text(f"📝 <b>Résumé :</b>\n\n{res}\n\n🔗 <a href='{url}'>Article complet</a>", parse_mode="HTML",
                                  disable_web_page_preview=True, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Retour", callback_data="back_news")]]))
    except: await q.edit_message_text("❌ Désolé, l'article est inaccessible (protection anti-robot).")

async def morning_brief(c):
    ids = load_users()
    if not ids: return
    try:
        f = feedparser.parse(NEWS_SOURCES[0]["url"])
        if f.entries:
            e = f.entries[0]; art = Article(e.link, config=conf); art.download(); art.parse()
            ct = art.text.strip() or art.meta_description or "Flash du matin."
            res = model.generate_content(f"Flash matinal (2 phrases) en français : \n\n{ct[:3000]}").text
            msg = f"☕ <b>Flash AI du Matinal !</b>\n\n🔹 {e.title}\n\n📝 {res}\n\n🔗 <a href='{e.link}'>LIEN</a>"
            for cid in ids:
                try: await c.bot.send_message(chat_id=cid, text=msg, parse_mode="HTML", disable_web_page_preview=True)
                except: pass
    except: pass

async def roles_handler(u, c):
    kb = [[InlineKeyboardButton(r, callback_data=f"role_{r}")] for r in ROLES_TIPS.keys()]
    await u.message.reply_html("💼 <b>Conseils par métier :</b>", reply_markup=InlineKeyboardMarkup(kb))

async def role_callback(u, c):
    q = u.callback_query; await q.answer(); rn = q.data.replace("role_", "")
    if rn == "back": return await roles_handler(q, c)
    await q.edit_message_text(f"👔 <b>{rn} :</b>\n\n{ROLES_TIPS.get(rn, '...')}", parse_mode="HTML",
                              reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Retour", callback_data="role_back")]]))

async def tools_handler(u, c):
    kb = [[InlineKeyboardButton(cat, callback_data=f"cat_{cat}")] for cat in TOOLS.keys()]
    await u.message.reply_html("🛠️ <b>Outils IA Gratuits :</b>", reply_markup=InlineKeyboardMarkup(kb))

async def category_callback(u, c):
    q = u.callback_query; await q.answer(); cn = q.data.replace("cat_", "")
    if cn == "back": return await tools_handler(q, c)
    m = f"<b>{cn}</b>\n\n" + "\n".join([f"✨ <b>{o['nom']}</b>\n{o['desc']}\n🔗 <a href='{o['url']}'>Lien</a>\n" for o in TOOLS.get(cn, [])])
    await q.edit_message_text(m, parse_mode="HTML", disable_web_page_preview=True,
                              reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Retour", callback_data="cat_back")]]))

# --- MAIN ---
def main():
    app = Application.builder().token(BOT_TOKEN_DT).build()
    app.job_queue.run_daily(morning_brief, time(8, 0, tzinfo=pytz.timezone('Europe/Paris')))
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Regex("^📰 Actualités"), news_handler))
    app.add_handler(MessageHandler(filters.Regex("^🛠️ Outils"), tools_handler))
    app.add_handler(MessageHandler(filters.Regex("^💼 Pépites"), roles_handler))
    app.add_handler(MessageHandler(filters.Regex("^❓ À propos"), lambda u,c: u.message.reply_html("💡 <b>Digital Tips</b>\nCoach IA.\nContact: @digital_tips_coach")))
    
    app.add_handler(CallbackQueryHandler(summary_callback, pattern="^sum_"))
    app.add_handler(CallbackQueryHandler(news_handler, pattern="^back_news"))
    app.add_handler(CallbackQueryHandler(category_callback, pattern="^cat_"))
    app.add_handler(CallbackQueryHandler(role_callback, pattern="^role_"))
    app.add_handler(CallbackQueryHandler(lambda u,c: tools_handler(u.callback_query.message,c), pattern="^cat_back"))
    app.add_handler(CallbackQueryHandler(lambda u,c: roles_handler(u.callback_query.message,c), pattern="^role_back"))
    
    print("🚀 Bot Digital Tips PRÊT !")
    app.run_polling()

if __name__ == "__main__": main()
