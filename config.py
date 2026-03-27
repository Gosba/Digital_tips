import os
# ── Token du bot Digital Tips ──────────────────────────────────────────────────
# Obtenez un nouveau token auprès de @BotFather pour @DigitalTipsBot
BOT_TOKEN_DT = os.getenv("TELEGRAM_BOT_TOKEN_DT", "8649075315:AAHQPM56RFKUIXkiFT2xTqvb0S431F1euh0")
# Obtenez votre clé gratuite sur https://aistudio.google.com/
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyB_aFXWXmYI-wvWny_bqgOulYgtoP9_RG8")
# ── Sources d'actualités (Exemples de flux RSS) ───────────────────────────────
# Vous pouvez en ajouter d'autres ici
NEWS_SOURCES = [
    {"nom": "TechCrunch (IA)", "url": "https://techcrunch.com/category/artificial-intelligence/feed/"},
    {"nom": "The Verge (AI)", "url": "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml"},
    {"nom": "CNIL (Législation)", "url": "https://www.cnil.fr/fr/flux-rss.xml"}
]
