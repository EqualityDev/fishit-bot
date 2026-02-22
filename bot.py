import discord
from discord import app_commands
from discord.ext import commands
import os
import random
import json
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv
import sqlite3
import aiosqlite
import shutil
import asyncio
import csv
import io
import logging
import html

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

STAFF_ROLE_NAME = "Admin Store"
DANA_NUMBER = "081266778093"
BCA_NUMBER = "8565330655"
RATE = 85

active_tickets = {}
transactions = []
invoice_counter = 1000
blacklist = set()
user_transaction_count = {}
LOG_CHANNEL_ID = None
logger = logging.getLogger(__name__)

# ==================== ERROR HANDLING UTILITY ====================

async def handle_error(interaction_or_ctx, error, title="❌ Error", ephemeral=True):
    """Handle error dengan konsisten"""
    error_msg = str(error)
    print(f"❌ Error: {error_msg}")
    print(f"📍 Location: {error.__traceback__.tb_frame.f_code.co_name}")
    
    # Coba kirim ke user
    try:
        if hasattr(interaction_or_ctx, 'response') and not interaction_or_ctx.response.is_done():
            await interaction_or_ctx.response.send_message(
                f"{title}\n```\n{error_msg[:1500]}\n```", 
                ephemeral=ephemeral
            )
        elif hasattr(interaction_or_ctx, 'followup'):
            await interaction_or_ctx.followup.send(
                f"{title}\n```\n{error_msg[:1500]}\n```", 
                ephemeral=ephemeral
            )
        elif hasattr(interaction_or_ctx, 'send'):
            await interaction_or_ctx.send(
                f"{title}\n```\n{error_msg[:1500]}\n```"
            )
    except:
        pass  # Gagal kirim pesan, minimal sudah tercetak di log

def log_error(error, context=""):
    """Log error ke console dengan format konsisten"""
    import traceback
    print(f"❌ ERROR [{context}]: {error}")
    print("".join(traceback.format_tb(error.__traceback__)))
#===============================
    
class SimpleDB:
    
    def __init__(self, db_name="store.db"):
        self.db_name = db_name
        # Init db async akan dipanggil terpisah
    
    async def init_db(self):
        """Buat tabel kalo belum ada (async)"""
        async with aiosqlite.connect(self.db_name) as db:
            await db.execute('''CREATE TABLE IF NOT EXISTS transactions
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          invoice TEXT,
                          user_id TEXT,
                          items TEXT,
                          total_price INTEGER,
                          payment_method TEXT,
                          timestamp TEXT)''')
            
            await db.execute('''CREATE TABLE IF NOT EXISTS products
                         (id INTEGER PRIMARY KEY,
                          name TEXT,
                          price INTEGER,
                          category TEXT)''')

            await db.execute('''CREATE TABLE IF NOT EXISTS blacklist
                         (user_id TEXT PRIMARY KEY,
                          reason TEXT,
                          timestamp TEXT)''')
            
            await db.commit()
        print("✅ Database siap (async)")
    
    async def save_transaction(self, trans_data):
        """Simpan transaksi ke database (async)"""
        try:
            async with aiosqlite.connect(self.db_name) as db:
                items_json = json.dumps(trans_data['items'])
                
                await db.execute('''INSERT INTO transactions 
                            (invoice, user_id, items, total_price, payment_method, timestamp)
                            VALUES (?, ?, ?, ?, ?, ?)''',
                         (trans_data['invoice'],
                          trans_data['user_id'],
                          items_json,
                          trans_data['total_price'],
                          trans_data.get('payment_method', ''),
                          datetime.now().isoformat()))
                
                await db.commit()
            return True
        except Exception as e:
            print(f"❌ Error simpan transaksi: {e}")
            return False
    
    async def get_user_transactions(self, user_id, limit=5):
        """Ambil transaksi user (async)"""
        try:
            async with aiosqlite.connect(self.db_name) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute('''SELECT * FROM transactions 
                            WHERE user_id = ? 
                            ORDER BY timestamp DESC 
                            LIMIT ?''', (user_id, limit))
                
                rows = await cursor.fetchall()
            
            result = []
            for row in rows:
                result.append({
                    'invoice': row['invoice'],
                    'user_id': row['user_id'],
                    'items': json.loads(row['items']),
                    'total_price': row['total_price'],
                    'payment_method': row['payment_method'],
                    'timestamp': datetime.fromisoformat(row['timestamp'])
                })
            return result
        except Exception as e:
            print(f"❌ Error ambil transaksi: {e}")
            return []
    
    async def get_all_transactions(self):
        """Ambil semua transaksi (async)"""
        try:
            async with aiosqlite.connect(self.db_name) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute('SELECT * FROM transactions ORDER BY timestamp DESC')
                rows = await cursor.fetchall()
            
            result = []
            for row in rows:
                result.append({
                    'invoice': row['invoice'],
                    'user_id': row['user_id'],
                    'items': json.loads(row['items']),
                    'total_price': row['total_price'],
                    'payment_method': row['payment_method'],
                    'timestamp': datetime.fromisoformat(row['timestamp'])
                })
            return result
        except Exception as e:
            print(f"❌ Error ambil semua transaksi: {e}")
            return []
    
    async def add_blacklist(self, user_id, reason=""):
        """Tambah user ke blacklist (async)"""
        try:
            async with aiosqlite.connect(self.db_name) as db:
                await db.execute('''INSERT OR REPLACE INTO blacklist 
                            (user_id, reason, timestamp)
                            VALUES (?, ?, ?)''',
                         (user_id, reason, datetime.now().isoformat()))
                await db.commit()
            return True
        except Exception as e:
            print(f"❌ Error blacklist: {e}")
            return False
    
    async def remove_blacklist(self, user_id):
        """Hapus dari blacklist (async)"""
        try:
            async with aiosqlite.connect(self.db_name) as db:
                await db.execute('DELETE FROM blacklist WHERE user_id = ?', (user_id,))
                await db.commit()
            return True
        except Exception as e:
            print(f"❌ Error hapus blacklist: {e}")
            return False
    
    async def is_blacklisted(self, user_id):
        """Cek apakah user di-blacklist (async)"""
        try:
            async with aiosqlite.connect(self.db_name) as db:
                cursor = await db.execute('SELECT 1 FROM blacklist WHERE user_id = ?', (user_id,))
                result = await cursor.fetchone() is not None
            return result
        except Exception as e:
            print(f"❌ Error cek blacklist: {e}")
            return False
    
    async def get_blacklist(self):
        """Ambil semua data blacklist (async)"""
        try:
            async with aiosqlite.connect(self.db_name) as db:
                cursor = await db.execute('SELECT user_id, reason, timestamp FROM blacklist ORDER BY timestamp DESC')
                rows = await cursor.fetchall()
            return rows
        except Exception as e:
            print(f"❌ Error ambil blacklist: {e}")
            return []
    
    async def save_products(self, products):
        """Simpan produk ke database (async)"""
        try:
            async with aiosqlite.connect(self.db_name) as db:
                await db.execute('DELETE FROM products')
                
                for p in products:
                    await db.execute('''
                        INSERT INTO products (id, name, price, category)
                        VALUES (?, ?, ?, ?)
                    ''', (p['id'], p['name'], p['price'], p['category']))
                
                await db.commit()
            print(f"✅ Saved {len(products)} products to database")
            return True
        except Exception as e:
            print(f"❌ Error saving products: {e}")
            return False

    # ===== TICKET DATABASE (PERMANEN) =====

    async def save_ticket(self, channel_id, user_id, items, total_price):
        """Simpan tiket aktif ke database (async)"""
        try:
            async with aiosqlite.connect(self.db_name) as db:
                await db.execute('''CREATE TABLE IF NOT EXISTS active_tickets (
                    channel_id TEXT PRIMARY KEY,
                    user_id TEXT,
                    items TEXT,
                    total_price INTEGER,
                    payment_method TEXT,
                    status TEXT DEFAULT 'OPEN',
                    created_at TEXT
                )''')
                
                await db.execute('''INSERT OR REPLACE INTO active_tickets 
                            (channel_id, user_id, items, total_price, status, created_at)
                            VALUES (?, ?, ?, ?, ?, ?)''',
                         (channel_id, user_id, json.dumps(items), total_price, 'OPEN', datetime.now().isoformat()))
                
                await db.commit()
            return True
        except Exception as e:
            print(f"❌ Error save ticket: {e}")
            return False

    async def get_active_tickets(self):
        """Ambil semua tiket aktif dari database (async)"""
        try:
            async with aiosqlite.connect(self.db_name) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute('SELECT * FROM active_tickets WHERE status = "OPEN"')
                rows = await cursor.fetchall()
            
            tickets = {}
            for row in rows:
                tickets[row['channel_id']] = {
                    'user_id': row['user_id'],
                    'items': json.loads(row['items']),
                    'total_price': row['total_price'],
                    'payment_method': row['payment_method'],
                    'status': row['status'],
                    'created_at': row['created_at']
                }
            return tickets
        except Exception as e:
            print(f"❌ Error get active tickets: {e}")
            return {}

    async def update_ticket_status(self, channel_id, status, payment_method=None):
        """Update status tiket (async)"""
        try:
            async with aiosqlite.connect(self.db_name) as db:
                if payment_method:
                    await db.execute('''UPDATE active_tickets 
                                SET status = ?, payment_method = ? 
                                WHERE channel_id = ?''',
                             (status, payment_method, channel_id))
                else:
                    await db.execute('''UPDATE active_tickets 
                                SET status = ? 
                                WHERE channel_id = ?''',
                             (status, channel_id))
                
                await db.commit()
            return True
        except Exception as e:
            print(f"❌ Error update ticket: {e}")
            return False

    async def delete_ticket(self, channel_id):
        """Hapus tiket dari database (async)"""
        try:
            async with aiosqlite.connect(self.db_name) as db:
                await db.execute('DELETE FROM active_tickets WHERE channel_id = ?', (channel_id,))
                await db.commit()
            return True
        except Exception as e:
            print(f"❌ Error delete ticket: {e}")
            return False

    async def load_active_tickets_to_memory(self):
        """Load semua tiket aktif ke memory (async)"""
        return await self.get_active_tickets()

    async def update_ticket_items(self, channel_id, items):
        """Update items di tiket (async)"""
        try:
            async with aiosqlite.connect(self.db_name) as db:
                await db.execute('''UPDATE active_tickets 
                            SET items = ? 
                            WHERE channel_id = ?''',
                         (json.dumps(items), channel_id))
                await db.commit()
            return True
        except Exception as e:
            print(f"❌ Error update items: {e}")
            return False

    async def update_ticket_total(self, channel_id, total_price):
        """Update total price di tiket (async)"""
        try:
            async with aiosqlite.connect(self.db_name) as db:
                await db.execute('''UPDATE active_tickets 
                            SET total_price = ? 
                            WHERE channel_id = ?''',
                         (total_price, channel_id))
                await db.commit()
            return True
        except Exception as e:
            print(f"❌ Error update total: {e}")
            return False

    async def load_products(self):
        """Load semua produk dari database"""
        try:
            async with aiosqlite.connect(self.db_name) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute('SELECT * FROM products ORDER BY id')
                rows = await cursor.fetchall()
        
            products = []
            for row in rows:
                products.append({
                    'id': row['id'],
                    'name': row['name'],
                    'price': row['price'],
                    'category': row['category']
                })
            print(f"✅ Loaded {len(products)} products from database")
            return products
        except Exception as e:
            print(f"❌ Error load products: {e}")
            return []
