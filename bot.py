import os
import shutil
import asyncio
import logging
import discord
from discord.ext import commands
from datetime import datetime, timedelta

from config import TOKEN, STAFF_ROLE_NAME, BACKUP_DIR, DB_NAME
from database import SimpleDB, ProductsCache
from utils import load_products_json, get_log_channel, cleanup_old_backups
from cogs.react import AutoReact

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

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

# ─── Background Tasks ─────────────────────────────────────────────────────────

async def auto_backup():
    while True:
        try:
            os.makedirs(BACKUP_DIR, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{BACKUP_DIR}/store_backup_{timestamp}.db"
            shutil.copy2(DB_NAME, backup_name)
            cleanup_old_backups()
            logger.info(f"✅ Auto backup berhasil: {backup_name}")
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
                            topic="🔒 Backup otomatis database Cellyn Store",
                        )
                    await backup_channel.send(
                        content=f"🗄️ **AUTO BACKUP**\n📅 {datetime.now().strftime('%d/%m/%Y %H:%M')}\n📦 `{backup_name}`",
                        file=discord.File(backup_name),
                    )
                except Exception as e:
                    logger.error(f"❌ Gagal kirim backup ke Discord: {e}")
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
            embed.set_footer(text="CELLYN STORE • Auto Summary")

            for guild in bot.guilds:
                backup_channel = discord.utils.get(guild.channels, name="backup-db")
                if backup_channel:
                    await backup_channel.send(embed=embed)
            logger.info(f"✅ Auto summary terkirim untuk {yesterday}")
        except Exception as e:
            logger.error(f"❌ Gagal auto summary: {e}")


async def update_member_count(guild):
    try:
        category = discord.utils.get(guild.categories, name="SERVER STATS")
        if not category:
            category = await guild.create_category("SERVER STATS")
        channel_name = f"Member: {guild.member_count}"
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
        print("✓ Instalasi pertama: produk diimport dari products.json")
    else:
        bot.PRODUCTS = db_products
        print(f"✓ Load {len(bot.PRODUCTS)} products from database")

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
        logger.info("✓ All cogs loaded")
        await bot.start(TOKEN)


if __name__ == "__main__":
    if not TOKEN:
        print("ERROR: DISCORD_TOKEN not found in .env")
        exit(1)
    print("Starting Cellyn Store Bot...")
    print("Under develop Equality")
    asyncio.run(main())
