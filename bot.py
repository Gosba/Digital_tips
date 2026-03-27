import logging, json, os, hashlib, feedparser
import google.generativeai as genai
from newspaper import Article
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from config import BOT_TOKEN_DT, NEWS_SOURCES, GEMINI_API_KEY
from data_tips import TOOLS, LEGISTLATION, ROLES_TIPS

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')
USER_FILE = "users_dt.json"

def load_users():
    if not os.path.exists(USER_FILE): return []
    with open(USER_FILE, "r") as f: return json.load(f)

def save_user(cid):
    users = load_users()
    if cid not in users:
        users.append(cid)
        with open(USER_FILE, "w") as f: json.dump(users, f)

async def start(update, context):
    save_user(update.effective_user.id)
    texte = "🚀 <b>Bienvenue dans Digital Tips !</b>\n\nChaque matin à 8h00, je vous enverrai un Flash IA personnalisé.\nEn attendant, explorez mon menu !"
    boutons = [["📰 Actualités IA", "🛠️ Outils Gratuits"], ["💼 Pépites par Métier", "❓ À propos"]]
