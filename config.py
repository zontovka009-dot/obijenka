import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_IDS = {
    int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",")
    if x.strip().isdigit()
}
GROUP_LINK = os.getenv("GROUP_LINK", "").strip()

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")
