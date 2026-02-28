import os
import asyncio
import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from config import STAFF_ROLE_NAME, STORE_NAME
from utils import is_staff

WELCOME_GIF_PATH = "data/welcome.gif"
BOOST_GIF_PATH = "data/boost.gif"


class WelcomeCog(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._welcome_channel_id = None
        self._has_gif = os.path.exists(WELCOME_GIF_PATH)
        self._has_boost_gif = os.path.exists(BOOST_GIF_PATH)

    async def cog_load(self):
        self.bot.loop.create_task(self._load_settings())

    async def _load_settings(self):
        await self.bot.wait_until_ready()
        try:
            ch_id = await self.bot.db.get_setting("welcome_channel_id")
            if ch_id:
                self._welcome_channel_id = int(ch_id)
            self._has_gif = os.path.exists(WELCOME_GIF_PATH)
            self._has_boost_gif = os.path.exists(BOOST_GIF_PATH)
        except Exception as e:
            print(f"[Welcome] Load settings error: {e}")

    async def _download_gif(self, url: str, path: str) -> bool:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        os.makedirs("data", exist_ok=True)
                        with open(path, "wb") as f:
                            f.write(await resp.read())
                        return True
            return False
        except Exception as e:
            print(f"[Welcome] Download error: {e}")
            return False

    @app_commands.command(name="setwelcome", description="[ADMIN] Set channel dan GIF welcome/boost")
    @app_commands.describe(
        action="channel / gif / boostgif / test / testboost / off",
        channel="Channel untuk pesan welcome (jika action=channel)",
        gif="File GIF background (jika action=gif atau boostgif)"
    )
    async def set_welcome(
        self,
        interaction: discord.Interaction,
        action: str,
        channel: discord.TextChannel = None,
        gif: discord.Attachment = None
    ):
        await interaction.response.defer(ephemeral=True)

        if not is_staff(interaction):
            await interaction.followup.send("❌ Admin only!", ephemeral=True)
            return

        action = action.lower().strip()

        if action == "channel":
            if not channel:
                await interaction.followup.send(
                    "Sertakan channel. Contoh: `/setwelcome action:channel channel:#welcome`",
                    ephemeral=True
                )
                return
            self._welcome_channel_id = channel.id
            await self.bot.db.set_setting("welcome_channel_id", str(channel.id))
            await interaction.followup.send(
                f"Welcome channel diset ke {channel.mention}", ephemeral=True
            )

        elif action == "gif":
            if not gif or not gif.filename.lower().endswith(".gif"):
                await interaction.followup.send("Sertakan file .gif untuk welcome.", ephemeral=True)
                return
            ok = await self._download_gif(gif.url, WELCOME_GIF_PATH)
            if ok:
                self._has_gif = True
                await interaction.followup.send(f"GIF welcome berhasil diupload! ({gif.filename})", ephemeral=True)
            else:
                await interaction.followup.send("Gagal upload GIF.", ephemeral=True)

        elif action == "boostgif":
            if not gif or not gif.filename.lower().endswith(".gif"):
                await interaction.followup.send("Sertakan file .gif untuk boost.", ephemeral=True)
                return
            ok = await self._download_gif(gif.url, BOOST_GIF_PATH)
            if ok:
                self._has_boost_gif = True
                await interaction.followup.send(f"GIF boost berhasil diupload! ({gif.filename})", ephemeral=True)
            else:
                await interaction.followup.send("Gagal upload GIF boost.", ephemeral=True)

        elif action == "test":
            await self._send_welcome(interaction.user, test=True, interaction=interaction)

        elif action == "testboost":
            await self._send_boost(interaction.user, test=True, interaction=interaction)

        elif action == "off":
            self._welcome_channel_id = None
            await self.bot.db.set_setting("welcome_channel_id", "")
            await interaction.followup.send("Welcome message dinonaktifkan.", ephemeral=True)

        else:
            await interaction.followup.send(
                "Action tidak dikenal. Gunakan: `channel`, `gif`, `boostgif`, `test`, `testboost`, `off`",
                ephemeral=True
            )

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        await self._send_welcome(member)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        if not self._welcome_channel_id:
            return
        channel = self.bot.get_channel(self._welcome_channel_id)
        if not channel:
            return
        member_count = sum(1 for m in member.guild.members if not m.bot)
        embed = discord.Embed(
            title="Member Keluar",
            description=(
                f"**{member.name}** telah meninggalkan server.\n\n"
                f"Total member saat ini: **{member_count}**"
            ),
            color=0x808080,
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"{STORE_NAME} • {member.guild.name}")
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if not self._welcome_channel_id:
            return
        if before.premium_since is None and after.premium_since is not None:
            await self._send_boost(after)

    async def _send_welcome(self, member: discord.Member, test=False, interaction=None):
        if not self._welcome_channel_id:
            if interaction:
                await interaction.followup.send(
                    "Welcome channel belum diset. Gunakan `/setwelcome action:channel`.", ephemeral=True
                )
            return
        channel = self.bot.get_channel(self._welcome_channel_id)
        if not channel:
            return
        guild = member.guild
        member_count = sum(1 for m in guild.members if not m.bot)
        embed = discord.Embed(
            title=f"Selamat Datang di {guild.name}!",
            description=(
                f"Halo, {member.mention}!\n\n"
                f"Kami dengan hangat menyambut kehadiran Anda di **{guild.name}**.\n"
                f"Silakan baca peraturan server dan nikmati komunitas kami.\n\n"
                f"Anda adalah member ke-**{member_count}**."
            ),
            color=0x00BFFF,
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"{STORE_NAME} • {guild.name}")
        if self._has_gif:
            file = discord.File(WELCOME_GIF_PATH, filename="welcome.gif")
            embed.set_image(url="attachment://welcome.gif")
            if test and interaction:
                await interaction.followup.send(embed=embed, file=file)
            else:
                await channel.send(embed=embed, file=file)
        else:
            if test and interaction:
                await interaction.followup.send(
                    "GIF welcome belum diupload. Gunakan `/setwelcome action:gif`.\nPreview embed:",
                    embed=embed
                )
            else:
                await channel.send(embed=embed)

    async def _send_boost(self, member: discord.Member, test=False, interaction=None):
        if not self._welcome_channel_id:
            if interaction:
                await interaction.followup.send(
                    "Welcome channel belum diset. Gunakan `/setwelcome action:channel`.", ephemeral=True
                )
            return
        channel = self.bot.get_channel(self._welcome_channel_id)
        if not channel:
            return
        embed = discord.Embed(
            title="Server Boost!",
            description=(
                f"**{member.mention}** baru saja melakukan boost pada server ini!\n\n"
                f"Terima kasih atas dukungan Anda kepada **{member.guild.name}**."
            ),
            color=0xFF73FA,
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"{STORE_NAME} • {member.guild.name}")
        if self._has_boost_gif:
            file = discord.File(BOOST_GIF_PATH, filename="boost.gif")
            embed.set_image(url="attachment://boost.gif")
            if test and interaction:
                await interaction.followup.send(embed=embed, file=file)
            else:
                await channel.send(embed=embed, file=file)
        else:
            if test and interaction:
                await interaction.followup.send(
                    "GIF boost belum diupload. Gunakan `/setwelcome action:boostgif`.\nPreview embed:",
                    embed=embed
                )
            else:
                await channel.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(WelcomeCog(bot))
