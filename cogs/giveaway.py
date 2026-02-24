import asyncio
import random
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta
from config import STAFF_ROLE_NAME
from utils import is_staff

GIVEAWAY_EMOJI = "🎉"


def parse_duration(duration_str: str) -> int:
    """Parse durasi: 10s, 5m, 2h, 1d → detik"""
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
        self.active_giveaways = {}  # message_id: giveaway_data

    def _build_embed(self, prize, end_time, winners, host, ended=False, winner_mentions=None):
        time_left = end_time - datetime.now()
        seconds = max(0, int(time_left.total_seconds()))

        if ended:
            color = 0x95a5a6
            status = "SELESAI"
        else:
            color = 0xFF6B6B
            status = f"Berakhir <t:{int(end_time.timestamp())}:R>"

        embed = discord.Embed(
            title=f"{GIVEAWAY_EMOJI} GIVEAWAY — {prize}",
            color=color,
            timestamp=end_time,
        )
        embed.add_field(name="Hadiah", value=prize, inline=True)
        embed.add_field(name="Pemenang", value=f"{winners} orang", inline=True)
        embed.add_field(name="Host", value=host.mention, inline=True)
        embed.add_field(name="Status", value=status, inline=False)

        if ended and winner_mentions:
            embed.add_field(name="Pemenang", value="\n".join(winner_mentions), inline=False)
            embed.description = f"Selamat kepada {', '.join(winner_mentions)}!"
        elif not ended:
            embed.description = f"React {GIVEAWAY_EMOJI} untuk ikutan!\nBerakhir: <t:{int(end_time.timestamp())}:F>"

        embed.set_footer(text="CELLYN STORE • Giveaway" + (" • Selesai" if ended else ""))
        return embed

    async def _end_giveaway(self, message_id, channel_id, guild_id, prize, winner_count, host_id):
        try:
            guild = self.bot.get_guild(guild_id)
            channel = guild.get_channel(channel_id)
            message = await channel.fetch_message(message_id)
            host = guild.get_member(host_id)

            # Ambil semua yang react
            reaction = discord.utils.get(message.reactions, emoji=GIVEAWAY_EMOJI)
            if not reaction:
                await channel.send("❌ Tidak ada yang ikut giveaway!")
                return

            users = [u async for u in reaction.users() if not u.bot]
            if not users:
                await channel.send("❌ Tidak ada peserta giveaway!")
                return

            actual_winners = min(winner_count, len(users))
            winners = random.sample(users, actual_winners)
            winner_mentions = [w.mention for w in winners]

            end_time = datetime.now()
            embed = self._build_embed(prize, end_time, winner_count, host, ended=True, winner_mentions=winner_mentions)
            await message.edit(embed=embed, view=None)

            await channel.send(
                f"{GIVEAWAY_EMOJI} **GIVEAWAY SELESAI!** {GIVEAWAY_EMOJI}\n"
                f"Hadiah: **{prize}**\n"
                f"Pemenang: {' '.join(winner_mentions)}\n"
                f"Selamat! Hubungi {host.mention if host else 'admin'} untuk klaim hadiah."
            )

            self.active_giveaways.pop(message_id, None)

            # Log ke backup-db
            backup_channel = discord.utils.get(guild.channels, name="backup-db")
            if backup_channel:
                log_embed = discord.Embed(
                    title="LOG GIVEAWAY SELESAI",
                    color=0x95a5a6,
                    timestamp=datetime.now(),
                )
                log_embed.add_field(name="Hadiah", value=prize, inline=True)
                log_embed.add_field(name="Peserta", value=str(len(users)), inline=True)
                log_embed.add_field(name="Pemenang", value="\n".join(winner_mentions), inline=False)
                log_embed.set_footer(text="CELLYN STORE • Giveaway Log")
                await backup_channel.send(embed=log_embed)

        except Exception as e:
            print(f"❌ Error end giveaway: {e}")

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
            await interaction.response.send_message(
                "❌ Format durasi salah! Contoh: `10s`, `5m`, `2h`, `1d`", ephemeral=True
            )
            return
        if pemenang < 1:
            await interaction.response.send_message("❌ Jumlah pemenang minimal 1!", ephemeral=True)
            return

        end_time = datetime.now() + timedelta(seconds=seconds)
        embed = self._build_embed(hadiah, end_time, pemenang, interaction.user)

        await interaction.response.send_message("✅ Giveaway dimulai!", ephemeral=True)
        msg = await interaction.channel.send(embed=embed)
        await msg.add_reaction(GIVEAWAY_EMOJI)

        self.active_giveaways[msg.id] = {
            "prize": hadiah,
            "end_time": end_time,
            "winners": pemenang,
            "host_id": interaction.user.id,
            "channel_id": interaction.channel.id,
            "guild_id": interaction.guild.id,
        }

        # Task untuk end otomatis
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
    @app_commands.describe(message_id="ID pesan giveaway yang sudah selesai")
    async def giveaway_reroll(self, interaction: discord.Interaction, message_id: str):
        if not is_staff(interaction):
            await interaction.response.send_message("❌ Admin only!", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        try:
            msg = await interaction.channel.fetch_message(int(message_id))
            reaction = discord.utils.get(msg.reactions, emoji=GIVEAWAY_EMOJI)
            if not reaction:
                await interaction.followup.send("❌ Tidak ada reaction di pesan ini!", ephemeral=True)
                return

            users = [u async for u in reaction.users() if not u.bot]
            if not users:
                await interaction.followup.send("❌ Tidak ada peserta!", ephemeral=True)
                return

            winner = random.choice(users)
            await interaction.channel.send(
                f"🎉 **REROLL!** Pemenang baru: {winner.mention}\nSelamat! Hubungi admin untuk klaim hadiah."
            )
            await interaction.followup.send("✅ Reroll selesai!", ephemeral=True)
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

        embed = discord.Embed(title="GIVEAWAY AKTIF", color=0xFF6B6B)
        for msg_id, data in self.active_giveaways.items():
            time_left = data["end_time"] - datetime.now()
            seconds = max(0, int(time_left.total_seconds()))
            embed.add_field(
                name=data["prize"],
                value=f"ID: `{msg_id}`\nBerakhir: <t:{int(data['end_time'].timestamp())}:R>\nPemenang: {data['winners']} orang",
                inline=False,
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(GiveawayCog(bot))
