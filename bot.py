import discord
from discord import app_commands
from discord.ext import commands
import os
import random
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

STAFF_ROLE_NAME = "🔰 Admin Store"
DANA_NUMBER = "081266778093"
BCA_NUMBER = "8565330655"
RATE = 85

active_tickets = {}
transactions = []
invoice_counter = 1000
blacklist = set()
user_transaction_count = {}
LOG_CHANNEL_ID = None

PRODUCTS = []

def save_products():
    with open('products.json', 'w') as f:
        json.dump(PRODUCTS, f, indent=2)

def load_products():
    global PRODUCTS
    try:
        with open('products.json', 'r') as f:
            PRODUCTS = json.load(f)
        print("✅ Products loaded from products.json")
    except FileNotFoundError:
        print("📝 products.json not found, using default PRODUCTS")
        save_products()

async def get_log_channel(guild):
    global LOG_CHANNEL_ID
    if LOG_CHANNEL_ID:
        channel = guild.get_channel(LOG_CHANNEL_ID)
        if channel:
            return channel
    channel = discord.utils.get(guild.channels, name="🧾┃log-transaksisi")
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
    
    if not transaction_data.get('fake', False):
        try:
            buyer_role = discord.utils.get(guild.roles, name="👑 Royal Customer")
            if buyer_role and user:
                if buyer_role not in user.roles:
                    await user.add_roles(buyer_role)
                    print(f"✅ Role {buyer_role.name} diberikan ke {user.name}")
        except Exception as e:
            print(f"❌ Error gift role: {e}")
    
    items_list = ""
    for item in transaction_data['items']:
        items_list += f"{item['qty']}x {item['name']} = Rp {item['price'] * item['qty']:,}\n"
    
    embed = discord.Embed(
        title="🔔 TRANSAKSI BERHASIL 🔔",
        color=0x00ff00,
        timestamp=datetime.now()
    )
    
    embed.add_field(name="📋 NO. INVOICE", value=f"`{invoice_num}`", inline=False)
    embed.add_field(name="👑 CUSTOMER", value=f"{user_name}\n<@{transaction_data['user_id']}>", inline=True)
    embed.add_field(name="📦 ITEMS", value=items_list, inline=False)
    embed.add_field(name="💰 TOTAL", value=f"Rp {transaction_data['total_price']:,}", inline=True)
    embed.add_field(name="💳 METODE", value=transaction_data.get('payment_method', '-'), inline=True)
    
    if transaction_data.get('admin_id'):
        admin = guild.get_member(int(transaction_data['admin_id']))
        if admin:
            embed.add_field(name="🛡️ ADMIN", value=admin.mention, inline=True)
    
    if transaction_data.get('fake', False):
        marker = "​"  
        footer_text = f"✨ Terima kasih telah bertransaksi ✨\nCELLYN STORE{marker}"
    else:
        footer_text = "✨ Terima kasih telah bertransaksi ✨\nCELLYN STORE"
    
    embed.set_footer(text=footer_text)
    
    await channel.send(embed=embed)
    return invoice_num

def calculate_total(items):
    return sum(item['price'] * item['qty'] for item in items)

