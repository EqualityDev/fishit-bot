import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
STAFF_ROLE_NAME = os.getenv("STAFF_ROLE_NAME", "Admin Store")
BUYER_ROLE_NAME = os.getenv("BUYER_ROLE_NAME", "Royal Customer")
DANA_NUMBER = os.getenv("DANA_NUMBER", "")
BCA_NUMBER = os.getenv("BCA_NUMBER", "")
RATE = int(os.getenv("RATE", 85))
LOG_CHANNEL_ID = os.getenv("LOG_CHANNEL_ID")

DB_NAME = "store.db"
PRODUCTS_FILE = "products.json"
INVOICE_COUNTER_FILE = "invoice_counter.txt"
BROADCAST_COOLDOWN_FILE = "broadcast_cooldown.json"
BACKUP_DIR = "backups"
TRANSCRIPT_DIR = "transcripts"

CATEGORY_PRIORITY = [
    "LIMITED SKIN", "GAMEPASS", "CRATE",
    "BOOST", "NITRO", "RED FINGER", "MIDMAN", "LAINNYA"
]

STORE_THUMBNAIL = os.getenv("STORE_THUMBNAIL", "https://i.imgur.com/xp2F452.png")
STORE_BANNER = os.getenv("STORE_BANNER", "https://i.imgur.com/dyLxR7B.png")
BROADCAST_BANNER = os.getenv("BROADCAST_BANNER", "https://i.imgur.com/eEti6Tj.png")
INVOICE_BANNER = os.getenv("INVOICE_BANNER", "https://i.imgur.com/CQAn1Un.png")
WELCOME_BANNER = os.getenv("WELCOME_BANNER", "https://i.imgur.com/bvtm58j.png")
