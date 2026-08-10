import re
import sys
from os import getenv
from dotenv import load_dotenv
from pyrogram import filters

load_dotenv()

# --- HELPER FUNCTIONS FOR SAFE ENV LOADING ---
def get_int(env_var, default=None):
    val = getenv(env_var, default)
    if val is None or val == "":
        return default
    try:
        return int(val)
    except ValueError:
        sys.exit(f"[CRITICAL ERROR] - {env_var} must be an integer, but got: '{val}'")

def get_bool(env_var, default=False):
    val = getenv(env_var)
    if val is None or val == "":
        return default
    return str(val).lower() in ["true", "1", "t", "y", "yes"]

# ==========================================
# 1. CORE BOT CREDENTIALS
# ==========================================
API_ID = get_int("API_ID")
API_HASH = getenv("API_HASH")
BOT_TOKEN = getenv("BOT_TOKEN")
MONGO_DB_URI = getenv("MONGO_DB_URI")

# System Checks for critical variables
if not all([API_ID, API_HASH, BOT_TOKEN, MONGO_DB_URI]):
    sys.exit("[CRITICAL ERROR] - API_ID, API_HASH, BOT_TOKEN or MONGO_DB_URI is missing from your environment variables!")

# ==========================================
# 2. OWNER & LOGGING
# ==========================================
OWNER_ID = get_int("OWNER_ID")
LOGGER_ID = get_int("LOGGER_ID")

if not OWNER_ID or not LOGGER_ID:
    sys.exit("[CRITICAL ERROR] - OWNER_ID and LOGGER_ID must be set in environment variables.")

# ==========================================
# 3. MUSIC & API SETTINGS
# ==========================================
YTPROXY_URL = getenv("YTPROXY_URL", "https://tgapi.xbitcode.com") # xBit Music Endpoint
YT_API_KEY = getenv("YT_API_KEY", None)

SPOTIFY_CLIENT_ID = getenv("SPOTIFY_CLIENT_ID", "1c21247d714244ddbb09925dac565aed")
SPOTIFY_CLIENT_SECRET = getenv("SPOTIFY_CLIENT_SECRET", "709e1a2969664491b58200860623ef19")

# ==========================================
# 4. BOT LIMITS & DURATIONS
# ==========================================
DURATION_LIMIT_MIN = get_int("DURATION_LIMIT", 300)
PLAYLIST_FETCH_LIMIT = get_int("PLAYLIST_FETCH_LIMIT", 25)

TG_AUDIO_FILESIZE_LIMIT = get_int("TG_AUDIO_FILESIZE_LIMIT", 204857600)  # 200MB
TG_VIDEO_FILESIZE_LIMIT = get_int("TG_VIDEO_FILESIZE_LIMIT", 2073741824) # 2GB

CACHE_DURATION = get_int("CACHE_DURATION", 86400) # 24 Hours
CACHE_SLEEP = get_int("CACHE_SLEEP", 3600)        # 1 Hour

# ==========================================
# 5. ASSISTANT SETTINGS
# ==========================================
AUTO_LEAVING_ASSISTANT = get_bool("AUTO_LEAVING_ASSISTANT", True)
ASSISTANT_LEAVE_TIME = get_int("ASSISTANT_LEAVE_TIME", 5400)
PRIVATE_BOT_MODE_MEM = get_int("PRIVATE_BOT_MODE_MEM", 1)

# Pyrogram v2 Sessions
STRING1 = getenv("STRING_SESSION", None)
STRING2 = getenv("STRING_SESSION2", None)
STRING3 = getenv("STRING_SESSION3", None)
STRING4 = getenv("STRING_SESSION4", None)
STRING5 = getenv("STRING_SESSION5", None)

# ==========================================
# 6. HEROKU & REPO DEPLOYMENT
# ==========================================
HEROKU_APP_NAME = getenv("HEROKU_APP_NAME")
HEROKU_API_KEY = getenv("HEROKU_API_KEY")
UPSTREAM_REPO = getenv("UPSTREAM_REPO", "https://github.com/xbitcode/music.git")
UPSTREAM_BRANCH = getenv("UPSTREAM_BRANCH", "main")
GIT_TOKEN = getenv("GIT_TOKEN", None)

SUPPORT_CHANNEL = getenv("SUPPORT_CHANNEL", "https://t.me/amigr8")
SUPPORT_CHAT = getenv("SUPPORT_CHAT", "https://t.me/randomlychats")

if SUPPORT_CHANNEL and not re.match("(?:http|https)://", SUPPORT_CHANNEL):
    sys.exit("[ERROR] - Your SUPPORT_CHANNEL url is wrong. Please ensure that it starts with https://")
if SUPPORT_CHAT and not re.match("(?:http|https)://", SUPPORT_CHAT):
    sys.exit("[ERROR] - Your SUPPORT_CHAT url is wrong. Please ensure that it starts with https://")

# ==========================================
# 7. BOT MEMORY CACHE & LISTS
# ==========================================
BANNED_USERS = filters.user()
adminlist = {}
lyrical = {}
votemode = {}
autoclean = []
confirmer = {}
file_cache: dict[str, float] = {}

# ==========================================
# 8. THEME & IMAGES
# ==========================================
START_IMG_URL = [
    "https://te.legra.ph/file/5fd13f2cc0d03bce9f7f2.jpg",
    "https://te.legra.ph/file/c15d01b3e6b40ea141dc9.jpg"
]
PING_IMG_URL = getenv("PING_IMG_URL", "https://telegra.ph/file/87f680aead03443f291b0.jpg")
PLAYLIST_IMG_URL = "https://graph.org/file/c95a687e777b55be1c792.jpg"
STATS_IMG_URL = "https://telegra.ph/file/edd388a42dd2c499fd868.jpg"
TELEGRAM_AUDIO_URL = "https://telegra.ph/file/492a3bb2e880d19750b79.jpg"
TELEGRAM_VIDEO_URL = "https://telegra.ph/file/492a3bb2e880d19750b79.jpg"
STREAM_IMG_URL = "https://graph.org/file/ff2af8d4d10afa1baf49e.jpg"
SOUNCLOUD_IMG_URL = "https://graph.org/file/c95a687e777b55be1c792.jpg"
YOUTUBE_IMG_URL = "https://graph.org/file/e8730fdece86a1166f608.jpg"
SPOTIFY_ARTIST_IMG_URL = "https://graph.org/file/0bb6f36796d496b4254ff.jpg"
SPOTIFY_ALBUM_IMG_URL = "https://graph.org/file/0bb6f36796d496b4254ff.jpg"
SPOTIFY_PLAYLIST_IMG_URL = "https://graph.org/file/0bb6f36796d496b4254ff.jpg"

# ==========================================
# 9. UTILS EXECUTIONS
# ==========================================
def time_to_seconds(time_str):
    if not isinstance(time_str, str):
        time_str = str(time_str)
    try:
        return sum(int(x) * 60**i for i, x in enumerate(reversed(time_str.split(":"))))
    except Exception:
        return 0

DURATION_LIMIT = int(time_to_seconds(f"{DURATION_LIMIT_MIN}:360"))

