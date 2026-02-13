import discord
from discord import app_commands
from discord.ext import commands
import os
import random
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# ========== KONFIGURASI ==========
STAFF_ROLE_NAME = "Admin Store"
DANA_NUMBER = "081266778093"
BCA_NUMBER = "8565330655"
RATE = 95
active_tickets = {}

# ========== ON READY ==========
@bot.event
async def on_ready():
    print(f"🔥 BOT READY! Login sebagai {bot.user}")
    print(f"✅ Bot aktif di {len(bot.guilds)} server")
    print(f"👮 Role Staff: {STAFF_ROLE_NAME}")
    print(f"💳 DANA: {DANA_NUMBER}")
    print(f"🏦 BCA: {BCA_NUMBER}")
    
    try:
        synced = await bot.tree.sync()
        print(f"✅ Slash commands: {len(synced)} commands")
        for cmd in synced:
            print(f"   - /{cmd.name}")
    except Exception as e:
        print(f"❌ Error sync: {e}")

# ========== LOG PUBLIK ==========
async def get_public_log_channel(guild):
    channel = discord.utils.get(guild.channels, name="✅ transaksi-sukses")
    if not channel:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=False),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        channel = await guild.create_text_channel(
            name="✅ transaksi-sukses",
            overwrites=overwrites,
            topic="✅ TRANSAKSI BERHASIL - BUKTI PEMBAYARAN"
        )
    return channel

async def send_success_log(guild, ticket_data):
    channel = await get_public_log_channel(guild)
    user = guild.get_member(int(ticket_data['user_id']))
    
    # Format nama buyer
    buyer_name = user.display_name if user else "Unknown"
    buyer_mention = user.mention if user else "Unknown"
    
    embed = discord.Embed(
        title="🔔 TRANSAKSI BERHASIL",
        color=0x00ff00,
        timestamp=datetime.now()
    )
    embed.add_field(name="👤 Buyer", value=f"{buyer_name}\n{buyer_mention}", inline=True)
    embed.add_field(name="🛒 Item", value=ticket_data['item_name'], inline=True)
    embed.add_field(name="💰 Harga", value=f"Rp {ticket_data['price']:,}", inline=True)
    embed.add_field(name="💳 Metode", value=ticket_data.get('payment_method', '-'), inline=True)
    embed.set_footer(text="CELLYN STORE")
    await channel.send(embed=embed)

