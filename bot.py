import logging
import feedparser
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from config import BOT_TOKEN_DT, NEWS_SOURCES
from data_tips import TOOLS, LEGISTLATION, ROLES_TIPS

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# --- States ---
MENU, TIPS, CATEGORY, ROLES = range(4)

# ── Handlers ───────────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Message de bienvenue avec menu principal à boutons."""
    texte = (
        "🚀 <b>Bienvenue dans Digital Tips !</b>\n\n"
        "Je suis votre assistant IA personnel. Que souhaitez-vous faire aujourd'hui ?"
    )
    boutons = [
        ["📰 Actualités IA", "⚖️ Législation"],
        ["🛠️ Outils Gratuits", "💼 Pépites par Métier"],
        ["❓ À propos"]
    ]
    await update.message.reply_html(
        texte,
        reply_markup=ReplyKeyboardMarkup(boutons, resize_keyboard=True)
    )

async def news_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Affiche les 5 dernières news des sources RSS."""
    msg = "📰 <b>Dernières actualités IA du jour :</b>\n\n"
    
    for source in NEWS_SOURCES:
        try:
            feed = feedparser.parse(source["url"])
            if feed.entries:
                msg += f"<b>Source: {source['nom']}</b>\n"
                for entry in feed.entries[:2]: # 2 par source
                    msg += f"🔹 <a href='{entry.link}'>{entry.title}</a>\n"
                msg += "\n"
        except:
            msg += f"❌ Impossible de lire {source['nom']}\n\n"
            
    await update.message.reply_html(msg, disable_web_page_preview=True)

async def legislation_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Affiche les infos législatives."""
    msg = "⚖️ <b>Infos & Protection des données :</b>\n\n"
    for k, v in LEGISTLATION.items():
        msg += f"<b>{k}</b> : {v}\n\n"
    await update.message.reply_html(msg)

async def roles_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menu interactif pour les conseils par métier."""
    boutons = []
    for role in ROLES_TIPS.keys():
        boutons.append([InlineKeyboardButton(role, callback_data=f"role_{role}")])
    
    await update.message.reply_html(
        "💼 <b>Conseils IA par métier :</b>\n\n"
        "Choisissez votre rôle pour voir comment booster votre activité avec l'IA.",
        reply_markup=InlineKeyboardMarkup(boutons)
    )

async def role_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    role_name = query.data.replace("role_", "")
    conseil = ROLES_TIPS.get(role_name, "Pas de conseil spécifique.")
    
    await query.edit_message_text(
        text=f"👔 <b>Conseil pour {role_name} :</b>\n\n{conseil}",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Retour", callback_data="back_roles")]])
    )

async def tools_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Menu pour les catégories d'outils."""
    boutons = []
    for cat in TOOLS.keys():
        boutons.append([InlineKeyboardButton(cat, callback_data=f"cat_{cat}")])
    
    await update.message.reply_html(
        "🛠️ <b>Le catalogue des outils IA gratuits :</b>\n\n"
        "Choisissez une catégorie pour découvrir des pépites.",
        reply_markup=InlineKeyboardMarkup(boutons)
    )

async def category_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cat_name = query.data.replace("cat_", "")
    outils = TOOLS.get(cat_name, [])
    
    msg = f"<b>Pépites IA - Catégorie {cat_name}</b>\n\n"
    for o in outils:
        msg += f"✨ <b>{o['nom']}</b>\n{o['desc']}\n🔗 <a href='{o['url']}'>Lien vers l'outil</a>\n\n"
        
    await query.edit_message_text(
        text=msg,
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Retour", callback_data="back_tools")]])
    )

async def apropos_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_html(
        "💡 <b>À propos de Digital Tips</b>\n\n"
        "Ce bot est piloté par l'IA pour accompagner les entrepreneurs du futur.\n\n"
        "Contact: @Mr_A_A (votre contact Telegram)."
    )

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Caused error: {context.error}")

# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    if BOT_TOKEN_DT == "VOTRE_NOUVEAU_TOKEN_ICI":
        print("❌ Token non configuré ! Arrêt.")
        return

    app = Application.builder().token(BOT_TOKEN_DT).build()

    # Handlers par boutons du clavier inférieur
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Regex("^📰 Actualités"), news_handler))
    app.add_handler(MessageHandler(filters.Regex("^⚖️ Législation"), legislation_handler))
    app.add_handler(MessageHandler(filters.Regex("^🛠️ Outils"), tools_handler))
    app.add_handler(MessageHandler(filters.Regex("^💼 Pépites"), roles_handler))
    app.add_handler(MessageHandler(filters.Regex("^❓ À propos"), apropos_handler))

    # Handlers dynamiques (Inline Buttons)
    app.add_handler(CallbackQueryHandler(category_callback, pattern="^cat_"))
    app.add_handler(CallbackQueryHandler(role_callback, pattern="^role_"))
    app.add_handler(CallbackQueryHandler(tools_handler, pattern="^back_tools"))
    app.add_handler(CallbackQueryHandler(roles_handler, pattern="^back_roles"))

    app.add_error_handler(error_handler)

    print("🚀 Bot Digital Tips démarré...")
    app.run_polling()

if __name__ == "__main__":
    main()
