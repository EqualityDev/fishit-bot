import os
import sys
import csv
import io
import json
import time
import shutil
import asyncio
import logging
import zipfile
import tempfile
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta
from config import STAFF_ROLE_NAME, BACKUP_DIR, DB_NAME, BROADCAST_BANNER, STORE_THUMBNAIL, STORE_NAME
from utils import (
    get_log_channel,
    cleanup_old_backups,
    load_broadcast_cooldown,
    save_broadcast_cooldown,
    is_staff,
)

logger = logging.getLogger(__name__)


# ─── Modals ──────────────────────────────────────────────────────────────────

class ResetDBModal(discord.ui.Modal, title="Konfirmasi Reset Database"):
    confirm_input = discord.ui.TextInput(
        label="Ketik CONFIRM untuk mereset database",
        placeholder="CONFIRM",
        required=True,
        max_length=10,
    )

    async def on_submit(self, interaction: discord.Interaction):
        if self.confirm_input.value.strip() != "CONFIRM":
            await interaction.response.send_message(
                "❌ Konfirmasi salah, reset dibatalkan.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)
        os.makedirs(BACKUP_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{BACKUP_DIR}/pre_reset_backup_{timestamp}.db"
        shutil.copy2(DB_NAME, backup_name)
        os.remove(DB_NAME)
        await interaction.client.db.init_db()
        await interaction.followup.send(
            f"✅ Database telah direset!\n📁 Backup: `{backup_name}`", ephemeral=True
        )


class CleanupConfirmModal(discord.ui.Modal, title="Konfirmasi Cleanup Stats"):
    confirm_input = discord.ui.TextInput(
        label="Ketik CONFIRM untuk melanjutkan",
        placeholder="CONFIRM",
        required=True,
        max_length=10,
    )

    async def on_submit(self, interaction: discord.Interaction):
        if self.confirm_input.value.strip() != "CONFIRM":
            await interaction.response.send_message(
                "❌ Konfirmasi salah, cleanup dibatalkan.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)
        deleted = 0
        for channel in interaction.guild.voice_channels:
            if channel.name.startswith("Member:"):
                await channel.delete()
                deleted += 1
        await interaction.followup.send(
            f"✅ {deleted} channel stats dibersihkan. Channel baru akan dibuat otomatis."
        )


# ─── Cog ─────────────────────────────────────────────────────────────────────

class AdminCog(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.broadcast_cooldown = load_broadcast_cooldown()

    # ─── System ──────────────────────────────────────────────────

    @app_commands.command(name="ping", description="Cek respon bot")
    async def ping(self, interaction: discord.Interaction):
        start = time.time()
        await interaction.response.send_message("🏓 Pinging...")
        latency = round((time.time() - start) * 1000)
        ws_latency = round(self.bot.latency * 1000)
        await interaction.edit_original_response(
            content=f"🏓 **Pong!**\n📡 Latensi: {latency}ms\n🌐 WebSocket: {ws_latency}ms"
        )

    @app_commands.command(name="resetdb", description="[ADMIN] Reset database (hapus semua transaksi)")
    async def reset_database(self, interaction: discord.Interaction):
        if not is_staff(interaction):
            await interaction.response.send_message("❌ Admin only!", ephemeral=True)
            return
        await interaction.response.send_modal(ResetDBModal())

    @app_commands.command(name="backup", description="[ADMIN] Backup database manual")
    async def manual_backup(self, interaction: discord.Interaction):
        if not is_staff(interaction):
            await interaction.response.send_message("❌ Admin only!", ephemeral=True)
            return
        try:
            os.makedirs(BACKUP_DIR, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{BACKUP_DIR}/manual_backup_{timestamp}.db"
            shutil.copy2(DB_NAME, backup_name)
            size = os.path.getsize(backup_name) / 1024
            await interaction.response.send_message(
                f"✅ **Backup berhasil!**\n"
                f"📁 File: `{backup_name}`\n"
                f"📊 Ukuran: `{size:.2f} KB`\n"
                f"🕒 Waktu: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
            )
        except Exception as e:
            await interaction.response.send_message(f"❌ Gagal backup: {str(e)[:100]}")

    @app_commands.command(name="listbackup", description="[ADMIN] Lihat daftar backup")
    async def list_backups(self, interaction: discord.Interaction):
        if not is_staff(interaction):
            await interaction.response.send_message("❌ Admin only!", ephemeral=True)
            return
        if not os.path.exists(BACKUP_DIR):
            await interaction.response.send_message("📁 Folder backups belum ada.")
            return
        backups = sorted(os.listdir(BACKUP_DIR), reverse=True)[:10]
        if not backups:
            await interaction.response.send_message("📝 Belum ada backup.")
            return
        embed = discord.Embed(title="📁 DAFTAR BACKUP", color=0x00BFFF)
        for b in backups:
            size = os.path.getsize(f"{BACKUP_DIR}/{b}") / 1024
            embed.add_field(name=b, value=f"{size:.2f} KB", inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="restore", description="[ADMIN] Restore database dari backup")
    @app_commands.describe(backup_file="Nama file backup (lihat di /listbackup)")
    async def restore_backup(self, interaction: discord.Interaction, backup_file: str):
        if not is_staff(interaction):
            await interaction.response.send_message("❌ Admin only!", ephemeral=True)
            return
        backup_path = f"{BACKUP_DIR}/{backup_file}"
        if not os.path.exists(backup_path):
            await interaction.response.send_message(
                f"❌ File `{backup_file}` tidak ditemukan!\nCek dengan `/listbackup`",
                ephemeral=True,
            )
            return
        await interaction.response.defer(ephemeral=True)
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            pre_restore = f"{BACKUP_DIR}/pre_restore_{timestamp}.db"
            shutil.copy2(DB_NAME, pre_restore)
            shutil.copy2(backup_path, DB_NAME)
            size = os.path.getsize(DB_NAME) / (1024 * 1024)
            embed = discord.Embed(
                title="✅ RESTORE BERHASIL",
                description=f"Database berhasil direstore dari `{backup_file}`",
                color=0x00BFFF,
            )
            embed.add_field(name="📊 Ukuran", value=f"{size:.2f} MB", inline=True)
            embed.add_field(name="💾 Backup sebelum restore", value=f"`pre_restore_{timestamp}.db`", inline=True)
            await interaction.followup.send(embed=embed)
            log_channel = await get_log_channel(interaction.guild)
            if log_channel:
                await log_channel.send(
                    f"🔄 **Database direstore** oleh {interaction.user.mention}\n"
                    f"Dari: `{backup_file}`"
                )
            await interaction.followup.send("⚠️ **Disarankan restart bot** agar perubahan diterapkan.")
        except Exception as e:
            await interaction.followup.send(f"❌ Gagal restore: {str(e)[:100]}")

    # ─── Stats ───────────────────────────────────────────────────

    @app_commands.command(name="stats", description="Lihat statistik penjualan")
    async def stats(self, interaction: discord.Interaction):
        if not is_staff(interaction):
            await interaction.response.send_message("Admin only!", ephemeral=True)
            return
        all_transactions = await self.bot.db.get_all_transactions()
        today = datetime.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        today_trans, week_trans, month_trans = [], [], []
        for t in all_transactions:
            try:
                ts = t["timestamp"] if isinstance(t["timestamp"], datetime) else datetime.fromisoformat(t["timestamp"])
                t_date = ts.date()
                if t_date == today:
                    today_trans.append(t)
                if t_date >= week_ago:
                    week_trans.append(t)
                if t_date >= month_ago:
                    month_trans.append(t)
            except Exception:
                continue
        embed = discord.Embed(title="STATISTIK PENJUALAN", color=0x00BFFF, timestamp=datetime.now())
        embed.add_field(name="HARI INI", value=f"{len(today_trans)} transaksi\nRp {sum(t['total_price'] for t in today_trans):,}", inline=True)
        embed.add_field(name="7 HARI", value=f"{len(week_trans)} transaksi\nRp {sum(t['total_price'] for t in week_trans):,}", inline=True)
        embed.add_field(name="30 HARI", value=f"{len(month_trans)} transaksi\nRp {sum(t['total_price'] for t in month_trans):,}", inline=True)
        embed.add_field(name="TOTAL", value=f"{len(all_transactions)} transaksi\nRp {sum(t['total_price'] for t in all_transactions):,}", inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="statdetail", description="[ADMIN] Statistik detail penjualan")
    async def stats_detail(self, interaction: discord.Interaction):
        if not is_staff(interaction):
            await interaction.response.send_message("❌ Admin only!", ephemeral=True)
            return
        all_trans = await self.bot.db.get_all_transactions()
        real_trans = [t for t in all_trans if not t.get("fake")]
        if not real_trans:
            await interaction.response.send_message("📝 Belum ada transaksi real.")
            return
        total_real = len(real_trans)
        total_fake = len(all_trans) - total_real
        total_omset = sum(t["total_price"] for t in real_trans)
        avg_transaksi = total_omset / total_real if total_real else 0
        metode = {}
        for t in real_trans:
            m = t.get("payment_method", "Unknown")
            metode[m] = metode.get(m, 0) + 1
        metode_str = "\n".join(f"  {m}: {c}x" for m, c in metode.items())
        first_date = min(datetime.fromisoformat(str(t["timestamp"])) if isinstance(t["timestamp"], str) else t["timestamp"] for t in real_trans)
        days_active = max(1, (datetime.now() - first_date).days)
        avg_daily = total_omset / days_active
        embed = discord.Embed(title="📊 STATISTIK DETAIL", color=0x00BFFF, timestamp=datetime.now())
        embed.add_field(name="💰 Total Omset", value=f"Rp {total_omset:,}", inline=True)
        embed.add_field(name="📦 Total Transaksi", value=f"{total_real} real / {total_fake} fake", inline=True)
        embed.add_field(name="📈 Rata-rata", value=f"Rp {avg_transaksi:,.0f}/transaksi", inline=True)
        embed.add_field(name="📅 Rata-rata/hari", value=f"Rp {avg_daily:,.0f}", inline=True)
        embed.add_field(name="💳 Metode", value=metode_str or "-", inline=True)
        embed.add_field(name="👥 Total User", value=len(set(t["user_id"] for t in real_trans)), inline=True)
        await interaction.response.send_message(embed=embed)

    # ─── Export ──────────────────────────────────────────────────

    @app_commands.command(name="export", description="[ADMIN] Export transaksi ke CSV")
    @app_commands.describe(filter_user="Filter berdasarkan user", filter_days="Filter N hari terakhir")
    async def export_transactions(
        self,
        interaction: discord.Interaction,
        filter_user: discord.User = None,
        filter_days: int = None,
    ):
        if not is_staff(interaction):
            await interaction.response.send_message("❌ Admin only!", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        try:
            all_trans = await self.bot.db.get_all_transactions()
            if filter_user:
                all_trans = [t for t in all_trans if t["user_id"] == str(filter_user.id)]
            if filter_days:
                cutoff = datetime.now() - timedelta(days=filter_days)
                all_trans = [t for t in all_trans if (t["timestamp"] if isinstance(t["timestamp"], datetime) else datetime.fromisoformat(t["timestamp"])) >= cutoff]
            if not all_trans:
                await interaction.followup.send("📝 Tidak ada data transaksi.", ephemeral=True)
                return
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["Invoice", "User ID", "Username", "Items", "Total (Rp)", "Metode", "Tanggal", "Fake", "Admin"])
            for t in all_trans:
                username = "Unknown"
                try:
                    user = await self.bot.fetch_user(int(t["user_id"]))
                    username = user.name
                except Exception:
                    pass
                items = t["items"] if isinstance(t["items"], list) else json.loads(t["items"])
                items_str = ", ".join(f"{i['qty']}x {i['name'][:20]}" for i in items)
                ts = t["timestamp"] if isinstance(t["timestamp"], datetime) else datetime.fromisoformat(t["timestamp"])
                writer.writerow([
                    t["invoice"], t["user_id"], username, items_str[:100],
                    t["total_price"], t.get("payment_method", "-"),
                    ts.strftime("%Y-%m-%d %H:%M:%S"),
                    "Ya" if t.get("fake") else "Tidak", t.get("admin_id", "-"),
                ])
            output.seek(0)
            filename = f"transactions_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            await interaction.followup.send(
                content=f"📊 **Export transaksi**\nTotal: {len(all_trans)} transaksi",
                file=discord.File(fp=io.BytesIO(output.getvalue().encode("utf-8-sig")), filename=filename),
                ephemeral=True,
            )
        except Exception as e:
            await interaction.followup.send(f"❌ Gagal export: {str(e)[:100]}", ephemeral=True)

    # ─── Blacklist ───────────────────────────────────────────────

    @app_commands.command(name="blacklist", description="[ADMIN] Blacklist user")
    @app_commands.describe(user="User yang akan diblacklist", reason="Alasan")
    async def blacklist_user(self, interaction: discord.Interaction, user: discord.User, reason: str = "No reason"):
        if not is_staff(interaction):
            await interaction.response.send_message("Admin only!", ephemeral=True)
            return

        admin = interaction.user
        bot_self = self

        view = discord.ui.View(timeout=30)
        ya_btn = discord.ui.Button(label="Ya, Blacklist", style=discord.ButtonStyle.danger)
        batal_btn = discord.ui.Button(label="Batal", style=discord.ButtonStyle.secondary)

        async def ya_callback(btn: discord.Interaction):
            if btn.user.id != admin.id:
                await btn.response.send_message("Bukan hakmu!", ephemeral=True)
                return
            bot_self.bot.blacklist.add(str(user.id))
            await bot_self.bot.db.add_blacklist(str(user.id), reason)
            embed = discord.Embed(
                title="BLACKLIST",
                description=f"User: {user.mention}\nAlasan: {reason}",
                color=0xFF0000,
                timestamp=datetime.now(),
            )
            embed.set_footer(text=f"Oleh: {admin.name}")
            await btn.response.edit_message(content=None, embed=embed, view=None)

        async def batal_callback(btn: discord.Interaction):
            if btn.user.id != admin.id:
                await btn.response.send_message("Bukan hakmu!", ephemeral=True)
                return
            await btn.response.edit_message(content="Blacklist dibatalkan.", embed=None, view=None)

        ya_btn.callback = ya_callback
        batal_btn.callback = batal_callback
        view.add_item(ya_btn)
        view.add_item(batal_btn)

        await interaction.response.send_message(
            content=f"Konfirmasi blacklist {user.mention} dengan alasan: **{reason}**?",
            view=view,
            ephemeral=True
        )

    @app_commands.command(name="unblacklist", description="[ADMIN] Hapus user dari blacklist")
    @app_commands.describe(user="User yang akan dihapus dari blacklist")
    async def unblacklist(self, interaction: discord.Interaction, user: discord.User):
        if not is_staff(interaction):
            await interaction.response.send_message("Admin only!", ephemeral=True)
            return
        self.bot.blacklist.discard(str(user.id))
        await self.bot.db.remove_blacklist(str(user.id))
        await interaction.response.send_message(f"✅ {user.mention} dihapus dari blacklist.")

    # ─── Broadcast ───────────────────────────────────────────────

    @app_commands.command(name="broadcast", description="[ADMIN] Kirim pesan ke semua member")
    @app_commands.describe(image_url="URL gambar opsional untuk disertakan di broadcast")
    async def broadcast(self, interaction: discord.Interaction, image_url: str = None):
        if not is_staff(interaction):
            await interaction.response.send_message("❌ Hanya admin yang bisa broadcast!", ephemeral=True)
            return
        user_id = str(interaction.user.id)
        current_time = time.time()
        last_used = self.broadcast_cooldown.get(user_id, 0)
        if current_time - last_used < 86400:
            remaining = 86400 - (current_time - last_used)
            jam = int(remaining // 3600)
            menit = int((remaining % 3600) // 60)
            await interaction.response.send_message(
                f"⏱️ Broadcast cuma bisa sekali per hari!\n🕐 Sisa: **{jam} jam {menit} menit**",
                ephemeral=True,
            )
            return

        admin = interaction.user
        broadcast_self = self

        class BroadcastModal(discord.ui.Modal, title="Broadcast Pesan"):
            pesan = discord.ui.TextInput(
                label="Pesan",
                style=discord.TextStyle.paragraph,
                placeholder="Tulis pesan broadcast di sini...\nBisa multiline dan pakai **bold**",
                max_length=2000,
            )

            async def on_submit(modal_self, modal_interaction: discord.Interaction):
                pesan_text = str(modal_self.pesan)
                embed = discord.Embed(
                    title=f"📢 Pengumuman {STORE_NAME}",
                    description=pesan_text,
                    color=0x00BFFF,
                    timestamp=datetime.now(),
                )
                embed.set_author(name=f"Dari: {admin.display_name}", icon_url=admin.display_avatar.url)
                embed.set_thumbnail(url=STORE_THUMBNAIL)
                embed.set_image(url=image_url if image_url else BROADCAST_BANNER)
                embed.set_footer(text=f"{STORE_NAME} • PREMIUM DIGITAL", icon_url=STORE_THUMBNAIL)

                view = discord.ui.View(timeout=60)
                kirim_btn = discord.ui.Button(label="Kirim", style=discord.ButtonStyle.success)
                batal_btn = discord.ui.Button(label="Batal", style=discord.ButtonStyle.danger)

                async def kirim_callback(btn: discord.Interaction):
                    if btn.user.id != admin.id:
                        await btn.response.send_message("❌ Bukan hakmu!", ephemeral=True)
                        return
                    await btn.response.edit_message(content="📢 Mengirim broadcast...", embed=None, view=None)
                    broadcast_self.broadcast_cooldown[user_id] = current_time
                    save_broadcast_cooldown(broadcast_self.broadcast_cooldown)
                    success = failed = 0
                    for member in btn.guild.members:
                        if member.bot:
                            continue
                        try:
                            await member.send(embed=embed)
                            success += 1
                            await asyncio.sleep(0.5)
                        except Exception:
                            failed += 1
                    await btn.edit_original_response(
                        content=f"✅ Broadcast selesai! Terkirim: **{success}**, Gagal: **{failed}**"
                    )
                    backup_channel = discord.utils.get(btn.guild.channels, name="backup-db")
                    if backup_channel:
                        log_embed = discord.Embed(title="LOG BROADCAST", color=0x00BFFF, timestamp=datetime.now())
                        log_embed.add_field(name="Admin", value=admin.mention, inline=True)
                        log_embed.add_field(name="Terkirim", value=str(success), inline=True)
                        log_embed.add_field(name="Gagal", value=str(failed), inline=True)
                        log_embed.add_field(name="Pesan", value=pesan_text[:500], inline=False)
                        log_embed.set_footer(text=f"{STORE_NAME} • Broadcast Log")
                        await backup_channel.send(embed=log_embed)

                async def batal_callback(btn: discord.Interaction):
                    if btn.user.id != admin.id:
                        await btn.response.send_message("❌ Bukan hakmu!", ephemeral=True)
                        return
                    await btn.response.edit_message(content="❌ Broadcast dibatalkan.", embed=None, view=None)

                kirim_btn.callback = kirim_callback
                batal_btn.callback = batal_callback
                view.add_item(kirim_btn)
                view.add_item(batal_btn)

                await modal_interaction.response.send_message(
                    content="**Preview broadcast — cek dulu sebelum kirim:**",
                    embed=embed, view=view, ephemeral=True,
                )

        await interaction.response.send_modal(BroadcastModal())

    # ─── Update ──────────────────────────────────────────────────
    @app_commands.command(name="update", description="[ADMIN] Pull update dari GitHub dan restart bot")
    async def update_bot(self, interaction: discord.Interaction):
        if not is_staff(interaction):
            await interaction.response.send_message("Hanya admin yang bisa update bot!", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        import subprocess, sys, asyncio
        result = subprocess.run(
            ["git", "pull", "origin", "main"],
            capture_output=True, text=True,
            cwd="/data/data/com.termux/files/home/fishit-bot"
        )
        output = (result.stdout.strip() or result.stderr.strip())[:500]
        if "Already up to date" in output:
            await interaction.followup.send("Bot sudah versi terbaru, tidak perlu update.", ephemeral=True)
            return
        msg = "Update berhasil!\n" + "```\n" + output + "\n```\n" + "Bot akan restart dalam 3 detik..."
        await interaction.followup.send(msg, ephemeral=True)

        # Kirim notif ke webhook
        import aiohttp
        webhook_url = os.getenv("WATCHDOG_WEBHOOK", "")
        if webhook_url:
            import datetime
            payload = {
                "embeds": [{
                    "title": "BOT UPDATE",
                    "description": f"Bot diupdate oleh **{interaction.user.display_name}**",
                    "color": 3066993,
                    "fields": [
                        {"name": "Changelog", "value": f"```{output[:400]}```", "inline": False}
                    ],
                    "footer": {"text": "EQUALITY BOT • Monitor"},
                    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
                }]
            }
            try:
                async with aiohttp.ClientSession() as session:
                    await session.post(webhook_url, json=payload)
            except Exception:
                pass

        await asyncio.sleep(5)
        sys.exit(0)

    # ─── Misc ────────────────────────────────────────────────────

    @app_commands.command(name="cleanupstats", description="[ADMIN] Bersihin voice channel stats duplikat")
    async def cleanup_stats_channels(self, interaction: discord.Interaction):
        if not is_staff(interaction):
            await interaction.response.send_message("❌ Admin only!", ephemeral=True)
            return
        await interaction.response.send_modal(CleanupConfirmModal())


    @app_commands.command(name="transcript", description="[ADMIN] Cari transcript tiket berdasarkan user")
    @app_commands.describe(user="User yang mau dicari transcriptnya")
    async def transcript(self, interaction: discord.Interaction, user: discord.Member):
        if not is_staff(interaction):
            await interaction.response.send_message("❌ Admin only!", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        transcript_dir = BACKUP_DIR.replace("backups", "transcripts")
        if not os.path.exists(transcript_dir):
            await interaction.followup.send("❌ Folder transcripts tidak ditemukan!", ephemeral=True)
            return

        files = os.listdir(transcript_dir)
        matched = [f for f in sorted(files, reverse=True) if user.name.lower() in f.lower()]

        if not matched:
            await interaction.followup.send(f"❌ Tidak ada transcript untuk **{user.name}**!", ephemeral=True)
            return

        matched = matched[:5]
        files_to_send = [discord.File(os.path.join(transcript_dir, f)) for f in matched]

        await interaction.followup.send(
            content=f"📁 **{len(matched)} Transcript untuk {user.mention}:**",
            files=files_to_send,
            ephemeral=True,
        )


    @app_commands.command(name="migrate", description="[ADMIN] Export atau import data migrasi")
    @app_commands.describe(file="Upload file migration_package.zip untuk import (kosongkan untuk export)")
    async def migrate(self, interaction: discord.Interaction, file: discord.Attachment = None):
        if not is_staff(interaction):
            await interaction.response.send_message("❌ Admin only!", ephemeral=True)
            return

        # ── EXPORT ──────────────────────────────────────────────
        if file is None:
            await interaction.response.defer(ephemeral=True)
            try:
                with tempfile.TemporaryDirectory() as tmpdir:
                    zip_path = os.path.join(tmpdir, "migration_package.zip")
                    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                        if os.path.exists(DB_NAME):
                            zf.write(DB_NAME, "store.db")
                        if os.path.exists("products.json"):
                            zf.write("products.json", "products.json")

                    embed = discord.Embed(
                        title="📦 MIGRATION PACKAGE",
                        description="File migrasi berhasil dibuat!\n\nCara import di server baru:\n`/migrate` → upload file `migration_package.zip`",
                        color=0x00BFFF,
                        timestamp=datetime.now()
                    )
                    embed.set_footer(text=f"{STORE_NAME} • Migration Export")

                    await interaction.followup.send(
                        embed=embed,
                        file=discord.File(zip_path, filename="migration_package.zip"),
                        ephemeral=True
                    )

                    # Kirim ke DM admin
                    try:
                        with open(zip_path, "rb") as f:
                            await interaction.user.send(
                                content="📦 **Migration Package**\nFile migrasi bot lo. Simpan baik-baik!",
                                file=discord.File(f, filename="migration_package.zip")
                            )
                    except Exception:
                        pass

                    # Kirim juga ke #backup-db
                    backup_channel = discord.utils.get(interaction.guild.channels, name="backup-db")
                    if backup_channel:
                        with open(zip_path, "rb") as f:
                            await backup_channel.send(
                                content=f"📦 **MIGRATION EXPORT**\n👤 Oleh: {interaction.user.mention}\n📅 {datetime.now().strftime('%d/%m/%Y %H:%M')}",
                                file=discord.File(f, filename="migration_package.zip")
                            )
            except Exception as e:
                await interaction.followup.send(f"❌ Gagal export: {e}", ephemeral=True)

        # ── IMPORT ──────────────────────────────────────────────
        else:
            if not file.filename.endswith(".zip"):
                await interaction.response.send_message("❌ File harus berformat `.zip`!", ephemeral=True)
                return

            await interaction.response.defer(ephemeral=True)
            try:
                zip_bytes = await file.read()

                with tempfile.TemporaryDirectory() as tmpdir:
                    zip_path = os.path.join(tmpdir, "migration_package.zip")
                    with open(zip_path, "wb") as f:
                        f.write(zip_bytes)

                    with zipfile.ZipFile(zip_path, "r") as zf:
                        names = zf.namelist()
                        if "store.db" not in names:
                            await interaction.followup.send("❌ File zip tidak valid, `store.db` tidak ditemukan!", ephemeral=True)
                            return

                        # Backup DB lama dulu
                        if os.path.exists(DB_NAME):
                            shutil.copy2(DB_NAME, DB_NAME + ".pre_migrate")

                        # Extract
                        if "store.db" in names:
                            with zf.open("store.db") as src, open(DB_NAME, "wb") as dst:
                                dst.write(src.read())
                        if "products.json" in names:
                            with zf.open("products.json") as src, open("products.json", "wb") as dst:
                                dst.write(src.read())

                # Reload data
                await self.bot.db.init()
                products = await self.bot.db.get_all_products()
                self.bot.PRODUCTS = products
                self.bot.products_cache.invalidate()

                embed = discord.Embed(
                    title="✅ MIGRASI BERHASIL",
                    description=f"Data berhasil diimport!\n\n**{len(products)} produk** berhasil dimuat.",
                    color=0x00FF88,
                    timestamp=datetime.now()
                )
                embed.add_field(name="⚠️ Catatan", value="Restart bot untuk memastikan semua data termuat dengan sempurna.", inline=False)
                embed.set_footer(text=f"{STORE_NAME} • Migration Import")

                await interaction.followup.send(embed=embed, ephemeral=True)

                # Log ke #backup-db
                backup_channel = discord.utils.get(interaction.guild.channels, name="backup-db")
                if backup_channel:
                    await backup_channel.send(
                        f"📥 **MIGRATION IMPORT**\n👤 Oleh: {interaction.user.mention}\n📅 {datetime.now().strftime('%d/%m/%Y %H:%M')}\n✅ {len(products)} produk dimuat"
                    )

            except Exception as e:
                await interaction.followup.send(f"❌ Gagal import: {e}", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(AdminCog(bot))
