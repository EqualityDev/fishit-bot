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
    STORE_NAME,
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

    # Invoice counter dari database (lebih aman dari file txt)
    today = datetime.now().strftime("%Y%m%d")
    counter_data = await db.get_setting("invoice_counter")
    try:
        data = json.loads(counter_data) if counter_data else {}
        if data.get("date") == today:
            counter = data["counter"] + 1
        else:
            counter = 1
    except Exception:
        counter = 1
    await db.set_setting("invoice_counter", json.dumps({"date": today, "counter": counter}))
    invoice_num = f"INV-{today}-{counter:04d}"

    transaction_data["invoice"] = invoice_num
    transaction_data["timestamp"] = datetime.now()
    trx_time = datetime.now().strftime("%d %B %Y, %H:%M")

    if not transaction_data.get("fake", False):
        try:
            buyer_role = discord.utils.get(guild.roles, name="👑 Royal Customer")
            if buyer_role and user and buyer_role not in user.roles:
                await user.add_roles(buyer_role)
                print(f"✅ Role {buyer_role.name} diberikan ke {user.name}")
        except Exception as e:
            print(f"❌ Error gift role: {e}")

    items_list = "".join(
        f"`{item['qty']}x` **{item['name']}**  —  Rp {item['price'] * item['qty']:,}\n"
        for item in transaction_data["items"]
    )

    # ── Log channel embed ──
    embed = discord.Embed(
        title="TRANSAKSI BERHASIL",
        color=0x00BFFF,
        timestamp=datetime.now(),
    )
    embed.set_thumbnail(url=STORE_THUMBNAIL)
    embed.add_field(name="No. Invoice", value=f"```{invoice_num}```", inline=False)
    embed.add_field(name="Customer", value=f"<@{transaction_data['user_id']}>", inline=True)
    embed.add_field(name="Metode", value=transaction_data.get("payment_method", "-"), inline=True)
    embed.add_field(name="Tanggal", value=trx_time, inline=True)
    embed.add_field(name="Items", value=items_list, inline=False)
    embed.add_field(name="Total", value=f"**Rp {transaction_data['total_price']:,}**", inline=True)

    if transaction_data.get("admin_id"):
        admin = guild.get_member(int(transaction_data["admin_id"]))
        if admin:
            embed.add_field(name="Diverifikasi oleh", value=admin.mention, inline=True)

    embed.set_image(url=INVOICE_BANNER)

    marker = "​" if transaction_data.get("fake", False) else ""
    embed.set_footer(text=f"{STORE_NAME}{marker} • {trx_time}")

    await channel.send(embed=embed)

    # ── DM embed ──
    if user and not transaction_data.get("fake", False):
        try:
            items_text = "".join(
                f"`{item['qty']}x` **{item['name']}**  —  Rp {item['price'] * item['qty']:,}\n"
                for item in transaction_data["items"]
            )
            dm_embed = discord.Embed(
                title="INVOICE PEMBELIAN",
                description=f"Terima kasih sudah belanja di **{STORE_NAME}**!\nBerikut detail transaksi kamu.",
                color=0x00BFFF,
                timestamp=datetime.now(),
            )
            dm_embed.set_thumbnail(url=STORE_THUMBNAIL)
            dm_embed.add_field(name="No. Invoice", value=f"```{invoice_num}```", inline=False)
            dm_embed.add_field(name="Tanggal", value=trx_time, inline=True)
            dm_embed.add_field(name="Metode Bayar", value=transaction_data.get("payment_method", "-"), inline=True)
            dm_embed.add_field(name="Items", value=items_text, inline=False)
            dm_embed.add_field(name="Total Pembayaran", value=f"**Rp {transaction_data['total_price']:,}**", inline=False)
            dm_embed.add_field(
                name="Info",
                value=f"Simpan nomor invoice kamu sebagai bukti pembelian.\nGunakan `/history` untuk melihat riwayat transaksi.",
                inline=False,
            )
            dm_embed.set_footer(text=f"{STORE_NAME} • Terima kasih sudah berbelanja!")
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
            topic=f"📋 LOG TRANSAKSI {STORE_NAME}",
        )
        embed = discord.Embed(
            title=f"📋 LOG TRANSAKSI {STORE_NAME}",
            description="Channel ini mencatat semua transaksi yang BERHASIL.",
            color=0x00BFFF,
            timestamp=datetime.now(),
        )
        embed.set_footer(text=f"{STORE_NAME}")
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

    now_str = datetime.now().strftime("%d %B %Y — %H:%M:%S")
    now_short = datetime.now().strftime("%d/%m/%Y %H:%M")

    html_content = f"""<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Transcript — {html.escape(channel.name)}</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-base: #0d0e11;
            --bg-card: #13151a;
            --bg-surface: #1a1d24;
            --bg-hover: #1f2229;
            --accent: #00bfff;
            --accent-dim: rgba(0,191,255,0.12);
            --accent-glow: rgba(0,191,255,0.25);
            --gold: #f0b232;
            --blurple: #5865f2;
            --text-primary: #e8eaf0;
            --text-secondary: #8b8fa8;
            --text-muted: #565a6e;
            --border: rgba(255,255,255,0.06);
            --border-accent: rgba(0,191,255,0.3);
            --shadow: 0 8px 32px rgba(0,0,0,0.6);
            --radius: 12px;
        }}

        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        body {{
            font-family: 'Inter', sans-serif;
            background: var(--bg-base);
            color: var(--text-primary);
            min-height: 100vh;
            padding: 32px 16px;
        }}

        /* ── TOP BAR ── */
        .topbar {{
            max-width: 860px;
            margin: 0 auto 20px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 10px 20px;
            background: var(--bg-card);
            border-radius: 999px;
            border: 1px solid var(--border);
        }}
        .topbar-brand {{
            font-size: 13px;
            font-weight: 600;
            color: var(--accent);
            letter-spacing: 0.05em;
            text-transform: uppercase;
        }}
        .topbar-date {{
            font-size: 11px;
            color: var(--text-muted);
        }}

        /* ── CONTAINER ── */
        .container {{
            max-width: 860px;
            margin: 0 auto;
            border-radius: var(--radius);
            overflow: hidden;
            box-shadow: var(--shadow);
            border: 1px solid var(--border);
        }}

        /* ── HEADER ── */
        .header {{
            background: linear-gradient(135deg, #0a1628 0%, #0d1f3a 50%, #091522 100%);
            padding: 36px 32px 28px;
            position: relative;
            overflow: hidden;
            border-bottom: 1px solid var(--border-accent);
        }}
        .header::before {{
            content: '';
            position: absolute;
            top: -60px; right: -60px;
            width: 220px; height: 220px;
            background: radial-gradient(circle, rgba(0,191,255,0.08) 0%, transparent 70%);
            pointer-events: none;
        }}
        .header::after {{
            content: '';
            position: absolute;
            bottom: 0; left: 0; right: 0;
            height: 1px;
            background: linear-gradient(90deg, transparent, var(--accent), transparent);
            opacity: 0.4;
        }}
        .header-top {{
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            margin-bottom: 20px;
        }}
        .header-title {{
            font-size: 22px;
            font-weight: 700;
            color: #fff;
            letter-spacing: -0.02em;
        }}
        .header-title span {{
            color: var(--accent);
        }}
        .header-badge {{
            background: var(--accent-dim);
            border: 1px solid var(--border-accent);
            color: var(--accent);
            font-size: 10px;
            font-weight: 600;
            padding: 4px 12px;
            border-radius: 999px;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }}
        .header-meta {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 12px;
        }}
        .meta-item {{
            background: rgba(255,255,255,0.03);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 10px 14px;
        }}
        .meta-label {{
            font-size: 10px;
            font-weight: 600;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.06em;
            margin-bottom: 4px;
        }}
        .meta-value {{
            font-size: 13px;
            font-weight: 500;
            color: var(--text-primary);
        }}

        /* ── MESSAGES ── */
        .messages {{
            background: var(--bg-card);
            padding: 24px 28px;
        }}
        .day-divider {{
            display: flex;
            align-items: center;
            gap: 12px;
            margin: 20px 0;
        }}
        .day-divider::before, .day-divider::after {{
            content: '';
            flex: 1;
            height: 1px;
            background: var(--border);
        }}
        .day-divider span {{
            font-size: 10px;
            color: var(--text-muted);
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            white-space: nowrap;
        }}
        .message {{
            display: flex;
            gap: 14px;
            padding: 8px 10px;
            border-radius: 8px;
            transition: background 0.15s;
            margin-bottom: 2px;
        }}
        .message:hover {{
            background: var(--bg-hover);
        }}
        .avatar {{
            width: 38px;
            height: 38px;
            border-radius: 50%;
            flex-shrink: 0;
            margin-top: 2px;
            object-fit: cover;
        }}
        .avatar-bot {{
            border: 2px solid var(--blurple);
        }}
        .avatar-staff {{
            border: 2px solid var(--gold);
        }}
        .msg-body {{
            flex: 1;
            min-width: 0;
        }}
        .msg-meta {{
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 3px;
        }}
        .msg-author {{
            font-size: 14px;
            font-weight: 600;
        }}
        .author-bot {{ color: var(--blurple); }}
        .author-staff {{ color: var(--gold); }}
        .author-user {{ color: var(--text-primary); }}
        .badge {{
            font-size: 9px;
            font-weight: 700;
            padding: 2px 7px;
            border-radius: 4px;
            letter-spacing: 0.05em;
            text-transform: uppercase;
        }}
        .badge-bot {{
            background: var(--blurple);
            color: #fff;
        }}
        .badge-staff {{
            background: rgba(240,178,50,0.2);
            color: var(--gold);
            border: 1px solid rgba(240,178,50,0.3);
        }}
        .msg-time {{
            font-size: 10px;
            color: var(--text-muted);
        }}
        .msg-content {{
            font-size: 14px;
            line-height: 1.55;
            color: var(--text-primary);
            white-space: pre-wrap;
            word-break: break-word;
        }}
        .msg-embed {{
            margin-top: 6px;
            padding: 8px 12px;
            background: var(--bg-surface);
            border-left: 3px solid var(--accent);
            border-radius: 0 6px 6px 0;
            font-size: 12px;
            color: var(--text-secondary);
            font-style: italic;
        }}
        .msg-attachment {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            margin-top: 6px;
            padding: 6px 12px;
            background: var(--bg-surface);
            border: 1px solid var(--border);
            border-radius: 6px;
            font-size: 12px;
            color: var(--accent);
            text-decoration: none;
        }}
        .msg-attachment:hover {{
            background: var(--accent-dim);
        }}

        /* ── FOOTER ── */
        .footer {{
            background: var(--bg-base);
            border-top: 1px solid var(--border);
            padding: 16px 32px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}
        .footer-brand {{
            font-size: 12px;
            font-weight: 600;
            color: var(--accent);
            letter-spacing: 0.04em;
        }}
        .footer-info {{
            font-size: 11px;
            color: var(--text-muted);
        }}
        .footer-dot {{
            width: 4px; height: 4px;
            background: var(--accent);
            border-radius: 50%;
            display: inline-block;
            margin: 0 8px;
            vertical-align: middle;
            opacity: 0.5;
        }}
        .msg-count {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            font-size: 11px;
            color: var(--text-muted);
            background: var(--bg-surface);
            padding: 4px 10px;
            border-radius: 999px;
            border: 1px solid var(--border);
        }}
    </style>
</head>
<body>

<div class="topbar">
    <span class="topbar-brand">{html.escape(STORE_NAME)}</span>
    <span class="topbar-date">{now_str}</span>
</div>

<div class="container">
    <div class="header">
        <div class="header-top">
            <div>
                <div class="header-title">Ticket <span>Transcript</span></div>
            </div>
            <span class="header-badge">Closed</span>
        </div>
        <div class="header-meta">
            <div class="meta-item">
                <div class="meta-label">Channel</div>
                <div class="meta-value">#{html.escape(channel.name)}</div>
            </div>
            <div class="meta-item">
                <div class="meta-label">Ditutup oleh</div>
                <div class="meta-value">{html.escape(closed_by.display_name)}</div>
            </div>
            <div class="meta-item">
                <div class="meta-label">Tanggal</div>
                <div class="meta-value">{now_str}</div>
            </div>
            <div class="meta-item">
                <div class="meta-label">Total Pesan</div>
                <div class="meta-value">{len(messages)} pesan</div>
            </div>
        </div>
    </div>

    <div class="messages">
        <div class="day-divider"><span>Awal percakapan</span></div>"""

    for msg in messages:
        if msg["is_bot"]:
            badge = '<span class="badge badge-bot">BOT</span>'
            author_class = "author-bot"
            avatar_class = "avatar-bot"
        elif msg["role"] == "staff":
            badge = '<span class="badge badge-staff">STAFF</span>'
            author_class = "author-staff"
            avatar_class = "avatar-staff"
        else:
            badge = ""
            author_class = "author-user"
            avatar_class = ""

        attachments_html = ""
        if msg["attachments"]:
            raw = msg["attachments"].replace("<br>📎 ", "")
            attachments_html = f'<div><a class="msg-attachment" href="#" target="_blank">📎 Lampiran</a></div>'

        embeds_html = ""
        if msg["embeds"]:
            embeds_html = '<div class="msg-embed">📦 Embed (tidak ditampilkan di transcript)</div>'

        content_html = f'<div class="msg-content">{msg["content"]}</div>' if msg["content"] else ""

        html_content += f"""
        <div class="message">
            <img class="avatar {avatar_class}" src="{msg['avatar']}" alt="" loading="lazy" onerror="this.src='https://cdn.discordapp.com/embed/avatars/0.png'">
            <div class="msg-body">
                <div class="msg-meta">
                    <span class="msg-author {author_class}">{msg['author']}</span>
                    {badge}
                    <span class="msg-time">{msg['timestamp']}</span>
                </div>
                {content_html}
                {attachments_html}
                {embeds_html}
            </div>
        </div>"""

    html_content += f"""
        <div class="day-divider"><span>Akhir percakapan</span></div>
    </div>

    <div class="footer">
        <span class="footer-brand">{html.escape(STORE_NAME)}</span>
        <span class="footer-info">
            <span class="msg-count">💬 {len(messages)} pesan</span>
            <span class="footer-dot"></span>
            {now_short}
        </span>
    </div>
</div>

</body>
</html>"""

    os.makedirs(TRANSCRIPT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{TRANSCRIPT_DIR}/ticket-{channel.name}-{timestamp}.html"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html_content)
    return filename
