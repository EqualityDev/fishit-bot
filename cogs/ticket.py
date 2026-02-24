import asyncio
import random
import discord
from discord.ext import commands
from datetime import datetime
from config import STAFF_ROLE_NAME, DANA_NUMBER, BCA_NUMBER, BACKUP_DIR, STORE_THUMBNAIL
from utils import (
    format_items,
    calculate_total,
    send_invoice,
    generate_html_transcript,
    get_log_channel,
)


async def _send_item_buttons(channel, ticket, products_cache):
    try:
        for entry in ticket["items"]:
            products = await products_cache.get_products()
            item = next((p for p in products if p["id"] == entry["id"]), None)
            if item:
                view = discord.ui.View()
                view.add_item(discord.ui.Button(
                    label="➖", style=discord.ButtonStyle.danger,
                    custom_id=f"ticket_remove_{item['id']}",
                ))
                view.add_item(discord.ui.Button(
                    label=str(entry["qty"]), style=discord.ButtonStyle.secondary, disabled=True,
                ))
                view.add_item(discord.ui.Button(
                    label="➕", style=discord.ButtonStyle.primary,
                    custom_id=f"ticket_add_{item['id']}",
                ))
                await channel.send(f"**{item['name']}**", view=view)
    except Exception as e:
        print(f"❌ Error send_item_buttons: {e}")


