import asyncio
import random
import discord
from datetime import datetime
from discord import app_commands
from discord.ext import commands
from config import STAFF_ROLE_NAME


class AutoReact:

    def __init__(self):
        self.enabled_channels = {}
        self.default_emojis = ["❤️", "🔥", "🚀", "👍", "⭐", "🎉", "👏", "💯"]
        self._last_react = {}  # channel_id: timestamp, untuk cooldown

    async def add_reactions(self, message, emoji_list=None):
        if message.author.bot:
            return
        channel_id = message.channel.id
        now = datetime.now().timestamp()
        # Cooldown 3 detik per channel untuk hindari rate limit
        if now - self._last_react.get(channel_id, 0) < 3:
            return
        self._last_react[channel_id] = now
        if not emoji_list:
            emoji_list = list(self.default_emojis)
        await asyncio.sleep(random.uniform(1, 3))
        random.shuffle(emoji_list)
        for emoji in emoji_list[:10]:
            try:
                await message.add_reaction(emoji)
                await asyncio.sleep(random.uniform(0.5, 1))
            except Exception:
                continue


class ReactCog(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="setreact", description="[ADMIN] Set auto-react di channel ini (khusus admin)")
    @app_commands.describe(emojis="List emoji pisah spasi", disable="Matiin auto-react")
    async def set_react(
        self,
        interaction: discord.Interaction,
        emojis: str = None,
        disable: bool = False,
    ):
        if not self._is_staff(interaction):
            await interaction.response.send_message("❌ Admin only!", ephemeral=True)
            return

        channel_id = interaction.channel_id
        db = self.bot.db

        if disable:
            if channel_id in self.bot.auto_react.enabled_channels:
                del self.bot.auto_react.enabled_channels[channel_id]
                await db.delete_auto_react(channel_id)
                await interaction.response.send_message(
                    f"✅ Auto-react dimatikan di {interaction.channel.mention}"
                )
            else:
                await interaction.response.send_message(
                    "❌ Auto-react gak aktif di sini", ephemeral=True
                )
            return

        if not emojis:
            if channel_id in self.bot.auto_react.enabled_channels:
                emoji_list = self.bot.auto_react.enabled_channels[channel_id]
                await interaction.response.send_message(
                    f"📊 **Auto-react aktif**\nChannel: {interaction.channel.mention}\nEmoji: {' '.join(emoji_list)}"
                )
            else:
                await interaction.response.send_message(
                    "❌ Auto-react tidak aktif. Gunakan `/setreact ❤️ 🔥 🚀`"
                )
            return

        emoji_list = emojis.split()[:20]
        self.bot.auto_react.enabled_channels[channel_id] = emoji_list
        await db.save_auto_react(channel_id, emoji_list)
        await interaction.response.send_message(
            f"✅ **Auto-react diaktifkan!**\nChannel: {interaction.channel.mention}\nEmoji: {' '.join(emoji_list)}"
        )

    @app_commands.command(name="setreactall", description="[ADMIN] Set auto-react untuk SEMUA orang di channel ini")
    @app_commands.describe(emojis="List emoji pisah spasi", disable="Matiin auto-react")
    async def set_react_all(
        self,
        interaction: discord.Interaction,
        emojis: str = None,
        disable: bool = False,
    ):
        if not self._is_staff(interaction):
            await interaction.response.send_message("❌ Admin only!", ephemeral=True)
            return

        channel_id = interaction.channel_id
        db = self.bot.db

        if disable:
            if channel_id in self.bot.auto_react_all:
                del self.bot.auto_react_all[channel_id]
                await db.delete_auto_react_all(channel_id)
                await interaction.response.send_message(
                    f"✅ Auto-react all dimatikan di {interaction.channel.mention}"
                )
            else:
                await interaction.response.send_message(
                    "❌ Auto-react all gak aktif di sini", ephemeral=True
                )
            return

        if not emojis:
            if channel_id in self.bot.auto_react_all:
                emoji_list = self.bot.auto_react_all[channel_id]
                await interaction.response.send_message(
                    f"📊 **Auto-react all aktif**\nChannel: {interaction.channel.mention}\nEmoji: {' '.join(emoji_list)}"
                )
            else:
                await interaction.response.send_message(
                    "❌ Auto-react all tidak aktif. Gunakan `/setreactall ❤️ 🔥 🚀`"
                )
            return

        emoji_list = emojis.split()[:20]
        self.bot.auto_react_all[channel_id] = emoji_list
        await db.save_auto_react_all(channel_id, emoji_list)
        await interaction.response.send_message(
            f"✅ **Auto-react all diaktifkan!**\nChannel: {interaction.channel.mention}\nEmoji: {' '.join(emoji_list)}"
        )

    @app_commands.command(name="reactlist", description="[ADMIN] Lihat daftar channel auto-react")
    async def react_list(self, interaction: discord.Interaction):
        if not self._is_staff(interaction):
            await interaction.response.send_message("❌ Admin only!", ephemeral=True)
            return

        has_react = bool(self.bot.auto_react.enabled_channels)
        has_react_all = bool(self.bot.auto_react_all)

        if not has_react and not has_react_all:
            await interaction.response.send_message("📝 Belum ada channel dengan auto-react")
            return

        embed = discord.Embed(title="📊 AUTO-REACT ACTIVE CHANNELS", color=0x00BFFF)

        if has_react:
            embed.add_field(name="🔹 /setreact (Admin only)", value="​", inline=False)
            for ch_id, emojis in self.bot.auto_react.enabled_channels.items():
                channel = interaction.guild.get_channel(ch_id)
                ch_name = channel.mention if channel else f"Unknown ({ch_id})"
                embed.add_field(name=ch_name, value=f"Emoji: {' '.join(emojis)}", inline=False)

        if has_react_all:
            embed.add_field(name="🔸 /setreactall (Semua user)", value="​", inline=False)
            for ch_id, emojis in self.bot.auto_react_all.items():
                channel = interaction.guild.get_channel(ch_id)
                ch_name = channel.mention if channel else f"Unknown ({ch_id})"
                embed.add_field(name=ch_name, value=f"Emoji: {' '.join(emojis)}", inline=False)

        await interaction.response.send_message(embed=embed)

    def _is_staff(self, interaction: discord.Interaction) -> bool:
        staff_role = discord.utils.get(interaction.guild.roles, name=STAFF_ROLE_NAME)
        return staff_role in interaction.user.roles


async def setup(bot: commands.Bot):
    await bot.add_cog(ReactCog(bot))
