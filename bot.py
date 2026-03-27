import logging, json, os, hashlib, feedparser
import google.generativeai as genai
from newspaper import Article
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from config import BOT_TOKEN_DT, NEWS_SOURCES, GEMINI_API_KEY
from data_tips import TOOLS, LEGISTLATION, ROLES_TIPS

# Initialisation
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')
USER_FILE = "users_dt.json"

# --- Gestion Utilisateurs ---
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

# --- Handlers de base ---
async def start(update, context):
    save_user(update.effective_user.id)
    texte = "🚀 <b>Bienvenue dans Digital Tips !</b>\n\nChaque matin à 8h00, je vous enverrai un Flash IA personnalisé.\nEn attendant, explorez mon menu !"
    boutons = [["📰 Actualités IA", "🛠️ Outils Gratuits"], ["💼 Pépites par Métier", "❓ À propos"]]
    await update.message.reply_html(texte, reply_markup=ReplyKeyboardMarkup(boutons, resize_keyboard=True))

async def apropos_handler(update, context):
    await update.message.reply_html("💡 <b>Digital Tips</b>\n\nIA coach pour entrepreneurs.\nContact: @Mr_A_A")
# --- Logique des News et Résumés ---
async def news_handler(update, context):
    msg_source = update.callback_query.message if update.callback_query else update.message
    await msg_source.reply_chat_action("typing")
    found = False
    for s in NEWS_SOURCES:
        try:
            feed = feedparser.parse(s["url"])
            if feed.entries:
                for entry in feed.entries[:2]:
                    sid = hashlib.md5(entry.link.encode()).hexdigest()[:8]
                    context.bot_data[sid] = entry.link
                    txt = f"<b>{s['nom']}</b>\n🔹 <a href='{entry.link}'>{entry.title}</a>"
                    kb = InlineKeyboardMarkup([[InlineKeyboardButton("📝 Résumer (IA)", callback_data=f"sum_{sid}")]])
                    await msg_source.reply_html(txt, reply_markup=kb, disable_web_page_preview=True)
                    found = True
        except: pass
    if not found: await msg_source.reply_text("Rien pour le moment.")

async def summary_callback(update, context):
    query = update.callback_query
    await query.answer()
    sid = query.data.replace("sum_", "")
    url = context.bot_data.get(sid)
    if not url: return await query.edit_message_text("❌ Lien expiré.")
    await query.edit_message_text("⏳ <i>Génération du résumé IA...</i>", parse_mode="HTML")
    try:
        art = Article(url); art.download(); art.parse()
        prompt = f"Résume en français cet article en 3 points clés pour un entrepreneur : \n\n{art.text[:4000]}"
        res = model.generate_content(prompt).text
        await query.edit_message_text(f"📝 <b>Résumé :</b>\n\n{res}\n\n🔗 <a href='{url}'>Lire plus</a>", parse_mode="HTML",
                                      disable_web_page_preview=True, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Retour", callback_data="back_news")]]))
    except: await query.edit_message_text("❌ Erreur de résumé (article protégé ou trop long).")

async def morning_brief(context):
    ids = load_users()
    if not ids: return
    try:
        feed = feedparser.parse(NEWS_SOURCES[0]["url"])
        if feed.entries:
            entry = feed.entries[0]
            art = Article(entry.link); art.download(); art.parse()
            res = model.generate_content(f"Flash matinal : résume cet article en 2 phrases pour un manager : \n\n{art.text[:3000]}").text
            msg = f"☕ <b>Flash AI du Matinal !</b>\n\n🔹 {entry.title}\n\n📝 {res}\n\n🔗 <a href='{entry.link}'>Détails</a>"
            for cid in ids:
                try: await context.bot.send_message(chat_id=cid, text=msg, parse_mode="HTML", disable_web_page_preview=True)
                except: pass
    except: pass

# --- Menus Outils et Roles ---
async def roles_handler(update, context):
    kb = [[InlineKeyboardButton(r, callback_data=f"role_{r}")] for r in ROLES_TIPS.keys()]
    await update.message.reply_html("💼 <b>Conseils IA :</b>", reply_markup=InlineKeyboardMarkup(kb))

async def role_callback(update, context):
    q = update.callback_query; await q.answer()
    rn = q.data.replace("role_", ""); cs = ROLES_TIPS.get(rn, "...")
    if rn == "back": return await roles_handler(q.message, context)
    await q.edit_message_text(f"👔 <b>{rn} :</b>\n\n{cs}", parse_mode="HTML",
                              reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Retour", callback_data="role_back")]]))

async def tools_handler(update, context):
    kb = [[InlineKeyboardButton(c, callback_data=f"cat_{c}")] for c in TOOLS.keys()]
    await update.message.reply_html("🛠️ <b>Outils IA :</b>", reply_markup=InlineKeyboardMarkup(kb))

async def category_callback(update, context):
    q = update.callback_query; await q.answer()
    cn = q.data.replace("cat_", ""); ots = TOOLS.get(cn, [])
    if cn == "back": return await tools_handler(q.message, context)
    m = f"<b>{cn}</b>\n\n" + "\n".join([f"✨ <b>{o['nom']}</b>\n{o['desc']}\n🔗 <a href='{o['url']}'>Lien</a>\n" for o in ots])
    await q.edit_message_text(m, parse_mode="HTML", disable_web_page_preview=True,
                              reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Retour", callback_data="cat_back")]]))

# --- Lancement ---
def main():
    app = Application.builder().token(BOT_TOKEN_DT).build()
    from datetime import time
    import pytz
    tz = pytz.timezone('Europe/Paris')
    app.job_queue.run_daily(morning_brief, time(8, 0, tzinfo=tz))

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Regex("^📰 Actualités"), news_handler))
    app.add_handler(MessageHandler(filters.Regex("^🛠️ Outils"), tools_handler))
    app.add_handler(MessageHandler(filters.Regex("^💼 Pépites"), roles_handler))
    app.add_handler(MessageHandler(filters.Regex("^❓ À propos"), apropos_handler))
    app.add_handler(CallbackQueryHandler(summary_callback, pattern="^sum_"))
    app.add_handler(CallbackQueryHandler(news_handler, pattern="^back_news"))
    app.add_handler(CallbackQueryHandler(category_callback, pattern="^cat_"))
    app.add_handler(CallbackQueryHandler(role_callback, pattern="^role_"))
    app.add_handler(CallbackQueryHandler(lambda u,c: tools_handler(u.callback_query.message,c), pattern="^cat_back"))
    app.add_handler(CallbackQueryHandler(lambda u,c: roles_handler(u.callback_query.message,c), pattern="^role_back"))

    print("🚀 Digital Tips IA prêt !")
    app.run_polling()

if __name__ == "__main__": main()
