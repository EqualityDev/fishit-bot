import discord
from discord import app_commands
from discord.ext import commands
import os
import random
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

STAFF_ROLE_NAME = "Admin Store"
DANA_NUMBER = "081266778093"
BCA_NUMBER = "8565330655"
RATE = 95

active_tickets = {}
transactions = []
invoice_counter = 1000
blacklist = set()
user_transaction_count = {}
LOG_CHANNEL_ID = None

PRODUCTS = [
    {"id": 1, "name": "CRESCENDO SCYTHE", "category": "LIMITED SKIN", "price": 80000},
    {"id": 2, "name": "CHROMATIC KATANA", "category": "LIMITED SKIN", "price": 85000},
    {"id": 3, "name": "MAGMA SURFBOARD", "category": "LIMITED SKIN", "price": 38000},
    {"id": 4, "name": "VIP + LUCK", "category": "GAMEPASS", "price": 40000},
    {"id": 5, "name": "MUTATION", "category": "GAMEPASS", "price": 25000},
    {"id": 6, "name": "ADVANCED LUCK", "category": "GAMEPASS", "price": 45000},
    {"id": 7, "name": "EXTRA LUCK", "category": "GAMEPASS", "price": 21000},
    {"id": 8, "name": "DOUBLE XP", "category": "GAMEPASS", "price": 18000},
    {"id": 9, "name": "SELL ANYWHERE", "category": "GAMEPASS", "price": 28000},
    {"id": 10, "name": "SMALL LUCK", "category": "GAMEPASS", "price": 5000},
    {"id": 11, "name": "HYPERBOATPACK", "category": "GAMEPASS", "price": 85000},
    {"id": 12, "name": "PIRATE CRATE 1X", "category": "CRATE", "price": 10000},
    {"id": 13, "name": "PIRATE CRATE 5X", "category": "CRATE", "price": 48000},
    {"id": 14, "name": "ELDERWOOD CRATE 1X", "category": "CRATE", "price": 9000},
    {"id": 15, "name": "ELDERWOOD CRATE 5X", "category": "CRATE", "price": 42000},
    {"id": 16, "name": "SERVER LUCK X2", "category": "BOOST", "price": 10000},
    {"id": 17, "name": "SERVER LUCK X4", "category": "BOOST", "price": 38000},
    {"id": 18, "name": "SERVER LUCK X8", "category": "BOOST", "price": 73000},
    {"id": 19, "name": "X8 3 JAM", "category": "BOOST", "price": 73000},
    {"id": 20, "name": "X8 6 JAM", "category": "BOOST", "price": 115000},
    {"id": 21, "name": "X8 12 JAM", "category": "BOOST", "price": 215000},
    {"id": 22, "name": "X8 24 JAM", "category": "BOOST", "price": 410000},
    {"id": 23, "name": "NITRO BOOST 1 MONTH", "category": "NITRO", "price": 50000},
    {"id": 24, "name": "NITRO BOOST 3 MONTH", "category": "NITRO", "price": 70000},
    {"id": 25, "name": "NITRO BOOST 1 YEAR", "category": "NITRO", "price": 650000},
    {"id": 26, "name": "RF VIP 7DAY", "category": "RED FINGER", "price": 10000},
    {"id": 27, "name": "RF KVIP 7DAY", "category": "RED FINGER", "price": 10000},
    {"id": 28, "name": "RF SVIP 7DAY", "category": "RED FINGER", "price": 18000},
    {"id": 29, "name": "RF XVIP 7DAY", "category": "RED FINGER", "price": 25000},
    {"id": 30, "name": "RF VIP 30DAY", "category": "RED FINGER", "price": 30000},
    {"id": 31, "name": "RF KVIP 30DAY", "category": "RED FINGER", "price": 30000},
    {"id": 32, "name": "RF SVIP 30DAY", "category": "RED FINGER", "price": 45000},
    {"id": 33, "name": "RF XVIP 30DAY", "category": "RED FINGER", "price": 55000},
    {"id": 34, "name": "RF SERVER SG READY", "category": "RED FINGER", "price": 50000},
    {"id": 35, "name": "JASA REDEEM KODE RF", "category": "RED FINGER", "price": 10000},
    {"id": 36, "name": "JASA REPLACE VIP", "category": "RED FINGER", "price": 10000},
    {"id": 37, "name": "JASA REPLACE KVIP", "category": "RED FINGER", "price": 10000},
    {"id": 38, "name": "JASA REPLACE SVIP", "category": "RED FINGER", "price": 18000},
    {"id": 39, "name": "JASA REPLACE XVIP", "category": "RED FINGER", "price": 25000},
]