# ========== DATA PRODUK - HARGA UPDATE ==========
PRODUCTS = [
    # LIMITED SKIN - HARGA UPDATE
    {"id": 1, "name": "CRESCENDO SCYTHE", "category": "LIMITED SKIN", "price": 80000},  # 🔴 75K -> 80K
    {"id": 2, "name": "CHROMATIC KATANA", "category": "LIMITED SKIN", "price": 85000},
    {"id": 3, "name": "MAGMA SURFBOARD", "category": "LIMITED SKIN", "price": 38000},   # 🔴 35K -> 38K
    # GAMEPASS
    {"id": 4, "name": "VIP + LUCK", "category": "GAMEPASS", "price": 40000},
    {"id": 5, "name": "MUTATION", "category": "GAMEPASS", "price": 25000},
    {"id": 6, "name": "ADVANCED LUCK", "category": "GAMEPASS", "price": 45000},
    {"id": 7, "name": "EXTRA LUCK", "category": "GAMEPASS", "price": 21000},
    {"id": 8, "name": "DOUBLE XP", "category": "GAMEPASS", "price": 18000},
    {"id": 9, "name": "SELL ANYWHERE", "category": "GAMEPASS", "price": 28000},
    {"id": 10, "name": "SMALL LUCK", "category": "GAMEPASS", "price": 5000},
    {"id": 11, "name": "HYPERBOATPACK", "category": "GAMEPASS", "price": 85000},
    # CRATE
    {"id": 12, "name": "PIRATE CRATE 1X", "category": "CRATE", "price": 10000},
    {"id": 13, "name": "PIRATE CRATE 5X", "category": "CRATE", "price": 48000},
    {"id": 14, "name": "ELDERWOOD CRATE 1X", "category": "CRATE", "price": 9000},
    {"id": 15, "name": "ELDERWOOD CRATE 5X", "category": "CRATE", "price": 42000},
    # BOOST
    {"id": 16, "name": "🍀 SERVER LUCK X2", "category": "BOOST", "price": 10000},
    {"id": 17, "name": "🍀 SERVER LUCK X4", "category": "BOOST", "price": 38000},
    {"id": 18, "name": "🍀 SERVER LUCK X8", "category": "BOOST", "price": 73000},
    {"id": 19, "name": "🍀 X8 3 JAM", "category": "BOOST", "price": 73000},
    {"id": 20, "name": "🍀 X8 6 JAM", "category": "BOOST", "price": 115000},
    {"id": 21, "name": "🍀 X8 12 JAM", "category": "BOOST", "price": 215000},
    {"id": 22, "name": "🍀 X8 24 JAM", "category": "BOOST", "price": 410000},
    # NITRO - HARGA UPDATE
    {"id": 23, "name": "NITRO BOOST 1 MONTH", "category": "NITRO", "price": 50000},     # 🔴 75K -> 50K
    {"id": 24, "name": "NITRO BOOST 3 MONTH", "category": "NITRO", "price": 70000},
    {"id": 25, "name": "NITRO BOOST 1 YEAR", "category": "NITRO", "price": 650000},
    # RED FINGER
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

# ========== SLASH COMMANDS ==========
@bot.tree.command(name="catalog", description="📋 Lihat semua item")
async def catalog(interaction: discord.Interaction):
    await interaction.response.defer()
    
    categories = {}
    for p in PRODUCTS:
        if p['category'] not in categories:
            categories[p['category']] = []
        categories[p['category']].append(p)
    
    embed = discord.Embed(
        title="🎣 FISH IT STORE — READY GIG",
        description=f"💎 Rate: 1 RBX = {RATE:,} IDR\n💳 Payment: QRIS / DANA / BCA\n━━━━━━━━━━━━━━━━━",
        color=0x00ff00
    )
    
    emoji = {"LIMITED SKIN": "✨", "GAMEPASS": "🎮", "CRATE": "📦", "BOOST": "🚀", "NITRO": "🎁", "RED FINGER": "📱"}
    
    for cat, items in categories.items():
        value = ""
        for item in items[:5]:
            value += f"**{item['name'][:30]}** — Rp {item['price']:,}\n"
        embed.add_field(name=f"{emoji.get(cat, '•')} {cat}", value=value or "•", inline=False)
    
    view = discord.ui.View()
    for cat in categories.keys():
        view.add_item(discord.ui.Button(label=f"🛒 {cat}", style=discord.ButtonStyle.primary, custom_id=f"buy_{cat}"))
    
    await interaction.followup.send(embed=embed, view=view)

@bot.tree.command(name="rate", description="💎 Cek rate Robux")
async def rate_cmd(interaction: discord.Interaction):
    await interaction.response.send_message(f"💎 1 RBX = {RATE:,} IDR")

@bot.tree.command(name="setrate", description="💰 Update rate Robux (Admin only)")
@app_commands.describe(rate="1 RBX = berapa IDR?")
async def setrate(interaction: discord.Interaction, rate: int):
    staff_role = discord.utils.get(interaction.guild.roles, name=STAFF_ROLE_NAME)
    if staff_role not in interaction.user.roles:
        await interaction.response.send_message("❌ Hanya Admin Store!", ephemeral=True)
        return
    global RATE
    RATE = rate
    await interaction.response.send_message(f"✅ Rate: 1 RBX = {rate:,} IDR")

@bot.tree.command(name="uploadqris", description="📤 Upload QRIS (Admin only)")
@app_commands.describe(gambar="Upload file gambar QR code")
async def upload_qris(interaction: discord.Interaction, gambar: discord.Attachment):
    staff_role = discord.utils.get(interaction.guild.roles, name=STAFF_ROLE_NAME)
    if staff_role not in interaction.user.roles:
        await interaction.response.send_message("❌ Hanya Admin Store!", ephemeral=True)
        return
    
    if not gambar.content_type.startswith('image/'):
        await interaction.response.send_message("❌ File harus gambar!", ephemeral=True)
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
    
    embed = discord.Embed(title="✅ QRIS PEMBAYARAN", color=0x00ff00)
    embed.set_image(url=gambar.url)
    embed.set_footer(text=f"Upload by {interaction.user.name}")
    
    await qr_channel.send(embed=embed)
    await interaction.followup.send(f"✅ QRIS di-upload ke {qr_channel.mention}", ephemeral=True)

@bot.tree.command(name="qris", description="📌 Lihat QR code")
async def cek_qris(interaction: discord.Interaction):
    qr_channel = discord.utils.get(interaction.guild.channels, name="qr-code")
    if not qr_channel:
        await interaction.response.send_message("❌ Belum ada QR code!", ephemeral=True)
        return
    
    async for msg in qr_channel.history(limit=10):
        if msg.author == bot.user and msg.embeds:
            await interaction.response.send_message(embed=msg.embeds[0])
            return
    
    await interaction.response.send_message("❌ QR code tidak ditemukan!", ephemeral=True)

# ========== HANDLER TIKET ==========
@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type != discord.InteractionType.component:
        return
    
    custom_id = interaction.data.get('custom_id', '')
    
    if custom_id.startswith('buy_'):
        category = custom_id.replace('buy_', '')
        items = [p for p in PRODUCTS if p['category'] == category]
        embed = discord.Embed(title=f"🛒 {category}", description="Pilih item:", color=0x3498db)
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
            await interaction.response.send_message("❌ Item tidak ditemukan!", ephemeral=True)
            return
        
        user = interaction.user
        guild = interaction.guild
        
        for t in active_tickets.values():
            if t['user_id'] == str(user.id) and t['status'] == 'OPEN':
                await interaction.response.send_message("❌ Kamu masih punya tiket aktif! Ketik `!cancel`", ephemeral=True)
                return
        
        cat = discord.utils.get(guild.categories, name="🎫 TICKETS")
        if not cat:
            cat = await guild.create_category("🎫 TICKETS")
        
        channel = await guild.create_text_channel(
            name=f"ticket-{user.name}-{random.randint(100,999)}",
            category=cat,
            overwrites={
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }
        )
        
        ticket = {
            'channel_id': str(channel.id),
            'user_id': str(user.id),
            'item_name': item['name'],
            'price': item['price'],
            'status': 'OPEN',
            'payment_method': None
        }
        active_tickets[str(channel.id)] = ticket
        
        embed = discord.Embed(title="🧾 TIKET PEMBELIAN", color=0xffa500)
        embed.description = f"**Item:** {item['name']}\n**Harga:** Rp {item['price']:,}"
        embed.add_field(name="💳 Metode", value="```\n1. QRIS\n2. DANA\n3. BCA\n```")
        embed.add_field(name="❌ Cancel", value="Ketik `!cancel` untuk batalkan")
        await channel.send(f"👋 Halo {user.mention}!", embed=embed)
        
        await interaction.response.send_message(f"✅ Tiket dibuat! Cek {channel.mention}", ephemeral=True)
    
    # ===== CONFIRM PAYMENT - KHUSUS ADMIN =====
    elif custom_id == "confirm_payment":
        channel_id = str(interaction.channel.id)
        
        if channel_id not in active_tickets:
            await interaction.response.send_message("❌ Tiket tidak ditemukan!", ephemeral=True)
            return
        
        # 🔴 CEK ADMIN - HANYA ADMIN YANG BISA KLIK!
        staff_role = discord.utils.get(interaction.guild.roles, name=STAFF_ROLE_NAME)
        if staff_role not in interaction.user.roles:
            await interaction.response.send_message("❌ Hanya **Admin Store** yang bisa konfirmasi pembayaran!", ephemeral=True)
            return
        
        ticket = active_tickets[channel_id]
        ticket['status'] = 'CONFIRMED'
        
        # Kirim log ke channel publik
        await send_success_log(interaction.guild, ticket)
        
        embed = discord.Embed(
            title="✅ PEMBAYARAN DIKONFIRMASI!",
            description=f"**Item:** {ticket['item_name']}\nTerima kasih sudah belanja!\n\n📋 Transaksi telah dicatat di channel ✅ transaksi-sukses",
            color=0x00ff00
        )
        await interaction.channel.send(embed=embed)
        
        await interaction.response.send_message("✅ Tiket akan ditutup dalam 5 detik...", ephemeral=True)
        
        import asyncio
        await asyncio.sleep(5)
        
        if channel_id in active_tickets:
            del active_tickets[channel_id]
        await interaction.channel.delete()

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    # ===== CANCEL TICKET =====
    if message.content.lower() == '!cancel' and message.channel.name and message.channel.name.startswith('ticket-'):
        channel_id = str(message.channel.id)
        if channel_id in active_tickets and active_tickets[channel_id]['status'] == 'OPEN':
            ticket = active_tickets[channel_id]
            staff_role = discord.utils.get(message.guild.roles, name=STAFF_ROLE_NAME)
            
            if str(message.author.id) == ticket['user_id'] or staff_role in message.author.roles:
                ticket['status'] = 'CANCELLED'
                await message.channel.send("❌ Transaksi dibatalkan. Tiket ditutup!")
                import asyncio
                await asyncio.sleep(3)
                del active_tickets[channel_id]
                await message.channel.delete()
                return
    
    # ===== PAYMENT METHOD =====
    if message.channel.name and message.channel.name.startswith('ticket-'):
        channel_id = str(message.channel.id)
        if channel_id in active_tickets and active_tickets[channel_id]['status'] == 'OPEN':
            ticket = active_tickets[channel_id]
            
            if message.content.strip() in ['1','2','3']:
                methods = ['QRIS', 'DANA', 'BCA']
                method = methods[int(message.content) - 1]
                ticket['payment_method'] = method
                
                if method == 'QRIS':
                    await message.channel.send("📌 **QRIS:** Gunakan perintah `/qris` untuk melihat QR code pembayaran")
                elif method == 'DANA':
                    embed = discord.Embed(
                        title="✅ DANA",
                        description=f"**Transfer ke:**\n`{DANA_NUMBER}`",
                        color=0x00ff00
                    )
                    embed.set_footer(text="CELLYN STORE")
                    await message.channel.send(embed=embed)
                elif method == 'BCA':
                    embed = discord.Embed(
                        title="✅ BCA",
                        description=f"**Transfer ke:**\n`{BCA_NUMBER}`",
                        color=0x00ff00
                    )
                    embed.set_footer(text="CELLYN STORE")
                    await message.channel.send(embed=embed)
                
                # 🔴 TOMBOL CONFIRM - TAPI NANTI ADMIN YANG KLIK
                view = discord.ui.View()
                view.add_item(discord.ui.Button(
                    label="💰 Sudah Transfer",
                    style=discord.ButtonStyle.success,
                    custom_id="confirm_payment"
                ))
                await message.channel.send("**Sudah transfer?**\n*Tombol ini hanya bisa diklik oleh **Admin Store***", view=view)
                
                # Tag staff
                staff_role = discord.utils.get(message.guild.roles, name=STAFF_ROLE_NAME)
                if staff_role:
                    await message.channel.send(f"{staff_role.mention} Ada pembayaran baru menunggu konfirmasi!")
    
    await bot.process_commands(message)

# ========== RUN ==========
if __name__ == "__main__":
    if not TOKEN:
        print("❌ ERROR: DISCORD_TOKEN tidak ditemukan di .env!")
        exit()
    print("🔥 Memulai bot CELLYN STORE...")
    print(f"👮 Role Staff: {STAFF_ROLE_NAME}")
    print(f"💰 Harga UPDATE: Crescendo 80K, Magma 38K, Nitro 1B 50K")
    bot.run(TOKEN)
