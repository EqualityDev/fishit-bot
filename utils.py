import os
import json
import html
import shutil
import asyncio
import discord
from datetime import datetime
from config import (
    STAFF_ROLE_NAME,
    INVOICE_COUNTER_FILE,
    BROADCAST_COOLDOWN_FILE,
    BACKUP_DIR,
    TRANSCRIPT_DIR,
    LOG_CHANNEL_ID as _LOG_CHANNEL_ID_ENV,
    STORE_THUMBNAIL,
    INVOICE_BANNER,
)

_log_channel_id = None


# ─── Staff Check ─────────────────────────────────────────────────────────────

def is_staff(interaction: discord.Interaction) -> bool:
    staff_role = discord.utils.get(interaction.guild.roles, name=STAFF_ROLE_NAME)
    return staff_role in interaction.user.roles


# ─── Error Handling ──────────────────────────────────────────────────────────

async def handle_error(interaction_or_ctx, error, title="❌ Error", ephemeral=True):
    import traceback
    msg = str(error)
    print(f"❌ Error: {msg}")
    print("".join(traceback.format_tb(error.__traceback__)))
    try:
        if hasattr(interaction_or_ctx, "response") and not interaction_or_ctx.response.is_done():
            await interaction_or_ctx.response.send_message(
                f"{title}\n```\n{msg[:1500]}\n```", ephemeral=ephemeral
            )
        elif hasattr(interaction_or_ctx, "followup"):
            await interaction_or_ctx.followup.send(
                f"{title}\n```\n{msg[:1500]}\n```", ephemeral=ephemeral
            )
        elif hasattr(interaction_or_ctx, "send"):
            await interaction_or_ctx.send(f"{title}\n```\n{msg[:1500]}\n```")
    except Exception:
        pass


# ─── Invoice ─────────────────────────────────────────────────────────────────

def generate_invoice_number(db=None):
    today = datetime.now().strftime("%Y%m%d")
    try:
        with open(INVOICE_COUNTER_FILE, "r") as f:
            data = json.loads(f.read().strip())
            if data.get("date") == today:
                counter = data["counter"] + 1
            else:
                counter = 1
    except Exception:
        counter = 1
    with open(INVOICE_COUNTER_FILE, "w") as f:
        f.write(json.dumps({"date": today, "counter": counter}))
    return f"INV-{today}-{counter:04d}"


async def send_invoice(guild, transaction_data, db):
    channel = await get_log_channel(guild)
    user = guild.get_member(int(transaction_data["user_id"]))
    user_name = user.display_name if user else "Unknown"
    invoice_num = generate_invoice_number()
    transaction_data["invoice"] = invoice_num
    transaction_data["timestamp"] = datetime.now()

    if not transaction_data.get("fake", False):
        try:
            buyer_role = discord.utils.get(guild.roles, name="👑 Royal Customer")
            if buyer_role and user and buyer_role not in user.roles:
                await user.add_roles(buyer_role)
                print(f"✅ Role {buyer_role.name} diberikan ke {user.name}")
        except Exception as e:
            print(f"❌ Error gift role: {e}")

    items_list = "".join(
        f"{item['qty']}x {item['name']} = Rp {item['price'] * item['qty']:,}\n"
        for item in transaction_data["items"]
    )

    embed = discord.Embed(
        title="TRANSAKSI BERHASIL",
        color=0x00FF00,
        timestamp=datetime.now(),
    )
    embed.set_thumbnail(url=STORE_THUMBNAIL)
    embed.add_field(name="Invoice", value=f"`{invoice_num}`", inline=False)
    embed.add_field(name="Customer", value=f"<@{transaction_data['user_id']}>", inline=True)
    embed.add_field(name="Total", value=f"Rp {transaction_data['total_price']:,}", inline=True)
    embed.add_field(name="Metode", value=transaction_data.get("payment_method", "-"), inline=True)
    embed.add_field(name="Items", value=items_list, inline=False)

    if transaction_data.get("admin_id"):
        admin = guild.get_member(int(transaction_data["admin_id"]))
        if admin:
            embed.add_field(name="Diverifikasi", value=admin.mention, inline=True)

    embed.set_image(url=INVOICE_BANNER)

    marker = "​" if transaction_data.get("fake", False) else ""
    embed.set_footer(text=f"CELLYN STORE{marker}")

    await channel.send(embed=embed)

    if user and not transaction_data.get("fake", False):
        try:
            items_text = "".join(
                f"{item['qty']}x {item['name']} = Rp {item['price'] * item['qty']:,}\n"
                for item in transaction_data["items"]
            )
            dm_embed = discord.Embed(
                title="🧾 **INVOICE PEMBAYARAN**",
                description="Terima kasih telah berbelanja di **CELLYN STORE**!",
                color=0x00FF00,
                timestamp=datetime.now(),
            )
            dm_embed.set_thumbnail(url=STORE_THUMBNAIL)
            dm_embed.add_field(name="📦 **ITEMS**", value=items_text, inline=False)
            dm_embed.add_field(name="💰 **TOTAL**", value=f"Rp {transaction_data['total_price']:,}", inline=True)
            dm_embed.add_field(name="💳 **METODE**", value=transaction_data.get("payment_method", "-"), inline=True)
            dm_embed.add_field(name="📋 **INVOICE**", value=f"`{invoice_num}`", inline=False)
            dm_embed.add_field(
                name="❤️ **DARI KAMI**",
                value=(
                    "👑 *Terima kasih telah menjadi bagian dari keluarga besar Cellyn Store!*\n"
                    "✨ *Anda adalah pelanggan yang sangat berharga bagi kami.*\n"
                    "🌟 *Tanpa dukungan anda, kami bukan apa-apa.*"
                ),
                inline=False,
            )
            dm_embed.add_field(
                name="🔍 **CEK TRANSAKSI**",
                value="Kamu bisa lihat history transaksi dengan command `/history`",
                inline=False,
            )
            dm_embed.set_footer(text="CELLYN STORE • Terima kasih!")
            await user.send(embed=dm_embed)
            print(f"✅ Invoice DM terkirim ke {user.name}")
        except discord.Forbidden:
            print(f"❌ Gagal kirim DM ke {user.name} (DM dimatikan)")
        except Exception as e:
            print(f"❌ Gagal kirim DM: {e}")

    await db.save_transaction(transaction_data)
    return invoice_num