async def get_log_channel(guild):
    global LOG_CHANNEL_ID
    if LOG_CHANNEL_ID:
        channel = guild.get_channel(LOG_CHANNEL_ID)
        if channel:
            return channel
    channel = discord.utils.get(guild.channels, name="log-transaksi")
    if not channel:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=False),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        channel = await guild.create_text_channel(
            name="log-transaksi",
            overwrites=overwrites,
            topic="LOG TRANSAKSI BERHASIL - CELLYN STORE"
        )
        embed = discord.Embed(
            title="LOG TRANSAKSI CELLYN STORE",
            description="Channel ini mencatat semua transaksi yang BERHASIL.",
            color=0x00ff00,
            timestamp=datetime.now()
        )
        embed.set_footer(text="CELLYN STORE")
        await channel.send(embed=embed)
    LOG_CHANNEL_ID = channel.id
    return channel

def generate_invoice_number():
    global invoice_counter
    invoice_counter += 1
    today = datetime.now().strftime("%Y%m%d")
    return f"INV-{today}-{invoice_counter:04d}"

async def send_invoice(guild, transaction_data):
    channel = await get_log_channel(guild)
    user = guild.get_member(int(transaction_data['user_id']))
    user_name = user.display_name if user else "Unknown"
    invoice_num = generate_invoice_number()
    transaction_data['invoice'] = invoice_num
    transaction_data['timestamp'] = datetime.now()
    transactions.append(transaction_data)
    user_id = transaction_data['user_id']
    if user_id not in user_transaction_count:
        user_transaction_count[user_id] = 0
    user_transaction_count[user_id] += 1
    embed = discord.Embed(
        title="TRANSAKSI BERHASIL",
        color=0x00ff00,
        timestamp=datetime.now()
    )
    embed.add_field(name="NO. INVOICE", value=f"`{invoice_num}`", inline=False)
    embed.add_field(name="CUSTOMER", value=f"{user_name}\n<@{transaction_data['user_id']}>", inline=True)
    embed.add_field(name="ITEM", value=transaction_data['item_name'], inline=True)
    embed.add_field(name="HARGA", value=f"Rp {transaction_data['price']:,}", inline=True)
    embed.add_field(name="METODE", value=transaction_data.get('payment_method', '-'), inline=True)
    embed.add_field(name="TANGGAL", value=datetime.now().strftime("%d/%m/%Y %H:%M"), inline=True)
    embed.add_field(name="STATUS", value="LUNAS", inline=True)
    if transaction_data.get('admin_id'):
        admin = guild.get_member(int(transaction_data['admin_id']))
        if admin:
            embed.add_field(name="ADMIN", value=admin.mention, inline=True)
    embed.set_footer(text="CELLYN STORE")
    await channel.send(embed=embed)
    return invoice_num