# ==================== PRODUCTS CACHE ====================

class ProductsCache:
    def __init__(self):
        self.data = []
        self.last_update = None
        self.cache_duration = 300  # 5 menit (dalam detik)
    
    def is_expired(self):
        """Cek apakah cache sudah expired"""
        if not self.last_update:
            return True
        return (datetime.now() - self.last_update).seconds > self.cache_duration
    
    async def load_from_db(self):
        """Load produk dari database"""
        self.data = await db.load_products()
        self.last_update = datetime.now()
        print(f"📦 Cache refreshed: {len(self.data)} products")
        return self.data
    
    async def get_products(self, force_refresh=False):
        """Ambil produk (dari cache kalo masih fresh)"""
        if force_refresh or self.is_expired():
            return await self.load_from_db()
        return self.data
    
    async def refresh(self):
        """Force refresh cache"""
        return await self.load_from_db()
    
    def invalidate(self):
        """Hapus cache (dipanggil kalo ada perubahan produk)"""
        self.last_update = None
        print("📦 Cache invalidated")

# Inisialisasi cache
products_cache = ProductsCache()
# Init database
db = SimpleDB()

active_tickets = {}
# Poad product from json
global PRODUCTS
try:
    with open('products.json', 'r') as f:
        PRODUCTS = json.load(f)
    print(f"✅ Load {len(PRODUCTS)} products from products.json")
    
    # Simpan ke database biar kedepannya aman
except Exception as e:
    print(f"❌ Gagal load products.json: {e}")
    PRODUCTS = []
# ===== BROADCAST COOLDOWN =====
# Load cooldown dari file (agar permanen walau bot restart)
try:
    with open('broadcast_cooldown.json', 'r') as f:
        broadcast_cooldown = json.load(f)
except FileNotFoundError:
    broadcast_cooldown = {}

async def get_item_by_id(item_id):
    products = await products_cache.get_products()
    return next((p for p in products if p['id'] == item_id), None)

async def calculate_total_from_ticket(ticket):
    total = 0
    for entry in ticket['items']:
        item = await get_item_by_id(entry['id'])
        if item:
            total += item['price'] * entry['qty']
    return total

async def format_items_from_ticket(ticket):
    if not ticket['items']:
        return "Tidak ada item"
    result = ""
    for entry in ticket['items']:
        item = await get_item_by_id(entry['id'])
        if item:
            result += f"{entry['qty']}x {item['name']} = Rp {item['price'] * entry['qty']:,}\n"
    return result

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
    
    # 🔴 BACA ID DARI ENV (kalo ada)
    if LOG_CHANNEL_ID is None:
        LOG_CHANNEL_ID = os.getenv('LOG_CHANNEL_ID')
        if LOG_CHANNEL_ID:
            try:
                LOG_CHANNEL_ID = int(LOG_CHANNEL_ID)
            except:
                LOG_CHANNEL_ID = None
    
    # 🔴 PAKSA PAKE ID
    if LOG_CHANNEL_ID:
        channel = guild.get_channel(LOG_CHANNEL_ID)
        if channel and isinstance(channel, discord.TextChannel):
            return channel
        else:
            print(f"⚠️ Channel {LOG_CHANNEL_ID} tidak ditemukan, cari channel dengan nama 'log-transaksi'...")
            LOG_CHANNEL_ID = None
    
    # Fallback: cari channel dengan nama
    channel = discord.utils.get(guild.channels, name="log-transaksi")
    
    if not channel:
        # BUAT CHANNEL BARU (kalo bener2 ga ada)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=True, send_messages=False),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        channel = await guild.create_text_channel(
            name="log-transaksi",
            overwrites=overwrites,
            topic="📋 LOG TRANSAKSI CELLYN STORE"
        )
        
        embed = discord.Embed(
            title="📋 LOG TRANSAKSI CELLYN STORE",
            description="Channel ini mencatat semua transaksi yang BERHASIL.",
            color=0x00ff00,
            timestamp=datetime.now()
        )
        embed.set_footer(text="CELLYN STORE")
        await channel.send(embed=embed)
        
        # Simpan ID channel baru
        LOG_CHANNEL_ID = channel.id
        
        # Update file .env (opsional, biar permanen)
        update_env_file(f"LOG_CHANNEL_ID={channel.id}")
    
    return channel

def update_env_file(key_value):
    """Update file .env dengan key baru"""
    try:
        with open('.env', 'r') as f:
            lines = f.readlines()
        
        key = key_value.split('=')[0]
        found = False
        for i, line in enumerate(lines):
            if line.startswith(key + '='):
                lines[i] = key_value + '\n'
                found = True
                break
        
        if not found:
            lines.append('\n' + key_value + '\n')
        
        with open('.env', 'w') as f:
            f.writelines(lines)
        print(f"✅ .env updated with {key_value}")
    except Exception as e:
        print(f"❌ Error updating .env: {e}")

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
    embed.set_thumbnail(url="https://i.imgur.com/55K63yR.png")
    
    embed.add_field(name="📋 NO. INVOICE", value=f"`{invoice_num}`", inline=False)
    embed.add_field(name="👑 CUSTOMER", value=f"{user_name}\n<@{transaction_data['user_id']}>", inline=True)
    embed.add_field(name="📦 ITEMS", value=items_list, inline=False)
    embed.add_field(name="💰 TOTAL", value=f"Rp {transaction_data['total_price']:,}", inline=True)
    embed.add_field(name="💳 METODE", value=transaction_data.get('payment_method', '-'), inline=True)
    
    if transaction_data.get('admin_id'):
        admin = guild.get_member(int(transaction_data['admin_id']))
        if admin:
            embed.add_field(name="🛡️ ADMIN", value=admin.mention, inline=True)
    embed.set_image(url="https://i.imgur.com/ZgLBWzX.png")
    
    if transaction_data.get('fake', False):
        marker = "​"  
        footer_text = f"_\nCELLYN STORE{marker}"
    else:
        footer_text = "_\nCELLYN STORE"
    
    embed.set_footer(text=footer_text)
    
    await channel.send(embed=embed)

    await db.save_transaction(transaction_data)
    return invoice_num

def calculate_total(items):
    return sum(item['price'] * item['qty'] for item in items)

def format_items(items):
    if not items:
        return "Tidak ada item"
    return "\n".join([f"{item['qty']}x {item['name']} = Rp {item['price']*item['qty']:,}" for item in items])

    
