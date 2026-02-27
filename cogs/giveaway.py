import asyncio
import random
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta
from config import STAFF_ROLE_NAME, STORE_NAME
from utils import is_staff


def parse_duration(duration_str: str) -> int:
    duration_str = duration_str.strip().lower()
    units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    if duration_str[-1] in units:
        try:
            return int(duration_str[:-1]) * units[duration_str[-1]]
        except ValueError:
            return 0
    return 0


class GiveawayCog(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.active_giveaways = {}  # message_id: {prize, end_time, winners, host_id, participants: set}

    async def cog_load(self):
        """Restore giveaway aktif dari database saat bot start"""
        self.bot.loop.create_task(self._restore_giveaways())

    async def _restore_giveaways(self):
        await self.bot.wait_until_ready()
        try:
            giveaways = await self.bot.db.load_giveaways()
            now = datetime.now()
            restored = 0
            for msg_id, data in giveaways.items():
                self.active_giveaways[msg_id] = data
                remaining = (data["end_time"] - now).total_seconds()
                if remaining > 0:
                    self.bot.loop.create_task(self._resume_giveaway(msg_id, remaining, data))
                    restored += 1
                else:
                    # Sudah lewat waktu, langsung akhiri
                    self.bot.loop.create_task(
                        self._end_giveaway(msg_id, data["channel_id"], data["guild_id"],
                                           data["prize"], data["winners"], data["host_id"])
                    )
            if restored:
                print(f"✓ Restored {restored} active giveaway(s) from database")
        except Exception as e:
            print(f"❌ Error restoring giveaways: {e}")

    async def _resume_giveaway(self, msg_id, remaining_seconds, data):
        await asyncio.sleep(remaining_seconds)
        if msg_id in self.active_giveaways:
            await self._end_giveaway(
                msg_id, data["channel_id"], data["guild_id"],
                data["prize"], data["winners"], data["host_id"]
            )

    def _build_embed(self, prize, end_time, winner_count, host, participants=0, ended=False, winner_mentions=None):
        color = 0x95a5a6 if ended else 0xFF6B6B
        embed = discord.Embed(
            title=f"🎉 GIVEAWAY — {prize}",
            color=color,
            timestamp=end_time,
        )
        embed.add_field(name="Hadiah", value=prize, inline=True)
        embed.add_field(name="Pemenang", value=f"{winner_count} orang", inline=True)
        embed.add_field(name="Host", value=host.mention if hasattr(host, 'mention') else str(host), inline=True)
        embed.add_field(name="Peserta", value=str(participants), inline=True)

        if ended:
            embed.add_field(name="Status", value="SELESAI", inline=True)
            if winner_mentions:
                embed.add_field(name="Pemenang", value="\n".join(winner_mentions), inline=False)
                embed.description = f"Selamat kepada {', '.join(winner_mentions)}! 🎉"
        else:
            embed.add_field(name="Berakhir", value=f"<t:{int(end_time.timestamp())}:R>", inline=True)
            embed.description = f"Klik tombol **IKUTAN** di bawah untuk ikut!\nBerakhir: <t:{int(end_time.timestamp())}:F>"

        embed.set_footer(text=f"{STORE_NAME} • Giveaway" + (" • Selesai" if ended else ""))
        return embed

    def _build_view(self, message_id, ended=False):
        view = discord.ui.View(timeout=None)
        btn = discord.ui.Button(
            label="IKUTAN" if not ended else "SELESAI",
            style=discord.ButtonStyle.success if not ended else discord.ButtonStyle.secondary,
            emoji="🎉",
            custom_id=f"giveaway_join_{message_id}",
            disabled=ended,
        )
        view.add_item(btn)
        return view

    async def _end_giveaway(self, message_id, channel_id, guild_id, prize, winner_count, host_id):
        try:
            guild = self.bot.get_guild(guild_id)
            channel = guild.get_channel(channel_id)
            message = await channel.fetch_message(message_id)
            host = guild.get_member(host_id)

            data = self.active_giveaways.get(message_id, {})
            participants = list(data.get("participants", set()))
            end_time = data.get("end_time", datetime.now())

            if not participants:
                await channel.send("❌ Tidak ada peserta giveaway!")
                embed = self._build_embed(prize, end_time, winner_count, host, participants=0, ended=True)
                await message.edit(embed=embed, view=self._build_view(message_id, ended=True))
                self.active_giveaways.pop(message_id, None)
                await self.bot.db.delete_giveaway(message_id)
                return

            actual_winners = min(winner_count, len(participants))
            winner_ids = random.sample(participants, actual_winners)
            winners = [guild.get_member(uid) for uid in winner_ids if guild.get_member(uid)]
            winner_mentions = [w.mention for w in winners if w]

            embed = self._build_embed(prize, end_time, winner_count, host, participants=len(participants), ended=True, winner_mentions=winner_mentions)
            await message.edit(embed=embed, view=self._build_view(message_id, ended=True))

            await channel.send(
                f"🎉 **GIVEAWAY SELESAI!**\n"
                f"Hadiah: **{prize}**\n"
                f"Pemenang: {' '.join(winner_mentions) if winner_mentions else 'Tidak ada'}\n"
                f"Hubungi {host.mention if host else 'admin'} untuk klaim hadiah!"
            )

            self.active_giveaways.pop(message_id, None)
            await self.bot.db.delete_giveaway(message_id)

            backup_channel = discord.utils.get(guild.channels, name="backup-db")
            if backup_channel:
                log_embed = discord.Embed(title="LOG GIVEAWAY SELESAI", color=0x00BFFF, timestamp=datetime.now())
                log_embed.add_field(name="Hadiah", value=prize, inline=True)
                log_embed.add_field(name="Peserta", value=str(len(participants)), inline=True)
                log_embed.add_field(name="Pemenang", value="\n".join(winner_mentions) or "-", inline=False)
                log_embed.set_footer(text=f"{STORE_NAME} • Giveaway Log")
                await backup_channel.send(embed=log_embed)

        except Exception as e:
            print(f"❌ Error end giveaway: {e}")

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        custom_id = interaction.data.get("custom_id", "")
        if not custom_id.startswith("giveaway_join_"):
            return

        message_id = int(custom_id.replace("giveaway_join_", ""))
        user_id = interaction.user.id

        if message_id not in self.active_giveaways:
            await interaction.response.send_message("❌ Giveaway ini sudah selesai!", ephemeral=True)
            return

        data = self.active_giveaways[message_id]
        participants = data.setdefault("participants", set())

        if user_id in participants:
            participants.discard(user_id)
            await interaction.response.send_message("❌ Kamu keluar dari giveaway.", ephemeral=True)
        else:
            participants.add(user_id)
            await interaction.response.send_message("✅ Kamu sudah terdaftar di giveaway! Semoga menang 🎉", ephemeral=True)

        # Simpan perubahan peserta ke database
        await self.bot.db.update_giveaway_participants(message_id, participants)

        # Update jumlah peserta di embed
        try:
            guild = interaction.guild
            host = guild.get_member(data["host_id"])
            embed = self._build_embed(
                data["prize"], data["end_time"], data["winners"],
                host, participants=len(participants)
            )
            await interaction.message.edit(embed=embed)
        except Exception:
            pass

    @app_commands.command(name="giveaway", description="[ADMIN] Mulai giveaway baru")
    @app_commands.describe(
        hadiah="Hadiah yang akan diberikan",
        durasi="Durasi giveaway (contoh: 10m, 2h, 1d)",
        pemenang="Jumlah pemenang (default: 1)",
    )
    async def giveaway(self, interaction: discord.Interaction, hadiah: str, durasi: str, pemenang: int = 1):
        if not is_staff(interaction):
            await interaction.response.send_message("❌ Admin only!", ephemeral=True)
            return

        seconds = parse_duration(durasi)
        if seconds <= 0:
            await interaction.response.send_message("❌ Format durasi salah! Contoh: `10m`, `2h`, `1d`", ephemeral=True)
            return
        if pemenang < 1:
            await interaction.response.send_message("❌ Jumlah pemenang minimal 1!", ephemeral=True)
            return

        end_time = datetime.now() + timedelta(seconds=seconds)
        embed = self._build_embed(hadiah, end_time, pemenang, interaction.user, participants=0)

        await interaction.response.send_message("✅ Giveaway dimulai!", ephemeral=True)
        msg = await interaction.channel.send(embed=embed)

        giveaway_data = {
            "prize": hadiah,
            "end_time": end_time,
            "winners": pemenang,
            "host_id": interaction.user.id,
            "channel_id": interaction.channel.id,
            "guild_id": interaction.guild.id,
            "participants": set(),
        }
        self.active_giveaways[msg.id] = giveaway_data

        # Simpan ke database
        await self.bot.db.save_giveaway(
            msg.id, interaction.channel.id, interaction.guild.id,
            hadiah, end_time, pemenang, interaction.user.id, set()
        )

        view = self._build_view(msg.id)
        await msg.edit(view=view)

        async def auto_end():
            await asyncio.sleep(seconds)
            if msg.id in self.active_giveaways:
                await self._end_giveaway(msg.id, interaction.channel.id, interaction.guild.id, hadiah, pemenang, interaction.user.id)

        self.bot.loop.create_task(auto_end())

    @app_commands.command(name="giveaway_end", description="[ADMIN] Akhiri giveaway lebih awal")
    @app_commands.describe(message_id="ID pesan giveaway")
    async def giveaway_end(self, interaction: discord.Interaction, message_id: str):
        if not is_staff(interaction):
            await interaction.response.send_message("❌ Admin only!", ephemeral=True)
            return

        msg_id = int(message_id)
        if msg_id not in self.active_giveaways:
            await interaction.response.send_message("❌ Giveaway tidak ditemukan!", ephemeral=True)
            return

        data = self.active_giveaways[msg_id]
        await interaction.response.send_message("✅ Mengakhiri giveaway...", ephemeral=True)
        await self._end_giveaway(msg_id, data["channel_id"], data["guild_id"], data["prize"], data["winners"], data["host_id"])

    @app_commands.command(name="giveaway_reroll", description="[ADMIN] Reroll pemenang giveaway")
    @app_commands.describe(message_id="ID pesan giveaway yang sudah selesai", channel="Channel tempat giveaway")
    async def giveaway_reroll(self, interaction: discord.Interaction, message_id: str, channel: discord.TextChannel = None):
        if not is_staff(interaction):
            await interaction.response.send_message("❌ Admin only!", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        try:
            target_channel = channel or interaction.channel
            msg = await target_channel.fetch_message(int(message_id))

            data = self.active_giveaways.get(int(message_id))
            if data and data.get("participants"):
                participants = list(data["participants"])
                winner_id = random.choice(participants)
                winner = interaction.guild.get_member(winner_id)
                if winner:
                    await target_channel.send(f"🎉 **REROLL!** Pemenang baru: {winner.mention}\nSelamat! Hubungi admin untuk klaim hadiah.")
                    await interaction.followup.send("✅ Reroll selesai!", ephemeral=True)
            else:
                await interaction.followup.send("❌ Data peserta tidak ditemukan. Reroll hanya bisa dilakukan saat giveaway masih aktif.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)

    @app_commands.command(name="giveaway_list", description="[ADMIN] Lihat giveaway yang sedang aktif")
    async def giveaway_list(self, interaction: discord.Interaction):
        if not is_staff(interaction):
            await interaction.response.send_message("❌ Admin only!", ephemeral=True)
            return

        if not self.active_giveaways:
            await interaction.response.send_message("📝 Tidak ada giveaway aktif.", ephemeral=True)
            return

        embed = discord.Embed(title="GIVEAWAY AKTIF", color=0x00BFFF)
        for msg_id, data in self.active_giveaways.items():
            embed.add_field(
                name=data["prize"],
                value=f"ID: `{msg_id}`\nBerakhir: <t:{int(data['end_time'].timestamp())}:R>\nPemenang: {data['winners']} orang\nPeserta: {len(data.get('participants', set()))}",
                inline=False,
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(GiveawayCog(bot))