@bot.tree.command(name="history", description="Lihat riwayat transaksi pribadi")
async def history(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    user_transactions = [t for t in transactions if t['user_id'] == user_id]
    if not user_transactions:
        await interaction.response.send_message("Belum ada transaksi.", ephemeral=True)
        return
    last_5 = user_transactions[-5:]
    embed = discord.Embed(
        title="RIWAYAT TRANSAKSI",
        description=f"Total: {len(user_transactions)} transaksi",
        color=0x3498db
    )
    for t in reversed(last_5):
        date_str = t['timestamp'].strftime("%d/%m/%Y %H:%M")
        embed.add_field(
            name=f"{t['invoice']} - {date_str}",
            value=f"{t['item_name']} | Rp {t['price']:,} | {t.get('payment_method', '-')}",
            inline=False
        )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="stats", description="Lihat statistik penjualan (Admin only)")
async def stats(interaction: discord.Interaction):
    staff_role = discord.utils.get(interaction.guild.roles, name=STAFF_ROLE_NAME)
    if staff_role not in interaction.user.roles:
        await interaction.response.send_message("Admin only!", ephemeral=True)
        return
    today = datetime.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    today_trans = [t for t in transactions if t['timestamp'].date() == today]
    week_trans = [t for t in transactions if t['timestamp'].date() >= week_ago]
    month_trans = [t for t in transactions if t['timestamp'].date() >= month_ago]
    total_revenue = sum(t['price'] for t in transactions)
    today_revenue = sum(t['price'] for t in today_trans)
    week_revenue = sum(t['price'] for t in week_trans)
    month_revenue = sum(t['price'] for t in month_trans)
    embed = discord.Embed(
        title="STATISTIK PENJUALAN",
        color=0x00ff00,
        timestamp=datetime.now()
    )
    embed.add_field(name="HARI INI", value=f"{len(today_trans)} transaksi\nRp {today_revenue:,}", inline=True)
    embed.add_field(name="7 HARI", value=f"{len(week_trans)} transaksi\nRp {week_revenue:,}", inline=True)
    embed.add_field(name="30 HARI", value=f"{len(month_trans)} transaksi\nRp {month_revenue:,}", inline=True)
    embed.add_field(name="TOTAL", value=f"{len(transactions)} transaksi\nRp {total_revenue:,}", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="blacklist", description="Blacklist user (Admin only)")
@app_commands.describe(user="User yang akan diblacklist", reason="Alasan")
async def blacklist_user(interaction: discord.Interaction, user: discord.User, reason: str = "No reason"):
    staff_role = discord.utils.get(interaction.guild.roles, name=STAFF_ROLE_NAME)
    if staff_role not in interaction.user.roles:
        await interaction.response.send_message("Admin only!", ephemeral=True)
        return
    blacklist.add(str(user.id))
    embed = discord.Embed(
        title="BLACKLIST",
        description=f"User: {user.mention}\nAlasan: {reason}",
        color=0xff0000,
        timestamp=datetime.now()
    )
    embed.set_footer(text=f"Oleh: {interaction.user.name}")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="unblacklist", description="Hapus user dari blacklist (Admin only)")
@app_commands.describe(user="User yang akan dihapus dari blacklist")
async def unblacklist(interaction: discord.Interaction, user: discord.User):
    staff_role = discord.utils.get(interaction.guild.roles, name=STAFF_ROLE_NAME)
    if staff_role not in interaction.user.roles:
        await interaction.response.send_message("Admin only!", ephemeral=True)
        return
    if str(user.id) in blacklist:
        blacklist.remove(str(user.id))
        await interaction.response.send_message(f"{user.mention} dihapus dari blacklist.")
    else:
        await interaction.response.send_message(f"{user.mention} tidak ada di blacklist.", ephemeral=True)