async def generate_html_transcript(channel, closed_by):
    """
    Generate HTML transcript dari channel ticket
    Hasil: file HTML dengan tampilan mirip Discord
    """
    import os
    os.makedirs("transcripts", exist_ok=True)
    # 1. Kumpulin semua pesan (dari lama ke baru)
    messages = []
    async for msg in channel.history(limit=1000, oldest_first=True):
        # Format waktu
        timestamp = msg.created_at.strftime("%H:%M %d/%m/%Y")
        
        # Escape konten biar aman di HTML
        content = html.escape(msg.content) if msg.content else ""
        
        # Handle attachment
        attachments = ""
        if msg.attachments:
            for att in msg.attachments:
                attachments += f'<br>📎 <a href="{att.url}" target="_blank">{html.escape(att.filename)}</a>'
        
        # Handle embed (sederhana)
        embeds = ""
        if msg.embeds:
            embeds = "<br>📦 [Embed]"
        
        # Tentukan role (staff/bot/user)
        role_class = "user"
        if msg.author.bot:
            role_class = "bot"
        else:
            # Cek apakah dia staff (pake STAFF_ROLE_NAME dari config)
            staff_role = discord.utils.get(msg.author.roles, name=STAFF_ROLE_NAME)
            if staff_role:
                role_class = "staff"
        
        # Avatar URL
        if msg.author.avatar:
            avatar_url = msg.author.avatar.url
        else:
            # Default avatar Discord
            avatar_url = f"https://cdn.discordapp.com/embed/avatars/{int(msg.author.id) % 5}.png"
        
        messages.append({
            'timestamp': timestamp,
            'author': html.escape(msg.author.display_name),
            'author_id': msg.author.id,
            'avatar': avatar_url,
            'content': content,
            'attachments': attachments,
            'embeds': embeds,
            'role': role_class,
            'is_bot': msg.author.bot
        })
    
    # 2. Template HTML (bawaan, gak perlu file terpisah)
    html_template = f"""<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Transcript Tiket - {html.escape(channel.name)}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Whitney', 'Helvetica Neue', Helvetica, Arial, sans-serif;
            background-color: #36393f;
            color: #dcddde;
            line-height: 1.5;
            padding: 20px;
        }}
        .transcript-container {{
            max-width: 900px;
            margin: 0 auto;
            background-color: #2f3136;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
        }}
        .header {{
            background-color: #202225;
            padding: 20px 25px;
            border-bottom: 2px solid #40444b;
        }}
        .header h1 {{
            color: #fff;
            font-size: 24px;
            font-weight: 600;
            margin-bottom: 8px;
        }}
        .header p {{
            color: #b9bbbe;
            font-size: 14px;
            margin: 3px 0;
        }}
        .messages-area {{
            padding: 20px 25px;
        }}
        .message {{
            display: flex;
            margin: 15px 0;
            padding: 5px 0;
            border-bottom: 1px solid #40444b;
        }}
        .message:last-child {{
            border-bottom: none;
        }}
        .avatar {{
            width: 45px;
            height: 45px;
            border-radius: 50%;
            margin-right: 15px;
            flex-shrink: 0;
        }}
        .message-content {{
            flex: 1;
            min-width: 0;
        }}
        .author-row {{
            display: flex;
            align-items: baseline;
            flex-wrap: wrap;
            gap: 8px;
            margin-bottom: 5px;
        }}
        .author {{
            font-weight: 600;
            font-size: 16px;
        }}
        .staff .author {{ color: #43b581; }}
        .bot .author {{ color: #faa61a; }}
        .user .author {{ color: #7289da; }}
        .timestamp {{
            color: #72767d;
            font-size: 12px;
            font-weight: 400;
        }}
        .content {{
            color: #dcddde;
            font-size: 15px;
            word-wrap: break-word;
            white-space: pre-wrap;
        }}
        .attachment {{
            margin-top: 8px;
        }}
        .attachment a {{
            color: #00aff4;
            text-decoration: none;
            background-color: #40444b;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 13px;
            display: inline-block;
            margin-right: 5px;
        }}
        .attachment a:hover {{
            background-color: #4f545c;
            text-decoration: none;
        }}
        .embed-indicator {{
            display: inline-block;
            background-color: #40444b;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 13px;
            color: #dcddde;
            margin-top: 5px;
        }}
        .system-message {{
            background-color: #40444b;
            padding: 12px 15px;
            border-radius: 5px;
            color: #dcddde;
            font-style: italic;
            margin: 15px 0;
            text-align: center;
            border-left: 4px solid #5865f2;
        }}
        .footer {{
            background-color: #202225;
            padding: 15px 25px;
            text-align: center;
            color: #72767d;
            font-size: 13px;
            border-top: 2px solid #40444b;
        }}
        .footer img {{
            vertical-align: middle;
            margin-right: 5px;
        }}
        .badge {{
            display: inline-block;
            background-color: #40444b;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 11px;
            margin-left: 8px;
            color: #b9bbbe;
        }}
    </style>
</head>
<body>
    <div class="transcript-container">
        <div class="header">
            <h1>🎫 Ticket Transcript</h1>
            <p>📌 Channel: #{html.escape(channel.name)}</p>
            <p>🔒 Ditutup oleh: {html.escape(closed_by.display_name)} (@{html.escape(closed_by.name)})</p>
            <p>📅 Tanggal transcript: {datetime.now().strftime('%d %B %Y %H:%M:%S')}</p>
            <p>💬 Total pesan: {len(messages)}</p>
        </div>
        
        <div class="messages-area">
"""

    # 3. Tambahin setiap pesan ke template
    for msg in messages:
        # Tentukan badge khusus untuk staff/bot
        badge = ""
        if msg['is_bot']:
            badge = '<span class="badge">BOT</span>'
        elif msg['role'] == "staff":
            badge = '<span class="badge">STAFF</span>'
        
        html_template += f"""
            <div class="message {msg['role']}">
                <img class="avatar" src="{msg['avatar']}" alt="Avatar" loading="lazy">
                <div class="message-content">
                    <div class="author-row">
                        <span class="author">{msg['author']}</span>
                        {badge}
                        <span class="timestamp">{msg['timestamp']}</span>
                    </div>
                    <div class="content">{msg['content']}</div>
                    {msg['attachments']}
                    {msg['embeds']}
                </div>
            </div>"""
    
    # 4. Footer
    html_template += f"""
        </div>
        
        <div class="system-message">
            ⚡ Transcript generated by Cellyn Store Bot
        </div>
        
        <div class="footer">
            <span>CELLYN STORE • {datetime.now().strftime('%d/%m/%Y %H:%M')}</span>
        </div>
    </div>
</body>
</html>"""
    
    # 5. Simpan ke file
    os.makedirs("transcripts", exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"transcripts/ticket-{channel.name}-{timestamp}.html"
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html_template)
    
    return filename

# ==================== BACKUP OTOMATIS ====================

async def auto_backup():
    """Backup database otomatis setiap 6 jam"""
    while True:
        await asyncio.sleep(21600)  # 6 jam = 21600 detik
        
        try:
            # Bikin folder backups kalo belum ada
            os.makedirs("backups", exist_ok=True)
            
            # Format nama file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"backups/store_backup_{timestamp}.db"
            
            # Copy file database
            shutil.copy2("store.db", backup_name)
            
            # Hapus backup lama (lebih dari 7 hari)
            cleanup_old_backups()
            
            logger.info(f"✅ Auto backup berhasil: {backup_name}")
            
        except Exception as e:
            logger.error(f"❌ Gagal backup otomatis: {e}")

def cleanup_old_backups(days=7):
    """Hapus backup yang lebih dari X hari"""
    try:
        now = datetime.now().timestamp()
        cutoff = now - (days * 86400)  # 86400 detik per hari
        
        for file in os.listdir("backups"):
            file_path = os.path.join("backups", file)
            if os.path.isfile(file_path):
                file_time = os.path.getmtime(file_path)
                if file_time < cutoff:
                    os.remove(file_path)
                    logger.info(f"🗑️ Hapus backup lama: {file}")
    except Exception as e:
        logger.error(f"❌ Gagal cleanup backup: {e}")
        
@bot.tree.command(name="ping", description="Cek respon bot")
async def ping(interaction: discord.Interaction):
    start = time.time()
    await interaction.response.send_message("🏓 Pinging...")
    end = time.time()
    
    latency = round((end - start) * 1000)
    ws_latency = round(bot.latency * 1000)
    
    await interaction.edit_original_response(
        content=f"🏓 **Pong!**\n📡 Latensi: {latency}ms\n🌐 WebSocket: {ws_latency}ms"
    )

@bot.tree.command(name="refreshcache", description="🔄 Refresh produk cache (Admin only)")
async def refresh_cache(interaction: discord.Interaction):
    staff_role = discord.utils.get(interaction.guild.roles, name=STAFF_ROLE_NAME)
    if staff_role not in interaction.user.roles:
        await interaction.response.send_message("❌ Admin only!", ephemeral=True)
        return
    
    await products_cache.refresh()
    await interaction.response.send_message(f"✅ Cache refreshed! {len(products_cache.data)} products loaded")

@bot.tree.command(name="listbackup", description="[ADMIN] Lihat daftar backup")
async def list_backups(interaction: discord.Interaction):
    # Cek admin
    staff_role = discord.utils.get(interaction.guild.roles, name=STAFF_ROLE_NAME)
    if staff_role not in interaction.user.roles:
        await interaction.response.send_message("❌ Admin only!", ephemeral=True)
        return
    
    if not os.path.exists("backups"):
        await interaction.response.send_message("📁 Folder backups belum ada.")
        return
    
    backups = sorted(os.listdir("backups"), reverse=True)[:10]
    
    if not backups:
        await interaction.response.send_message("📝 Belum ada backup.")
        return
    
    embed = discord.Embed(title="📁 DAFTAR BACKUP", color=0x00ff00)
    
    for b in backups:
        size = os.path.getsize(f"backups/{b}") / 1024
        embed.add_field(name=b, value=f"{size:.2f} KB", inline=False)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="statdetail", description="[ADMIN] Statistik detail penjualan")
