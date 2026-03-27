import logging, json, os, hashlib, feedparser, pytz
import google.generativeai as genai
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from config import BOT_TOKEN_DT, NEWS_SOURCES, GEMINI_API_KEY
from data_tips import TOOLS, LEGISTLATION, ROLES_TIPS
from datetime import time

# --- LOGS ET INIT ---
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')
USER_FILE = "users_dt.json"

# --- UTILITAIRES ---
def is_relevant(title, summary=""):
    """Vérification intelligente de la pertinence de l'article via IA."""
    p = f"Répond par OUI ou NON uniquement. Cet article est-il utile pour un formateur ou enseignant utilisant l'IA ? Titre : {title} / Résumé : {summary}"
    try:
        res = model.generate_content(p).text.strip().upper()
        logger.info(f"Filtre IA : {title[:30]}... | Pertinence : {res}")
        return "OUI" in res
    except Exception as e:
        logger.error(f"Erreur filtre IA : {e}")
        return True # On laisse passer si l'IA bug par précaution !

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

# --- HANDLERS NAVIGATION ---
async def start(update, context):
    save_user(update.effective_user.id)
    txt = (
        "🎓 <b>Assistant Pédagogie & IA</b>\n\n"
        "Je sélectionne chaque jour les meilleures actualités EdTech validées par l'IA.\n"
        "Explorez mon catalogue d'outils et de conseils :"
    )
    kb = [["📰 Actualités Sélectionnées", "🛠️ Outils Gratuits"], ["💼 Pépites Pédago", "❓ À propos"]]
    await update.message.reply_html(txt, reply_markup=ReplyKeyboardMarkup(kb, resize_keyboard=True))

async def news_handler(update, context):
    msg = update.callback_query.message if update.callback_query else update.message
    await msg.reply_chat_action("typing")
    found = 0
    for s in NEWS_SOURCES:
        try:
            feed = feedparser.parse(s["url"])
            if feed.entries:
                for e in feed.entries[:3]:
                    if is_relevant(e.title, getattr(e, "summary", "")):
                        t = f"<b>{s['nom']}</b>\n🔹 <a href='{e.link}'>{e.title}</a>"
                        await msg.reply_html(t, disable_web_page_preview=True)
                        found += 1
                        if found >= 3: break
        except: pass
        if found >= 3: break
    if found == 0: await msg.reply_text("🕵️‍♂️ Aucune news pertinente trouvée ce jour.")

# --- NAVIGATION FLUIDE (EDIT MESSAGE) ---
async def roles_handler(update, context):
    is_cb = update.callback_query is not None
    msg = update.callback_query.message if is_cb else update.message
    kb = [[InlineKeyboardButton(r, callback_data=f"role_{r}")] for r in ROLES_TIPS.keys()]
    t = "💼 <b>Conseils par métier :</b>"
    if is_cb: await msg.edit_text(t, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(kb))
    else: await msg.reply_html(t, reply_markup=InlineKeyboardMarkup(kb))

async def tools_handler(update, context):
    is_cb = update.callback_query is not None
    msg = update.callback_query.message if is_cb else update.message
    kb = [[InlineKeyboardButton(cat, callback_data=f"cat_{cat}")] for cat in TOOLS.keys()]
    t = "🛠️ <b>Outils IA Gratuits :</b>"
    if is_cb: await msg.edit_text(t, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(kb))
    else: await msg.reply_html(t, reply_markup=InlineKeyboardMarkup(kb))

async def role_callback(update, context):
    q = update.callback_query; await q.answer(); rn = q.data.replace("role_", "")
    if rn == "back": return await roles_handler(update, context)
    kb = [[InlineKeyboardButton("⬅️ Retour", callback_data="role_back")]]
    await q.edit_message_text(f"👔 <b>{rn} :</b>\n\n{ROLES_TIPS.get(rn, '...')}", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(kb))

async def category_callback(update, context):
    q = update.callback_query; await q.answer(); cn = q.data.replace("cat_", "")
    if cn == "back": return await tools_handler(update, context)
    m = f"<b>{cn}</b>\n\n" + "\n".join([f"✨ <b>{o['nom']}</b>\n{o['desc']}\n🔗 <a href='{o['url']}'>Lien</a>\n" for o in TOOLS.get(cn, [])])
    kb = [[InlineKeyboardButton("⬅️ Retour", callback_data="cat_back")]]
    await q.edit_message_text(m, parse_mode="HTML", disable_web_page_preview=True, reply_markup=InlineKeyboardMarkup(kb))

# --- BRIEFING MATIN AUTOMATIQUE ---
async def morning_brief(context):
    ids = load_users()
    if not ids: return
    try:
        f = feedparser.parse(NEWS_SOURCES[0]["url"])
        for e in f.entries[:5]:
            if is_relevant(e.title):
                m = f"☕ <b>Flash AI Pédagogie !</b>\n\n🔹 {e.title}\n🔗 <a href='{e.link}'>Lien de l'article</a>"
                for cid in ids:
                    try: await context.bot.send_message(chat_id=cid, text=m, parse_mode="HTML", disable_web_page_preview=True)
                    except: pass
                break # On n'envoie qu'une news par brief
    except: pass

# --- MAIN ---
def main():
    app = Application.builder().token(BOT_TOKEN_DT).build()
    app.job_queue.run_daily(morning_brief, time(8, 0, tzinfo=pytz.timezone('Europe/Paris')))
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Regex("^📰 Actualités"), news_handler))
    app.add_handler(MessageHandler(filters.Regex("^🛠️ Outils"), tools_handler))
    app.add_handler(MessageHandler(filters.Regex("^💼 Pépites"), roles_handler))
    app.add_handler(MessageHandler(filters.Regex("^❓ À propos"), lambda u,c: u.message.reply_html("💡 <b>Digital Tips</b>\nContact: @digital_tips_coach")))
    
    app.add_handler(CallbackQueryHandler(category_callback, pattern="^cat_"))
    app.add_handler(CallbackQueryHandler(role_callback, pattern="^role_"))
    # Correction Back Buttons
    app.add_handler(CallbackQueryHandler(lambda u,c: tools_handler(u,c), pattern="^cat_back"))
    app.add_handler(CallbackQueryHandler(lambda u,c: roles_handler(u,c), pattern="^role_back"))
    
    print("🚀 Bot Digital Tips PRÊT !")
    app.run_polling()

if __name__ == "__main__": main()