@bot.tree.command(name="catalog", description="Lihat semua item")
async def catalog(interaction: discord.Interaction):
    await interaction.response.defer()
    categories = {}
    for p in PRODUCTS:
        if p['category'] not in categories:
            categories[p['category']] = []
        categories[p['category']].append(p)
    embed = discord.Embed(
        title="CELLYN STORE - READY STOCK",
        description=f"Rate: 1 RBX = Rp {RATE:,}\nPayment: QRIS / DANA / BCA",
        color=0x00ff00
    )
    for cat, items in categories.items():
        value = ""
        for item in items[:5]:
            value += f"{item['name']} - Rp {item['price']:,}\n"
        embed.add_field(name=cat, value=value or "-", inline=False)
    view = discord.ui.View()
    for cat in categories.keys():
        view.add_item(discord.ui.Button(
            label=f"BUY {cat}", 
            style=discord.ButtonStyle.primary, 
            custom_id=f"buy_{cat}"
        ))
    await interaction.followup.send(embed=embed, view=view)

@bot.tree.command(name="rate", description="Cek rate Robux")
async def rate_cmd(interaction: discord.Interaction):
    await interaction.response.send_message(f"1 RBX = Rp {RATE:,}")

@bot.tree.command(name="setrate", description="Update rate Robux (Admin only)")
@app_commands.describe(rate="1 RBX = berapa IDR?")
async def setrate(interaction: discord.Interaction, rate: int):
    staff_role = discord.utils.get(interaction.guild.roles, name=STAFF_ROLE_NAME)
    if staff_role not in interaction.user.roles:
        await interaction.response.send_message("Admin only!", ephemeral=True)
        return
    global RATE
    RATE = rate
    await interaction.response.send_message(f"Rate updated: 1 RBX = Rp {rate:,}")

@bot.tree.command(name="uploadqris", description="Upload QRIS (Admin only)")
@app_commands.describe(image="Upload file gambar QR code")
async def upload_qris(interaction: discord.Interaction, image: discord.Attachment):
    staff_role = discord.utils.get(interaction.guild.roles, name=STAFF_ROLE_NAME)
    if staff_role not in interaction.user.roles:
        await interaction.response.send_message("Admin only!", ephemeral=True)
        return
    if not image.content_type.startswith('image/'):
        await interaction.response.send_message("File harus gambar!", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    qr_channel = discord.utils.get(interaction.guild.channels, name="qr-code")
    if not qr_channel:
        qr_channel = await interaction.guild.create_text_channel(
            name="qr-code",
            overwrites={
                interaction.guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=False),
                interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }
        )
    embed = discord.Embed(title="QRIS PAYMENT", color=0x00ff00)
    embed.set_image(url=image.url)
    embed.set_footer(text=f"Uploaded by {interaction.user.name}")
    await qr_channel.send(embed=embed)
    await interaction.followup.send(f"QRIS uploaded to {qr_channel.mention}", ephemeral=True)

@bot.tree.command(name="qris", description="Lihat QR code")
async def cek_qris(interaction: discord.Interaction):
    qr_channel = discord.utils.get(interaction.guild.channels, name="qr-code")
    if not qr_channel:
        await interaction.response.send_message("QR code tidak tersedia!", ephemeral=True)
        return
    async for msg in qr_channel.history(limit=10):
        if msg.author == bot.user and msg.embeds:
            await interaction.response.send_message(embed=msg.embeds[0])
            return
    await interaction.response.send_message("QR code tidak ditemukan!", ephemeral=True)