async def stats_detail(interaction: discord.Interaction):
    # Cek admin
    staff_role = discord.utils.get(interaction.guild.roles, name=STAFF_ROLE_NAME)
    if staff_role not in interaction.user.roles:
        await interaction.response.send_message("❌ Admin only!", ephemeral=True)
        return
    
    all_trans = await db.get_all_transactions() + transactions
    
    # Filter transaksi real (bukan fake)
    real_trans = [t for t in all_trans if not t.get('fake')]
    
    if not real_trans:
        await interaction.response.send_message("📝 Belum ada transaksi real.")
        return
    
    # Hitung berbagai statistik
    total_real = len(real_trans)
    total_fake = len(all_trans) - total_real
    total_omset = sum(t['total_price'] for t in real_trans)
    avg_transaksi = total_omset / total_real if total_real else 0
    
    # Transaksi per metode
    metode = {}
    for t in real_trans:
        m = t.get('payment_method', 'Unknown')
        metode[m] = metode.get(m, 0) + 1
    
    metode_str = "\n".join([f"  {m}: {c}x" for m, c in metode.items()])
    
    # Rata-rata per hari
    first_date = min(datetime.fromisoformat(t['timestamp']) for t in real_trans)
    days_active = max(1, (datetime.now() - first_date).days)
    avg_daily = total_omset / days_active
    
    embed = discord.Embed(
        title="📊 STATISTIK DETAIL",
        color=0x00ff00,
        timestamp=datetime.now()
    )
    
    embed.add_field(name="💰 Total Omset", value=f"Rp {total_omset:,}", inline=True)
    embed.add_field(name="📦 Total Transaksi", value=f"{total_real} real / {total_fake} fake", inline=True)
    embed.add_field(name="📈 Rata-rata", value=f"Rp {avg_transaksi:,.0f}/transaksi", inline=True)
    embed.add_field(name="📅 Rata-rata/hari", value=f"Rp {avg_daily:,.0f}", inline=True)
    embed.add_field(name="💳 Metode", value=metode_str or "-", inline=True)
    embed.add_field(name="👥 Total User", value=len(set(t['user_id'] for t in real_trans)), inline=True)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="resetdb", description="[ADMIN] Reset database (hapus semua transaksi)")
async def reset_database(interaction: discord.Interaction):
    # Cek admin
    staff_role = discord.utils.get(interaction.guild.roles, name=STAFF_ROLE_NAME)
    if staff_role not in interaction.user.roles:
        await interaction.response.send_message("❌ Admin only!", ephemeral=True)
        return
    
    # Konfirmasi dulu
    view = discord.ui.View()
    confirm = discord.ui.Button(label="✅ YA, Reset!", style=discord.ButtonStyle.danger)
    cancel = discord.ui.Button(label="❌ Batal", style=discord.ButtonStyle.secondary)
    
    async def confirm_callback(interaction):
        # Backup dulu sebelum reset
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"backups/pre_reset_backup_{timestamp}.db"
        os.makedirs("backups", exist_ok=True)
        shutil.copy2("store.db", backup_name)
        
        # Reset database
        os.remove("store.db")
        db = SimpleDB()  # Init ulang
        
        await interaction.response.edit_message(
            content=f"✅ Database telah direset!\n📁 Backup otomatis: `{backup_name}`",
            view=None
        )
    
    async def cancel_callback(interaction):
        await interaction.response.edit_message(content="❌ Reset dibatalkan.", view=None)
    
    confirm.callback = confirm_callback
    cancel.callback = cancel_callback
    view.add_item(confirm)
    view.add_item(cancel)
    
    await interaction.response.send_message(
        "⚠️ **PERINGATAN!**\nIni akan menghapus SEMUA transaksi! Yakin?",
        view=view,
        ephemeral=True
    )

@bot.tree.command(name="export", description="[ADMIN] Export transaksi ke file CSV")
@app_commands.describe(
    filter_user="Filter berdasarkan user (opsional)",
    filter_days="Filter jumlah hari terakhir (opsional)"
    )
async def export_transactions(
    interaction: discord.Interaction, 
    filter_user: discord.User = None,
    filter_days: int = None
    ):
    """Export data transaksi ke CSV"""
    # Cek admin
    staff_role = discord.utils.get(interaction.guild.roles, name=STAFF_ROLE_NAME)
    if staff_role not in interaction.user.roles:
        await interaction.response.send_message("❌ Admin only!", ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True)  # Biar gak timeout
    
    try:
        # Ambil semua transaksi dari database
        all_trans = await db.get_all_transactions()
        
        # Gabung dengan transaksi di memory
        all_trans = all_trans + transactions
        
        # Filter berdasarkan user
        if filter_user:
            user_id = str(filter_user.id)
            all_trans = [t for t in all_trans if t['user_id'] == user_id]
        
        # Filter berdasarkan hari
        if filter_days:
            cutoff = datetime.now() - timedelta(days=filter_days)
            all_trans = [t for t in all_trans 
                        if datetime.fromisoformat(t['timestamp']) >= cutoff]
        
        if not all_trans:
            await interaction.followup.send("📝 Tidak ada data transaksi.", ephemeral=True)
            return
        
        # Bikin file CSV di memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            'Invoice', 
            'User ID', 
            'Username',
            'Items', 
            'Total (Rp)', 
            'Metode', 
            'Tanggal', 
            'Fake',
            'Admin'
        ])
        
        # Data
        for t in all_trans:
            # Cari username
            username = "Unknown"
            try:
                user = await bot.fetch_user(int(t['user_id']))
                username = user.name
            except:
                pass
            
            # Format items (dipendekin biar gak terlalu panjang)
            if isinstance(t['items'], str):
                items = json.loads(t['items'])
            else:
                items = t['items']
            
            items_str = ", ".join([f"{i['qty']}x {i['name'][:20]}" for i in items])
            
            writer.writerow([
                t['invoice'],
                t['user_id'],
                username,
                items_str[:100],  # potong kalo kepanjangan
                t['total_price'],
                t.get('payment_method', '-'),
                t['timestamp'][:19],  # ambil YYYY-MM-DD HH:MM:SS aja
                'Ya' if t.get('fake') else 'Tidak',
                t.get('admin_id', '-')
            ])
        
        # Siapkan file untuk dikirim
        output.seek(0)
        
        # Nama file
        filename = f"transactions_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        # Kirim file
        await interaction.followup.send(
            content=f"📊 **Export data transaksi**\n"
                    f"Total: {len(all_trans)} transaksi\n"
                    f"Filter: {filter_user.name if filter_user else 'Semua user'} | "
                    f"{filter_days or 'Semua'} hari terakhir",
            file=discord.File(
                fp=io.BytesIO(output.getvalue().encode('utf-8-sig')), 
                filename=filename
            ),
            ephemeral=True
        )
        
    except Exception as e:
        logger.error(f"Error export: {e}")
        await interaction.followup.send(f"❌ Gagal export: {str(e)[:100]}", ephemeral=True)

@bot.tree.command(name="backup", description="[ADMIN] Backup database manual")
async def manual_backup(interaction: discord.Interaction):
    """Backup database secara manual"""
    # Cek admin
    staff_role = discord.utils.get(interaction.guild.roles, name=STAFF_ROLE_NAME)
    if staff_role not in interaction.user.roles:
        await interaction.response.send_message("❌ Admin only!", ephemeral=True)
        return
    
    try:
        # Bikin folder backups
        os.makedirs("backups", exist_ok=True)
        
        # Format nama file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"backups/manual_backup_{timestamp}.db"
        
        # Copy database
        shutil.copy2("store.db", backup_name)
        
        # Hitung ukuran file
        size = os.path.getsize(backup_name) / 1024  # KB
        
        await interaction.response.send_message(
            f"✅ **Backup berhasil!**\n"
            f"📁 File: `{backup_name}`\n"
            f"📊 Ukuran: `{size:.2f} KB`\n"
            f"🕒 Waktu: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
        )
        
    except Exception as e:
        await interaction.response.send_message(f"❌ Gagal backup: {str(e)[:100]}")

@bot.tree.command(name="history", description="Lihat riwayat transaksi pribadi")
async def history(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    
    # Ambil dari database dulu (5 transaksi terakhir)
    user_transactions = await db.get_user_transactions(user_id, limit=5)
    
    # Kalau dari database kosong, ambil dari list lama
    if not user_transactions:
        user_transactions = [t for t in transactions if t['user_id'] == user_id][-5:]
    
    if not user_transactions:
        await interaction.response.send_message("Belum ada transaksi.", ephemeral=True)
        return
    
    # Hitung total semua transaksi user
    all_user = await db.get_user_transactions(user_id, limit=1000)
    total_trans = len(all_user) if all_user else len([t for t in transactions if t['user_id'] == user_id])
    
    last_5 = user_transactions[-5:]
    embed = discord.Embed(
        title="RIWAYAT TRANSAKSI",
        description=f"Total: {total_trans} transaksi",
        color=0x3498db
    )
    
    for t in reversed(last_5):
        # Parse timestamp
        if isinstance(t['timestamp'], str):
            try:
                timestamp = datetime.fromisoformat(t['timestamp'])
            except:
                timestamp = datetime.now()
        else:
            timestamp = t['timestamp']
        
        date_str = timestamp.strftime("%d/%m/%Y %H:%M")
        
        # Handle items (bisa string JSON atau list)
        if isinstance(t['items'], str):
            items = json.loads(t['items'])
        else:
            items = t['items']
        
        items_short = ", ".join([f"{i['qty']}x {i['name'][:15]}" for i in items[:2]])
        if len(items) > 2:
            items_short += f" +{len(items)-2} lagi"
        
        embed.add_field(
            name=f"{t['invoice']} - {date_str}",
            value=f"{items_short} | Rp {t['total_price']:,} | {t.get('payment_method', '-')}",
            inline=False
        )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="allhistory", description="[ADMIN] Lihat SEMUA riwayat transaksi user")