class TicketCog(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.component:
            return

        custom_id = interaction.data.get("custom_id", "")
        user_id = str(interaction.user.id)

        if user_id in self.bot.blacklist:
            await interaction.response.send_message(
                "Kamu diblacklist dari CELLYN STORE.", ephemeral=True
            )
            return

        # ─── Catalog Browse ──────────────────────────────────────

        if custom_id.startswith("buy_"):
            category = custom_id.replace("buy_", "")
            items = [p for p in self.bot.PRODUCTS if p["category"] == category]
            embed = discord.Embed(
                title=f"📦 {category}",
                description="Klik item yang mau dibeli:",
                color=0x3498DB,
            )
            for item in items[:10]:
                embed.add_field(
                    name=f"ID:{item['id']} — {item['name']}",
                    value=f"Rp {item['price']:,}",
                    inline=True,
                )
            view = discord.ui.View()
            for item in items[:10]:
                view.add_item(discord.ui.Button(
                    label=f"{item['name'][:30]} — Rp {item['price']:,}",
                    style=discord.ButtonStyle.secondary,
                    custom_id=f"item_{item['id']}",
                ))
            await interaction.response.send_message(
                embed=embed, view=view, ephemeral=True, delete_after=30
            )

        # ─── Open Ticket ─────────────────────────────────────────

        elif custom_id.startswith("item_"):
            item_id = int(custom_id.replace("item_", ""))
            item = next((p for p in self.bot.PRODUCTS if p["id"] == item_id), None)
            if not item:
                await interaction.response.send_message("Item tidak ditemukan!", ephemeral=True)
                return

            user = interaction.user
            guild = interaction.guild

            for t in self.bot.active_tickets.values():
                if t["user_id"] == user_id and t["status"] == "OPEN":
                    await interaction.response.send_message(
                        "Kamu masih punya tiket aktif! Gunakan !cancel", ephemeral=True
                    )
                    return

            # Defer dulu sebelum operasi yang butuh waktu lama
            await interaction.response.defer(ephemeral=True)

            category = discord.utils.get(guild.categories, name="TICKETS")
            if not category:
                category = await guild.create_category("TICKETS")

            staff_role = discord.utils.get(guild.roles, name=STAFF_ROLE_NAME)
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            }
            if staff_role:
                overwrites[staff_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

            channel = await guild.create_text_channel(
                name=f"ticket-{user.name}-{random.randint(100, 999)}",
                category=category,
                overwrites=overwrites,
            )

            ticket = {
                "channel_id": str(channel.id),
                "user_id": user_id,
                "items": [{"id": item["id"], "name": item["name"], "price": item["price"], "qty": 1}],
                "total_price": item["price"],
                "status": "OPEN",
                "payment_method": None,
                "created_at": datetime.now().isoformat(),
            }
            await self.bot.db.save_ticket(
                channel_id=str(channel.id),
                user_id=user_id,
                items=ticket["items"],
                total_price=ticket["total_price"],
            )
            self.bot.active_tickets[str(channel.id)] = ticket

            embed = discord.Embed(
                title="🧾 TIKET PEMBELIAN",
                description=(
                    f"{user.mention}, tiket kamu sudah dibuat!\n\n"
                    f"**📦 Item:** {item['name']}\n"
                    f"**💰 Harga:** Rp {item['price']:,}\n\n"
                    f"Pilih metode pembayaran:\n"
                    f"**1** — QRIS  |  **2** — DANA  |  **3** — BCA\n\n"
                    f"Ketik angka **1**, **2**, atau **3** untuk lanjut.\n"
                    f"Ketik `!cancel` untuk batalkan."
                ),
                color=0x2B2D31,
            )
            embed.set_thumbnail(url=STORE_THUMBNAIL)
            embed.set_footer(text="CELLYN STORE • PREMIUM DIGITAL", icon_url=STORE_THUMBNAIL)

            await channel.send(embed=embed)

            if staff_role:
                await channel.send(f"📢 {staff_role.mention} tiket baru dari {user.mention}!")

            await interaction.followup.send(
                f"✅ Tiket dibuat! {channel.mention}", ephemeral=True
            )

        # ─── Ticket Qty Buttons ───────────────────────────────────

        elif custom_id.startswith("ticket_add_") or custom_id.startswith("ticket_remove_"):
            is_add = custom_id.startswith("ticket_add_")
            item_id = int(custom_id.split("_")[-1])
            channel_id = str(interaction.channel.id)

            if channel_id not in self.bot.active_tickets:
                await interaction.response.send_message("❌ Tiket tidak ditemukan!", ephemeral=True)
                return

            ticket = self.bot.active_tickets[channel_id]

            if user_id != ticket["user_id"]:
                staff_role = discord.utils.get(interaction.guild.roles, name=STAFF_ROLE_NAME)
                if staff_role not in interaction.user.roles:
                    await interaction.response.send_message("❌ Bukan tiket kamu!", ephemeral=True)
                    return

            item_entry = next((i for i in ticket["items"] if i["id"] == item_id), None)
            if not item_entry:
                await interaction.response.send_message("❌ Item tidak ada di tiket!", ephemeral=True)
                return

            if is_add:
                item_entry["qty"] += 1
                msg = f"➕ **{item_entry['name']}** qty jadi **{item_entry['qty']}**"
            else:
                if item_entry["qty"] <= 1:
                    ticket["items"].remove(item_entry)
                    msg = f"🗑️ **{item_entry['name']}** dihapus dari tiket"
                else:
                    item_entry["qty"] -= 1
                    msg = f"➖ **{item_entry['name']}** qty jadi **{item_entry['qty']}**"

            ticket["total_price"] = calculate_total(ticket["items"])
            await self.bot.db.update_ticket_items(channel_id, ticket["items"])
            await self.bot.db.update_ticket_total(channel_id, ticket["total_price"])

            if not ticket["items"]:
                await interaction.response.send_message("🔄 Tiket kosong, menutup dalam 5 detik...")
                await asyncio.sleep(5)
                del self.bot.active_tickets[channel_id]
                await self.bot.db.delete_ticket(channel_id)
                await interaction.channel.delete()
                return

            await interaction.response.send_message(
                f"{msg}\n🛒 **Items:**\n{format_items(ticket['items'])}\n💰 **Total: Rp {ticket['total_price']:,}**"
            )

        # ─── Confirm Payment ─────────────────────────────────────

        elif custom_id == "confirm_payment":
            channel_id = str(interaction.channel.id)
            if channel_id not in self.bot.active_tickets:
                await interaction.response.send_message("❌ Tiket tidak ditemukan!", ephemeral=True)
                return

            ticket = self.bot.active_tickets[channel_id]
            if user_id != ticket["user_id"]:
                await interaction.response.send_message("❌ Bukan tiket kamu!", ephemeral=True)
                return
            if ticket["status"] != "OPEN":
                await interaction.response.send_message("❌ Tiket sudah diproses.", ephemeral=True)
                return

            await interaction.response.send_message(
                "✅ **Pembayaran kamu sedang diverifikasi oleh admin.**\n"
                "⏳ Estimasi: 1-5 menit. Mohon tunggu sebentar."
            )

            staff_role = discord.utils.get(interaction.guild.roles, name=STAFF_ROLE_NAME)
            verify_view = discord.ui.View()
            verify_btn = discord.ui.Button(
                label="✅ VERIFIKASI & CLOSE",
                style=discord.ButtonStyle.success,
                custom_id="verify_payment",
            )
            verify_view.add_item(verify_btn)
            if staff_role:
                await interaction.channel.send(
                    f"{staff_role.mention} **{interaction.user.display_name}** mengklaim sudah bayar!\n"
                    f"💰 Total: **Rp {ticket['total_price']:,}** | Metode: **{ticket.get('payment_method', '-')}**",
                    view=verify_view,
                )

        # ─── Verify Payment ───────────────────────────────────────

        elif custom_id == "verify_payment":
            channel_id = str(interaction.channel.id)
            if channel_id not in self.bot.active_tickets:
                await interaction.response.send_message("❌ Tiket tidak ditemukan!", ephemeral=True)
                return

            staff_role = discord.utils.get(interaction.guild.roles, name=STAFF_ROLE_NAME)
            if staff_role not in interaction.user.roles:
                await interaction.response.send_message("❌ Admin only!", ephemeral=True)
                return

            ticket = self.bot.active_tickets[channel_id]
            if ticket["status"] != "OPEN":
                await interaction.response.send_message("❌ Tiket sudah diproses.", ephemeral=True)
                return

            await interaction.response.defer()

            invoice_num = await send_invoice(
                interaction.guild,
                {
                    "user_id": ticket["user_id"],
                    "items": ticket["items"],
                    "total_price": ticket["total_price"],
                    "payment_method": ticket.get("payment_method"),
                    "admin_id": str(interaction.user.id),
                },
                self.bot.db,
            )

            await interaction.channel.send(
                f"✅ **TRANSAKSI SELESAI!**\n📋 Invoice: `{invoice_num}`\nTerima kasih! Channel akan ditutup dalam 5 detik..."
            )

            try:
                html_file = await generate_html_transcript(interaction.channel, interaction.user)
                backup_channel = discord.utils.get(interaction.guild.channels, name="backup-db")
                if not backup_channel:
                    overwrites = {
                        interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                        interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                    }
                    if staff_role:
                        overwrites[staff_role] = discord.PermissionOverwrite(read_messages=True)
                    backup_channel = await interaction.guild.create_text_channel(
                        name="backup-db", overwrites=overwrites,
                        topic="🔒 Backup otomatis database Cellyn Store"
                    )
                if backup_channel:
                    await backup_channel.send(
                        content=(
                            f"📁 **HTML Transcript**\n"
                            f"Channel: {interaction.channel.name}\n"
                            f"Ditutup oleh: {interaction.user.mention}\n"
                            f"Invoice: `{invoice_num}`"
                        ),
                        file=discord.File(html_file),
                    )
            except Exception as e:
                print(f"❌ Error transcript: {e}")

            await self.bot.db.update_ticket_status(channel_id, "CLOSED", ticket.get("payment_method"))
            await asyncio.sleep(5)
            self.bot.active_tickets.pop(channel_id, None)
            await interaction.channel.delete()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if message.guild is None:
            return
        if str(message.author.id) in self.bot.blacklist:
            return

        channel_id = str(message.channel.id)
        is_ticket = message.channel.name and message.channel.name.startswith("ticket-")

        # ─── Cancel Command ──────────────────────────────────────

        if message.content.lower() == "!cancel" and is_ticket:
            if channel_id in self.bot.active_tickets and self.bot.active_tickets[channel_id]["status"] == "OPEN":
                ticket = self.bot.active_tickets[channel_id]
                staff_role = discord.utils.get(message.guild.roles, name=STAFF_ROLE_NAME)
                if str(message.author.id) == ticket["user_id"] or staff_role in message.author.roles:
                    await message.channel.send("Transaksi dibatalkan. Ticket closed.")
                    await asyncio.sleep(3)
                    self.bot.active_tickets.pop(channel_id, None)
                    await self.bot.db.delete_ticket(channel_id)
                    await message.channel.delete()
                    return

        # ─── Payment Method Selection ────────────────────────────

        if is_ticket and channel_id in self.bot.active_tickets:
            ticket = self.bot.active_tickets[channel_id]
            if ticket["status"] == "OPEN" and message.content.strip() in ["1", "2", "3"]:
                methods = ["QRIS", "DANA", "BCA"]
                method = methods[int(message.content) - 1]
                ticket["payment_method"] = method
                total = ticket["total_price"]
                await self.bot.db.update_ticket_status(channel_id, "OPEN", method)

                if method == "QRIS":
                    await message.channel.send("Gunakan /qris untuk melihat QR code")
                elif method == "DANA":
                    embed = discord.Embed(
                        title="DANA",
                        description=f"Transfer ke:\n`{DANA_NUMBER}`\n\n**TOTAL: Rp {total:,}**",
                        color=0x00FF00,
                    )
                    await message.channel.send(embed=embed)
                elif method == "BCA":
                    embed = discord.Embed(
                        title="BCA",
                        description=f"Transfer ke:\n`{BCA_NUMBER}`\n\n**TOTAL: Rp {total:,}**",
                        color=0x00FF00,
                    )
                    await message.channel.send(embed=embed)

                await message.channel.send(
                    f"**🛒 ITEMS:**\n{format_items(ticket['items'])}\n**💰 TOTAL: Rp {total:,}**"
                )
                view = discord.ui.View()
                view.add_item(discord.ui.Button(
                    label="PAID", style=discord.ButtonStyle.success, custom_id="confirm_payment"
                ))
                await message.channel.send("Sudah transfer? Klik tombol di bawah:", view=view)
                staff_role = discord.utils.get(message.guild.roles, name=STAFF_ROLE_NAME)
                if staff_role:
                    await message.channel.send(f"{staff_role.mention} Ada pembayaran baru!")

        # ─── Auto React ──────────────────────────────────────────

        if message.channel.id in self.bot.auto_react.enabled_channels:
            staff_role = discord.utils.get(message.author.roles, name=STAFF_ROLE_NAME)
            if staff_role:
                emoji_list = self.bot.auto_react.enabled_channels[message.channel.id]
                self.bot.loop.create_task(self.bot.auto_react.add_reactions(message, emoji_list))

        if message.channel.id in self.bot.auto_react_all:
            emoji_list = self.bot.auto_react_all[message.channel.id]
            self.bot.loop.create_task(self.bot.auto_react.add_reactions(message, emoji_list))


async def setup(bot: commands.Bot):
    await bot.add_cog(TicketCog(bot))