# ─── Log Channel ─────────────────────────────────────────────────────────────

async def get_log_channel(guild):
    global _log_channel_id

    if _log_channel_id is None:
        try:
            _log_channel_id = int(_LOG_CHANNEL_ID_ENV)
        except Exception:
            _log_channel_id = None

    if _log_channel_id:
        channel = guild.get_channel(_log_channel_id)
        if channel and isinstance(channel, discord.TextChannel):
            return channel
        _log_channel_id = None

    channel = discord.utils.get(guild.channels, name="log-transaksi")

    if not channel:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(
                read_messages=True, send_messages=False
            ),
            guild.me: discord.PermissionOverwrite(
                read_messages=True, send_messages=True
            ),
        }
        channel = await guild.create_text_channel(
            name="log-transaksi",
            overwrites=overwrites,
            topic="📋 LOG TRANSAKSI CELLYN STORE",
        )
        embed = discord.Embed(
            title="📋 LOG TRANSAKSI CELLYN STORE",
            description="Channel ini mencatat semua transaksi yang BERHASIL.",
            color=0x00FF00,
            timestamp=datetime.now(),
        )
        embed.set_footer(text="CELLYN STORE")
        await channel.send(embed=embed)
        _log_channel_id = channel.id
        update_env_file(f"LOG_CHANNEL_ID={channel.id}")

    return channel


def update_env_file(key_value):
    try:
        with open(".env", "r") as f:
            lines = f.readlines()
        key = key_value.split("=")[0]
        found = False
        for i, line in enumerate(lines):
            if line.startswith(key + "="):
                lines[i] = key_value + "\n"
                found = True
                break
        if not found:
            lines.append("\n" + key_value + "\n")
        with open(".env", "w") as f:
            f.writelines(lines)
    except Exception as e:
        print(f"❌ Error updating .env: {e}")


# ─── Product Helpers ─────────────────────────────────────────────────────────

def calculate_total(items):
    return sum(item["price"] * item["qty"] for item in items)


def format_items(items):
    if not items:
        return "Tidak ada item"
    return "\n".join(
        f"{item['qty']}x {item['name']} = Rp {item['price'] * item['qty']:,}"
        for item in items
    )


async def get_item_by_id(item_id, products_cache):
    products = await products_cache.get_products()
    return next((p for p in products if p["id"] == item_id), None)


# ─── Product File ─────────────────────────────────────────────────────────────

def save_products_json(products, filepath="products.json"):
    with open(filepath, "w") as f:
        json.dump(products, f, indent=2)


def load_products_json(filepath="products.json"):
    try:
        with open(filepath, "r") as f:
            products = json.load(f)
        print(f"✓ Load {len(products)} products from {filepath}")
        return products
    except Exception as e:
        print(f"❌ Gagal load {filepath}: {e}")
        return []


# ─── Broadcast Cooldown ──────────────────────────────────────────────────────