@app_commands.describe(user="User yang mau dilihat transaksinya")
async def all_history(interaction: discord.Interaction, user: discord.User):
    # Cek admin
    staff_role = discord.utils.get(interaction.guild.roles, name=STAFF_ROLE_NAME)
    if staff_role not in interaction.user.roles:
        await interaction.response.send_message("❌ Admin only!", ephemeral=True)
        return
    
    user_id = str(user.id)
    
    # Ambil SEMUA transaksi dari database
    all_trans = await db.get_user_transactions(user_id, limit=1000)  # ambil semua
    
    # Kalo kosong, coba dari list lama
    if not all_trans:
        all_trans = [t for t in transactions if t['user_id'] == user_id]
    
    if not all_trans:
        await interaction.response.send_message(f"📝 {user.mention} belum punya transaksi.", ephemeral=True)
        return
    
    # Hitung total
    total_trans = len(all_trans)
    total_spent = sum(t['total_price'] for t in all_trans)
    
    # Buat embed
    embed = discord.Embed(
        title=f"📋 SEMUA TRANSAKSI {user.name}",
        description=f"Total: **{total_trans}** transaksi | Total belanja: **Rp {total_spent:,}**",
        color=0x3498db
    )
    
    # Tampilin 10 terakhir (biar gak kepanjangan)
    for t in all_trans[-10:]:
        # Parse timestamp
        if isinstance(t['timestamp'], str):
            try:
                timestamp = datetime.fromisoformat(t['timestamp'])
            except:
                timestamp = datetime.now()
        else:
            timestamp = t['timestamp']
        
        date_str = timestamp.strftime("%d/%m/%Y %H:%M")
        
        # Parse items
        if isinstance(t['items'], str):
            items = json.loads(t['items'])
        else:
            items = t['items']
        
        # Ringkas items
        items_short = ", ".join([f"{i['qty']}x {i['name'][:15]}" for i in items[:2]])
        if len(items) > 2:
            items_short += f" +{len(items)-2} lagi"
        
        embed.add_field(
            name=f"{t['invoice']} - {date_str}",
            value=f"{items_short} | Rp {t['total_price']:,} | {t.get('payment_method', '-')}",
            inline=False
        )
    
    if total_trans > 10:
        embed.set_footer(text=f"Menampilkan 10 transaksi terakhir dari {total_trans}")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="stats", description="Lihat statistik penjualan (Admin only)")
async def stats(interaction: discord.Interaction):
    staff_role = discord.utils.get(interaction.guild.roles, name=STAFF_ROLE_NAME)
    if staff_role not in interaction.user.roles:
        await interaction.response.send_message("Admin only!", ephemeral=True)
        return
    
    # ===== GABUNG DATA DARI DATABASE + MEMORY =====
    db_transactions = await db.get_all_transactions()
    all_transactions = await db_transactions + transactions  # Gabung database + list lama
    # ===============================================
    
    today = datetime.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    today_trans = []
    week_trans = []
    month_trans = []
    
    for t in all_transactions:
        try:
            # Handle timestamp (bisa string atau datetime)
            if isinstance(t['timestamp'], str):
                t_date = datetime.fromisoformat(t['timestamp']).date()
            else:
                t_date = t['timestamp'].date()
            
            if t_date == today:
                today_trans.append(t)
            if t_date >= week_ago:
                week_trans.append(t)
            if t_date >= month_ago:
                month_trans.append(t)
        except:
            continue
    
    total_revenue = sum(t['total_price'] for t in all_transactions)
    today_revenue = sum(t['total_price'] for t in today_trans)
    week_revenue = sum(t['total_price'] for t in week_trans)
    month_revenue = sum(t['total_price'] for t in month_trans)
    
    embed = discord.Embed(
        title="STATISTIK PENJUALAN",
        color=0x00ff00,
        timestamp=datetime.now()
    )
    
    embed.add_field(
        name="HARI INI",
        value=f"{len(today_trans)} transaksi\nRp {today_revenue:,}",
        inline=True
    )
    embed.add_field(
        name="7 HARI",
        value=f"{len(week_trans)} transaksi\nRp {week_revenue:,}",
        inline=True
    )
    embed.add_field(
        name="30 HARI",
        value=f"{len(month_trans)} transaksi\nRp {month_revenue:,}",
        inline=True
    )
    embed.add_field(
        name="TOTAL",
        value=f"{len(all_transactions)} transaksi\nRp {total_revenue:,}",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="blacklist", description="Blacklist user (Admin only)")
@app_commands.describe(user="User yang akan diblacklist", reason="Alasan")
async def blacklist_user(interaction: discord.Interaction, user: discord.User, reason: str = "No reason"):
    staff_role = discord.utils.get(interaction.guild.roles, name=STAFF_ROLE_NAME)
    if staff_role not in interaction.user.roles:
        await interaction.response.send_message("Admin only!", ephemeral=True)
        return
    
    # Simpan di memory (buat kompatibilitas)
    blacklist.add(str(user.id))
    
    # Simpan di database (biar permanen)
    await db.add_blacklist(str(user.id), reason)
    
    embed = discord.Embed(
        title="⛔ BLACKLIST",
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
    
    # Hapus dari memory
    if str(user.id) in blacklist:
        blacklist.remove(str(user.id))
    
    # Hapus dari database
    await db.remove_blacklist(str(user.id))
    
    await interaction.response.send_message(f"✅ {user.mention} dihapus dari blacklist.")

@bot.tree.command(name="catalog", description="Lihat semua item")
async def catalog(interaction: discord.Interaction):
    # Ambil produk dari cache
    products = await products_cache.get_products()
    
    # Group produk berdasarkan kategori
    categories = {}
    for p in products:
        if p['category'] not in categories:
            categories[p['category']] = []
        categories[p['category']].append(p)

    embed = discord.Embed(
        title="CELLYN STORE - READY STOCK",
        description=f"Rate: 1 RBX = Rp {RATE:,}\nPayment: QRIS / DANA / BCA",
        color=0x00ff00
    )
    embed.set_thumbnail(url="https://i.imgur.com/55K63yR.png")
    embed.set_image(url="https://i.imgur.com/FvBULuL.png")

    # ===== KATEGORI OTOMATIS (GAK PERLU EDIT KODE LAGI) =====
    # Ambil semua kategori dari produk yang ADA
    all_categories = list(categories.keys())

    # Urutan prioritas (kategori lama biar tetap di depan)
    priority_order = ["LIMITED SKIN", "GAMEPASS", "CRATE", "BOOST", "NITRO", "RED FINGER", "MIDMAN", "LAINNYA"]

    # Gabungkan: kategori prioritas dulu, baru sisanya
    category_order = []
    for cat in priority_order:
        if cat in all_categories:
            category_order.append(cat)
            all_categories.remove(cat)

    # Tambah sisa kategori yang belum masuk (kategori baru otomatis masuk)
    category_order.extend(all_categories)
    # ======================================================

    # Tampilkan produk sesuai urutan
    for cat in category_order:
        if cat in categories:
            items = categories[cat][:5]  # Max 5 produk per kategori
            value = ""
            for item in items:
                value += f"ID: {item['id']} - {item['name']} - Rp {item['price']:,}\n"
            embed.add_field(name=cat, value=value or "-", inline=False)

    # Buat tombol sesuai kategori yang ADA (bukan cuma priority_order)
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
    await interaction.response.send_message(f"1000 RBX = Rp {RATE:,}")

@bot.tree.command(name="help", description="📋 Bantuan menggunakan bot CELLYN STORE")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📋 **BANTUAN CELLYN STORE**",
        description="**Selamat datang di Cellyn Store!**\nBerikut adalah cara menggunakan bot kami:",
        color=0x00ff00
    )
    # THUMBNAIL LOGO
    embed.set_thumbnail(url="https://i.imgur.com/55K63yR.png")
    
    # 🛒 CATALOG
    embed.add_field(
        name="🛒 **CARA ORDER**",
        value="```\n1. /catalog → pilih kategori\n2. Klik item → tiket terbuka\n3. Transfer sesuai total\n4. Klik PAID\n```",
        inline=False
    )
    
    # COMMANDS
    embed.add_field(
        name="📌 **COMMAND UNTUK CUSTOMER**",
        value="```\n/catalog   - Lihat semua item\n/rate      - Cek rate Robux\n/items     - Lihat item di tiket\n/additem   - Tambah item\n/removeitem- Hapus item\n!cancel    - Batalkan tiket\n```",
        inline=False
    )
    
    embed.add_field(
        name="👑 **COMMAND UNTUK ADMIN**",
        value="```\n/addproduct - Tambah produk\n/editprice - Ubah harga\n/editname  - Ubah nama\n/deleteitem- Hapus produk\n/setrate   - Update rate\n/uploadqris- Upload QRIS\n/blacklist - Blokir user\n/stats     - Statistik\n/fakeinvoice- Test invoice\n```",
        inline=False
    )
    
    # METODE PEMBAYARAN
    embed.add_field(
        name="💳 **METODE PEMBAYARAN**",
        value=f"```\n🏧 QRIS - Scan di embed\n💰 DANA - {DANA_NUMBER}\n🏦 BCA  - {BCA_NUMBER}\n```",
        inline=False
    )
    
    # FOOTER
    embed.set_footer(
        text="CELLYN STORE • PREMIUM DIGITAL",
        icon_url="https://i.imgur.com/55K63yR.png"
    )
    
    await interaction.response.send_message(embed=embed)
    
