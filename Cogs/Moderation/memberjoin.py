
import discord
from discord.ext import commands
from discord.commands import slash_command, Option
import json
import os

class MemberJoin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.settings = {}
        self.load_settings()

    def load_settings(self):
        """Load member join settings from file"""
        try:
            file_path = "Cogs/Moderation/data/memberjoin_settings.json"
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    self.settings = json.load(f)
        except Exception as e:
            print(f"Error loading member join settings: {e}")
            self.settings = {}

    def save_settings(self):
        """Save member join settings to file"""
        try:
            os.makedirs("Cogs/Moderation/data", exist_ok=True)
            file_path = "Cogs/Moderation/data/memberjoin_settings.json"
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving member join settings: {e}")

    @slash_command(description="👋 Setup welcome message")
    async def welcome_setup(self, ctx, 
                           channel: Option(discord.TextChannel, "Channel untuk welcome message"),
                           message: Option(str, "Welcome message (gunakan {user} untuk mention user)")):
        """Setup welcome message untuk anggota baru"""
        
        if not ctx.author.guild_permissions.manage_guild:
            embed = discord.Embed(
                title="❌ Izin Ditolak",
                description="Anda tidak memiliki izin untuk mengatur server!",
                color=0xFF0000
            )
            await ctx.respond(embed=embed, ephemeral=True)
            return

        try:
            guild_id = str(ctx.guild.id)
            
            if guild_id not in self.settings:
                self.settings[guild_id] = {}

            self.settings[guild_id]["welcome"] = {
                "channel_id": channel.id,
                "message": message,
                "enabled": True
            }
            
            self.save_settings()

            embed = discord.Embed(
                title="👋 Welcome Message Setup",
                description="Welcome message berhasil diatur!",
                color=0x00FF00
            )
            embed.add_field(name="📍 Channel", value=channel.mention, inline=True)
            embed.add_field(name="💬 Message", value=message, inline=False)
            
            # Preview
            preview_message = message.replace("{user}", ctx.author.mention)
            embed.add_field(name="🔍 Preview", value=preview_message, inline=False)

            await ctx.respond(embed=embed)

        except Exception as e:
            embed = discord.Embed(
                title="❌ Error",
                description=f"Terjadi kesalahan: {str(e)}",
                color=0xFF0000
            )
            await ctx.respond(embed=embed, ephemeral=True)

    @slash_command(description="👋 Setup goodbye message")
    async def goodbye_setup(self, ctx, 
                           channel: Option(discord.TextChannel, "Channel untuk goodbye message"),
                           message: Option(str, "Goodbye message (gunakan {user} untuk nama user)")):
        """Setup goodbye message untuk anggota yang keluar"""
        
        if not ctx.author.guild_permissions.manage_guild:
            embed = discord.Embed(
                title="❌ Izin Ditolak",
                description="Anda tidak memiliki izin untuk mengatur server!",
                color=0xFF0000
            )
            await ctx.respond(embed=embed, ephemeral=True)
            return

        try:
            guild_id = str(ctx.guild.id)
            
            if guild_id not in self.settings:
                self.settings[guild_id] = {}

            self.settings[guild_id]["goodbye"] = {
                "channel_id": channel.id,
                "message": message,
                "enabled": True
            }
            
            self.save_settings()

            embed = discord.Embed(
                title="👋 Goodbye Message Setup",
                description="Goodbye message berhasil diatur!",
                color=0x00FF00
            )
            embed.add_field(name="📍 Channel", value=channel.mention, inline=True)
            embed.add_field(name="💬 Message", value=message, inline=False)
            
            # Preview
            preview_message = message.replace("{user}", ctx.author.name)
            embed.add_field(name="🔍 Preview", value=preview_message, inline=False)

            await ctx.respond(embed=embed)

        except Exception as e:
            embed = discord.Embed(
                title="❌ Error",
                description=f"Terjadi kesalahan: {str(e)}",
                color=0xFF0000
            )
            await ctx.respond(embed=embed, ephemeral=True)

    @slash_command(description="🎭 Setup auto role untuk anggota baru")
    async def auto_role_setup(self, ctx, role: Option(discord.Role, "Role yang akan otomatis diberikan ke anggota baru")):
        """Setup auto role untuk anggota baru"""
        
        if not ctx.author.guild_permissions.manage_guild:
            embed = discord.Embed(
                title="❌ Izin Ditolak",
                description="Anda tidak memiliki izin untuk mengatur server!",
                color=0xFF0000
            )
            await ctx.respond(embed=embed, ephemeral=True)
            return

        # Check role hierarchy
        if role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
            embed = discord.Embed(
                title="❌ Hierarki Role",
                description="Anda tidak dapat mengatur auto role untuk role yang lebih tinggi dari Anda!",
                color=0xFF0000
            )
            await ctx.respond(embed=embed, ephemeral=True)
            return

        if role >= ctx.guild.me.top_role:
            embed = discord.Embed(
                title="❌ Hierarki Bot",
                description="Bot tidak dapat memberikan role yang lebih tinggi dari role bot!",
                color=0xFF0000
            )
            await ctx.respond(embed=embed, ephemeral=True)
            return

        try:
            guild_id = str(ctx.guild.id)
            
            if guild_id not in self.settings:
                self.settings[guild_id] = {}

            self.settings[guild_id]["auto_role"] = {
                "role_id": role.id,
                "enabled": True
            }
            
            self.save_settings()

            embed = discord.Embed(
                title="🎭 Auto Role Setup",
                description="Auto role berhasil diatur!",
                color=0x00FF00
            )
            embed.add_field(name="🎭 Role", value=role.mention, inline=True)
            embed.add_field(name="📝 Info", value="Semua anggota baru akan otomatis mendapat role ini", inline=False)

            await ctx.respond(embed=embed)

        except Exception as e:
            embed = discord.Embed(
                title="❌ Error",
                description=f"Terjadi kesalahan: {str(e)}",
                color=0xFF0000
            )
            await ctx.respond(embed=embed, ephemeral=True)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Handle member join events"""
        guild_id = str(member.guild.id)
        
        if guild_id not in self.settings:
            return

        # Send welcome message
        if ("welcome" in self.settings[guild_id] and 
            self.settings[guild_id]["welcome"]["enabled"]):
            
            welcome_config = self.settings[guild_id]["welcome"]
            channel = member.guild.get_channel(welcome_config["channel_id"])
            
            if channel:
                try:
                    message = welcome_config["message"].replace("{user}", member.mention)
                    embed = discord.Embed(
                        title="👋 Selamat Datang!",
                        description=message,
                        color=0x00FF00
                    )
                    embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
                    embed.set_footer(text=f"Anggota #{member.guild.member_count}")
                    
                    await channel.send(embed=embed)
                except Exception as e:
                    print(f"Error sending welcome message: {e}")

        # Give auto role
        if ("auto_role" in self.settings[guild_id] and 
            self.settings[guild_id]["auto_role"]["enabled"]):
            
            auto_role_config = self.settings[guild_id]["auto_role"]
            role = member.guild.get_role(auto_role_config["role_id"])
            
            if role:
                try:
                    await member.add_roles(role, reason="Auto role for new member")
                except Exception as e:
                    print(f"Error giving auto role: {e}")

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """Handle member leave events"""
        guild_id = str(member.guild.id)
        
        if guild_id not in self.settings:
            return

        # Send goodbye message
        if ("goodbye" in self.settings[guild_id] and 
            self.settings[guild_id]["goodbye"]["enabled"]):
            
            goodbye_config = self.settings[guild_id]["goodbye"]
            channel = member.guild.get_channel(goodbye_config["channel_id"])
            
            if channel:
                try:
                    message = goodbye_config["message"].replace("{user}", member.name)
                    embed = discord.Embed(
                        title="👋 Selamat Tinggal",
                        description=message,
                        color=0xFF8C00
                    )
                    embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
                    embed.set_footer(text=f"Anggota tersisa: {member.guild.member_count}")
                    
                    await channel.send(embed=embed)
                except Exception as e:
                    print(f"Error sending goodbye message: {e}")

def setup(bot):
    bot.add_cog(MemberJoin(bot))
    print("✅ MemberJoin cog loaded successfully")
