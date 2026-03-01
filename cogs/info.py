import discord
from discord import app_commands
from discord.ext import commands
from config import STAFF_ROLE_NAME, STORE_NAME, DANA_NUMBER, BCA_NUMBER, STORE_THUMBNAIL, STORE_BANNER
from utils import is_staff

TIKTOK_URL = "https://www.tiktok.com/@panggilan437"
INFO_CHANNEL_NAME = "📒┃panduan"


async def _get_qris_url(bot):
    try:
        async with bot.db.db.execute("SELECT value FROM settings WHERE key = 'qris_url'") as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None
    except Exception:
        return None


async def _get_items_by_category(bot):
    try:
        async with bot.db.db.execute("SELECT category, name FROM items ORDER BY category, name") as cursor:
            rows = await cursor.fetchall()
        result = {}
        for category, name in rows:
            result.setdefault(category, []).append(name)
        return result
    except Exception:
        return {}


async def build_embeds(bot, guild):
    embeds = []

    e1 = discord.Embed(
        title=f"\U0001f3ea {STORE_NAME}",
        description=(
            f"**{STORE_NAME} — Toko Digital Premium Terpercaya**\n\n"
            f"Kami menyediakan berbagai produk digital berkualitas dengan harga terjangkau "
            f"dan pelayanan yang ramah. Setiap transaksi dijamin aman dan transparan.\n\n"
            f"**Keunggulan kami:**\n"
            f"- Proses cepat dan responsif\n"
            f"- Harga kompetitif mengikuti pasar\n"
            f"- Bukti serah terima tersedia di channel dokumentasi\n"
            f"- Testimoni buyer nyata, bukan palsu\n\n"
            f"**Produk yang tersedia:**\n"
            f"- Gamepass & item Roblox\n"
            f"- Discord Nitro & Boost\n"
            f"- Red Finger & item lainnya\n\n"
            f"**Jam layanan:** Setiap hari, selama admin online\n"
            f"**Kontak admin:** Mention atau DM langsung di server\n\n"
            f"\U0001f4f1 **TikTok:** [Kunjungi TikTok kami]({TIKTOK_URL}) — Kami sering live di sana!"
        ),
        color=0x00BFFF,
    )
    e1.set_thumbnail(url=STORE_THUMBNAIL)
    e1.set_image(url=STORE_BANNER)
    e1.set_footer(text=f"{STORE_NAME} \u2022 Toko Digital Premium")
    embeds.append(e1)

    e2 = discord.Embed(
        title="\U0001f6d2 Cara Order",
        description=(
            "Ikuti langkah-langkah berikut untuk melakukan pembelian:\n\n"
            "**1.** Lihat produk yang tersedia di channel catalog\n"
            "**2.** Klik tombol **BUY** sesuai kategori produk\n"
            "**3.** Pilih item yang ingin dibeli dari dropdown\n"
            "**4.** Tiket order akan terbuka secara otomatis\n"
            "**5.** Admin akan menyapa dan mengkonfirmasi item beserta harga terkini\n"
            "**6.** Diskusikan detail pembelian dengan admin di dalam tiket\n"
            "**7.** Setelah sepakat, pilih metode pembayaran yang diinginkan\n"
            "**8.** Lakukan transfer sesuai nominal dan kirim bukti pembayaran\n"
            "**9.** Klik tombol **PAID** setelah transfer\n"
            "**10.** Admin memverifikasi pembayaran dan proses serah terima item dimulai\n"
            "**11.** Setelah item diterima, tinggalkan testimoni di channel yang tersedia\n"
            "**12.** Transaksi selesai!\n\n"
            "\u26a0\ufe0f **Perlu diketahui:**\n"
            "- Harga dapat berbeda dari yang tertera di catalog karena mengikuti rate pasar\n"
            "- Pastikan tanya admin terlebih dahulu sebelum membuka tiket\n"
            "- Buka tiket hanya jika sudah yakin ingin membeli"
        ),
        color=0x00BFFF,
    )
    e2.set_footer(text=f"{STORE_NAME} \u2022 Cara Order")
    embeds.append(e2)

    qris_url = await _get_qris_url(bot)
    e3 = discord.Embed(
        title="\U0001f4b3 Metode Pembayaran",
        description=(
            "Kami menerima pembayaran melalui metode berikut:\n\n"
            f"**DANA**\n`{DANA_NUMBER}`\n\n"
            f"**BCA**\n`{BCA_NUMBER}`\n\n"
            "**QRIS**\nScan QR Code di bawah\n\n"
            "\u26a0\ufe0f Pastikan nominal transfer sesuai dengan yang disepakati bersama admin."
        ),
        color=0x00BFFF,
    )
    if qris_url:
        e3.set_image(url=qris_url)
    e3.set_footer(text=f"{STORE_NAME} \u2022 Metode Pembayaran")
    embeds.append(e3)

    items_by_cat = await _get_items_by_category(bot)
    desc = ""
    if items_by_cat:
        for cat, items in items_by_cat.items():
            desc += f"**{cat}**\n"
            for item in items:
                desc += f"- {item}\n"
            desc += "\n"
    else:
        desc = "Belum ada produk yang terdaftar."
    desc += "\n\U0001f4a1 **Harga menyesuaikan rate pasar, tanya admin untuk harga terkini.**"

    e4 = discord.Embed(
        title="\U0001f4e6 Daftar Produk",
        description=desc,
        color=0x00BFFF,
    )
    e4.set_footer(text=f"{STORE_NAME} \u2022 Daftar Produk")
    embeds.append(e4)

    e5 = discord.Embed(
        title="\u2753 FAQ — Pertanyaan yang Sering Ditanya",
        description=(
            "**Apakah toko ini aman?**\n"
            "Ya. Setiap transaksi didokumentasikan dan tersedia bukti serah terima di channel khusus. "
            "Testimoni buyer juga bisa dilihat di channel testimoni.\n\n"
            "**Apakah item yang saya inginkan tersedia?**\n"
            "Kami tidak menggunakan sistem stok otomatis. Silakan tanya langsung ke admin "
            "untuk memastikan ketersediaan item sebelum membuka tiket.\n\n"
            "**Berapa lama proses transaksi?**\n"
            "Tergantung ketersediaan admin. Kami berusaha seresponsif mungkin. "
            "Proses serah terima item biasanya berlangsung singkat setelah pembayaran dikonfirmasi.\n\n"
            "**Apakah harga bisa berubah?**\n"
            "Ya. Harga produk mengikuti rate pasar yang dapat berubah sewaktu-waktu. "
            "Harga final disepakati bersama admin di dalam tiket.\n\n"
            "**Bagaimana jika terjadi masalah?**\n"
            "Hubungi admin langsung di server. Kami berkomitmen menyelesaikan setiap masalah "
            "dengan transparan dan bertanggung jawab.\n\n"
            "**Apakah ada refund?**\n"
            "Kebijakan refund ditentukan case by case oleh admin. "
            "Hubungi admin jika ada kendala pasca transaksi."
        ),
        color=0x00BFFF,
    )
    e5.set_footer(text=f"{STORE_NAME} \u2022 FAQ")
    embeds.append(e5)

    return embeds


