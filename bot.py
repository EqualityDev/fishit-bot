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

STAFF_ROLE_NAME = "Admin Store"
DANA_NUMBER = "081266778093"
BCA_NUMBER = "8565330655"
RATE = 95
active_tickets = {}

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

@bot.event
async def on_ready():
    print(f"BOT READY - {bot.user}")
    print(f"Server: {len(bot.guilds)}")
    print(f"Staff Role: {STAFF_ROLE_NAME}")
    
    try:
        synced = await bot.tree.sync()
        print(f"Commands: {len(synced)}")
        for cmd in synced:
            print(f"  - /{cmd.name}")
    except Exception as e:
        print(f"Sync error: {e}")

@bot.tree.command(name="catalog", description="Lihat semua item yang tersedia")
async def catalog(interaction: discord.Interaction):
    await interaction.response.defer()
    
    categories = {}
    for p in PRODUCTS:
        if p['category'] not in categories:
            categories[p['category']] = []
        categories[p['category']].append(p)
    
    embed = discord.Embed(
        title="FISH IT STORE - READY STOCK",
        description=f"Rate: 1 RBX = Rp {RATE:,}\nPayment: QRIS / DANA / BCA",
        color=0x00ff00
    )
    
    category_names = {
        "LIMITED SKIN": "LIMITED SKIN",
        "GAMEPASS": "GAMEPASS",
        "CRATE": "CRATE",
        "BOOST": "BOOST",
        "NITRO": "NITRO",
        "RED FINGER": "RED FINGER"
    }
    
    for cat, items in categories.items():
        value = ""
        for item in items[:5]:
            value += f"{item['name']} - Rp {item['price']:,}\n"
        embed.add_field(name=category_names.get(cat, cat), value=value or "-", inline=False)
    
    view = discord.ui.View()
    for cat in categories.keys():
        view.add_item(discord.ui.Button(
            label=f"BUY {cat}", 
            style=discord.ButtonStyle.primary, 
            custom_id=f"buy_{cat}"
        ))
    
    await interaction.followup.send(embed=embed, view=view)

@bot.tree.command(name="rate", description="Cek rate Robux saat ini")
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
        await interaction.response.send_message("File must be image!", ephemeral=True)
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

@bot.tree.command(name="qris", description="Lihat QR code pembayaran")
async def cek_qris(interaction: discord.Interaction):
    qr_channel = discord.utils.get(interaction.guild.channels, name="qr-code")
    if not qr_channel:
        await interaction.response.send_message("QR code not available!", ephemeral=True)
        return
    
    async for msg in qr_channel.history(limit=10):
        if msg.author == bot.user and msg.embeds:
            await interaction.response.send_message(embed=msg.embeds[0])
            return
    
    await interaction.response.send_message("QR code not found!", ephemeral=True)

@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type != discord.InteractionType.component:
        return
    
    custom_id = interaction.data.get('custom_id', '')
    
    if custom_id.startswith('buy_'):
        category = custom_id.replace('buy_', '')
        items = [p for p in PRODUCTS if p['category'] == category]
        
        embed = discord.Embed(title=f"{category}", description="Select item:", color=0x3498db)
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
            await interaction.response.send_message("Item not found!", ephemeral=True)
            return
        
        user = interaction.user
        guild = interaction.guild
        
        for t in active_tickets.values():
            if t['user_id'] == str(user.id) and t['status'] == 'OPEN':
                await interaction.response.send_message("You have an active ticket! Use !cancel", ephemeral=True)
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
            'item_name': item['name'],
            'price': item['price'],
            'status': 'OPEN',
            'payment_method': None
        }
        active_tickets[str(channel.id)] = ticket
        
        embed = discord.Embed(title="TICKET", color=0xffa500)
        embed.description = f"Item: {item['name']}\nPrice: Rp {item['price']:,}"
        embed.add_field(name="Payment Method", value="1. QRIS\n2. DANA\n3. BCA", inline=False)
        embed.add_field(name="Cancel", value="Type !cancel to cancel", inline=False)
        
        await channel.send(f"Hello {user.mention}!", embed=embed)
        await interaction.response.send_message(f"Ticket created: {channel.mention}", ephemeral=True)
    
    elif custom_id == "confirm_payment":
        channel_id = str(interaction.channel.id)
        
        if channel_id not in active_tickets:
            await interaction.response.send_message("Ticket not found!", ephemeral=True)
            return
        
        staff_role = discord.utils.get(interaction.guild.roles, name=STAFF_ROLE_NAME)
        if staff_role not in interaction.user.roles:
            await interaction.response.send_message("Admin only!", ephemeral=True)
            return
        
        ticket = active_tickets[channel_id]
        ticket['status'] = 'CONFIRMED'
        
        embed = discord.Embed(
            title="PAYMENT CONFIRMED",
            description=f"Item: {ticket['item_name']}\nThank you for your purchase!",
            color=0x00ff00
        )
        
        await interaction.channel.send(embed=embed)
        await interaction.response.send_message("Ticket will be closed in 5 seconds...", ephemeral=True)
        
        import asyncio
        await asyncio.sleep(5)
        
        if channel_id in active_tickets:
            del active_tickets[channel_id]
        await interaction.channel.delete()

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    if message.content.lower() == '!cancel' and message.channel.name and message.channel.name.startswith('ticket-'):
        channel_id = str(message.channel.id)
        if channel_id in active_tickets and active_tickets[channel_id]['status'] == 'OPEN':
            ticket = active_tickets[channel_id]
            staff_role = discord.utils.get(message.guild.roles, name=STAFF_ROLE_NAME)
            
            if str(message.author.id) == ticket['user_id'] or staff_role in message.author.roles:
                ticket['status'] = 'CANCELLED'
                await message.channel.send("Transaction cancelled. Ticket closed.")
                
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
                
                if method == 'QRIS':
                    await message.channel.send("Use /qris to see QR code")
                elif method == 'DANA':
                    embed = discord.Embed(
                        title="DANA",
                        description=f"Transfer to:\n`{DANA_NUMBER}`",
                        color=0x00ff00
                    )
                    await message.channel.send(embed=embed)
                elif method == 'BCA':
                    embed = discord.Embed(
                        title="BCA",
                        description=f"Transfer to:\n`{BCA_NUMBER}`",
                        color=0x00ff00
                    )
                    await message.channel.send(embed=embed)
                
                view = discord.ui.View()
                view.add_item(discord.ui.Button(
                    label="PAID",
                    style=discord.ButtonStyle.success,
                    custom_id="confirm_payment"
                ))
                await message.channel.send("Already paid? Click button below:", view=view)
                
                staff_role = discord.utils.get(message.guild.roles, name=STAFF_ROLE_NAME)
                if staff_role:
                    await message.channel.send(f"{staff_role.mention} New payment!")
    
    await bot.process_commands(message)

if __name__ == "__main__":
    if not TOKEN:
        print("ERROR: DISCORD_TOKEN not found in .env")
        exit()
    
    print("Starting bot...")
    bot.run(TOKEN)
