
import discord
from discord.ext import commands
from discord.commands import slash_command

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @slash_command(description="📋 Tampilkan semua perintah bot")
    async def bantuan(self, ctx):
        """Tampilkan daftar lengkap perintah bot dengan kategori"""
        
        embed = discord.Embed(
            title="📋 Bantuan Bot Discord All-in-One",
            description="**Bot multifungsi dengan UI mobile-friendly dan fitur lengkap!**\n\n🌟 *Semua perintah menggunakan slash commands (/)*",
            color=0x00D4FF
        )
        
        # General Commands
        embed.add_field(
            name="🌟 **Umum**",
            value=(
                "`/ping` - Cek latency bot\n"
                "`/bantuan` - Tampilkan bantuan ini"
            ),
            inline=False
        )

        # Music Commands
        embed.add_field(
            name="🎵 **Musik**",
            value=(
                "`/play <lagu>` - Putar musik dari YouTube\n"
                "`/auto_play <lagu>` - Putar dengan auto-play\n"
                "`/queue` - Lihat antrian musik\n"
                "`/stop` - Hentikan musik\n"
                "`/remove <posisi>` - Hapus lagu dari antrian\n"
                "`/cleanup` - Bersihkan file download"
            ),
            inline=False
        )

        # Moderation Commands
        embed.add_field(
            name="🛡️ **Moderasi**",
            value=(
                "`/ban <user>` - Ban anggota\n"
                "`/kick <user>` - Kick anggota\n"
                "`/warn <user>` - Beri peringatan\n"
                "`/timeout <user>` - Timeout anggota\n"
                "`/clear <jumlah>` - Hapus pesan\n"
                "`/warnings <user>` - Lihat peringatan\n"
                "`/unban <user_id>` - Unban pengguna"
            ),
            inline=False
        )

        # Role Commands
        embed.add_field(
            name="👥 **Role Management**",
            value=(
                "`/addrole <user> <role>` - Tambah role\n"
                "`/removerole <user> <role>` - Hapus role\n"
                "`/add_reaction_role` - Setup reaction role\n"
                "`/remove_reaction_role` - Hapus reaction role\n"
                "`/list_reaction_roles` - List reaction roles"
            ),
            inline=False
        )

        # Search Commands
        embed.add_field(
            name="🔍 **Pencarian**",
            value="`/search <query>` - Cari di Google",
            inline=False
        )

        # Features
        embed.add_field(
            name="🚀 **Fitur Unggulan**",
            value=(
                "✅ **Auto-Play Musik** dengan rekomendasi\n"
                "✅ **Download & Stream** untuk kualitas terbaik\n"
                "✅ **Interactive Controls** dengan tombol\n"
                "✅ **Mobile Optimized** untuk semua perangkat\n"
                "✅ **Auto Cleanup** file temporary\n"
                "✅ **Voice Reconnection** otomatis"
            ),
            inline=False
        )

        embed.set_footer(
            text="🎯 Bot siap melayani • Dioptimalkan untuk mobile • Created with py-cord",
            icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None
        )
        
        embed.set_thumbnail(url=self.bot.user.avatar.url if self.bot.user.avatar else None)

        await ctx.respond(embed=embed)

def setup(bot):
    bot.add_cog(Help(bot))
    print("✅ Help cog loaded successfully")
