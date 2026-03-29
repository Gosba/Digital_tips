import logging, json, os, hashlib, feedparser, pytz
import google.generativeai as genai
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from config import BOT_TOKEN_DT, NEWS_SOURCES, GEMINI_API_KEY, YOUTUBE_CHANNELS, RESSOURCES_PEDAGO
from data_tips import TOOLS, LEGISTLATION, ROLES_TIPS
from datetime import time, datetime, timedelta

# --- LOGS ET INIT ---
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')
USER_FILE = "users_dt.json"

# --- UTILITAIRES ---
def is_relevant(title, summary=""):
    """Vérification intelligente de la pertinence de l'article via IA (Filtre Laser)."""
    p = f"Analyste EdTech : Répond par 'OUI' ou 'NON' uniquement. Cet article traite-t-il d'innovation pédagogique, d'IA en classe ou d'outils numériques pour l'éducation ? REJETTE ALORS : politique générale, faits divers, violence, sport. Titre : {title} / Résumé : {summary}"
    try:
        res = model.generate_content(p).text.strip().upper()
        logger.info(f"Filtre IA : {title[:30]}... | Pertinence : {res}")
        return "OUI" in res
    except Exception as e:
        logger.error(f"Erreur filtre IA : {e}")
        return True # Sécurité : laisse passer si l'IA sature

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
    user_name = update.effective_user.first_name
    logger.info(f"🔍 [NEWS] Requête lancée par {user_name}")
    await msg.reply_chat_action("typing")
    
    all_articles = []
    seen_links = set()
    now = datetime.now(pytz.UTC)
    threshold = now - timedelta(hours=48)

    for s in NEWS_SOURCES:
        logger.info(f"📡 [NEWS] Scraping source : {s['nom']}")
        try:
            feed = feedparser.parse(s["url"])
            count_source = 0
            for e in feed.entries:
                if e.link in seen_links: continue
                
                published = None
                if hasattr(e, "published_parsed") and e.published_parsed:
                    published = datetime(*e.published_parsed[:6], tzinfo=pytz.UTC)
                elif hasattr(e, "updated_parsed") and e.updated_parsed:
                    published = datetime(*e.updated_parsed[:6], tzinfo=pytz.UTC)
                
                if published and published < threshold: continue
                
                all_articles.append({
                    "title": e.title,
                    "link": e.link,
                    "summary": getattr(e, "summary", ""),
                    "source": s["nom"],
                    "date": published or now
                })
                seen_links.add(e.link)
                count_source += 1
            logger.info(f"✅ [NEWS] {count_source} articles frais trouvés sur {s['nom']}")
        except Exception as e:
            logger.error(f"❌ [NEWS] Erreur sur {s['nom']}: {e}")

    logger.info(f"📊 [NEWS] Total articles à analyser par l'IA : {len(all_articles)}")
    # Tri par date (plus récent en premier)
    all_articles.sort(key=lambda x: x["date"], reverse=True)

    # 5. Filtrage IA et Affichage (Limit 5)
    found = 0
    for art in all_articles:
        if is_relevant(art["title"], art["summary"]):
            d_str = art["date"].strftime("%d/%m %H:%M")
            t = f"📅 <b>{d_str}</b> | <b>{art['source']}</b>\n🔹 <a href='{art['link']}'>{art['title']}</a>"
            await msg.reply_html(t, disable_web_page_preview=True)
            found += 1
            if found >= 5: break

    if found == 0:
        await msg.reply_text("🕵️‍♂️ Aucune news fraîche (-48h) n'a passé le filtre IA aujourd'hui.")

async def pepites_handler(update, context):
    """Menu principal des Pépites Pédago."""
    is_cb = update.callback_query is not None
    msg = update.callback_query.message if is_cb else update.message
    kb = [
        [InlineKeyboardButton("👔 Conseils par métier", callback_data="pepites_roles")],
        [InlineKeyboardButton("🎥 Vidéos de Veille (YouTube)", callback_data="pepites_videos")],
        [InlineKeyboardButton("📘 Guides, Fiches & Outils IA", callback_data="pepites_resources")]
    ]
    t = "💼 <b>Pépites Pédago</b>\n\nAccédez aux meilleures ressources sélectionnées par IA :"
    if is_cb: await msg.edit_text(t, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(kb))
    else: await msg.reply_html(t, reply_markup=InlineKeyboardMarkup(kb))

async def resource_menu_handler(update, context):
    """Menu du centre de ressources IA (catégories statiques)."""
    q = update.callback_query; await q.answer()
    kb = [[InlineKeyboardButton(cat, callback_data=f"rescat_{cat}")] for cat in RESSOURCES_PEDAGO.keys()]
    kb.append([InlineKeyboardButton("⬅️ Retour", callback_data="pepites_back")])
    await q.edit_message_text("📘 <b>Centre de Ressources IA</b>\nSélectionnez une catégorie :", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(kb))

