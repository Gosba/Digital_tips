import os

# ── Token du bot Digital Tips ──────────────────────────────────────────────────
# Obtenez un nouveau token auprès de @BotFather pour @DigitalTipsBot
BOT_TOKEN_DT = os.getenv("TELEGRAM_BOT_TOKEN_DT", "8649075315:AAHQPM56RFKUIXkiFT2xTqvb0S431F1euh0")

# Obtenez votre clé gratuite sur https://aistudio.google.com/
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyB_aFXWXmYI-wvWny_bqgOulYgtoP9_RG8")

# ── Sources d'actualités (Flux RSS FR Spécialisés Pédagogie) ────────────────
NEWS_SOURCES = [
    {"nom": "IA Pulse (Substack)", "url": "https://iapulse.substack.com/feed"},
    {"nom": "Thot Cursus (Pédagogie)", "url": "https://cursus.edu/fr/rss"},
    {"nom": "Apprendre Demain (IA & Edu)", "url": "https://apprendredemain.fr/feed/"},
    {"nom": "Café Pédagogique", "url": "https://www.cafepedagogique.net/feed/"},
    {"nom": "EdTech Actu", "url": "https://edtechactu.com/feed/"},
    {"nom": "CNIL Éducation", "url": "https://www.cnil.fr/fr/flux-rss.xml"}
]

# ── Sources Vidéos (Filtre 6 mois par défaut) ───────────────────────────────
YOUTUBE_CHANNELS = [
    {"nom": "ÊtreProf", "url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCFYx4sp35cCIC9Yi_ft_hwA"},
    {"nom": "Académie Aix-Marseille", "url": "https://www.youtube.com/feeds/videos.xml?channel_id=UC2G2rJCaqo1wbb_84r0UiXQ"},
    {"nom": "Philippe Meirieu", "url": "https://www.youtube.com/feeds/videos.xml?channel_id=UCopiwrmPgBWEsDRZ6JiYLqw"}
]

# ── Sélection Guides & Tutoriels IA (Recherche Spécifique) ──────────────────
GUIDE_VIDEOS = [
    {"titre": "PROFS : 3 Prompts qui peuvent VRAIMENT faire progresser vos élèves !", "url": "https://www.youtube.com/watch?v=r3-jU5Fnzm0"},
    {"titre": "IA à l’école : Guide pratique pour enseignants", "url": "https://www.youtube.com/watch?v=Cbr0Iw8iEm0"},
    {"titre": "Machine Learning et IA : Guide Simple pour Formateurs", "url": "https://www.youtube.com/watch?v=lwId4AH1mUA"},
    {"titre": "Dinobot : Tutoriel Complet pour Enseignants", "url": "https://www.youtube.com/watch?v=Rf-2xcxS0g8"},
    {"titre": "Comment mieux utiliser l’IA quand on est enseignant ?", "url": "https://www.youtube.com/watch?v=yh3CiGEay_Y"},
    {"titre": "Maîtriser l’IA pour Votre Classe : Le guide pratique du prompting", "url": "https://www.youtube.com/watch?v=YxdhDd8auos"},
    {"titre": "Canva Éducation : le guide complet pour enseignants", "url": "https://www.youtube.com/watch?v=gAJaYs6QnJc"}
]

