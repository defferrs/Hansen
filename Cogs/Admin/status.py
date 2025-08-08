
import discord
from discord.ext import commands
from discord.commands import slash_command, Option
import json
import os
import asyncio

class StatusManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.status_file = "Cogs/Admin/data/bot_status.json"
        self.ensure_data_dir()
        
    def ensure_data_dir(self):
        """Ensure the data directory exists"""
        os.makedirs("Cogs/Admin/data", exist_ok=True)
        
    def load_status(self):
        """Load saved status from file"""
        try:
            if os.path.exists(self.status_file):
                with open(self.status_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading status: {e}")
        return {"type": "playing", "name": "Discord Bot", "url": None}
    
    def save_status(self, status_data):
        """Save status to file"""
        try:
            with open(self.status_file, 'w', encoding='utf-8') as f:
                json.dump(status_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving status: {e}")
    
    async def set_bot_status(self, status_type, name, url=None):
        """Set the bot's status"""
        try:
            if status_type == "playing":
                activity = discord.Game(name=name)
            elif status_type == "watching":
                activity = discord.Activity(type=discord.ActivityType.watching, name=name)
            elif status_type == "listening":
                activity = discord.Activity(type=discord.ActivityType.listening, name=name)
            elif status_type == "streaming":
                activity = discord.Streaming(name=name, url=url or "https://twitch.tv/discord")
            else:
                return False
                
            await self.bot.change_presence(activity=activity)
            
            # Save status
            status_data = {"type": status_type, "name": name, "url": url}
            self.save_status(status_data)
            return True
        except Exception as e:
            print(f"Error setting status: {e}")
            return False

    @commands.Cog.listener()
    async def on_ready(self):
        """Restore saved status when bot starts"""
        if self.bot.is_ready():
            await asyncio.sleep(2)  # Wait a bit for bot to fully initialize
            status_data = self.load_status()
            await self.set_bot_status(
                status_data["type"], 
                status_data["name"], 
                status_data.get("url")
            )
            print(f"✅ Status restored: {status_data['type']} {status_data['name']}")

    @slash_command(description="🎮 Set status bot ke 'Sedang Bermain'")
    async def set_playing(
        self, 
        ctx, 
        game: Option(str, "Nama game yang akan ditampilkan", required=True)
    ):
        """Set status bot menjadi sedang bermain game"""
        if not ctx.author.guild_permissions.administrator:
            embed = discord.Embed(
                title="❌ Akses Ditolak",
                description="Hanya administrator yang dapat mengubah status bot!",
                color=0xFF0000
            )
            await ctx.respond(embed=embed, ephemeral=True)
            return
        
        success = await self.set_bot_status("playing", game)
        
        if success:
            embed = discord.Embed(
                title="✅ Status Diperbarui",
                description=f"Bot sekarang sedang bermain: **{game}**",
                color=0x00FF00
            )
        else:
            embed = discord.Embed(
                title="❌ Error",
                description="Gagal memperbarui status bot",
                color=0xFF0000
            )
        
        await ctx.respond(embed=embed)

    @slash_command(description="👀 Set status bot ke 'Sedang Menonton'")
    async def set_watching(
        self, 
        ctx, 
        content: Option(str, "Apa yang sedang ditonton bot", required=True)
    ):
        """Set status bot menjadi sedang menonton sesuatu"""
        if not ctx.author.guild_permissions.administrator:
            embed = discord.Embed(
                title="❌ Akses Ditolak",
                description="Hanya administrator yang dapat mengubah status bot!",
                color=0xFF0000
            )
            await ctx.respond(embed=embed, ephemeral=True)
            return
        
        success = await self.set_bot_status("watching", content)
        
        if success:
            embed = discord.Embed(
                title="✅ Status Diperbarui",
                description=f"Bot sekarang sedang menonton: **{content}**",
                color=0x00FF00
            )
        else:
            embed = discord.Embed(
                title="❌ Error",
                description="Gagal memperbarui status bot",
                color=0xFF0000
            )
        
        await ctx.respond(embed=embed)

    @slash_command(description="🎵 Set status bot ke 'Sedang Mendengarkan'")
    async def set_listening(
        self, 
        ctx, 
        music: Option(str, "Apa yang sedang didengarkan bot", required=True)
    ):
        """Set status bot menjadi sedang mendengarkan musik"""
        if not ctx.author.guild_permissions.administrator:
            embed = discord.Embed(
                title="❌ Akses Ditolak",
                description="Hanya administrator yang dapat mengubah status bot!",
                color=0xFF0000
            )
            await ctx.respond(embed=embed, ephemeral=True)
            return
        
        success = await self.set_bot_status("listening", music)
        
        if success:
            embed = discord.Embed(
                title="✅ Status Diperbarui",
                description=f"Bot sekarang sedang mendengarkan: **{music}**",
                color=0x00FF00
            )
        else:
            embed = discord.Embed(
                title="❌ Error",
                description="Gagal memperbarui status bot",
                color=0xFF0000
            )
        
        await ctx.respond(embed=embed)

    @slash_command(description="📺 Set status bot ke 'Sedang Streaming'")
    async def set_streaming(
        self, 
        ctx, 
        title: Option(str, "Judul stream", required=True),
        url: Option(str, "URL stream (opsional)", required=False, default=None)
    ):
        """Set status bot menjadi sedang streaming"""
        if not ctx.author.guild_permissions.administrator:
            embed = discord.Embed(
                title="❌ Akses Ditolak",
                description="Hanya administrator yang dapat mengubah status bot!",
                color=0xFF0000
            )
            await ctx.respond(embed=embed, ephemeral=True)
            return
        
        stream_url = url or "https://twitch.tv/discord"
        success = await self.set_bot_status("streaming", title, stream_url)
        
        if success:
            embed = discord.Embed(
                title="✅ Status Diperbarui",
                description=f"Bot sekarang sedang streaming: **{title}**\nURL: {stream_url}",
                color=0x9146FF
            )
        else:
            embed = discord.Embed(
                title="❌ Error",
                description="Gagal memperbarui status bot",
                color=0xFF0000
            )
        
        await ctx.respond(embed=embed)

    @slash_command(description="📊 Lihat status bot saat ini")
    async def status_info(self, ctx):
        """Tampilkan informasi status bot saat ini"""
        status_data = self.load_status()
        
        embed = discord.Embed(
            title="🤖 Status Bot Saat Ini",
            color=0x00D4FF
        )
        
        status_type = status_data["type"].title()
        status_name = status_data["name"]
        
        embed.add_field(
            name="📱 Tipe Status",
            value=f"```{status_type}```",
            inline=True
        )
        
        embed.add_field(
            name="📝 Konten",
            value=f"```{status_name}```",
            inline=True
        )
        
        if status_data.get("url"):
            embed.add_field(
                name="🔗 URL",
                value=f"```{status_data['url']}```",
                inline=False
            )
        
        embed.add_field(
            name="⚙️ Perintah Tersedia",
            value="```\n/set_playing - Set status bermain\n/set_watching - Set status menonton\n/set_listening - Set status mendengarkan\n/set_streaming - Set status streaming```",
            inline=False
        )
        
        embed.set_footer(text="Hanya administrator yang dapat mengubah status bot")
        
        await ctx.respond(embed=embed)

    @slash_command(description="🔄 Reset status bot ke default")
    async def reset_status(self, ctx):
        """Reset status bot ke default"""
        if not ctx.author.guild_permissions.administrator:
            embed = discord.Embed(
                title="❌ Akses Ditolak",
                description="Hanya administrator yang dapat mengubah status bot!",
                color=0xFF0000
            )
            await ctx.respond(embed=embed, ephemeral=True)
            return
        
        success = await self.set_bot_status("playing", "Discord Bot")
        
        if success:
            embed = discord.Embed(
                title="✅ Status Direset",
                description="Status bot telah direset ke default",
                color=0x00FF00
            )
        else:
            embed = discord.Embed(
                title="❌ Error",
                description="Gagal mereset status bot",
                color=0xFF0000
            )
        
        await ctx.respond(embed=embed)

def setup(bot):
    bot.add_cog(StatusManager(bot))
    print("✅ StatusManager cog loaded")