async def resource_category_callback(update, context):
    """Affiche les ressources d'une catégorie spécifique."""
    q = update.callback_query; await q.answer(); cat = q.data.replace("rescat_", "")
    items = RESSOURCES_PEDAGO.get(cat, [])
    m = f"✨ <b>{cat}</b>\n\n" + "\n".join([f"🔹 {i['titre']}\n🔗 <a href='{i['url']}'>Accéder</a>\n" for i in items])
    kb = [[InlineKeyboardButton("⬅️ Retour", callback_data="pepites_resources")]]
    await q.edit_message_text(m, parse_mode="HTML", disable_web_page_preview=True, reply_markup=InlineKeyboardMarkup(kb))

async def videos_handler(update, context):
    """Récupère les dernières vidéos YouTube (< 6 mois) validées par l'IA."""
    q = update.callback_query; await q.answer()
    await q.message.reply_chat_action("typing")
    
    all_videos = []
    now = datetime.now(pytz.UTC)
    threshold = now - timedelta(days=180) # ~ 6 mois

    logger.info("🎬 [VIDEOS] Lancement du scan YouTube")
    for s in YOUTUBE_CHANNELS:
        try:
            feed = feedparser.parse(s["url"])
            count_v = 0
            for e in feed.entries:
                pub = datetime(*e.published_parsed[:6], tzinfo=pytz.UTC)
                if pub < threshold: continue
                
                # Validation IA (plus large que les news)
                prompt = f"Analyse ce titre de vidéo YouTube : '{e.title}'. Traite-t-il de pédagogie, d'éducation, de numérique ou d'intelligence artificielle ? Répond par OUI ou NON."
                res = model.generate_content(prompt).text.strip().upper()
                
                if "OUI" in res:
                    all_videos.append({
                        "title": e.title,
                        "link": e.link,
                        "source": s["nom"],
                        "date": pub
                    })
                    count_v += 1
            logger.info(f"✅ [VIDEOS] {count_v} vidéos trouvées sur {s['nom']}")
        except Exception as ex:
            logger.error(f"❌ [VIDEOS] Erreur sur {s['nom']}: {ex}")

    all_videos.sort(key=lambda x: x["date"], reverse=True)
    
    if not all_videos:
        await q.message.reply_text("🕵️‍♂️ Aucune vidéo fraîche (insérée depuis < 6 mois) n'est disponible pour le moment.")
        return

    for v in all_videos[:5]:
        d_str = v["date"].strftime("%d/%m/%Y")
        t = f"📺 <b>{v['source']}</b> ({d_str})\n🔹 <a href='{v['link']}'>{v['title']}</a>"
        await q.message.reply_html(t)

    kb = [[InlineKeyboardButton("⬅️ Retour", callback_data="pepites_back")]]
    await q.message.reply_text("--- Fin des pépites vidéos ---", reply_markup=InlineKeyboardMarkup(kb))

# --- NAVIGATION FLUIDE (EDIT MESSAGE) ---
async def roles_handler(update, context):
    is_cb = update.callback_query is not None
    msg = update.callback_query.message if is_cb else update.message
    kb = [[InlineKeyboardButton(r, callback_data=f"role_{r}")] for r in ROLES_TIPS.keys()]
    kb.append([InlineKeyboardButton("⬅️ Retour", callback_data="pepites_back")]) # Ajout Retour
    t = "👔 <b>Conseils par métier :</b>"
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
    app.add_handler(MessageHandler(filters.Regex("^💼 Pépites"), pepites_handler))
    app.add_handler(MessageHandler(filters.Regex("^❓ À propos"), lambda u,c: u.message.reply_html("💡 <b>Digital Tips</b>\nContact: @digital_tips_coach")))
    
    app.add_handler(CallbackQueryHandler(category_callback, pattern="^cat_"))
    app.add_handler(CallbackQueryHandler(role_callback, pattern="^role_"))
    
    # Callback Pépites
    app.add_handler(CallbackQueryHandler(lambda u,c: roles_handler(u,c), pattern="^pepites_roles$"))
    app.add_handler(CallbackQueryHandler(videos_handler, pattern="^pepites_videos$"))
    app.add_handler(CallbackQueryHandler(resource_menu_handler, pattern="^pepites_resources$"))
    app.add_handler(CallbackQueryHandler(resource_category_callback, pattern="^rescat_"))
    app.add_handler(CallbackQueryHandler(pepites_handler, pattern="^pepites_back$"))
    
    # Correction Back Buttons Outils
    app.add_handler(CallbackQueryHandler(lambda u,c: tools_handler(u,c), pattern="^cat_back"))
    app.add_handler(CallbackQueryHandler(lambda u,c: roles_handler(u,c), pattern="^role_back"))
    
    print("🚀 --- BOT DIGITAL TIPS V2 (FILTRE IA LASER) PRÊT ! ---")
    logger.info("🤖 Bot démarré avec la logique de fraîcheur 48h.")
    app.run_polling()

if __name__ == "__main__": main()