def format_items(items):
    if not items:
        return "Tidak ada item"
    return "\n".join([f"{item['qty']}x {item['name']} = Rp {item['price']*item['qty']:,}" for item in items])

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
        items_short = ", ".join([f"{i['qty']}x {i['name'][:15]}" for i in t['items'][:2]])
        if len(t['items']) > 2:
            items_short += f" +{len(t['items'])-2} lagi"
        embed.add_field(
            name=f"{t['invoice']} - {date_str}",
            value=f"{items_short} | Rp {t['total_price']:,} | {t.get('payment_method', '-')}",
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
    total_revenue = sum(t['total_price'] for t in transactions)
    today_revenue = sum(t['total_price'] for t in today_trans)
    week_revenue = sum(t['total_price'] for t in week_trans)
    month_revenue = sum(t['total_price'] for t in month_trans)
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
    category_order = ["LIMITED SKIN", "GAMEPASS", "CRATE", "BOOST", "NITRO", "RED FINGER", "MIDMAN", "LAINNYA"]
    for cat in category_order:
        if cat in categories:
            items = categories[cat][:5]
            value = ""
            for item in items:
                value += f"ID:{item['id']} - {item['name']} - Rp {item['price']:,}\n"
            embed.add_field(name=cat, value=value or "-", inline=False)
    view = discord.ui.View()
    for cat in category_order:
        if cat in categories:
            view.add_item(discord.ui.Button(
                label=f"BUY {cat}", 
                style=discord.ButtonStyle.primary, 
                custom_id=f"buy_{cat}"
            ))
    await interaction.response.send_message(embed=embed, view=view)

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
@bot.tree.command(name="addproduct", description="➕ Tambah product baru (Admin only)")
@app_commands.describe(name="Nama item", category="Kategori", price="Harga")
async def add_item(interaction: discord.Interaction, name: str, category: str, price: int):
    staff_role = discord.utils.get(interaction.guild.roles, name=STAFF_ROLE_NAME)
    if staff_role not in interaction.user.roles:
        await interaction.response.send_message("❌ Admin only!", ephemeral=True)
        return
    new_id = max(item['id'] for item in PRODUCTS) + 1
    PRODUCTS.append({
        "id": new_id,
        "name": name,
        "category": category,
        "price": price
    })
    save_products()
    embed = discord.Embed(
        title="✅ ITEM DITAMBAHKAN",
        description=f"**ID:** {new_id}\n**Nama:** {name}\n**Kategori:** {category}\n**Harga:** Rp {price:,}",
        color=0x00ff00
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="editprice", description="💰 Ubah harga item (Admin only)")
@app_commands.describe(item_id="ID item", new_price="Harga baru")
async def edit_price(interaction: discord.Interaction, item_id: int, new_price: int):
    staff_role = discord.utils.get(interaction.guild.roles, name=STAFF_ROLE_NAME)
    if staff_role not in interaction.user.roles:
        await interaction.response.send_message("❌ Admin only!", ephemeral=True)
        return
    item = next((p for p in PRODUCTS if p['id'] == item_id), None)
    if not item:
        await interaction.response.send_message("❌ Item tidak ditemukan!", ephemeral=True)
        return
    old_price = item['price']
    item['price'] = new_price
    save_products()
    embed = discord.Embed(
        title="💰 HARGA DIUPDATE",
        description=f"**Item:** {item['name']} (ID: {item_id})\n**Harga lama:** Rp {old_price:,}\n**Harga baru:** Rp {new_price:,}",
        color=0x00ff00
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="editname", description="📝 Ubah nama item (Admin only)")
@app_commands.describe(item_id="ID item", new_name="Nama baru")
async def edit_name(interaction: discord.Interaction, item_id: int, new_name: str):
    staff_role = discord.utils.get(interaction.guild.roles, name=STAFF_ROLE_NAME)
    if staff_role not in interaction.user.roles:
        await interaction.response.send_message("❌ Admin only!", ephemeral=True)
        return
    item = next((p for p in PRODUCTS if p['id'] == item_id), None)
    if not item:
        await interaction.response.send_message("❌ Item tidak ditemukan!", ephemeral=True)
        return
    old_name = item['name']
    item['name'] = new_name
    save_products()
    embed = discord.Embed(
        title="📝 NAMA DIUPDATE",
        description=f"**ID:** {item_id}\n**Nama lama:** {old_name}\n**Nama baru:** {new_name}",
        color=0x00ff00
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="deleteitem", description="🗑️ Hapus item (Admin only)")
@app_commands.describe(item_id="ID item yang mau dihapus")
async def delete_item(interaction: discord.Interaction, item_id: int):
    staff_role = discord.utils.get(interaction.guild.roles, name=STAFF_ROLE_NAME)
    if staff_role not in interaction.user.roles:
        await interaction.response.send_message("❌ Admin only!", ephemeral=True)
        return
    item = next((p for p in PRODUCTS if p['id'] == item_id), None)
    if not item:
        await interaction.response.send_message("❌ Item tidak ditemukan!", ephemeral=True)
        return
    PRODUCTS.remove(item)
    save_products()
    embed = discord.Embed(
        title="🗑️ ITEM DIHAPUS",
        description=f"**Item:** {item['name']} (ID: {item_id})",
        color=0xff0000
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="listitems", description="📋 Lihat semua item (dikirim ke DM)")
async def list_items_admin(interaction: discord.Interaction):
    staff_role = discord.utils.get(interaction.guild.roles, name=STAFF_ROLE_NAME)
    if staff_role not in interaction.user.roles:
        await interaction.response.send_message("❌ Admin only!", ephemeral=True)
        return
    await interaction.response.send_message("📋 Mengirim daftar item ke DM...", ephemeral=True)
    categories = {}
    for p in PRODUCTS:
        if p['category'] not in categories:
            categories[p['category']] = []
        categories[p['category']].append(p)
    embed = discord.Embed(
        title="📋 DAFTAR ITEM CELLYN STORE",
        color=0x00ff00,
        timestamp=datetime.now()
    )
    for cat, items in categories.items():
        value = ""
        for item in items:
            value += f"ID:{item['id']} - {item['name']} - Rp {item['price']:,}\n"
        embed.add_field(name=cat, value=value[:1024], inline=False)
    await interaction.user.send(embed=embed)

@bot.tree.command(name="fakeinvoice", description="🧪 Generate fake invoice (Admin only)")
@app_commands.describe(jumlah="Jumlah invoice (1-5)")
async def fake_invoice(interaction: discord.Interaction, jumlah: int = 1):
    # Cek admin
    staff_role = discord.utils.get(interaction.guild.roles, name=STAFF_ROLE_NAME)
    if staff_role not in interaction.user.roles:
        await interaction.response.send_message("❌ Admin only!", ephemeral=True)
        return
    
    if jumlah < 1 or jumlah > 5:
        await interaction.response.send_message("❌ Jumlah minimal 1, maksimal 5", ephemeral=True)
        return
    
    await interaction.response.send_message(f"🧪 Generating {jumlah} fake invoice...", ephemeral=True)
    
    # ===== 125+ NAMA BUYER RANDOM =====
    buyer_names = [
        # Game Related (30)
        "FishHunter99", "SharkBait", "TunaMaster", "SalmonSlayer", "BassPro",
        "FishermanJoe", "NetCaster", "RodMaster", "LureKing", "BaitTaker",
        "DeepSeaDiver", "CoralReaper", "OceanExplorer", "WaveRider", "TideHunter",
        "AnglerPro", "FishFinder", "GillHunter", "FinCollector", "ScaleSnatcher",
        "PirateKing", "ShipCaptain", "SailorMoon", "BoatDriver", "AnchorDrop",
        "FishWhisperer", "WaterBender", "SeaLord", "OceanMaster", "TidalWave",
        
        # Katana / Samurai (20)
        "KatanaMaster", "SamuraiJack", "BladeRunner", "SwordSaint", "EdgeLord",
        "SlashKing", "CutMaster", "BladeDancer", "NinjaWarrior", "ShogunRuler",
        "RoninSpirit", "BushidoCode", "KatanaSlasher", "BladeRunner2", "SwordCollector",
        "EdgeHunter", "SlashMaster", "CutThroat", "BladeMaster", "NinjaStar",
        
        # Nitro / Premium (20)
        "NitroKing", "BoostMaster", "PremiumUser", "DiscordElite", "ServerBooster",
        "NitroHunter", "BoostCollector", "PremiumHunter", "EliteMember", "DiscordPro",
        "NitroLover", "BoostKing", "PremiumPlus", "DiscordAddict", "ServerLover",
        "NitroMaster", "BoostHunter", "PremiumSeeker", "EliteHunter", "DiscordFan",
        
        # Red Finger (15)
        "RFHunter", "VIPMaster", "KVIPSeeker", "SVIPKing", "XVIPLord",
        "RedFingerPro", "FingerMaster", "RedCollector", "VIPHunter", "KVIPHunter",
        "SVIPMaster", "XVIPCollector", "RedFingerFan", "FingerKing", "RedElite",
        
        # Generic Keren (25)
        "ShadowHunter", "DarkKnight", "LightBringer", "StarCollector", "MoonWalker",
        "SunChaser", "CloudRider", "StormBringer", "ThunderStrike", "LightningBolt",
        "NightOwl", "EarlyBird", "NightRider", "DayDreamer", "StarGazer",
        "CosmicHunter", "GalaxyMaster", "UnicornRider", "PhoenixFire", "DragonSlayer",
        "TigerClaw", "EagleEye", "WolfPack", "BearHug", "LionHeart",
        
        # Tambahan Tech (15)
        "NeonNights", "CyberPunk", "RetroGamer", "PixelWarrior", "BitHunter",
        "DataMiner", "CodeBreaker", "LogicBomb", "SyntaxError", "NullPointer",
        "InfiniteLoop", "StackOverflow", "BinaryKing", "HexMaster", "RootAccess"
    ]
    # Total: 125 nama
    
    # Metode pembayaran dengan proporsi realistik
    methods = ['DANA', 'BCA', 'QRIS']
    method_weights = [0.5, 0.3, 0.2]  # 50% DANA, 30% BCA, 20% QRIS
    
    for _ in range(jumlah):
        # Random jumlah item dalam 1 transaksi (1-3 item)
        num_items = random.choices([1, 2, 3], weights=[0.6, 0.3, 0.1])[0]
        
        # Pilih item random dari PRODUCTS (tanpa duplikat)
        selected_items = random.sample(PRODUCTS, k=min(num_items, len(PRODUCTS)))
        
        # Random quantity per item (1-3)
        items = []
        for item in selected_items:
            qty = random.randint(1, 3)
            items.append({
                "id": item['id'],
                "name": item['name'],
                "price": item['price'],
                "qty": qty
            })
        
        # Hitung total
        total_price = sum(item['price'] * item['qty'] for item in items)
        
        # Pilih metode random
        method = random.choices(methods, weights=method_weights)[0]
        
        # Buat fake user ID (angka random panjang)
        fake_user_id = str(random.randint(100000000000000000, 999999999999999999))
        
        # Pilih nama buyer random dari 125 nama
        buyer_name = random.choice(buyer_names)
        
        # Kirim invoice ke channel log
        invoice_num = await send_invoice(interaction.guild, {
            'user_id': fake_user_id,
            'items': items,
            'total_price': total_price,
            'payment_method': method,
            'admin_id': str(interaction.user.id),
            'fake': True  # Tandai sebagai fake
        })
        
        # Log di console
        print(f"🧪 Fake invoice {invoice_num}: {buyer_name} - Rp {total_price:,} - {method}")
    
    await interaction.followup.send(f"✅ {jumlah} fake invoice berhasil dikirim ke channel log!", ephemeral=True)

@bot.tree.command(name="refreshcatalog", description="🔄 Refresh catalog tanpa restart (Admin only)")
async def refresh_catalog(interaction: discord.Interaction):
    staff_role = discord.utils.get(interaction.guild.roles, name=STAFF_ROLE_NAME)
    if staff_role not in interaction.user.roles:
        await interaction.response.send_message("❌ Admin only!", ephemeral=True)
        return
    load_products()
    embed = discord.Embed(
        title="🔄 CATALOG REFRESHED",
        description=f"Total item: {len(PRODUCTS)}",
        color=0x00ff00
    )
    await interaction.response.send_message(embed=embed)
@bot.tree.command(name="additem", description="➕ Tambah item ke tiket ini")
@app_commands.describe(item_id="ID item", qty="Jumlah (default 1)")
async def add_item_to_ticket(interaction: discord.Interaction, item_id: int, qty: int = 1):
    if not interaction.channel.name.startswith('ticket-'):
        await interaction.response.send_message("❌ Ini bukan channel tiket!", ephemeral=True)
        return
    channel_id = str(interaction.channel.id)
    if channel_id not in active_tickets or active_tickets[channel_id]['status'] != 'OPEN':
        await interaction.response.send_message("❌ Tiket tidak ditemukan atau sudah closed!", ephemeral=True)
        return
    item = next((p for p in PRODUCTS if p['id'] == item_id), None)
    if not item:
        await interaction.response.send_message("❌ Item tidak ditemukan!", ephemeral=True)
        return
    ticket = active_tickets[channel_id]
    staff_role = discord.utils.get(interaction.guild.roles, name=STAFF_ROLE_NAME)
    is_owner = str(interaction.user.id) == ticket['user_id']
    is_admin = staff_role in interaction.user.roles
    if not (is_owner or is_admin):
        await interaction.response.send_message("❌ Hanya pemilik tiket atau admin yang bisa nambah item!", ephemeral=True)
        return
    found = False
    for existing in ticket['items']:
        if existing['id'] == item_id:
            existing['qty'] += qty
            found = True
            break
    if not found:
        ticket['items'].append({
            "id": item['id'],
            "name": item['name'],
            "price": item['price'],
            "qty": qty
        })
    ticket['total_price'] = calculate_total(ticket['items'])
    embed = discord.Embed(
        title="➕ ITEM DITAMBAHKAN",
        description=f"**{qty}x {item['name']}** berhasil ditambahkan!",
        color=0x00ff00
    )
    embed.add_field(name="🛒 ITEMS SAAT INI", value=format_items(ticket['items']), inline=False)
    embed.add_field(name="💰 TOTAL", value=f"Rp {ticket['total_price']:,}", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="removeitem", description="➖ Hapus item dari tiket ini")
@app_commands.describe(item_id="ID item", qty="Jumlah yang dihapus (default semua)")
async def remove_item_from_ticket(interaction: discord.Interaction, item_id: int, qty: int = None):
    if not interaction.channel.name.startswith('ticket-'):
        await interaction.response.send_message("❌ Ini bukan channel tiket!", ephemeral=True)
        return
    channel_id = str(interaction.channel.id)
    if channel_id not in active_tickets or active_tickets[channel_id]['status'] != 'OPEN':
        await interaction.response.send_message("❌ Tiket tidak ditemukan!", ephemeral=True)
        return
    ticket = active_tickets[channel_id]
    staff_role = discord.utils.get(interaction.guild.roles, name=STAFF_ROLE_NAME)
    is_owner = str(interaction.user.id) == ticket['user_id']
    is_admin = staff_role in interaction.user.roles
    if not (is_owner or is_admin):
        await interaction.response.send_message("❌ Hanya pemilik tiket atau admin yang bisa hapus item!", ephemeral=True)
        return
    item_found = None
    item_index = None
    for i, item in enumerate(ticket['items']):
        if item['id'] == item_id:
            item_found = item
            item_index = i
            break
    if not item_found:
        await interaction.response.send_message("❌ Item tidak ditemukan di tiket ini!", ephemeral=True)
        return
    if qty is None or qty >= item_found['qty']:
        removed_item = ticket['items'].pop(item_index)
        removal_msg = f"✅ **{removed_item['qty']}x {removed_item['name']}** dihapus dari tiket!"
    else:
        ticket['items'][item_index]['qty'] -= qty
        removal_msg = f"✅ **{qty}x {item_found['name']}** dikurangi!\nSisa: {ticket['items'][item_index]['qty']}x"
    ticket['total_price'] = calculate_total(ticket['items'])
    if not ticket['items']:
        await interaction.channel.send("🔄 Tiket kosong, menutup tiket dalam 5 detik...")
        import asyncio
        await asyncio.sleep(5)
        del active_tickets[channel_id]
        await interaction.channel.delete()
        return
    embed = discord.Embed(
        title="➖ ITEM DIHAPUS",
        description=removal_msg,
        color=0xffa500
    )
    embed.add_field(name="🛒 ITEMS SAAT INI", value=format_items(ticket['items']), inline=False)
    embed.add_field(name="💰 TOTAL", value=f"Rp {ticket['total_price']:,}", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="items", description="📋 Lihat item di tiket ini")
async def list_items(interaction: discord.Interaction):
    if not interaction.channel.name.startswith('ticket-'):
        await interaction.response.send_message("❌ Ini bukan channel tiket!", ephemeral=True)
        return
    channel_id = str(interaction.channel.id)
    if channel_id not in active_tickets:
        await interaction.response.send_message("❌ Tiket tidak ditemukan!", ephemeral=True)
        return
    ticket = active_tickets[channel_id]
    embed = discord.Embed(
        title="🛒 DAFTAR ITEM",
        description=format_items(ticket['items']) or "Belum ada item",
        color=0x3498db
    )
    embed.add_field(name="💰 TOTAL", value=f"Rp {ticket['total_price']:,}", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)

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
        embed = discord.Embed(title=category, description="Pilih item (catat ID nya):", color=0x3498db)
        view = discord.ui.View()
        for item in items[:10]:
            view.add_item(discord.ui.Button(
                label=f"ID:{item['id']} - {item['name'][:30]} - Rp {item['price']:,}",
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
            'items': [{"id": item['id'], "name": item['name'], "price": item['price'], "qty": 1}],
            'total_price': item['price'],
            'status': 'OPEN',
            'payment_method': None,
            'created_at': datetime.now()
        }
        active_tickets[str(channel.id)] = ticket
        embed = discord.Embed(title="🧾 TICKET PEMBELIAN", color=0xffa500)
        embed.description = f"**Item:**\n1x {item['name']}\n**Harga:** Rp {item['price']:,}"
        embed.add_field(name="➕ NAMBAH ITEM", value="Gunakan `/additem [id] [jumlah]`", inline=False)
        embed.add_field(name="➖ HAPUS ITEM", value="Gunakan `/removeitem [id] [jumlah]`", inline=False)
        embed.add_field(name="📋 LIHAT ITEM", value="Gunakan `/items`", inline=False)
        embed.add_field(name="💳 PAYMENT", value="1. QRIS\n2. DANA\n3. BCA", inline=False)
        embed.add_field(name="❌ CANCEL", value="Ketik !cancel", inline=False)
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
        invoice_num = await send_invoice(interaction.guild, {
            'user_id': ticket['user_id'],
            'items': ticket['items'],
            'total_price': ticket['total_price'],
            'payment_method': ticket.get('payment_method'),
            'admin_id': str(interaction.user.id)
        })
        items_short = ", ".join([f"{i['qty']}x {i['name'][:15]}" for i in ticket['items'][:2]])
        if len(ticket['items']) > 2:
            items_short += f" +{len(ticket['items'])-2} lagi"
        embed = discord.Embed(
            title="✅ PAYMENT CONFIRMED",
            description=f"**Items:** {items_short}\n**Total: Rp {ticket['total_price']:,}**\nInvoice: `{invoice_num}`\nTerima kasih!",
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
                await message.channel.send("Transaksi dibatalkan. Ticket closed.")
                import asyncio
                await asyncio.sleep(3)
                del active_tickets[channel_id]
                await message.channel.delete()
                return
    if message.channel.name and message.channel.name.startswith('ticket-'):
        channel_id = str(message.channel.id)
        if channel_id in active_tickets and active_tickets[channel_id]['status'] == 'OPEN':
            ticket = active_tickets[channel_id]
            if message.content.strip() in ['1','2','3']:
                methods = ['QRIS', 'DANA', 'BCA']
                method = methods[int(message.content) - 1]
                ticket['payment_method'] = method
                total = ticket['total_price']
                if method == 'QRIS':
                    await message.channel.send("Gunakan /qris untuk melihat QR code")
                elif method == 'DANA':
                    embed = discord.Embed(
                        title="DANA",
                        description=f"Transfer ke:\n`{DANA_NUMBER}`\n\n**TOTAL: Rp {total:,}**",
                        color=0x00ff00
                    )
                    await message.channel.send(embed=embed)
                elif method == 'BCA':
                    embed = discord.Embed(
                        title="BCA",
                        description=f"Transfer ke:\n`{BCA_NUMBER}`\n\n**TOTAL: Rp {total:,}**",
                        color=0x00ff00
                    )
                    await message.channel.send(embed=embed)
                await message.channel.send(f"**🛒 ITEMS:**\n{format_items(ticket['items'])}\n**💰 TOTAL: Rp {total:,}**")
                view = discord.ui.View()
                view.add_item(discord.ui.Button(
                    label="PAID",
                    style=discord.ButtonStyle.success,
                    custom_id="confirm_payment"
                ))
                await message.channel.send("Sudah transfer? Klik tombol di bawah:", view=view)
                staff_role = discord.utils.get(message.guild.roles, name=STAFF_ROLE_NAME)
                if staff_role:
                    await message.channel.send(f"{staff_role.mention} Ada pembayaran baru!")
    await bot.process_commands(message)

@bot.event
async def on_ready():
    print(f"BOT READY - {bot.user}")
    print(f"Server: {len(bot.guilds)}")
    print(f"Staff Role: {STAFF_ROLE_NAME}")
    global LOG_CHANNEL_ID
    LOG_CHANNEL_ID = None
    load_products()
    try:
        synced = await bot.tree.sync()
        print(f"Commands: {len(synced)}")
        for cmd in synced:
            print(f"  - /{cmd.name}")
    except Exception as e:
        print(f"Sync error: {e}")

if __name__ == "__main__":
    if not TOKEN:
        print("ERROR: DISCORD_TOKEN not found in .env")
        exit()
    print("Starting CELLYN STORE BOT...")
    print("Fitur: Multi-item, Additem, Removeitem, Items, Custom Invoice, Product Management")
    bot.run(TOKEN)