@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type != discord.InteractionType.component:
        return
    custom_id = interaction.data.get('custom_id', '')
    if str(interaction.user.id) in blacklist:
        await interaction.response.send_message("Kamu diblacklist dari CELLYN STORE.", ephemeral=True)
        return
    if custom_id.startswith('buy_'):
        category = custom_id.replace('buy_', '')
        items = [p for p in PRODUCTS if p['category'] == category]
        embed = discord.Embed(title=category, description="Pilih item:", color=0x3498db)
        view = discord.ui.View()
        for item in items[:10]:
            view.add_item(discord.ui.Button(
                label=f"{item['name'][:50]} - Rp {item['price']:,}",
                style=discord.ButtonStyle.secondary,
                custom_id=f"item_{item['id']}"
            ))
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    elif custom_id.startswith('item_'):
        item_id = int(custom_id.replace('item_', ''))
        item = next((p for p in PRODUCTS if p['id'] == item_id), None)
        if not item:
            await interaction.response.send_message("Item tidak ditemukan!", ephemeral=True)
            return
        if str(interaction.user.id) in blacklist:
            await interaction.response.send_message("Kamu diblacklist!", ephemeral=True)
            return
        user = interaction.user
        guild = interaction.guild
        for t in active_tickets.values():
            if t['user_id'] == str(user.id) and t['status'] == 'OPEN':
                await interaction.response.send_message("Kamu masih punya tiket aktif! Gunakan !cancel", ephemeral=True)
                return
        user_tickets = [t for t in active_tickets.values() if t['user_id'] == str(user.id)]
        if len(user_tickets) >= 3:
            await interaction.response.send_message("Maksimal 3 tiket aktif!", ephemeral=True)
            return
        category = discord.utils.get(guild.categories, name="TICKETS")
        if not category:
            category = await guild.create_category("TICKETS")
        channel = await guild.create_text_channel(
            name=f"ticket-{user.name}-{random.randint(100,999)}",
            category=category,
            overwrites={
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }
        )
        ticket = {
            'channel_id': str(channel.id),
            'user_id': str(user.id),
            'item_id': item['id'],
            'item_name': item['name'],
            'price': item['price'],
            'status': 'OPEN',
            'payment_method': None,
            'created_at': datetime.now()
        }
        active_tickets[str(channel.id)] = ticket
        embed = discord.Embed(title="TICKET PEMBELIAN", color=0xffa500)
        embed.description = f"Item: {item['name']}\nHarga: Rp {item['price']:,}"
        embed.add_field(name="Payment Method", value="1. QRIS\n2. DANA\n3. BCA", inline=False)
        embed.add_field(name="Cancel", value="Type !cancel to cancel", inline=False)
        await channel.send(f"Halo {user.mention}!", embed=embed)
        await interaction.response.send_message(f"Ticket created: {channel.mention}", ephemeral=True)
    elif custom_id == "confirm_payment":
        channel_id = str(interaction.channel.id)
        if channel_id not in active_tickets:
            await interaction.response.send_message("Ticket tidak ditemukan!", ephemeral=True)
            return
        staff_role = discord.utils.get(interaction.guild.roles, name=STAFF_ROLE_NAME)
        if staff_role not in interaction.user.roles:
            await interaction.response.send_message("Admin only!", ephemeral=True)
            return
        ticket = active_tickets[channel_id]
        ticket['status'] = 'CONFIRMED'
        ticket['admin_id'] = str(interaction.user.id)
        invoice_num = await send_invoice(interaction.guild, ticket)
        embed = discord.Embed(
            title="PAYMENT CONFIRMED",
            description=f"Item: {ticket['item_name']}\nInvoice: `{invoice_num}`\nTerima kasih telah berbelanja!",
            color=0x00ff00
        )
        embed.set_footer(text="CELLYN STORE")
        await interaction.channel.send(embed=embed)
        await interaction.response.send_message("Ticket akan ditutup dalam 5 detik...", ephemeral=True)
        import asyncio
        await asyncio.sleep(5)
        if channel_id in active_tickets:
            del active_tickets[channel_id]
        await interaction.channel.delete()

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if str(message.author.id) in blacklist:
        return
    if message.content.lower() == '!cancel' and message.channel.name and message.channel.name.startswith('ticket-'):
        channel_id = str(message.channel.id)
        if channel_id in active_tickets and active_tickets[channel_id]['status'] == 'OPEN':
            ticket = active_tickets[channel_id]
            staff_role = discord.utils.get(message.guild.roles, name=STAFF_ROLE_NAME)
            if str(message.author.id) == ticket['user_id'] or staff_role in message.author.roles:
                ticket['status'] = 'CANCELLED'
                await me
