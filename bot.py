import logging, json, os, hashlib, feedparser, google.generativeai as genai, pytz
from newspaper import Article
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from config import BOT_TOKEN_DT, NEWS_SOURCES, GEMINI_API_KEY
from data_tips import TOOLS, LEGISTLATION, ROLES_TIPS
from datetime import time

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')
USER_FILE = "users_dt.json"

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

async def start(u, c):
    save_user(u.effective_user.id)
    txt = "🎓 <b>Digital Tips - Édition Pédagogie</b>\n\nVotre veille sur l'IA pour les formateurs et enseignants.\nExplorez le catalogue :"
    kb = [["📰 Actualités IA", "🛠️ Outils Gratuits"], ["💼 Pépites par Métier", "❓ À propos"]]
    await u.message.reply_html(txt, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

async def news_handler(u, c):
    msg = u.callback_query.message if u.callback_query else u.message
    await msg.reply_chat_action("typing")
    found = False
    for s in NEWS_SOURCES:
        try:
            feed = feedparser.parse(s["url"])
            for e in feed.entries[:2]:
                sid = hashlib.md5(e.link.encode()).hexdigest()[:8]
                c.bot_data[sid] = e.link
                txt = f"<b>{s['nom']}</b>\n🔹 <a href='{e.link}'>{e.title}</a>"
                kb = InlineKeyboardMarkup([[InlineKeyboardButton("📝 Résumer (IA)", callback_data=f"sum_{sid}")]])
                await msg.reply_html(txt, reply_markup=kb, disable_web_page_preview=True)
                found = True
        except: pass
    if not found: await msg.reply_text("Rien pour le moment.")

async def summary_callback(u, c):
    q = u.callback_query; await q.answer(); sid = q.data.replace("sum_", ""); url = c.bot_data.get(sid)
    if not url: return await q.edit_message_text("❌ Lien expiré.")
    await q.edit_message_text("⏳ <i>Génération du résumé IA...</i>", parse_mode="HTML")
    try:
        art = Article(url); art.download(); art.parse()
        res = model.generate_content(f"Résume en français cet article en 3 points pour un entrepreneur: \n\n{art.text[:4000]}").text
        await q.edit_message_text(f"📝 <b>Résumé :</b>\n\n{res}\n\n🔗 <a href='{url}'>Lire plus</a>", parse_mode="HTML",
                                  disable_web_page_preview=True, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Retour", callback_data="back_news")]]))
    except: await q.edit_message_text("❌ Erreur de résumé.")

async def morning_brief(c):
    ids = load_users()
    if not ids: return
    try:
        f = feedparser.parse(NEWS_SOURCES[0]["url"])
        if f.entries:
            e = f.entries[0]; art = Article(e.link); art.download(); art.parse()
            res = model.generate_content(f"Flash matinal : résume cet article en 2 phrases pour un manager : \n\n{art.text[:3000]}").text
            msg = f"☕ <b>Flash AI du Matinal !</b>\n\n🔹 {e.title}\n\n📝 {res}\n\n🔗 <a href='{e.link}'>Détails</a>"
            for cid in ids:
                try: await c.bot.send_message(chat_id=cid, text=msg, parse_mode="HTML", disable_web_page_preview=True)
                except: pass
    except: pass

async def roles_handler(u, c):
    kb = [[InlineKeyboardButton(r, callback_data=f"role_{r}")] for r in ROLES_TIPS.keys()]
    await u.message.reply_html("💼 <b>Conseils IA :</b>", reply_markup=InlineKeyboardMarkup(kb))

async def role_callback(u, c):
    q = u.callback_query; await q.answer(); rn = q.data.replace("role_", ""); cs = ROLES_TIPS.get(rn, "...")
    if rn == "back": return await roles_handler(q, c)
    await q.edit_message_text(f"👔 <b>{rn} :</b>\n\n{cs}", parse_mode="HTML",
                              reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Retour", callback_data="role_back")]]))

async def tools_handler(u, c):
    kb = [[InlineKeyboardButton(cat, callback_data=f"cat_{cat}")] for cat in TOOLS.keys()]
    await u.message.reply_html("🛠️ <b>Outils IA :</b>", reply_markup=InlineKeyboardMarkup(kb))

async def category_callback(u, c):
    q = u.callback_query; await q.answer(); cn = q.data.replace("cat_", ""); ots = TOOLS.get(cn, [])
    if cn == "back": return await tools_handler(q, c)
    m = f"<b>{cn}</b>\n\n" + "\n".join([f"✨ <b>{o['nom']}</b>\n{o['desc']}\n🔗 <a href='{o['url']}'>Lien</a>\n" for o in ots])
    await q.edit_message_text(m, parse_mode="HTML", disable_web_page_preview=True,
                              reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Retour", callback_data="cat_back")]]))

def main():
    app = Application.builder().token(BOT_TOKEN_DT).build()
    app.job_queue.run_daily(morning_brief, time(8, 0, tzinfo=pytz.timezone('Europe/Paris')))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Regex("^📰 Actualités"), news_handler))
    app.add_handler(MessageHandler(filters.Regex("^🛠️ Outils"), tools_handler))
    app.add_handler(MessageHandler(filters.Regex("^💼 Pépites"), roles_handler))
    app.add_handler(MessageHandler(filters.Regex("^❓ À propos"), lambda u,c: u.message.reply_html("💡 <b>Digital Tips</b>\n\nContact: @digital_tips_coach")))
    app.add_handler(CallbackQueryHandler(summary_callback, pattern="^sum_"))
    app.add_handler(CallbackQueryHandler(news_handler, pattern="^back_news"))
    app.add_handler(CallbackQueryHandler(category_callback, pattern="^cat_"))
    app.add_handler(CallbackQueryHandler(role_callback, pattern="^role_"))
    app.add_handler(CallbackQueryHandler(lambda u,c: tools_handler(u.callback_query.message,c), pattern="^cat_back"))
    app.add_handler(CallbackQueryHandler(lambda u,c: roles_handler(u.callback_query.message,c), pattern="^role_back"))
    print("🚀 Digital Tips IA prêt !")
    app.run_polling()

if __name__ == "__main__": main()
