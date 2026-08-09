import os
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────
# OpenAI
# ─────────────────────────────────────────
OPENAI_API_KEY   = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL     = "gpt-4o"
OPENAI_FAST_MODEL = "gpt-4o-mini"   # for real-time roasts (cheaper + faster)
JWT_SECRET_KEY   = os.getenv("JWT_SECRET_KEY", "dev-only-change-me")
JWT_ALGORITHM    = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./mimo.db")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")

# ─────────────────────────────────────────
SCREEN_POLL_INTERVAL  = 2     # seconds
SESSION_GAP_THRESHOLD = 10    # seconds of same app before stitching into one session

# ─────────────────────────────────────────
# Roasting
# ─────────────────────────────────────────
DISTRACTION_ROAST_AFTER_MINUTES = 5   # roast fires after 5 min on a distracting app
ABSENCE_ROAST_AFTER_MINUTES     = 15  # roast fires after 15 min absent from desk
MIN_ROAST_INTERVAL_SECONDS      = 300 # don't roast more than once per 5 min
LIVE_ROAST_USE_AI               = True # set False to use only pre-written roasts (faster demo)

# ─────────────────────────────────────────
# Scheduling
# ─────────────────────────────────────────
EOD_REPORT_HOUR   = 22   # 10 PM
REMINDER_CHECK_INTERVAL_MINUTES = 15

# ─────────────────────────────────────────
# App categorization
# These are keyword matches against app_name.lower()
# ─────────────────────────────────────────
PRODUCTIVE_KEYWORDS = {
    # Code editors & IDEs
    "code", "vscode", "pycharm", "intellij", "webstorm", "clion", "rider",
    "sublime_text", "atom", "vim", "nvim", "neovim", "emacs", "nano",
    # Terminals
    "terminal", "cmd", "powershell", "bash", "zsh", "wt",  # windows terminal
    "iterm", "konsole", "gnome-terminal", "alacritty", "kitty",
    # Browsers (neutral-ish, categorized by tab title if possible)
    "chrome", "chromium", "firefox", "edge", "brave", "safari", "opera",
    # Document / notes
    "word", "winword", "libreoffice", "notion", "obsidian", "typora",
    "acrobat", "foxit", "okular", "evince", "zathura",
    # Study tools
    "anki", "quizlet",
    # Data / science
    "jupyter", "rstudio", "spyder", "matlab",
    # Design (can be productive)
    "figma", "sketch", "xd",
    # Calls (study sessions)
    "zoom", "teams", "meet", "webex",
    # Dev tools
    "postman", "insomnia", "dbeaver", "pgadmin", "mongodb compass",
    "docker", "virtualbox", "vmware",
    # Version control
    "github desktop", "sourcetree", "gitkraken",
}

DISTRACTING_KEYWORDS = {
    # Social media
    "instagram", "facebook", "twitter", "tiktok", "snapchat",
    "pinterest", "tumblr", "linkedin",
    # Video
    "netflix", "primevideo", "prime video", "hotstar", "jiocinema",
    "youtube",   # youtube music is okay, but youtube in general = distracting flag
    "vlc", "mpv",  # watching movies locally
    # Games
    "steam", "epicgameslauncher", "battle.net", "origin", "ubisoft connect",
    "valorant", "csgo", "minecraft", "roblox", "fortnite", "apex",
    "genshin", "freefire",
    # Shopping
    "amazon", "flipkart", "myntra", "meesho", "nykaa",
    # Other
    "reddit",
    "meme",
}

YOUTUBE_EDUCATIONAL_KEYWORDS = {
    "lecture", "tutorial", "course", "lesson", "class", "explained",
    "study", "exam", "revision", "homework", "assignment", "practice",
    "calculus", "algebra", "statistics", "physics", "chemistry", "biology",
    "python", "java", "kotlin", "sql", "algorithm", "dsa", "machine learning",
}

YOUTUBE_DISTRACTING_KEYWORDS = {
    "shorts", "vlog", "prank", "reaction", "trailer", "music video",
    "gaming", "gameplay", "stream", "lo-fi", "lofi", "comedy",
    "meme", "challenge", "highlights",
}

NEUTRAL_KEYWORDS = {
    "explorer", "finder", "nautilus", "thunar",   # file managers
    "settings", "controlpanel", "preferences",
    "calculator",
    "calendar",
    "clock",
    "spotify",   # music while studying - neutral not distracting
    "photos",
    "slack",     # neutral - could be productive
    "discord",   # neutral - could be distracting, tracked separately
    "whatsapp",
    "telegram",
}

# ─────────────────────────────────────────
# Daily accountability questions
# ─────────────────────────────────────────
ACCOUNTABILITY_QUESTIONS = [
    "What assignments or deadlines do you have today?",
    "What subjects are you planning to study right now?",
    "What is your single biggest priority for today?",
    "Anything you've been putting off that needs to happen today?",
    "What time are you planning to be done studying?",
]

# ─────────────────────────────────────────
# Pre-written roasts (used when AI is slow or LIVE_ROAST_USE_AI=False)
# ─────────────────────────────────────────
PREWRITTEN_ROASTS = {
    "instagram": [
        "You opened Instagram again. Revolutionary choice for someone with 3 assignments due this week.",
        "Scrolling Instagram won't make your GPA scroll up.",
        "Wow, Instagram. Did the algorithm finally teach you thermodynamics? No? Then why are you there?",
        "You've spent more time on Instagram today than you have on any single subject. Let that sink in.",
    ],
    "youtube": [
        "YouTube again. I assume it's a 6-hour lecture on your exact exam syllabus? No? Interesting.",
        "That YouTube video is not going to watch your assignments back.",
        "YouTube counts as studying only if the title starts with your subject name. Does it? I didn't think so.",
    ],
    "reddit": [
        "Reddit will still be there after your assignment is submitted. Your grade won't improve on its own though.",
        "You opened Reddit. The upvotes on your post won't be as satisfying as passing this semester.",
    ],
    "game": [
        "Gaming during study time. Bold strategy. Let's see how it pays off during exams.",
        "The only game you should be playing right now is 'how fast can I finish this assignment'.",
    ],
    "absent": [
        "You've been away from your desk for a while. Unless you're studying with your eyes closed somewhere else, come back.",
        "Desk empty for over 15 minutes. Either you found a more productive place to study, or you didn't. Be honest.",
        "Your chair misses you. More importantly, your assignments miss you.",
    ],
    "generic": [
        "You got distracted again. You have assignments. They exist. They need to be done. By you.",
        "Current trajectory: maximum distraction, minimum output. Consider adjusting.",
        "You've been on something unproductive. I'm not angry. I'm just disappointed. Actually I'm both.",
    ],
}

FOCUS_SCORE_WEIGHTS = {
    "productive_time": 0.5,
    "presence_ratio":  0.3,
    "distraction_penalty": 0.2,
}
