import os
import shutil
import asyncio
import logging
import discord
from discord.ext import commands
from datetime import datetime, timedelta

from config import TOKEN, STAFF_ROLE_NAME, BACKUP_DIR, DB_NAME, STORE_NAME
from database import SimpleDB, ProductsCache
from utils import load_products_json, get_log_channel, cleanup_old_backups
from cogs.react import AutoReact

# Terminal colors
CYAN  = "\033[0;36m"
GREEN = "\033[0;32m"
YELLOW= "\033[1;33m"
PURPLE= "\033[0;35m"
GRAY  = "\033[0;37m"
WHITE = "\033[1;37m"
RED   = "\033[0;31m"
NC    = "\033[0m"

class ColorFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG:    "\033[0;37m",
        logging.INFO:     "\033[0;36m",
        logging.WARNING:  "\033[1;33m",
        logging.ERROR:    "\033[0;31m",
        logging.CRITICAL: "\033[1;31m",
    }
    NC = "\033[0m"
    def format(self, record):
        import copy
        record = copy.copy(record)
        color = self.COLORS.get(record.levelno, self.NC)
        record.levelname = f"{color}{record.levelname}{self.NC}"
        record.msg = f"{color}{record.msg}{self.NC}"
        return super().format(record)

handler = logging.StreamHandler()
handler.setFormatter(ColorFormatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
logging.basicConfig(level=logging.INFO, handlers=[handler])
logger = logging.getLogger(__name__)


class DiscordErrorHandler(logging.Handler):
    """Kirim log ERROR ke channel #backup-db di Discord"""
    def __init__(self, bot):
        super().__init__(level=logging.ERROR)
        self.bot = bot
        self._queue = []

    def emit(self, record):
        self._queue.append(self.format(record))

    async def flush_to_discord(self):
        while True:
            await asyncio.sleep(5)
            if not self._queue:
                continue
            messages = self._queue.copy()
            self._queue.clear()
            for guild in self.bot.guilds:
                backup_channel = discord.utils.get(guild.channels, name="backup-db")
                if backup_channel:
                    for msg in messages:
                        try:
                            await backup_channel.send(f"```\n⚠️ ERROR LOG\n{msg[:1900]}\n```")
                        except Exception:
                            pass

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ─── Shared State ─────────────────────────────────────────────────────────────

bot.db = SimpleDB()
bot.products_cache = ProductsCache(bot.db)
bot.active_tickets = {}
bot.blacklist = set()
bot.PRODUCTS = []
bot.auto_react = AutoReact()
bot.auto_react_all = {}

# Error handler untuk kirim log ke Discord
bot._error_handler = DiscordErrorHandler(bot)
logging.getLogger().addHandler(bot._error_handler)

# ─── Background Tasks ─────────────────────────────────────────────────────────

async def rotating_status():
    await bot.wait_until_ready()
    while True:
        try:
            all_trans = await bot.db.get_all_transactions()
            total_trx = len(all_trans)
            total_products = len(bot.PRODUCTS)
            total_members = sum(
                sum(1 for m in g.members if not m.bot)
                for g in bot.guilds
            )

            statuses = [
                (discord.ActivityType.playing, f"{STORE_NAME}"),
                (discord.ActivityType.watching, f"{total_members} members"),
                (discord.ActivityType.playing, f"{total_products} produk tersedia"),
                (discord.ActivityType.watching, f"{total_trx} transaksi selesai"),
                (discord.ActivityType.listening, "QRIS • DANA • BCA"),
            ]

            for activity_type, text in statuses:
                await bot.change_presence(
                    status=discord.Status.online,
                    activity=discord.Activity(type=activity_type, name=text)
                )
                await asyncio.sleep(300)
        except Exception as e:
            logger.error(f"Rotating status error: {e}")
            await asyncio.sleep(300)


async def auto_backup():
    while True:
        try:
            os.makedirs(BACKUP_DIR, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{BACKUP_DIR}/store_backup_{timestamp}.db"
            shutil.copy2(DB_NAME, backup_name)
            logger.info(f"✓ Auto backup berhasil: {backup_name}")
            for guild in bot.guilds:
                try:
                    backup_channel = discord.utils.get(guild.channels, name="backup-db")
                    if not backup_channel:
                        staff_role = discord.utils.get(guild.roles, name=STAFF_ROLE_NAME)
                        overwrites = {
                            guild.default_role: discord.PermissionOverwrite(read_messages=False),
                            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                        }
                        if staff_role:
                            overwrites[staff_role] = discord.PermissionOverwrite(read_messages=True)
                        backup_channel = await guild.create_text_channel(
                            name="backup-db",
                            overwrites=overwrites,
                            topic=f"🔒 Backup otomatis database {STORE_NAME}",
                        )
                    await backup_channel.send(
                        content=f"🗄️ **AUTO BACKUP**\n📅 {datetime.now().strftime('%d/%m/%Y %H:%M')}\n📦 `{backup_name}`",
                        file=discord.File(backup_name),
                    )
                except Exception as e:
                    logger.error(f"❌ Gagal kirim backup ke Discord: {e}")
            cleanup_old_backups()
        except Exception as e:
            logger.error(f"❌ Gagal auto backup: {e}")

        await asyncio.sleep(21600)


async def auto_daily_summary():
    while True:
        now = datetime.now()
        next_midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        seconds_until_midnight = (next_midnight - now).total_seconds()
        await asyncio.sleep(seconds_until_midnight)

        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        try:
            all_trans = await bot.db.get_all_transactions()
            daily = [
                t for t in all_trans
                if t["timestamp"].strftime("%Y-%m-%d") == yesterday
            ]
            total_omset = sum(t["total_price"] for t in daily)
            total_trx = len(daily)

            methods = {}
            for t in daily:
                m = t.get("payment_method") or "-"
                methods[m] = methods.get(m, 0) + 1

            method_str = "\n".join(f"{m}: {c} transaksi" for m, c in methods.items()) or "-"

            embed = discord.Embed(
                title=f"REKAP HARIAN — {yesterday}",
                color=0x00FF00,
                timestamp=datetime.now(),
            )
            embed.add_field(name="Total Transaksi", value=str(total_trx), inline=True)
            embed.add_field(name="Total Omset", value=f"Rp {total_omset:,}", inline=True)
            embed.add_field(name="Metode Bayar", value=method_str, inline=False)
            if total_trx == 0:
                embed.description = "Tidak ada transaksi hari ini."
            embed.set_footer(text=f"{STORE_NAME} • Auto Summary")

            for guild in bot.guilds:
                backup_channel = discord.utils.get(guild.channels, name="backup-db")
                if backup_channel:
                    await backup_channel.send(embed=embed)
            logger.info(f"✓ Auto summary terkirim untuk {yesterday}")
        except Exception as e:
            logger.error(f"❌ Gagal auto summary: {e}")


async def update_member_count(guild):
    try:
        if not guild.chunked:
            await guild.chunk()
        category = discord.utils.get(guild.categories, name="SERVER STATS")
        if not category:
            category = await guild.create_category("SERVER STATS")
        human_count = sum(1 for m in guild.members if not m.bot)
        channel_name = f"Member: {human_count}"
        existing = [c for c in guild.voice_channels if c.name.startswith("Member:")]
        if existing:
            if existing[0].name != channel_name:
                await existing[0].edit(name=channel_name)
            for dup in existing[1:]:
                try:
                    await dup.delete()
                except Exception:
                    pass
        else:
            await guild.create_voice_channel(name=channel_name, category=category, user_limit=0)
    except Exception as e:
        logger.error(f"Error update member count {guild.name}: {e}")


async def update_all_member_counts():
    while True:
        for guild in bot.guilds:
            await update_member_count(guild)
        await asyncio.sleep(600)

# ─── Events ───────────────────────────────────────────────────────────────────

@bot.event
async def on_ready():
    if hasattr(bot, "_ready_called"):
        return
    bot._ready_called = True

    logger.info(f"BOT READY — {bot.user} | Servers: {len(bot.guilds)}")

    await bot.db.init_db()

    db_products = await bot.db.load_products()
    if not db_products:
        bot.PRODUCTS = load_products_json()
        await bot.db.save_products(bot.PRODUCTS)
        print(f"{GREEN}  ✓ Database: produk diimport dari products.json{NC}")
    else:
        bot.PRODUCTS = db_products
        print(f"{GREEN}  ✓ Database: {len(bot.PRODUCTS)} produk dimuat{NC}")

    await bot.products_cache.load_from_db()

    await asyncio.sleep(2)

    try:
        bot.active_tickets = await bot.db.get_active_tickets()
        logger.info(f"✓ Loaded {len(bot.active_tickets)} active tickets")
    except Exception as e:
        logger.error(f"Error loading tickets: {e}")
        bot.active_tickets = {}

    try:
        bot.auto_react_all = await bot.db.load_auto_react_all()
        logger.info(f"✓ Loaded {len(bot.auto_react_all)} auto_react_all entries")
    except Exception as e:
        logger.error(f"Error loading auto_react_all: {e}")

    try:
        bot.auto_react.enabled_channels = await bot.db.load_auto_react()
        logger.info(f"✓ Loaded {len(bot.auto_react.enabled_channels)} auto_react entries")
    except Exception as e:
        logger.error(f"Error loading auto_react: {e}")

    try:
        synced = await bot.tree.sync()
        logger.info(f"✓ Synced {len(synced)} slash commands")
    except Exception as e:
        logger.error(f"Sync error: {e}")

    bot.loop.create_task(auto_backup())
    bot.loop.create_task(auto_daily_summary())
    bot.loop.create_task(update_all_member_counts())
    bot.loop.create_task(bot._error_handler.flush_to_discord())
    bot.loop.create_task(rotating_status())
    logger.info("✓ Background tasks started")


@bot.event
async def on_member_join(member):
    await update_member_count(member.guild)


@bot.event
async def on_member_remove(member):
    await update_member_count(member.guild)


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return


# ─── Load Cogs ────────────────────────────────────────────────────────────────

async def main():
    async with bot:
        await bot.load_extension("cogs.react")
        await bot.load_extension("cogs.admin")
        await bot.load_extension("cogs.store")
        await bot.load_extension("cogs.ticket")
        await bot.load_extension("cogs.giveaway")
        logger.info("✓ All cogs loaded")
        await bot.start(TOKEN)


if __name__ == "__main__":
    if not TOKEN:
        print(f"{RED}  ✗ ERROR: DISCORD_TOKEN tidak ditemukan di .env{NC}")
        exit(1)
    print(f"{CYAN}  ▶ Starting {STORE_NAME} Bot...{NC}")
    print(f"{GRAY}  ✎ Under develop by Equality{NC}")
    asyncio.run(main())