@bot.tree.command(name="broadcast", description="📢 Kirim pesan ke semua member (Admin only)")
@app_commands.describe(pesan="isi Pesan yang mau dikirim ke semua member")
async def broadcast(interaction: discord.Interaction, pesan: str):
    # CEK ADMIN
    staff_role = discord.utils.get(interaction.guild.roles, name=STAFF_ROLE_NAME)
    if staff_role not in interaction.user.roles:
        await interaction.response.send_message("❌ Hanya admin yang bisa broadcast!", ephemeral=True)
        return
    
    # ANTI SPAM: 1x PER HARI (86400 detik)
    user_id = str(interaction.user.id)
    last_used = broadcast_cooldown.get(user_id, 0)
    current_time = time.time()
    
    if current_time - last_used < 86400:  # 24 jam
        remaining = 86400 - (current_time - last_used)
        jam = int(remaining // 3600)
        menit = int((remaining % 3600) // 60)
        
        await interaction.response.send_message(
            f"⏱️ Broadcast cuma bisa sekali per hari!\n"
            f"🕐 Sisa waktu: **{jam} jam {menit} menit**",
            ephemeral=True,
            delete_after=10
        )
        return
    
    broadcast_cooldown[user_id] = current_time
    
    # Simpan cooldown ke file
    with open('broadcast_cooldown.json', 'w') as f:
        json.dump(broadcast_cooldown, f)
    
    await interaction.response.send_message(f"📢 Mengirim broadcast ke semua member...", ephemeral=True, delete_after=4)
    
    success = 0
    failed = 0
    
    # EMBED KEREN DENGAN BANNER
    embed = discord.Embed(
        title="📢 **✨ PENGUMUMAN CELLYN STORE ✨**",
        description=f"{pesan}",
        color=0x00ff00,
        timestamp=datetime.now()
    )
    
    # LOGO DI POJOK KANAN ATAS
    embed.set_thumbnail(url="https://i.imgur.com/55K63yR.png")
    
    # TAMBAH BANNER
    embed.set_image(url="https://i.imgur.com/md5cK3K.png")
    
    # FOOTER DENGAN LOGO
    embed.set_footer(
        text="CELLYN STORE • PREMIUM DIGITAL",
        icon_url="https://i.imgur.com/55K63yR.png"
    )
    
    # Kirim ke semua member
    for member in interaction.guild.members:
        if member.bot:
            continue
        
        try:
            await member.send(embed=embed)
            success += 1
        except:
            failed += 1
    
    # Laporan hasil
    await interaction.followup.send(
        f"✅ Broadcast selesai!\n"
        f"📨 Terkirim: **{success}** member\n"
        f"❌ Gagal: **{failed}** member (DM tertutup/bot)",
        ephemeral=True
    )

@bot.tree.command(name="setrate", description="Update rate Robux (Admin only)")
@app_commands.describe(rate="1000 RBX = berapa IDR?")
async def setrate(interaction: discord.Interaction, rate: int):
    staff_role = discord.utils.get(interaction.guild.roles, name=STAFF_ROLE_NAME)
    if staff_role not in interaction.user.roles:
        await interaction.response.send_message("Admin only!", ephemeral=True, delete_after=5)
        return
    global RATE
    RATE = rate
    await interaction.response.send_message(f"Rate updated: 1000 RBX = Rp {rate:,}")

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

@bot.tree.command(name="addproduct", description="🆕 Tambah produk baru (Admin only)")
@app_commands.describe(id="ID produk (angka unik)", name="Nama produk", price="Harga", category="Kategori")
async def add_product(interaction: discord.Interaction, id: int, name: str, price: int, category: str):
    staff_role = discord.utils.get(interaction.guild.roles, name=STAFF_ROLE_NAME)
    if staff_role not in interaction.user.roles:
        await interaction.response.send_message("❌ Admin only!", ephemeral=True)
        return
    
    # Validasi ID
    if any(p['id'] == id for p in PRODUCTS):
        await interaction.response.send_message(f"❌ ID {id} sudah dipakai!", ephemeral=True)
        return
    
    # Validasi harga
    if price <= 0:
        await interaction.response.send_message("❌ Harga harus lebih dari 0!", ephemeral=True)
        return
    
    # Produk baru
    new_product = {
        'id': id,
        'name': name,
        'price': price,
        'category': category.upper()
    }
    
    # Tambah ke list PRODUCTS
    PRODUCTS.append(new_product)
    
    # Simpan ke file JSON
    save_products()
    
    # Simpan ke database
    await db.save_products(PRODUCTS)
    
    # ===== INVALIDATE CACHE =====
    products_cache.invalidate()
    # ============================
    
    embed = discord.Embed(
        title="✅ PRODUK DITAMBAHKAN",
        description=f"**ID:** {id}\n**Nama:** {name}\n**Harga:** Rp {price:,}\n**Kategori:** {category.upper()}",
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
    
    # Cari item
    item = next((p for p in PRODUCTS if p['id'] == item_id), None)
    if not item:
        await interaction.response.send_message("❌ Item tidak ditemukan!", ephemeral=True)
        return
    
    # Validasi harga
    if new_price <= 0:
        await interaction.response.send_message("❌ Harga harus lebih dari 0!", ephemeral=True)
        return
    
    old_price = item['price']
    item['price'] = new_price
    
    # Simpan ke file JSON
    save_products()
    
    # Simpan ke database
    await db.save_products(PRODUCTS)
    
    # ===== INVALIDATE CACHE =====
    products_cache.invalidate()
    # ============================
    
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
    
    # Cari item
    item = next((p for p in PRODUCTS if p['id'] == item_id), None)
    if not item:
        await interaction.response.send_message("❌ Item tidak ditemukan!", ephemeral=True)
        return
    
    old_name = item['name']
    item['name'] = new_name
    
    # Simpan ke file JSON
    save_products()
    
    # Simpan ke database
    await db.save_products(PRODUCTS)
    
    # ===== INVALIDATE CACHE =====
    products_cache.invalidate()
    # ============================
    
    embed = discord.Embed(
        title="📝 NAMA DIUPDATE",
        description=f"**ID:** {item_id}\n**Nama lama:** {old_name}\n**Nama baru:** {new_name}",
        color=0x00ff00
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="deleteitem", description="🗑️ Hapus item (Admin only)")
@app_commands.describe(item_id="ID item yang akan dihapus")
async def delete_item(interaction: discord.Interaction, item_id: int):
    staff_role = discord.utils.get(interaction.guild.roles, name=STAFF_ROLE_NAME)
    if staff_role not in interaction.user.roles:
        await interaction.response.send_message("❌ Admin only!", ephemeral=True)
        return
    
    # Cari item
    item = next((p for p in PRODUCTS if p['id'] == item_id), None)
    if not item:
        await interaction.response.send_message("❌ Item tidak ditemukan!", ephemeral=True)
        return
    
    # Hapus dari list
    PRODUCTS.remove(item)
    
    # Simpan ke file JSON
    save_products()
    
    # Simpan ke database
    await db.save_products(PRODUCTS)
    
    # ===== INVALIDATE CACHE =====
    products_cache.invalidate()
    # ============================
    
    embed = discord.Embed(
        title="🗑️ ITEM DIHAPUS",
        description=f"**ID:** {item_id}\n**Nama:** {item['name']}\n**Harga:** Rp {item['price']:,}",
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
    
    await interaction.response.send_message(f"🧪 Generating {jumlah} fake invoice...", ephemeral=True, delete_after=3)
    
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

@bot.tree.command(name="cleanupstats", description="[ADMIN] Bersihin voice channel stats duplikat")
async def cleanup_stats_channels(interaction: discord.Interaction):
    # Cek admin
    staff_role = discord.utils.get(interaction.user.roles, name=STAFF_ROLE_NAME)
    if staff_role not in interaction.user.roles:
        await interaction.response.send_message("❌ Admin only!", ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True)
    
    deleted = 0
    for channel in interaction.guild.voice_channels:
        if channel.name.startswith("Member:"):
            pass
    
    for channel in interaction.guild.voice_channels:
        if channel.name.startswith("Member:"):
            await channel.delete()
            deleted += 1
    
    await interaction.followup.send(f"✅ {deleted} channel stats telah dibersihkan. Channel baru akan dibuat otomatis.")

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
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True, delete_after=20)
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
        # Setelah channel tiket berhasil dibuat, simpan ke database
        await db.save_ticket(
            channel_id=str(channel.id),
            user_id=str(interaction.user.id),
            items=ticket['items'],
            total_price=ticket['total_price']
        )
        
        active_tickets[str(channel.id)] = ticket
        embed = discord.Embed(
            title="🧾 *SELAMAT DATANG DI STORE KAMI**",
            description=f"━━━━━━━━━━━━━━━━━━━━━\n"
                        f"**📦 ITEM YANG DIPILIH**\n"
                        f"```\n{item['name']}\n```\n"
                        f"**💰 HARGA**\n"
                        f"```\nRp {item['price']:,}\n```\n"
                        f"━━━━━━━━━━━━━━━━━━━━━",
            color=0x2B2D31
        )
        
        # THUMBNAIL (logo kecil di pojok kanan atas)
        embed.set_thumbnail(url="https://i.imgur.com/55K63yR.png")  # GANTI DENGAN LOGO LO!
        
        # FIELD PEMBAYARAN
        embed.add_field(
            name="💳 **METODE PEMBAYARAN**",
            value="```\n1. QRIS\n2. DANA\n3. BCA\n```",
            inline=True
        )
        
        # FIELD STATUS
        embed.add_field(
            name="⚡ **STATUS**",
            value="```\n🟢 AKTIF\n```",
            inline=True
        )
        
        # FIELD INSTRUKSI RINGKAS
        embed.add_field(
            name="🔔 **LAYANAN PREMIUM**",
            value="```\n⚡ Eksekusi Instan\n💬 Live Support 24/7\n🔒 Data Terjamin Aman\n✨ Member Exclusive\n```",
            inline=False
        )
        
        # FOOTER DENGAN ICON
        embed.set_footer(
            text="CELLYN STORE • PREMIUM DIGITAL",
            icon_url="https://i.imgur.com/55K63yR.png"
        )
        embed.set_image(url="https://i.imgur.com/FvBULuL.png")
        await channel.send(f"Hallo {user.mention}!", embed=embed)
        await send_item_buttons(channel, ticket)
        await interaction.response.send_message(f"Ticket created: {channel.mention}", ephemeral=True, delete_after=5)
        
    # ===== HANDLER TOMBOL TAMBAH =====
    if custom_id.startswith('ticket_add_'):
        try:
            item_id = int(custom_id.split('_')[2])
            channel_id = str(interaction.channel.id)
        
            if channel_id not in active_tickets:
                await interaction.response.send_message("❌ Tiket tidak ditemukan!", ephemeral=True)
                return
        
            ticket = active_tickets[channel_id]
        
            staff_role = discord.utils.get(interaction.guild.roles, name=STAFF_ROLE_NAME)
            is_owner = str(interaction.user.id) == ticket['user_id']
            is_admin = staff_role in interaction.user.roles
        
            if not (is_owner or is_admin):
                await interaction.response.send_message("❌ Hanya pemilik tiket atau admin!", ephemeral=True)
                return
            found = False
            for entry in ticket['items']:
                if entry['id'] == item_id:
                    entry['qty'] += 1
                    found = True
                    break
            if found:
                await db.update_ticket_items(channel_id, ticket['items'])
                await db.update_ticket_total(channel_id, ticket['total_price'])
            else:
                ticket['items'].append({"id": item_id, "qty": 1})
                await db.update_ticket_items(channel_id, ticket['items'])
                await db.update_ticket_total(channel_id, ticket['total_price'])
        
            ticket['total_price'] = await calculate_total_from_ticket(ticket)
        
            await interaction.channel.purge(limit=10, check=lambda m: m.author == bot.user and m.components)
            await send_item_buttons(interaction.channel, ticket)
        
        except Exception as e:
            print(f"❌ Error ticket_add: {e}")
        return
        
        # ===== HANDLER TOMBOL KURANG =====
    if custom_id.startswith('ticket_remove_'):
        try:
            item_id = int(custom_id.split('_')[2])
            channel_id = str(interaction.channel.id)
        
            if channel_id not in active_tickets:
                await interaction.response.send_message("❌ Tiket tidak ditemukan!", ephemeral=True)
                return
        
            ticket = active_tickets[channel_id]
        
            staff_role = discord.utils.get(interaction.guild.roles, name=STAFF_ROLE_NAME)
            is_owner = str(interaction.user.id) == ticket['user_id']
            is_admin = staff_role in interaction.user.roles
        
            if not (is_owner or is_admin):
                await interaction.response.send_message("❌ Hanya pemilik tiket atau admin!", ephemeral=True)
                return
        
            for i, entry in enumerate(ticket['items']):
                if entry['id'] == item_id:
                    if entry['qty'] > 1:
                            entry['qty'] -= 1
                    break
            ticket['total_price'] = await calculate_total_from_ticket(ticket)
        
            await interaction.channel.purge(limit=10, check=lambda m: m.author == bot.user and m.components)
            await send_item_buttons(interaction.channel, ticket)
        
        except Exception as e:
            print(f"❌ Error ticket_remove: {e}")
        return

    elif custom_id == "confirm_payment":
        channel_id = str(interaction.channel.id)
        print(f"🔵 PAID clicked in channel: {channel_id}")
        print(f"🔵 Active tickets: {list(active_tickets.keys())}")

        if channel_id not in active_tickets:
            print(f"❌ ERROR: Channel {channel_id} not in active_tickets!")
            print(f"✅ Active tickets: {list(active_tickets.keys())}")
            await interaction.response.send_message("Ticket tidak ditemukan!", ephemeral=True)
            return
        staff_role = discord.utils.get(interaction.guild.roles, name=STAFF_ROLE_NAME)
        if staff_role not in interaction.user.roles:
            await interaction.response.send_message("Admin only!", ephemeral=True)
            return
        ticket = active_tickets[channel_id]
        ticket['status'] = 'CONFIRMED'
        ticket['admin_id'] = str(interaction.user.id)
    
        # PINDAHKAN INVOICE_NUM KE LUAR AGAR BISA DIAKSES DI EXCEPT
        invoice_num = None
        try:
            invoice_num = await send_invoice(interaction.guild, {
                'user_id': ticket['user_id'],
                'items': ticket['items'],
                'total_price': ticket['total_price'],
                'payment_method': ticket.get('payment_method'),
                'admin_id': str(interaction.user.id)
            })
        except Exception as e:
            print(f"❌ Error send_invoice: {e}")
            invoice_num = "ERROR"
    
        items_short = ", ".join([f"{i['qty']}x {i['name'][:15]}" for i in ticket['items'][:2]])
        if len(ticket['items']) > 2:
            items_short += f" +{len(ticket['items'])-2} lagi"
    
        # RESPONSE KE USER
        await interaction.response.send_message(
            f"✅ Pembayaran dikonfirmasi! Invoice: `{invoice_num}`\nTicket akan ditutup dalam 5 detik...", 
            ephemeral=True
        )
    
        # Kirim embed ke channel
        embed = discord.Embed(
            title="✅ PAYMENT CONFIRMED",
            description=f"**Items:** {items_short}\n**Total: Rp {ticket['total_price']:,}**\nInvoice: `{invoice_num}`\nTerima kasih!",
            color=0x00ff00
        )
        embed.set_footer(text="CELLYN STORE")
        await interaction.channel.send(embed=embed)
        
        # ===== KIRIM INVOICE VIA DM =====
        try:
            # Dapetin user object dari ID
            buyer = await bot.fetch_user(int(ticket['user_id']))
    
            if buyer:
                # Buat embed invoice
                dm_embed = discord.Embed(
                    title="🧾 **INVOICE PEMBAYARAN**",
                    description="Terima kasih telah berbelanja di **CELLYN STORE**!",
                    color=0x00ff00
                )
                dm_embed.set_thumbnail(url="https://i.imgur.com/55K63yR.png")
        
                # Items
                items_text = ""
                for item in ticket['items']:
                    items_text += f"{item['qty']}x {item['name']} = Rp {item['price'] * item['qty']:,}\n"
        
                dm_embed.add_field(name="📦 **ITEMS**", value=items_text, inline=False)
                dm_embed.add_field(name="💰 **TOTAL**", value=f"Rp {ticket['total_price']:,}", inline=True)
                dm_embed.add_field(name="💳 **METODE**", value=ticket.get('payment_method', '-'), inline=True)
                dm_embed.add_field(name="📋 **INVOICE**", value=f"`{invoice_num}`", inline=False)
        
                kesan = (
                    "👑 *Terima kasih telah menjadi bagian dari keluarga besar Cellyn Store!*\n"
                    "✨ *Anda adalah pelanggan yang sangat berharga bagi kami.*\n"
                    "🌟 *Tanpa dukungan anda, kami bukan apa-apa.*"
                )
                dm_embed.add_field(name="❤️ **DARI KAMI**", value=kesan, inline=False)
        
                dm_embed.add_field(
                    name="🔍 **CEK TRANSAKSI**",
                    value="Kamu bisa lihat history transaksi dengan command `/history`",
                    inline=False
                )
        
                dm_embed.set_footer(text="CELLYN STORE • Terima kasih!")
                dm_embed.timestamp = datetime.now()
        
                # Kirim DM
                await buyer.send(embed=dm_embed)
                print(f"✅ Invoice DM terkirim ke {buyer.name}")
        
        except discord.Forbidden:
            print(f"❌ Gagal kirim DM ke {ticket['user_id']} (DM dimatikan)")
        except Exception as e:
            print(f"❌ Gagal kirim DM: {e}")
        
        # ===== GENERATE HTML TRANSCRIPT =====
        print("🔵 MULAI GENERATE TRANSCRIPT...")
        try:
            html_file = await generate_html_transcript(interaction.channel, interaction.user)
            print(f"✅ TRANSCRIPT BERHASIL: {html_file}")
        
            # CARI LOG CHANNEL
            log_channel = None
        
            if LOG_CHANNEL_ID:
                log_channel = interaction.guild.get_channel(LOG_CHANNEL_ID)
                print(f"🔵 COBA CHANNEL ID: {LOG_CHANNEL_ID} -> {log_channel}")
        
            if not log_channel:
                log_channel = discord.utils.get(interaction.guild.channels, name="log-transaksi")
                print(f"🔵 FALLBACK KE NAMA: log-transaksi -> {log_channel}")
        
            print(f"🔵 LOG CHANNEL FINAL: {log_channel}")
        
            if log_channel:
                await log_channel.send(
                    content=f"📁 **HTML Transcript**\nChannel: {interaction.channel.name}\nDitutup oleh: {interaction.user.mention}\nInvoice: `{invoice_num}`",
                    file=discord.File(html_file)
                )
                print("✅ TRANSCRIPT TERKIRIM KE LOG")
            else:
                print("❌ LOG CHANNEL TIDAK DITEMUKAN")
            
        except Exception as e:
            print(f"❌ ERROR DI TRANSCRIPT: {e}")
            import traceback
            traceback.print_exc()
    # ===== SELESAI =====
        await db.update_ticket_status(channel_id, 'CLOSED', ticket.get('payment_method'))
    # TUNGGU 5 DETIK & HAPUS CHANNEL (PINDAHKAN KE LUAR TRY)
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
                await db.update_ticket_status(str(message.channel.id), 'OPEN', method)
                
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
    
    # Auto react untuk channel tertentu (cuma admin)
    if hasattr(bot, 'auto_react') and message.channel.id in bot.auto_react.enabled_channels:
        staff_role = discord.utils.get(message.author.roles, name=STAFF_ROLE_NAME)
        if staff_role:  # Hanya untuk admin
            emoji_list = bot.auto_react.enabled_channels[message.channel.id]
            bot.loop.create_task(bot.auto_react.add_reactions(message, emoji_list))
    # =========================================
    
    await bot.process_commands(message)

@bot.event
async def on_ready():
    print(f"BOT READY - {bot.user}")
    print(f"Server: {len(bot.guilds)}")
    print(f"Staff Role: {STAFF_ROLE_NAME}")
    global LOG_CHANNEL_ID, active_tickets
    LOG_CHANNEL_ID = None
    
    await db.init_db()

    load_products()

    # Simpan produk ke database (async)
    await db.save_products(PRODUCTS)
    
    # ===== LOAD PRODUK KE CACHE =====
    await products_cache.load_from_db()
    # ================================

    # Delay biar koneksi stabil
    await asyncio.sleep(2)

    # Load tiket aktif dari database ke memory (ASYNC)
    try:
        active_tickets = await db.load_active_tickets_to_memory()
        print(f"✅ Loaded {len(active_tickets)} active tickets from database")
    except Exception as e:
        print(f"❌ Error loading tickets: {e}")
        active_tickets = {}

    # Sync commands
    try:
        synced = await bot.tree.sync()
        print(f"✅ Commands synced: {len(synced)}")

        # Tampilin daftar command
        cmd_list = [cmd.name for cmd in synced]
        print(f"📋 Commands: {', '.join(cmd_list)}")

        # Cek apakah /ping ada
        if 'ping' in cmd_list:
            print("✅ /ping is registered!")
        else:
            print("❌ /ping NOT found in synced commands")

    except Exception as e:
        print(f"❌ Sync error: {e}")

    # ===== AUTO BACKUP =====
    bot.loop.create_task(auto_backup())
    print("Auto backup started")

    bot.loop.create_task(update_all_member_counts())
    print("Member count started")

# ===== FUNGSI KIRIM TOMBOL + / - =====
async def send_item_buttons(channel, ticket):
    """Kirim tombol + dan - untuk setiap item di tiket"""
    try:
        for entry in ticket['items']:
            item = await get_item_by_id(entry['id'])
            if item:
                view = discord.ui.View()
                
                minus = discord.ui.Button(
                    label="➖",
                    style=discord.ButtonStyle.danger,
                    custom_id=f"ticket_remove_{item['id']}"
                )
                
                qty_label = discord.ui.Button(
                    label=f"{entry['qty']}",
                    style=discord.ButtonStyle.secondary,
                    disabled=True
                )
                
                plus = discord.ui.Button(
                    label="➕",
                    style=discord.ButtonStyle.primary,
                    custom_id=f"ticket_add_{item['id']}"
                )
                
                view.add_item(minus)
                view.add_item(qty_label)
                view.add_item(plus)
                
                await channel.send(f"**{item['name']}**", view=view)
        
    except Exception as e:
        print(f"❌ Error send_item_buttons: {e}")
        
# ==================== AUTO REACTION SYSTEM ====================
import asyncio
import random

class AutoReact:
    def __init__(self):
        self.enabled_channels = {}
        self.default_emojis = ["❤️", "🔥", "🚀", "👍", "⭐", "🎉", "👏", "💯"]
    
    async def add_reactions(self, message, emoji_list=None):
        if not emoji_list:
            emoji_list = self.default_emojis
        
        await asyncio.sleep(random.uniform(2, 5))
        random.shuffle(emoji_list)
        
        for emoji in emoji_list[:8]:
            try:
                await message.add_reaction(emoji)
                await asyncio.sleep(random.uniform(0.3, 0.8))
            except:
                continue

# Tambahin auto_react ke bot
bot.auto_react = AutoReact()

@bot.tree.command(name="setreact", description="[ADMIN] Set auto-react di channel ini")
@app_commands.describe(emojis="List emoji pisah spasi", disable="Matiin auto-react")
async def set_react(interaction: discord.Interaction, emojis: str = None, disable: bool = False):
    staff_role = discord.utils.get(interaction.user.roles, name=STAFF_ROLE_NAME)
    if staff_role not in interaction.user.roles:
        await interaction.response.send_message("❌ Admin only!", ephemeral=True)
        return
    
    channel_id = interaction.channel_id
    
    if disable:
        if channel_id in bot.auto_react.enabled_channels:
            del bot.auto_react.enabled_channels[channel_id]
            await interaction.response.send_message(f"✅ Auto-react dimatikan di {interaction.channel.mention}")
        else:
            await interaction.response.send_message("❌ Auto-react gak aktif di sini", ephemeral=True)
        return
    
    if not emojis:
        if channel_id in bot.auto_react.enabled_channels:
            emoji_list = bot.auto_react.enabled_channels[channel_id]
            await interaction.response.send_message(f"📊 **Auto-react aktif**\nChannel: {interaction.channel.mention}\nEmoji: {' '.join(emoji_list)}")
        else:
            await interaction.response.send_message("❌ Auto-react tidak aktif. Gunakan `/setreact ❤️ 🔥 🚀`")
        return
    
    emoji_list = emojis.split()[:8]
    bot.auto_react.enabled_channels[channel_id] = emoji_list
    
    await interaction.response.send_message(f"✅ **Auto-react diaktifkan!**\nChannel: {interaction.channel.mention}\nEmoji: {' '.join(emoji_list)}")

@bot.tree.command(name="reactlist", description="[ADMIN] Lihat daftar channel auto-react")
async def react_list(interaction: discord.Interaction):
    staff_role = discord.utils.get(interaction.user.roles, name=STAFF_ROLE_NAME)
    if staff_role not in interaction.user.roles:
        await interaction.response.send_message("❌ Admin only!", ephemeral=True)
        return
    
    if not bot.auto_react.enabled_channels:
        await interaction.response.send_message("📝 Belum ada channel dengan auto-react")
        return
    
    embed = discord.Embed(title="📊 AUTO-REACT ACTIVE CHANNELS", color=0x00ff00)
    for ch_id, emojis in bot.auto_react.enabled_channels.items():
        channel = interaction.guild.get_channel(ch_id)
        ch_name = channel.mention if channel else f"Unknown ({ch_id})"
        embed.add_field(name=ch_name, value=f"Emoji: {' '.join(emojis)}", inline=False)
    
    await interaction.response.send_message(embed=embed)

# ==================== VOICE CHANNEL STATS ====================

async def update_member_count(guild):
    """Update voice channel dengan jumlah member terkini (CEK DUPLIKASI)"""
    try:
        # Cari atau buat kategori stats
        category = discord.utils.get(guild.categories, name="📊 SERVER STATS")
        if not category:
            category = await guild.create_category("📊 SERVER STATS")
        
        # Nama channel yang diinginkan
        channel_name = f"Member: {guild.member_count}"
        
        # ===== CEK CHANNEL YANG UDAH ADA =====
        # Cari semua channel dengan awalan "👥 Member:"
        existing_channels = []
        for channel in guild.voice_channels:
            if channel.name.startswith("Member:"):
                existing_channels.append(channel)
        
        if existing_channels:
            # Kalo ada channel yang udah ada, update yang pertama
            main_channel = existing_channels[0]
            if main_channel.name != channel_name:
                await main_channel.edit(name=channel_name)
            
            # Hapus channel duplikat lainnya
            for dup_channel in existing_channels[1:]:
                try:
                    await dup_channel.delete()
                    print(f"🗑️ Deleted duplicate member count channel: {dup_channel.name}")
                except:
                    pass
        else:
            await guild.create_voice_channel(
                name=channel_name,
                category=category,
                user_limit=0
            )
            
    except Exception as e:
        print(f"❌ Error updating member count in {guild.name}: {e}")

async def update_all_member_counts():
    """Update member count di semua guild"""
    while True:
        for guild in bot.guilds:
            await update_member_count(guild)
        
        await asyncio.sleep(600)
@bot.event
async def on_member_join(member):
    """Update member count pas ada yang join"""
    await update_member_count(member.guild)

@bot.event
async def on_member_remove(member):
    """Update member count pas ada yang leave"""
    await update_member_count(member.guild)

if __name__ == "__main__":
    if not TOKEN:
        print("ERROR: DISCORD_TOKEN not found in .env")
        exit()
    print("Starting BOT...")
    print("Under develop Equality")
    bot.run(TOKEN)