def load_broadcast_cooldown():
    try:
        with open(BROADCAST_COOLDOWN_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_broadcast_cooldown(data):
    with open(BROADCAST_COOLDOWN_FILE, "w") as f:
        json.dump(data, f)


# ─── Backup ──────────────────────────────────────────────────────────────────

def cleanup_old_backups(keep=5):
    try:
        files = [
            os.path.join(BACKUP_DIR, f)
            for f in os.listdir(BACKUP_DIR)
            if f.endswith(".db")
        ]
        files.sort(key=os.path.getmtime, reverse=True)
        for old_file in files[keep:]:
            os.remove(old_file)
            print(f"🗑️ Hapus backup lama: {os.path.basename(old_file)}")
    except Exception as e:
        print(f"❌ Gagal cleanup backup: {e}")


# ─── HTML Transcript ─────────────────────────────────────────────────────────

async def generate_html_transcript(channel, closed_by):
    messages = []
    async for msg in channel.history(limit=1000, oldest_first=True):
        timestamp = msg.created_at.strftime("%H:%M %d/%m/%Y")
        content = html.escape(msg.content) if msg.content else ""
        attachments = "".join(
            f'<br>📎 <a href="{a.url}" target="_blank">{html.escape(a.filename)}</a>'
            for a in msg.attachments
        )
        embeds = "<br>📦 [Embed]" if msg.embeds else ""

        role_class = "bot" if msg.author.bot else (
            "staff" if discord.utils.get(msg.author.roles, name=STAFF_ROLE_NAME) else "user"
        )
        avatar_url = (
            msg.author.avatar.url
            if msg.author.avatar
            else f"https://cdn.discordapp.com/embed/avatars/{int(msg.author.id) % 5}.png"
        )

        messages.append({
            "timestamp": timestamp,
            "author": html.escape(msg.author.display_name),
            "avatar": avatar_url,
            "content": content,
            "attachments": attachments,
            "embeds": embeds,
            "role": role_class,
            "is_bot": msg.author.bot,
        })

    html_content = f"""<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Transcript - {html.escape(channel.name)}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Whitney', Arial, sans-serif; background: #313338; color: #dcddde; padding: 20px; }}
        .container {{ max-width: 900px; margin: 0 auto; background: #2b2d31; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,.4); }}
        .header {{ background: #1e1f22; padding: 20px 25px; border-bottom: 2px solid #111214; }}
        .header h1 {{ color: #fff; font-size: 22px; margin-bottom: 8px; }}
        .header p {{ color: #96989d; font-size: 13px; margin: 3px 0; }}
        .messages {{ padding: 20px 25px; }}
        .message {{ display: flex; margin: 12px 0; padding-bottom: 12px; border-bottom: 1px solid #3f4147; }}
        .message:last-child {{ border-bottom: none; }}
        .avatar {{ width: 40px; height: 40px; border-radius: 50%; margin-right: 12px; flex-shrink: 0; }}
        .meta {{ display: flex; align-items: baseline; gap: 8px; margin-bottom: 4px; }}
        .author {{ font-weight: 600; font-size: 15px; }}
        .staff .author {{ color: #f0b232; }}
        .bot .author {{ color: #5865f2; }}
        .user .author {{ color: #fff; }}
        .timestamp {{ color: #96989d; font-size: 11px; }}
        .content {{ color: #dcddde; font-size: 14px; white-space: pre-wrap; word-wrap: break-word; }}
        .badge {{ background: #5865f2; padding: 1px 6px; border-radius: 10px; font-size: 10px; color: #fff; }}
        .footer {{ background: #1e1f22; padding: 12px 25px; text-align: center; color: #96989d; font-size: 12px; border-top: 2px solid #111214; }}
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>🎫 Ticket Transcript</h1>
        <p>📌 Channel: #{html.escape(channel.name)}</p>
        <p>🔒 Ditutup oleh: {html.escape(closed_by.display_name)} (@{html.escape(closed_by.name)})</p>
        <p>📅 {datetime.now().strftime('%d %B %Y %H:%M:%S')} &nbsp;|&nbsp; 💬 {len(messages)} pesan</p>
    </div>
    <div class="messages">"""

    for msg in messages:
        badge = ""
        if msg["is_bot"]:
            badge = '<span class="badge">BOT</span>'
        elif msg["role"] == "staff":
            badge = '<span class="badge">STAFF</span>'

        html_content += f"""
        <div class="message {msg['role']}">
            <img class="avatar" src="{msg['avatar']}" alt="Avatar" loading="lazy">
            <div>
                <div class="meta">
                    <span class="author">{msg['author']}</span>
                    {badge}
                    <span class="timestamp">{msg['timestamp']}</span>
                </div>
                <div class="content">{msg['content']}</div>
                {msg['attachments']}{msg['embeds']}
            </div>
        </div>"""

    html_content += f"""
    </div>
    <div class="footer">CELLYN STORE • {datetime.now().strftime('%d/%m/%Y %H:%M')}</div>
</div>
</body>
</html>"""

    os.makedirs(TRANSCRIPT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{TRANSCRIPT_DIR}/ticket-{channel.name}-{timestamp}.html"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html_content)
    return filename