class InfoCog(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="setupinfo", description="[ADMIN] Post semua info toko ke channel panduan")
    async def setup_info(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        if not is_staff(interaction):
            await interaction.followup.send("\u274c Admin only!", ephemeral=True)
            return
        channel = discord.utils.get(interaction.guild.text_channels, name=INFO_CHANNEL_NAME)
        if not channel:
            await interaction.followup.send(f"\u274c Channel **#{INFO_CHANNEL_NAME}** tidak ditemukan. Buat dulu channelnya.", ephemeral=True)
            return
        try:
            await channel.purge(limit=100)
        except Exception:
            pass
        embeds = await build_embeds(self.bot, interaction.guild)
        for embed in embeds:
            await channel.send(embed=embed)
        await interaction.followup.send(f"\u2705 Info toko berhasil dipost ke {channel.mention}", ephemeral=True)

    @app_commands.command(name="refreshinfo", description="[ADMIN] Refresh info toko di channel panduan")
    async def refresh_info(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        if not is_staff(interaction):
            await interaction.followup.send("\u274c Admin only!", ephemeral=True)
            return
        channel = discord.utils.get(interaction.guild.text_channels, name=INFO_CHANNEL_NAME)
        if not channel:
            await interaction.followup.send(f"\u274c Channel **#{INFO_CHANNEL_NAME}** tidak ditemukan.", ephemeral=True)
            return
        try:
            await channel.purge(limit=100)
        except Exception:
            pass
        embeds = await build_embeds(self.bot, interaction.guild)
        for embed in embeds:
            await channel.send(embed=embed)
        await interaction.followup.send(f"\u2705 Info toko berhasil direfresh di {channel.mention}", ephemeral=True)


async def setup(bot):
    await bot.add_cog(InfoCog(bot))
